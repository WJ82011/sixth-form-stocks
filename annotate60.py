"""Chart annotations anchored to an instrument, a price and a timestamp."""
import contextlib
import hashlib
import json
import time

METHOD = 'chart-annotation-v6.0'
KINDS = ('level', 'trend', 'note', 'measure')


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS annotate60(
        id TEXT PRIMARY KEY, symbol TEXT NOT NULL, body TEXT NOT NULL, updated_at INTEGER NOT NULL)''')
    con.execute('''CREATE TABLE IF NOT EXISTS annotate60_undo(
        symbol TEXT PRIMARY KEY, stack TEXT NOT NULL)''')


def measure(price_a, price_b, time_a, time_b):
    price_a, price_b = float(price_a), float(price_b)
    time_a, time_b = int(time_a), int(time_b)
    if price_a <= 0 or price_b <= 0:
        raise ValueError('Both recorded prices have to be above zero.')
    if time_b < time_a:
        raise ValueError('The second point is earlier than the first.')
    elapsed = time_b - time_a
    days = elapsed / 86400000
    return {
        'changePct': round((price_b - price_a) / price_a * 100, 4),
        'elapsedMs': elapsed,
        'elapsedDays': round(days, 4),
        'label': f'{(price_b - price_a) / price_a * 100:.2f}% over {days:.2f} days',
    }


def _clean(symbol, item):
    kind = str(item.get('kind') or '')
    if kind not in KINDS:
        raise ValueError('Choose a price level, a trend line, a note or a measurement.')
    body = {'kind': kind, 'symbol': symbol}
    if kind == 'level':
        body['price'] = float(item['price'])
        body['label'] = str(item.get('label') or 'Price level')[:80]
        if body['price'] <= 0:
            raise ValueError('A price level has to be above zero.')
    elif kind == 'note':
        body['t'] = int(item['t'])
        body['price'] = float(item['price'])
        body['text'] = str(item.get('text') or '').strip()[:180]
        if not body['text'] or body['price'] <= 0:
            raise ValueError('A note needs a recorded price and some wording.')
    else:
        body['t1'] = int(item['t1'])
        body['p1'] = float(item['p1'])
        body['t2'] = int(item['t2'])
        body['p2'] = float(item['p2'])
        if kind == 'measure':
            body.update(measure(body['p1'], body['p2'], body['t1'], body['t2']))
    raw = json.dumps(body, sort_keys=True)
    body['id'] = hashlib.sha256(raw.encode()).hexdigest()[:12]
    return body


def for_symbol(g, symbol):
    symbol = str(symbol or '').upper()
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        rows = con.execute('SELECT body FROM annotate60 WHERE symbol=? ORDER BY updated_at', (symbol,)).fetchall()
    return [json.loads(row[0]) for row in rows]


def replace(g, symbol, items, now_ms):
    symbol = g['valid_symbol'](symbol)
    cleaned = [_clean(symbol, item) for item in (items or [])][:40]
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        current = [json.loads(row[0]) for row in con.execute('SELECT body FROM annotate60 WHERE symbol=? ORDER BY updated_at', (symbol,))]
        stack_row = con.execute('SELECT stack FROM annotate60_undo WHERE symbol=?', (symbol,)).fetchone()
        stack = json.loads(stack_row[0]) if stack_row else []
        stack.append(current)
        con.execute('INSERT INTO annotate60_undo(symbol,stack) VALUES(?,?) ON CONFLICT(symbol) DO UPDATE SET stack=excluded.stack',
                    (symbol, json.dumps(stack[-20:])))
        con.execute('DELETE FROM annotate60 WHERE symbol=?', (symbol,))
        for item in cleaned:
            con.execute('INSERT INTO annotate60(id,symbol,body,updated_at) VALUES(?,?,?,?)',
                        (item['id'], symbol, json.dumps(item), int(now_ms)))
    return {'symbol': symbol, 'items': cleaned, 'method': METHOD}


def undo(g, symbol):
    symbol = g['valid_symbol'](symbol)
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        row = con.execute('SELECT stack FROM annotate60_undo WHERE symbol=?', (symbol,)).fetchone()
        stack = json.loads(row[0]) if row else []
        if not stack:
            raise ValueError('Nothing to undo.')
        previous = stack.pop()
        con.execute('INSERT INTO annotate60_undo(symbol,stack) VALUES(?,?) ON CONFLICT(symbol) DO UPDATE SET stack=excluded.stack',
                    (symbol, json.dumps(stack)))
        con.execute('DELETE FROM annotate60 WHERE symbol=?', (symbol,))
        now = int(time.time() * 1000)
        for item in previous:
            con.execute('INSERT INTO annotate60(id,symbol,body,updated_at) VALUES(?,?,?,?)',
                        (item['id'], symbol, json.dumps(item), now))
    return {'symbol': symbol, 'items': previous, 'notice': 'Restored the previous annotations.'}


def remove(g, symbol, ident):
    items = [item for item in for_symbol(g, symbol) if item.get('id') != ident]
    return replace(g, symbol, items, int(time.time() * 1000))
