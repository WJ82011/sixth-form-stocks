"""Research journal entries. Original evidence stays with the idea; a later edit keeps the earlier wording."""
import contextlib
import datetime as dt
import math
import re

import events42

SYMBOL = re.compile(r'^[A-Z0-9][A-Z0-9.\-:_]{0,23}$')
STATUSES = {'open', 'supported', 'challenged', 'unresolved'}
ORIGINS = {'chart', 'move', 'alert', 'answer', 'compare', 'scenario', 'strategy', 'scan', 'stress', 'practice'}
TEXT = {
    'title': 160, 'expectation': 4000, 'reasons': 4000, 'changeMind': 4000, 'learned': 4000,
}
NY = events42.NY


def _text(value, limit):
    return str(value or '')[:limit]


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    if not 0 < value <= 1e9:
        return None
    return float(value)


def _day(value):
    text = str(value or '')[:10]
    try:
        dt.date.fromisoformat(text)
    except ValueError:
        return ''
    return text


def _link(row):
    if not isinstance(row, dict):
        return None
    url = str(row.get('url') or row.get('source') or '')
    if not (url.startswith('http://') or url.startswith('https://')):
        return None
    return {'title': _text(row.get('title'), 180), 'url': url[:300]}


def _evidence(raw):
    raw = raw if isinstance(raw, dict) else {}
    links = []
    for row in (raw.get('links') or [])[:8]:
        link = _link(row)
        if link:
            links.append(link)
    return {
        'startPrice': _number(raw.get('startPrice')),
        'endPrice': _number(raw.get('endPrice')),
        'priceTs': int(raw['priceTs']) if isinstance(raw.get('priceTs'), int) and not isinstance(raw.get('priceTs'), bool) and raw['priceTs'] > 0 else None,
        'source': _text(raw.get('source'), 300),
        'capturedAt': int(raw['capturedAt']) if isinstance(raw.get('capturedAt'), int) and not isinstance(raw.get('capturedAt'), bool) and raw['capturedAt'] > 0 else None,
        'answer': _text(raw.get('answer'), 2000),
        'basis': _text(raw.get('basis'), 300),
        'qualification': _text(raw.get('qualification'), 500),
        'links': links,
    }


def _revision(raw):
    if not isinstance(raw, dict):
        return None
    stamp = raw.get('at')
    if isinstance(stamp, bool) or not isinstance(stamp, int) or stamp <= 0:
        return None
    status = raw.get('status') if raw.get('status') in STATUSES else 'open'
    return {'at': stamp, 'status': status, **{key: _text(raw.get(key), limit) for key, limit in TEXT.items() if key != 'title'}, 'reviewDate': _day(raw.get('reviewDate'))}


def clean_entry(raw):
    if not isinstance(raw, dict):
        return None
    symbol = str(raw.get('symbol') or '').strip().upper()
    if not SYMBOL.fullmatch(symbol):
        return None
    ident = str(raw.get('id') or '')
    if not re.fullmatch(r'[a-f0-9]{8,32}', ident):
        return None
    created = raw.get('createdAt')
    updated = raw.get('updatedAt')
    if any(isinstance(stamp, bool) or not isinstance(stamp, int) or stamp <= 0 for stamp in (created, updated)):
        return None
    history = []
    for row in (raw.get('history') or [])[:20]:
        revision = _revision(row)
        if revision:
            history.append(revision)
    status = raw.get('status') if raw.get('status') in STATUSES else 'open'
    origin = raw.get('origin') if raw.get('origin') in ORIGINS else 'chart'
    return {
        'id': ident, 'symbol': symbol, 'title': _text(raw.get('title'), 160) or symbol,
        'createdAt': created, 'updatedAt': updated, 'status': status, 'origin': origin,
        'range': _text(raw.get('range'), 12), 'start': _day(raw.get('start')), 'end': _day(raw.get('end')),
        'reviewDate': _day(raw.get('reviewDate')),
        'expectation': _text(raw.get('expectation'), 4000), 'reasons': _text(raw.get('reasons'), 4000),
        'changeMind': _text(raw.get('changeMind'), 4000), 'learned': _text(raw.get('learned'), 4000),
        'evidence': _evidence(raw.get('evidence')), 'history': history,
    }


def normalise(raw):
    if not isinstance(raw, list):
        return []
    found = []
    seen = set()
    for item in raw[:200]:
        clean = clean_entry(item)
        if not clean or clean['id'] in seen:
            continue
        seen.add(clean['id'])
        found.append(clean)
    return found


def merge(local, remote):
    """Keep every entry. A newer edit wins the wording, and the earlier evidence stays."""
    chosen = {}
    order = []
    for item in normalise(remote) + normalise(local):
        previous = chosen.get(item['id'])
        if previous is None:
            chosen[item['id']] = item
            order.append(item['id'])
            continue
        newer = item if item['updatedAt'] >= previous['updatedAt'] else previous
        older = previous if newer is item else item
        newer = dict(newer)
        newer['evidence'] = older['evidence']
        newer['createdAt'] = min(older['createdAt'], newer['createdAt'])
        history = older['history'] + newer['history']
        newer['history'] = history[-20:]
        chosen[item['id']] = newer
    return [chosen[ident] for ident in order][:200]


def latest(g, symbol, now_ms=None):
    symbol = g['valid_symbol'](symbol)
    now_ms = int(g['time'].time() * 1000) if now_ms is None else int(now_ms)
    try:
        with contextlib.closing(g['db_connection']()) as con:
            rows = con.execute('SELECT ts_ms,c FROM massive_daily_bars WHERE symbol=? ORDER BY ts_ms', (symbol,)).fetchall()
    except Exception:
        rows = []
    chosen = None
    for ts, price in rows:
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            continue
        day = dt.datetime.fromtimestamp(ts / 1000, NY).date()
        close = events42.close_on(day) if events42.is_session(day) else None
        if close is None or int(close.timestamp() * 1000) > now_ms:
            continue
        chosen = (day.isoformat(), float(price))
    if chosen is None:
        return {'symbol': symbol, 'price': None, 'date': '', 'source': 'Massive · saved split-adjusted daily close. Read from this Mac.', 'reason': 'No saved close is available for a later comparison.'}
    return {'symbol': symbol, 'price': chosen[1], 'date': chosen[0], 'source': 'Massive · saved split-adjusted daily close. Read from this Mac.', 'reason': ''}


def export_text(entries):
    lines = ['Market Desk research journal', '']
    for entry in normalise(entries):
        evidence = entry['evidence']
        lines.extend([
            entry['title'],
            f"{entry['symbol']} · {entry['status']} · saved {dt.datetime.fromtimestamp(entry['createdAt']/1000, NY).strftime('%Y-%m-%d %H:%M %Z')}",
            f"Dates: {entry['start'] or 'not set'} to {entry['end'] or 'not set'} · chart {entry['range'] or 'not set'}",
            f"What I think might happen: {entry['expectation'] or 'Not written.'}",
            f"Reasons: {entry['reasons'] or 'Not written.'}",
            f"What would change my mind: {entry['changeMind'] or 'Not written.'}",
            f"Review date: {entry['reviewDate'] or 'Not set'}",
            f"What I learned: {entry['learned'] or 'Not written.'}",
            f"Original prices: {evidence['startPrice'] if evidence['startPrice'] is not None else 'not saved'} to {evidence['endPrice'] if evidence['endPrice'] is not None else 'not saved'}",
            f"Source: {evidence['source'] or 'Not recorded.'}",
        ])
        for link in evidence['links']:
            lines.append(f"Link: {link['title']} · {link['url']}")
        if entry['history']:
            lines.append(f"Earlier versions kept: {len(entry['history'])}")
        lines.extend(['', '------------------------------------------------------------', ''])
    return '\n'.join(lines).strip() + '\n'
