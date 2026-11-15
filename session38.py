"""A separately labelled replay of a completed New York date's equity minute bars."""
import contextlib
import datetime as dt
import json
import threading

import coverage41
import market37

LOCK = threading.Lock()


def init(con):
    con.execute("""CREATE TABLE IF NOT EXISTS session38_cache
        (symbol TEXT NOT NULL, day TEXT NOT NULL, payload TEXT NOT NULL,
         fetched_at INTEGER NOT NULL, PRIMARY KEY(symbol,day))""")


def read(g, symbol, latest):
    with contextlib.closing(g['db_connection']()) as con:
        row = con.execute("""SELECT day,payload FROM session38_cache
            WHERE symbol=? AND day<=? ORDER BY day DESC LIMIT 1""", (symbol, latest)).fetchone()
    if row:
        try:
            return label(g, {'day': row[0], 'points': json.loads(row[1]), 'symbol': symbol, 'status': 'saved'})
        except ValueError:
            pass
    return None


def packet(g, raw_symbol):
    symbol = g['valid_symbol'](raw_symbol)
    if not g['ai_catalog_entry'](symbol):
        raise ValueError('Choose a company in the US stock directory.')
    day = market37.sessions(market37.today(g), 1)[0]
    with LOCK:
        saved = read(g, symbol, day)
        if saved and saved['day'] == day:
            return saved
        if not g['get_massive_key']():
            return saved or {'status': 'unavailable', 'notice': 'Add a Massive key in Settings to load past equity minutes.'}
        date = dt.date.fromisoformat(day)
        start = int(dt.datetime.combine(date, dt.time(), market37.NY).timestamp())
        end = int(dt.datetime.combine(date + dt.timedelta(days=1), dt.time(), market37.NY).timestamp())
        try:
            payload, _ = g['massive_request'](
                'v2/aggs/ticker/' + symbol + '/range/1/minute/' + day + '/' + day,
                {'adjusted': 'true', 'sort': 'asc', 'limit': 5000})
            bars = g['normalized_massive_candles'](payload, symbol, start, end)
        except g['ProviderError'] as error:
            return saved or {'status': 'unavailable', 'notice': error.message}
        points = [{'t': (stamp + 60) * 1000, 'p': price, 'source': 'massive_minute'}
                  for stamp, price in zip(bars['t'], bars['c'])
                  if stamp % 60 == 0 and start <= stamp < end]
        if not points:
            return saved or {'status': 'unavailable', 'notice': 'Massive supplied no usable minutes for ' + day + '.'}
        with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
            con.execute('INSERT OR REPLACE INTO session38_cache VALUES(?,?,?,?)',
                        (symbol, day, json.dumps(points, allow_nan=False), int(g['time'].time())))
            con.execute("""DELETE FROM session38_cache WHERE rowid NOT IN
                (SELECT rowid FROM session38_cache ORDER BY fetched_at DESC,rowid DESC LIMIT 30)""")
        return label(g, {'day': day, 'points': points, 'symbol': symbol, 'status': 'ok'})


def label(g, row):
    if row.get('points'):
        row['coverage'] = coverage41.intraday(row['points'], int(g['time'].time() * 1000), 'Massive split-adjusted minute bars')
        row['coverage']['freshness'] = 'saved'
        row['coverage']['notice'] = 'Saved minute bars for one completed New York date. Missing minutes stay missing. This is not a live tape.'
    return row
