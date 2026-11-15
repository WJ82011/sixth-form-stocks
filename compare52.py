"""Saved comparison of up to four directory companies from local records."""
import contextlib
import json
import math
import re

import events42
import financials
import market37

SOURCE = 'Massive split-adjusted daily close'
IDENT = re.compile(r'^[a-f0-9]{16}$')


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS compare52(
        id TEXT PRIMARY KEY, title TEXT NOT NULL, symbols TEXT NOT NULL, start_day TEXT NOT NULL,
        end_day TEXT NOT NULL, body TEXT NOT NULL, created_at INTEGER NOT NULL)''')


def _symbols(g, raw):
    if isinstance(raw, str):
        raw = [part for part in raw.split(',') if part.strip()]
    chosen = []
    for item in raw or []:
        symbol = g['valid_symbol'](item)
        if not g['ai_catalog_entry'](symbol):
            raise ValueError(symbol + ' is not in the supported directory.')
        if symbol not in chosen:
            chosen.append(symbol)
    if not 2 <= len(chosen) <= 4:
        raise ValueError('Choose two, three or four different directory companies.')
    return chosen


def _closes(g, symbol):
    with contextlib.closing(g['db_connection']()) as con:
        rows = con.execute('SELECT ts_ms,c FROM massive_daily_bars WHERE symbol=? ORDER BY ts_ms', (symbol,)).fetchall()
    found = {}
    for stamp, price in rows:
        if not isinstance(price, (int, float)) or isinstance(price, bool) or not math.isfinite(price) or price <= 0:
            continue
        day = market37.dt.datetime.fromtimestamp(stamp / 1000, market37.NY).date().isoformat()
        found[day] = float(price)
    return found


def _session(day):
    try:
        date = market37.dt.date.fromisoformat(day)
    except ValueError:
        return False
    return date.weekday() < 5 and date not in market37.holidays(date.year)


def _match_periods(reports):
    if not reports:
        return False, []
    common = []
    for period in reports[0].get('annual') or []:
        matched = [period]
        for report in reports[1:]:
            candidates = [row for row in report.get('annual') or []
                          if abs((financials.day(row['start']) - financials.day(period['start'])).days) <= 7
                          and abs((financials.day(row['end']) - financials.day(period['end'])).days) <= 7
                          and abs(row['durationDays'] - period['durationDays']) <= 14]
            if len(candidates) != 1:
                break
            matched.append(candidates[0])
        if len(matched) == len(reports):
            common.append(matched)
    aligned = bool(common)
    selected = common[-1] if common else [((report.get('annual') or [None])[-1]) for report in reports]
    return aligned, selected


def _fact(period, key):
    metrics = (period or {}).get('metrics') or {}
    fact = metrics.get(key) or {}
    return fact if 'value' in fact else None


def _financials(g, symbols):
    reports = []
    for symbol in symbols:
        try:
            report = g['sec_saved'](symbol) or {}
        except Exception:
            report = {}
        report = {**report, 'symbol': symbol}
        reports.append(report)
    aligned, periods = _match_periods(reports)
    rows = []
    currencies = set()
    for report, period in zip(reports, periods):
        currency = (period or {}).get('currency') or report.get('unit') or ''
        if currency:
            currencies.add(currency)
        revenue = _fact(period, 'revenue')
        cash = _fact(period, 'cash')
        growth = (period or {}).get('revenueGrowthPct')
        margin = (period or {}).get('netMarginPct')
        filing = ''
        for key in ('revenue', 'profit', 'cash'):
            fact = _fact(period, key)
            if fact and fact.get('url'):
                filing = fact['url']
                break
        rows.append({
            'symbol': report.get('symbol'), 'name': report.get('name') or '',
            'start': (period or {}).get('start') or '', 'end': (period or {}).get('end') or '',
            'currency': currency or 'not recorded', 'revenueGrowthPct': growth, 'netMarginPct': margin,
            'operatingMarginPct': None,
            'operatingMarginNote': 'Operating income is not in the saved SEC facts, so operating margin was not calculated.',
            'cash': cash.get('value') if cash else None, 'debt': (period or {}).get('longTermDebt'),
            'debtScope': (period or {}).get('debtScope') or '', 'filing': filing,
            'revenueTag': (revenue or {}).get('tag') or '', 'available': bool(period),
        })
    ends = [financials.day(row['end']) for row in rows if row['end']]
    far = bool(ends) and (max(ends) - min(ends)).days > 45
    if not any(row['available'] for row in rows):
        basis = 'No supported annual SEC statement is saved for these companies. No financial figure was invented.'
    elif aligned and not far:
        basis = 'The latest saved annual periods match within seven days. Revenue tags can still differ, so read each filing.'
    else:
        basis = 'The saved fiscal periods do not cover the same months. Figures are shown with their own dates and are not ranked as one period.'
    if len(currencies) > 1 or (currencies and currencies != {'USD'}):
        basis += ' Cash and debt use more than one currency or a currency other than US dollars, so those amounts are not ranked.'
    return {'aligned': aligned and not far, 'basis': basis, 'rows': rows, 'notice': financials.NOTICE}


def _events(g, symbol, start, end):
    saved = events42.load(g, symbol) or {}
    rows = events42.dedupe([*(saved.get('events') or []), *events42.local_items(g, symbol)])
    chosen = []
    for row in rows:
        if row['date'] < start or row['date'] > end:
            continue
        chosen.append({
            'symbol': symbol, 'title': row['title'], 'date': row['date'], 'kindLabel': row.get('kindLabel') or '',
            'publishedAt': row.get('publishedAt'), 'timeLabel': row.get('timeLabel') or row['date'],
            'timing': row.get('timing') or 'date', 'source': row.get('source') or '',
            'timingNote': 'Publication time saved.' if row.get('timing') == 'timestamp' else 'The publication time was not saved. This mark uses the date only.',
        })
        if len(chosen) == 8:
            break
    return chosen


def build(g, symbols, start='', end=''):
    symbols = _symbols(g, symbols)
    series = {symbol: _closes(g, symbol) for symbol in symbols}
    catalog = {row['symbol']: row for row in market37.directory(g)}
    shared = set.intersection(*(set(points) for points in series.values())) if series else set()
    if start:
        shared = {day for day in shared if day >= start[:10]}
    if end:
        shared = {day for day in shared if day <= end[:10]}
    dates = sorted(shared)
    latest = {symbol: (max(points) if points else '') for symbol, points in series.items()}
    if len(dates) < 2:
        return {'status': 'insufficient', 'symbols': symbols, 'dates': dates, 'rows': [
            {'symbol': symbol, 'latestDate': latest[symbol], 'currency': (catalog.get(symbol) or {}).get('currency') or 'USD', 'savedCloses': len(series[symbol])}
            for symbol in symbols], 'events': [], 'financials': _financials(g, symbols),
            'notice': 'At least two completed sessions saved for every company are needed. Missing dates stay missing.'}
    first, last = dates[0], dates[-1]
    expected = []
    cursor = market37.dt.date.fromisoformat(first)
    stop = market37.dt.date.fromisoformat(last)
    while cursor <= stop:
        if _session(cursor.isoformat()):
            expected.append(cursor.isoformat())
        cursor += market37.dt.timedelta(days=1)
    rows = []
    events = []
    for symbol in symbols:
        points = series[symbol]
        base = points[first]
        plotted = []
        split = ''
        previous = None
        for day in dates:
            price = points[day]
            if previous and previous > 0 and abs(math.log(price / previous)) > 0.7:
                split = 'A one-day move in the saved closes is large enough to review as a split or a bad print. Prices were not rewritten.'
            previous = price
            plotted.append({'date': day, 'price': price, 'index': price / base * 100})
        missing = [day for day in expected if day not in points]
        entry = catalog.get(symbol) or {}
        rows.append({
            'symbol': symbol, 'name': entry.get('name') or symbol, 'currency': entry.get('currency') or 'USD',
            'latestDate': latest[symbol], 'latestPrice': points.get(latest[symbol]), 'source': SOURCE,
            'adjusted': True, 'adjustment': SOURCE, 'startPrice': base, 'endPrice': points[last],
            'indexEnd': plotted[-1]['index'], 'returnPct': (points[last] / base - 1) * 100,
            'missing': missing[:12], 'missingCount': len(missing), 'splitNote': split, 'points': plotted,
        })
        events.extend(_events(g, symbol, first, last))
    currencies = {row['currency'] for row in rows}
    notice = 'Each company starts at 100 on ' + first + '. Only completed sessions saved for every company are plotted.'
    notice += ' Listing currencies: ' + ', '.join(sorted(currencies)) + '.'
    notice += ' Prices were not converted between currencies.' if currencies != {'USD'} else ' These directory listings are priced in US dollars. This is not a total-return chart.'
    return {'status': 'ok', 'symbols': symbols, 'start': first, 'end': last, 'dates': dates, 'rows': rows,
            'events': events, 'financials': _financials(g, symbols), 'notice': notice}


def answer(g, question, symbols, start='', end=''):
    built = build(g, symbols, start, end)
    text = str(question or '').lower()
    if built['status'] != 'ok':
        return built['notice'], {**built, 'sampleSize': len(built.get('dates') or []), 'qualification': built['notice']}
    if 'margin' in text:
        books = built['financials']
        parts = []
        for row in books['rows']:
            if row['netMarginPct'] is None:
                parts.append(row['symbol'] + ' has no saved net profit margin for a supported annual period.')
            else:
                parts.append(row['symbol'] + ' net profit margin ' + format(row['netMarginPct'], '.2f') + '% for ' + row['start'] + ' to ' + row['end'] + ' (' + row['currency'] + ').')
        sentence = 'Operating margin was not calculated. ' + books['rows'][0]['operatingMarginNote'] + ' ' + ' '.join(parts) + ' ' + books['basis']
        return sentence, {**built, 'sampleSize': len(built['dates']), 'qualification': books['basis'], 'source': 'Saved SEC annual facts on this Mac.'}
    ranked = sorted(built['rows'], key=lambda row: row['indexEnd'], reverse=True)
    leader = ranked[0]
    tied = [row['symbol'] for row in ranked if math.isclose(row['indexEnd'], leader['indexEnd'], abs_tol=1e-9)]
    sentence = ', '.join(tied) + ' finished highest at ' + format(leader['indexEnd'], '.2f') + ' from ' + built['start'] + ' to ' + built['end'] + ', a saved-close change of ' + format(leader['returnPct'], '.2f') + '%.'
    sentence += ' Every company uses the same ' + str(len(built['dates'])) + ' completed sessions, starting at 100.'
    gaps = [row['symbol'] + ' is missing ' + str(row['missingCount']) + ' sessions inside this span.' for row in built['rows'] if row['missingCount']]
    splits = [row['symbol'] + ': ' + row['splitNote'] for row in built['rows'] if row['splitNote']]
    if gaps:
        sentence += ' ' + ' '.join(gaps)
    if splits:
        sentence += ' ' + ' '.join(splits)
    return sentence, {**built, 'sampleSize': len(built['dates']), 'startPrice': 100, 'endPrice': leader['indexEnd'],
                      'qualification': built['notice'], 'source': SOURCE, 'gaps': gaps + splits}


def save(g, body, now_ms):
    built = build(g, body.get('symbols'), str(body.get('start') or ''), str(body.get('end') or ''))
    if built['status'] != 'ok':
        raise ValueError(built['notice'])
    title = str(body.get('title') or ' · '.join(built['symbols']))[:160]
    ident = __import__('secrets').token_hex(8)
    payload = {**built, 'savedAt': int(now_ms), 'title': title}
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('INSERT INTO compare52 VALUES(?,?,?,?,?,?,?)', (
            ident, title, ','.join(built['symbols']), built['start'], built['end'], json.dumps(payload, allow_nan=False), int(now_ms)))
        con.execute('DELETE FROM compare52 WHERE id NOT IN (SELECT id FROM compare52 ORDER BY created_at DESC LIMIT 40)')
    return {'id': ident, 'saved': payload}


def read(g, ident, now_ms):
    if not IDENT.fullmatch(str(ident or '')):
        raise ValueError('Choose a saved comparison.')
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        row = con.execute('SELECT body FROM compare52 WHERE id=?', (ident,)).fetchone()
    if not row:
        raise ValueError('That comparison is not saved on this Mac.')
    saved = json.loads(row[0])
    fresh = build(g, saved['symbols'], saved['start'], saved['end'])
    return {'saved': saved, 'fresh': fresh, 'openedAt': int(now_ms),
            'notice': 'The saved comparison keeps the records from when it was stored. The updated view reads the prices and statements saved now.'}


def listed(g):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        rows = con.execute('SELECT id,title,symbols,start_day,end_day,created_at FROM compare52 ORDER BY created_at DESC LIMIT 40').fetchall()
    return [{'id': row[0], 'title': row[1], 'symbols': row[2], 'start': row[3], 'end': row[4], 'createdAt': row[5]} for row in rows]
