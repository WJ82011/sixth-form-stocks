"""Coinbase Exchange public USD spot data with a bounded offline cache."""
import contextlib
import datetime as dt
import json
import math
import threading
import urllib.error
import urllib.parse
import urllib.request

import coverage41

# Provider display_name is the market id. base_currency and quote_currency were
# read from Coinbase Exchange on 13 Nov 2026. All nine were online USD markets.
PRODUCTS = {
    'BTC-USD': 'Bitcoin', 'ETH-USD': 'Ethereum', 'SOL-USD': 'Solana', 'XRP-USD': 'XRP',
    'DOGE-USD': 'Dogecoin', 'ADA-USD': 'Cardano', 'LINK-USD': 'Chainlink',
    'AVAX-USD': 'Avalanche', 'LTC-USD': 'Litecoin',
}
MARKETS = {product: {'id': product, 'name': name, 'base': product.split('-')[0], 'quote': 'USD',
                     'providerName': product, 'exchange': 'Coinbase Exchange', 'timezone': 'UTC'}
           for product, name in PRODUCTS.items()}
UNAVAILABLE = []
RANGES = {'1H': (60, 60), '1D': (300, 288), '1W': (3600, 168),
          '1M': (21600, 120), '1Y': (86400, 365)}
BASE = 'https://api.exchange.coinbase.com/products/'
LOCK = threading.Lock()
RETRY_AFTER = {}


def init(con):
    con.execute("""CREATE TABLE IF NOT EXISTS crypto38_cache
        (product TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
         fetched_at INTEGER NOT NULL, PRIMARY KEY(product,kind))""")
    con.execute("""CREATE TABLE IF NOT EXISTS crypto38_follow
        (product TEXT PRIMARY KEY, added_at INTEGER NOT NULL)""")


def read(g, product, kind):
    with contextlib.closing(g['db_connection']()) as con:
        row = con.execute('SELECT payload,fetched_at FROM crypto38_cache WHERE product=? AND kind=?',
                          (product, kind)).fetchone()
    if not row:
        return None
    try:
        data = json.loads(row[0])
        return {**data, 'fetchedAt': row[1]}
    except (ValueError, TypeError):
        return None


def public_get(g, product, path, params=None):
    url = BASE + product + '/' + path
    if params:
        url += '?' + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={
        'Accept': 'application/json', 'User-Agent': 'MarketDesk-Reborn/3.8'})
    tls, _ = g['verified_tls_context']()
    with urllib.request.urlopen(request, timeout=7, context=tls) as response:
        data = response.read(250001)
    if len(data) > 250000:
        raise ValueError('Oversized Coinbase response')
    return json.loads(data)


def normalise_candles(rows, start, end, step):
    if not isinstance(rows, list) or len(rows) > 300:
        raise ValueError('Invalid candle collection')
    points = {}
    for row in rows:
        if not isinstance(row, list) or len(row) != 6:
            continue
        stamp, low, high, opening, close, volume = row
        if type(stamp) is not int or stamp % step or not start <= stamp < end:
            continue
        if any(type(n) not in (int, float) or not math.isfinite(n)
               for n in (low, high, opening, close, volume)):
            continue
        if not (0 < low <= opening <= high <= 1e9 and low <= close <= high and volume > 0):
            continue
        if stamp in points and points[stamp] != close:
            raise ValueError('Conflicting candles at the same timestamp')
        points[stamp] = close
    return [{'t': (stamp + step) * 1000, 'p': points[stamp]} for stamp in sorted(points)]


def iso(seconds):
    return dt.datetime.fromtimestamp(seconds, dt.timezone.utc).isoformat()


def fetch_chart(g, product, kind, now):
    step, count = RANGES[kind]
    end = (now // 1000 // step) * step
    start = end - count * step
    points = []
    # One year needs two requests. Keep each below the 300-candle ceiling.
    for left in range(start, end, step * 290):
        right = min(end, left + step * 290)
        rows = public_get(g, product, 'candles', {
            'start': iso(left), 'end': iso(right), 'granularity': step})
        points.extend(normalise_candles(rows, left, right, step))
    if not points:
        raise ValueError('No usable completed candles')
    return {'points': points, 'start': start * 1000, 'end': end * 1000,
            'interval': step * 1000, 'expected': count}


def normalise_trade(row, now):
    if not isinstance(row, dict) or isinstance(row.get('price'), bool):
        raise ValueError('Invalid ticker')
    price = float(row['price'])
    at = dt.datetime.fromisoformat(row['time'].replace('Z', '+00:00'))
    if at.tzinfo is None:
        raise ValueError('Missing ticker timezone')
    stamp = int(at.timestamp() * 1000)
    if not (0 < price <= 1e9 and 1230768000000 <= stamp <= now + 5000):
        raise ValueError('Unusable ticker price or timestamp')
    return {'price': price, 'time': stamp}


def packet(g, product, kind):
    if product not in PRODUCTS or (kind != 'quote' and kind not in RANGES):
        raise ValueError('Choose a supported Coinbase USD market and chart period.')
    key = (product, kind)
    ttl = 8 if kind == 'quote' else max(30, min(900, RANGES[kind][0]))
    with LOCK:
        now = int(g['time'].time() * 1000)
        saved = read(g, product, kind)
        age = now - saved['fetchedAt'] if saved else None
        if saved and 0 <= age < ttl * 1000 and not _incomplete(kind, saved):
            return finish(kind, product, {**saved, 'status': 'cached', 'product': product})
        if now < RETRY_AFTER.get(key, 0):
            return finish(kind, product, {**(saved or {}), 'status': 'saved' if saved else 'unavailable', 'product': product})
        try:
            if kind == 'quote':
                ticker = public_get(g, product, 'ticker')
                data = normalise_trade(ticker, int(g['time'].time() * 1000))
                if saved and data['time'] < saved['time']:
                    return finish(kind, product, {**saved, 'status': 'saved', 'product': product})
            else:
                data = fetch_chart(g, product, kind, now)
            stamp = int(g['time'].time() * 1000)
            with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
                con.execute('INSERT OR REPLACE INTO crypto38_cache VALUES(?,?,?,?)',
                            (product, kind, json.dumps(data, allow_nan=False), stamp))
            RETRY_AFTER.pop(key, None)
            result = finish(kind, product, {**data, 'fetchedAt': stamp, 'status': 'ok', 'product': product})
            if kind == 'quote':
                _alert(g, product, result, stamp)
            return result
        except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as error:
            delay = 60 if isinstance(error, urllib.error.HTTPError) and error.code == 429 else 20
            RETRY_AFTER[key] = now + delay * 1000
            return finish(kind, product, {**(saved or {}), 'status': 'saved' if saved else 'unavailable', 'product': product})


def _incomplete(kind, saved):
    if kind == 'quote' or not saved or not saved.get('points'):
        return False
    points = saved.get('points') or []
    expected = saved.get('expected') or 0
    if expected and len(points) < expected:
        return True
    interval = saved.get('interval') or 0
    ordered = sorted(points, key=lambda row: row.get('t', 0))
    return any(right['t'] - left['t'] > interval * 1.5 for left, right in zip(ordered, ordered[1:])) if interval else False


def _alert(g, product, row, now):
    import price_alerts
    try:
        with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
            price_alerts.init(con)
            price_alerts.observe(con, product, int(row['time']), row['price'], 'coinbase_ticker', int(now))
    except (OSError, ValueError, KeyError, TypeError):
        return


def follow(g, products, now_ms):
    chosen = []
    for product in products or []:
        if product in PRODUCTS and product not in chosen:
            chosen.append(product)
    if len(chosen) > len(PRODUCTS):
        raise ValueError('Follow the supported USD markets only.')
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('DELETE FROM crypto38_follow')
        con.executemany('INSERT INTO crypto38_follow VALUES(?,?)', [(product, int(now_ms)) for product in chosen])
    return {'followed': chosen}


def followed(g):
    try:
        with contextlib.closing(g['db_connection']()) as con:
            init(con)
            rows = con.execute('SELECT product FROM crypto38_follow ORDER BY added_at').fetchall()
    except (OSError, TypeError, KeyError):
        return []
    return [row[0] for row in rows if row[0] in PRODUCTS]


def rotation(g):
    loved = followed(g)
    return loved + [product for product in PRODUCTS if product not in loved]


def _change(saved):
    points = (saved or {}).get('points') or []
    if len(points) < 2 or points[0].get('p') in (None, 0):
        return None
    return (points[-1]['p'] / points[0]['p'] - 1) * 100


def board(g):
    rows = []
    for product, name in PRODUCTS.items():
        quote = read(g, product, 'quote')
        day = read(g, product, '1D')
        week = read(g, product, '1W')
        chart = finish('1D', product, day) if day else {}
        rows.append({
            'product': product, 'name': name, **MARKETS[product],
            'price': (quote or {}).get('price'), 'time': (quote or {}).get('time'),
            'quoteStatus': (quote or {}).get('status') or 'not saved',
            'change24h': _change(day), 'change7d': _change(week),
            'coverage': chart.get('coverage'),
        })
    return {'exchange': 'Coinbase Exchange', 'quote': 'USD', 'timezone': 'UTC',
            'trading': '24 hours, seven days. Candles are labelled in UTC, not the New York equity calendar.',
            'unavailable': UNAVAILABLE, 'rows': rows, 'followed': followed(g)}


def match_move(points, threshold):
    """Compare the last two completed candles. Crypto is not filtered by equity sessions."""
    if len(points) < 2 or not 0 < threshold <= 100:
        return None
    change = (points[-1]['p'] / points[-2]['p'] - 1) * 100
    if abs(change) < threshold:
        return None
    return {'changePct': change, 'threshold': threshold, 'timezone': 'UTC',
            'start': points[-2]['t'], 'end': points[-1]['t'], 'source': 'Coinbase completed candles'}


def utc_change(points):
    """Percent change between the first and last completed candle. Dates are UTC."""
    if len(points) < 2:
        raise ValueError('Two completed candles are required.')
    start = dt.datetime.fromtimestamp(points[0]['t'] / 1000, dt.timezone.utc)
    end = dt.datetime.fromtimestamp(points[-1]['t'] / 1000, dt.timezone.utc)
    return {'changePct': (points[-1]['p'] / points[0]['p'] - 1) * 100,
            'start': start.isoformat(), 'end': end.isoformat(), 'timezone': 'UTC',
            'sessions': 'Crypto candles are not limited to equity sessions.'}


def finish(kind, product, row):
    if kind != 'quote':
        row['coverage'] = coverage41.crypto(row, product)
    return row
