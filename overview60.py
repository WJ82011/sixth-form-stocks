"""A coverage overview of saved equity sessions and saved crypto days. They stay separate."""
import contextlib
import datetime as dt
import json
import math
from pathlib import Path

import events42

METHOD = 'market-overview-v6.0'
UNUSUAL = 3.0
DAY = 86400000


def _return(start, end):
    if start <= 0 or end <= 0:
        return None
    if abs(math.log(end / start)) > 0.7:
        return 'split'
    return (end - start) / start * 100


def _categories():
    path = Path(__file__).with_name('ai_catalog.json')
    try:
        rows = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return {row.get('symbol'): row.get('category') or 'Sector not recorded' for row in rows}


def _equity(g, now_ms, categories):
    now = dt.datetime.fromtimestamp(now_ms / 1000, events42.NY)
    books = {}
    try:
        with contextlib.closing(g['db_connection']()) as con:
            symbols = [row[0] for row in con.execute('SELECT DISTINCT symbol FROM massive_daily_bars ORDER BY symbol')]
            for symbol in symbols[:250]:
                rows = con.execute('SELECT ts_ms,c FROM massive_daily_bars WHERE symbol=? ORDER BY ts_ms DESC LIMIT 16', (symbol,)).fetchall()
                by_day = {}
                for stamp, price in rows:
                    if isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0:
                        continue
                    day = dt.datetime.fromtimestamp(stamp / 1000, events42.NY).date()
                    if events42.is_session(day) and day not in by_day:
                        by_day[day] = float(price)
                if by_day:
                    books[symbol] = by_day
    except Exception:
        books = {}
    completed = []
    for book in books.values():
        for day in book:
            close = events42.close_on(day)
            if close is not None and close <= now and day not in completed:
                completed.append(day)
    if not completed:
        return {'calendar': 'New York sessions', 'evaluated': 0, 'included': 0, 'advancing': 0, 'declining': 0,
                'unchanged': 0, 'excluded': [], 'sectors': [], 'unusual': [], 'companies': [],
                'notice': 'No completed saved equity session is available.'}
    end = max(completed)
    start = events42.previous_session(end)
    excluded, companies = [], []
    for symbol, book in books.items():
        if start not in book or end not in book:
            excluded.append({'symbol': symbol, 'reason': 'missing-close'})
            continue
        change = _return(book[start], book[end])
        if change == 'split':
            excluded.append({'symbol': symbol, 'reason': 'split-sized'})
            continue
        companies.append({'symbol': symbol, 'changePct': round(change, 4), 'start': book[start], 'end': book[end],
                          'sector': categories.get(symbol) or 'Sector not recorded'})
    sectors = {}
    for row in companies:
        sectors.setdefault(row['sector'], []).append(row['changePct'])
    sector_rows = [{'name': name, 'count': len(values), 'changePct': round(sum(values) / len(values), 4)}
                   for name, values in sectors.items() if len(values) >= 2]
    return {
        'calendar': 'New York sessions', 'start': start.isoformat(), 'end': end.isoformat(),
        'evaluated': len(books), 'included': len(companies),
        'advancing': sum(1 for row in companies if row['changePct'] > 0),
        'declining': sum(1 for row in companies if row['changePct'] < 0),
        'unchanged': sum(1 for row in companies if row['changePct'] == 0),
        'excluded': excluded, 'companies': companies,
        'sectors': sector_rows,
        'unusual': [row for row in companies if abs(row['changePct']) >= UNUSUAL],
        'thresholdPct': UNUSUAL,
        'notice': 'Equal-weight sector moves use included companies only. A move of at least 3% is listed as unusual. It is not a historical percentile.',
    }


def _crypto(g, now_ms):
    books = {}
    try:
        with contextlib.closing(g['db_connection']()) as con:
            rows = con.execute('SELECT product,ts_ms,price FROM crypto57_candles WHERE interval_ms=?', (DAY,)).fetchall()
        for product, stamp, price in rows:
            if not isinstance(price, (int, float)) or isinstance(price, bool) or price <= 0 or stamp > now_ms:
                continue
            day = dt.datetime.fromtimestamp(stamp / 1000, dt.timezone.utc).date()
            books.setdefault(product, {})[day] = float(price)
    except Exception:
        books = {}
    if not books:
        return {'calendar': 'UTC days', 'evaluated': 0, 'included': 0, 'advancing': 0, 'declining': 0,
                'excluded': [], 'companies': [], 'notice': 'No saved Coinbase daily candles are available.'}
    end = max(day for book in books.values() for day in book)
    start = end - dt.timedelta(days=1)
    excluded, companies = [], []
    for product, book in books.items():
        if start not in book or end not in book:
            excluded.append({'symbol': product, 'reason': 'missing-close'})
            continue
        change = _return(book[start], book[end])
        if change == 'split':
            excluded.append({'symbol': product, 'reason': 'split-sized'})
            continue
        companies.append({'symbol': product, 'changePct': round(change, 4), 'start': book[start], 'end': book[end]})
    return {
        'calendar': 'UTC days', 'start': start.isoformat(), 'end': end.isoformat(),
        'evaluated': len(books), 'included': len(companies),
        'advancing': sum(1 for row in companies if row['changePct'] > 0),
        'declining': sum(1 for row in companies if row['changePct'] < 0),
        'excluded': excluded, 'companies': companies,
        'notice': 'Crypto uses consecutive UTC dates, including weekends. It is not mixed into the equity counts.',
    }


def build(g, now_ms=None, categories=None):
    now_ms = int(g['time'].time() * 1000) if now_ms is None else int(now_ms)
    categories = _categories() if categories is None else categories
    equity = _equity(g, now_ms, categories)
    crypto = _crypto(g, now_ms)
    return {'method': METHOD, 'equity': equity, 'crypto': crypto,
            'notice': 'Stocks use completed New York sessions. Crypto uses UTC days. Counts are saved records only.'}
