"""Coinbase Exchange public USD spot data with a bounded offline cache."""
import contextlib
import datetime as dt
import json
import math
import threading
import urllib.error
import urllib.parse
import urllib.request

PRODUCTS = {'BTC-USD': 'Bitcoin', 'ETH-USD': 'Ethereum'}
RANGES = {'1H': (60, 60), '1D': (300, 288), '1W': (3600, 168),
          '1M': (21600, 120), '1Y': (86400, 365)}
BASE = 'https://api.exchange.coinbase.com/products/'
LOCK = threading.Lock()
RETRY_AFTER = {}


def init(con):
    con.execute("""CREATE TABLE IF NOT EXISTS crypto38_cache
        (product TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL,
         fetched_at INTEGER NOT NULL, PRIMARY KEY(product,kind))""")


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
        raise ValueError('Choose Bitcoin or Ethereum and a supported chart period.')
    key = (product, kind)
    ttl = 8 if kind == 'quote' else max(30, min(900, RANGES[kind][0]))
    with LOCK:
        now = int(g['time'].time() * 1000)
        saved = read(g, product, kind)
        age = now - saved['fetchedAt'] if saved else None
        if saved and 0 <= age < ttl * 1000:
            return {**saved, 'status': 'cached', 'product': product}
        if now < RETRY_AFTER.get(key, 0):
            return {**(saved or {}), 'status': 'saved' if saved else 'unavailable', 'product': product}
        try:
            if kind == 'quote':
                ticker = public_get(g, product, 'ticker')
                data = normalise_trade(ticker, int(g['time'].time() * 1000))
                if saved and data['time'] < saved['time']:
                    return {**saved, 'status': 'saved', 'product': product}
            else:
                data = fetch_chart(g, product, kind, now)
            stamp = int(g['time'].time() * 1000)
            with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
                con.execute('INSERT OR REPLACE INTO crypto38_cache VALUES(?,?,?,?)',
                            (product, kind, json.dumps(data, allow_nan=False), stamp))
            RETRY_AFTER.pop(key, None)
            return {**data, 'fetchedAt': stamp, 'status': 'ok', 'product': product}
        except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError) as error:
            delay = 60 if isinstance(error, urllib.error.HTTPError) and error.code == 429 else 20
            RETRY_AFTER[key] = now + delay * 1000
            return {**(saved or {}), 'status': 'saved' if saved else 'unavailable', 'product': product}
