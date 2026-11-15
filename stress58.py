"""Portfolio stress tests. Cash stays put. The practice ledger is not edited.

A percentage changes today's allocated value. A historical test applies each
holding's own past return to today's allocation. Equity dates are New York
sessions. Crypto dates are UTC calendar days. A missing price or exchange rate
withholds the combined total.
"""
import contextlib
import datetime as dt
import hashlib
import json

import crypto38
import events42
import portfolio3

METHOD = 'portfolio-stress-v5.8'
ASSUMPTIONS = (
    'Cash is not changed.',
    'The practice ledger and its transactions are not changed.',
    'A percentage applies to today\'s allocated value, after any hypothetical weights.',
    'Hypothetical weights redistribute today\'s invested value. They are not transactions.',
    'A historical test applies each holding\'s recorded return to today\'s allocation. It does not replay the old portfolio.',
    'Equity observations use New York sessions. Crypto observations use UTC days, including weekends.',
    'Values are USD. A non-USD holding uses only the exchange rate already saved on its mark. No rate is invented.',
)


def _money(value):
    return round(float(value) + 0, 2)


def _rows(holdings, sectors=None):
    sectors = sectors or {}
    rows = []
    for holding in holdings or []:
        sector = holding.get('sector') or sectors.get(holding['symbol']) or 'Sector not recorded'
        if sector == '':
            sector = 'Sector not recorded'
        value = holding.get('valueUSD')
        rows.append({
            'symbol': holding['symbol'],
            'valueUSD': None if value is None else _money(value),
            'currency': holding.get('currency') or 'USD',
            'fx': holding.get('fx'),
            'sector': sector,
            'asset': holding.get('asset') or 'stock',
            'quantity': holding.get('quantity'),
        })
    return rows


def from_account(account, sectors=None, types=None):
    types = types or {}
    holdings = []
    for holding in account.get('holdings') or []:
        mark = holding.get('mark') or {}
        holdings.append({
            'symbol': holding['symbol'], 'valueUSD': holding.get('valueUSD'),
            'currency': holding.get('currency') or 'USD', 'fx': mark.get('fx'),
            'quantity': holding.get('quantity'), 'asset': types.get(holding['symbol']) or 'stock',
        })
    return {'cashUSD': account.get('cashUSD') or 0, 'holdings': _rows(holdings, sectors),
            'complete': account.get('complete'), 'asOf': account.get('asOf')}


def _allocate(rows, weights):
    priced = [row for row in rows if row['valueUSD'] is not None]
    missing = [row['symbol'] for row in rows if row['valueUSD'] is None]
    invested = round(sum(row['valueUSD'] for row in priced), 2)
    if weights:
        if missing:
            raise ValueError('A holding has no saved USD value, so hypothetical weights are withheld.')
        names = {row['symbol'] for row in rows}
        if set(weights) != names:
            raise ValueError('Hypothetical weights must name every current holding.')
        total = round(sum(float(weights[name]) for name in names), 2)
        if abs(total - 100) > 0.05:
            raise ValueError('Hypothetical weights must add to 100%.')
        for row in rows:
            if float(weights[row['symbol']]) < 0:
                raise ValueError('A hypothetical weight cannot be negative.')
            row['allocatedUSD'] = _money(invested * float(weights[row['symbol']]) / 100)
            row['weightPct'] = round(float(weights[row['symbol']]), 2)
    else:
        for row in rows:
            row['allocatedUSD'] = row['valueUSD']
            row['weightPct'] = None if not invested or row['valueUSD'] is None else round(row['valueUSD'] / invested * 100, 2)
    return missing, invested


def _finish(rows, cash, missing, assumptions_extra, mode):
    cash = _money(cash)
    missing = list(dict.fromkeys(missing))
    withheld = bool(missing) or any(row.get('currency') not in ('USD',) and row.get('valueUSD') is None for row in rows)
    fx_missing = [row['symbol'] for row in rows if row.get('currency') != 'USD' and row.get('valueUSD') is None]
    if fx_missing:
        withheld = True
    stressed = None
    if not withheld and all(row.get('stressedUSD') is not None for row in rows):
        stressed = _money(cash + sum(row['stressedUSD'] for row in rows))
    recorded = None if missing or fx_missing else _money(cash + sum(row['valueUSD'] for row in rows))
    for row in rows:
        if row.get('stressedUSD') is None or row.get('allocatedUSD') is None:
            row['contributionUSD'] = None
        else:
            row['contributionUSD'] = _money(row['stressedUSD'] - row['allocatedUSD'])
    contributions = sorted((row for row in rows if row.get('contributionUSD') is not None),
                           key=lambda row: (-abs(row['contributionUSD']), row['symbol']))
    largest = contributions[0] if contributions else None
    return {
        'method': METHOD, 'mode': mode, 'cashUSD': cash, 'cashChanged': False,
        'recordedUSD': recorded, 'stressedUSD': stressed,
        'changeUSD': None if recorded is None or stressed is None else _money(stressed - recorded),
        'status': 'withheld' if withheld else 'ok',
        'missing': missing, 'fxMissing': fx_missing, 'holdings': rows,
        'contributions': [{'symbol': row['symbol'], 'contributionUSD': row['contributionUSD'],
                           'stressedUSD': row['stressedUSD']} for row in contributions],
        'largest': None if not largest else {'symbol': largest['symbol'], 'contributionUSD': largest['contributionUSD']},
        'assumptions': list(ASSUMPTIONS) + assumptions_extra,
        'ledgerUntouched': True,
    }


def shock(holdings, cash, scope, percent, symbol=None, sector=None, weights=None, sectors=None):
    if scope not in ('all', 'symbol', 'sector'):
        raise ValueError('Choose all holdings, one holding, or one sector.')
    percent = float(percent)
    if percent < -100 or percent > 300:
        raise ValueError('Use a percentage from -100 to 300.')
    if scope == 'symbol' and not symbol:
        raise ValueError('Choose the holding to change.')
    if scope == 'sector' and not sector:
        raise ValueError('Choose the sector to change.')
    if scope == 'sector' and sector == 'Sector not recorded':
        raise ValueError('A holding without a sector is not part of a named sector shock.')
    rows = _rows(holdings, sectors)
    missing, _invested = _allocate(rows, weights)
    moved = []
    for row in rows:
        if row['allocatedUSD'] is None:
            row['stressedUSD'] = None
            row['note'] = 'No saved USD value. This holding is left out and the combined total is withheld.'
            continue
        hit = scope == 'all' or (scope == 'symbol' and row['symbol'] == symbol) or (
            scope == 'sector' and row['sector'] == sector)
        row['shocked'] = hit
        row['percent'] = percent if hit else 0
        row['stressedUSD'] = _money(row['allocatedUSD'] * (1 + (percent if hit else 0) / 100))
        if hit:
            moved.append(row['symbol'])
    extra = [f'The typed change is {percent:g}% on {scope}.']
    if scope == 'sector' and not moved:
        extra.append(f'No holding is classified as {sector}. Nothing was moved.')
    if missing:
        extra.append('A missing price withholds the combined portfolio value.')
    return _finish(rows, cash, missing, extra, 'hypothetical')


def _dates(book):
    found = {}
    for row in book or []:
        day = str(row.get('date') or '')
        price = row.get('price')
        if not day or isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0:
            continue
        found[day] = {'date': day, 'price': float(price), 'source': row.get('source') or 'Saved close'}
    return found


def _span(asset, start, end):
    first = dt.date.fromisoformat(start)
    last = dt.date.fromisoformat(end)
    days = []
    cursor = first
    while cursor <= last:
        if asset == 'crypto' or events42.is_session(cursor):
            days.append(cursor.isoformat())
        cursor += dt.timedelta(days=1)
    return days


def _asset_return(row, book, start, end):
    observed = _dates(book)
    if row['asset'] != 'crypto' and not events42.is_session(dt.date.fromisoformat(start)):
        return {'status': 'missing', 'reason': start + ' is not a New York equity session.', 'observations': []}
    if row['asset'] != 'crypto' and not events42.is_session(dt.date.fromisoformat(end)):
        return {'status': 'missing', 'reason': end + ' is not a New York equity session.', 'observations': []}
    calendar = _span(row['asset'], start, end)
    gaps = [day for day in calendar if day not in observed and day not in (start, end)]
    start_obs = observed.get(start)
    end_obs = observed.get(end)
    observations = [item for item in (start_obs, end_obs) if item]
    if not start_obs or not end_obs:
        missing = start if not start_obs else end
        return {'status': 'missing', 'reason': 'No saved observation on ' + missing + '.',
                'observations': observations, 'gaps': gaps}
    change = end_obs['price'] / start_obs['price'] - 1
    return {'status': 'ok', 'returnPct': round(change * 100, 4), 'observations': [start_obs, end_obs],
            'gaps': gaps, 'calendar': 'UTC days' if row['asset'] == 'crypto' else 'New York sessions'}


def common_period(holdings, books, start, end):
    sets = []
    for row in holdings:
        observed = set(_dates(books.get(row['symbol'])).keys())
        allowed = set(_span(row['asset'], start, end))
        sets.append(observed & allowed)
    if not sets:
        return None
    shared = set.intersection(*sets) if sets else set()
    ordered = sorted(shared)
    if len(ordered) < 2:
        return None
    return {'start': ordered[0], 'end': ordered[-1], 'days': len(ordered)}


def replay(holdings, cash, books, start, end, weights=None, sectors=None):
    portfolio3.date(start)
    portfolio3.date(end)
    if end < start:
        raise ValueError('The end date must be on or after the start date.')
    rows = _rows(holdings, sectors)
    missing, _invested = _allocate(rows, weights)
    books = books or {}
    for row in rows:
        history = _asset_return(row, books.get(row['symbol']), start, end)
        row['history'] = history
        if row['allocatedUSD'] is None:
            row['stressedUSD'] = None
            row['note'] = 'No saved USD value. The past return cannot be applied.'
            continue
        if history['status'] != 'ok':
            row['stressedUSD'] = None
            row['note'] = history['reason']
            missing.append(row['symbol'])
            continue
        row['percent'] = history['returnPct']
        row['stressedUSD'] = _money(row['allocatedUSD'] * (1 + history['returnPct'] / 100))
        row['note'] = 'Today\'s allocated value multiplied by the recorded return from ' + start + ' to ' + end + '.'
    offered = common_period(rows, books, start, end)
    extra = ['This uses today\'s holdings and the past return of each symbol. It is not the portfolio you held then.']
    if offered and (offered['start'] != start or offered['end'] != end):
        extra.append('A common covered period is ' + offered['start'] + ' to ' + offered['end'] + '.')
    elif offered:
        extra.append('Every holding has observations on the selected dates.')
    else:
        extra.append('No common period with two covered dates was found in this range.')
    result = _finish(rows, cash, missing, extra, 'historical')
    result['start'] = start
    result['end'] = end
    result['common'] = offered
    return result


def question(text):
    words = str(text or '').lower()
    return 'portfolio' in words and any(word in words for word in ('stress', 'drive', 'concentration', 'result'))


def explain(saved):
    if not saved:
        return 'No saved portfolio stress was found.', {'sampleSize': 0, 'gaps': ['Save the stress test first.']}
    body = saved.get('result') or saved
    lines = []
    if body.get('status') != 'ok':
        lines.append('The combined result is withheld.')
    else:
        lines.append(f"Recorded value {body['recordedUSD']:.2f} USD becomes {body['stressedUSD']:.2f} USD. The change is {body['changeUSD']:.2f} USD. Cash stays {body['cashUSD']:.2f} USD.")
    if body.get('largest'):
        lines.append(f"The largest contribution is {body['largest']['symbol']} at {body['largest']['contributionUSD']:.2f} USD.")
    invested = [row for row in body.get('holdings') or [] if row.get('stressedUSD')]
    total = body.get('stressedUSD') or 0
    if total:
        for row in invested:
            share = row['stressedUSD'] / total * 100
            if share >= 25:
                lines.append(f"{row['symbol']} is {share:.1f}% of the stressed total, including cash.")
    if body.get('fxMissing'):
        lines.append('Missing exchange-rate data withholds a combined result for ' + ', '.join(body['fxMissing']) + '.')
    if body.get('missing'):
        lines.append('Missing prices or history: ' + ', '.join(body['missing']) + '.')
    lines.append(' '.join(body.get('assumptions') or ASSUMPTIONS[:3]))
    return ' '.join(lines), {
        'sampleSize': len(body.get('holdings') or []),
        'rows': body.get('contributions') or [],
        'qualification': 'The figures are the saved stress test. Training or later prices do not replace them.',
        'source': 'Practice portfolio values and saved market observations on this Mac.',
        'gaps': body.get('missing') or [],
    }


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS stress58(
        id TEXT PRIMARY KEY, body TEXT NOT NULL, created_at INTEGER NOT NULL)''')


def _types(ledger):
    found = {}
    try:
        clean = portfolio3.events(ledger)
    except portfolio3.LedgerError:
        return found
    for event in clean:
        if event.get('symbol') and event.get('assetType'):
            found[event['symbol']] = event['assetType']
    return found


def current(g, as_of=None):
    import workspace3
    snap = workspace3.normalise((g['read_workspace']().get('snapshot') or {}).get('v3') or {})
    account = portfolio3.calculate(snap['ledger'], snap['marks'], as_of)
    catalog = json.loads((g['ROOT'] / 'ai_catalog.json').read_text())
    sectors = {row['symbol']: row.get('category') or '' for row in catalog if isinstance(row, dict) and row.get('symbol')}
    prepared = from_account(account, sectors, _types(snap['ledger']))
    prepared['assumptions'] = list(ASSUMPTIONS)
    return prepared


def _books(g, rows, start, end):
    books = {}
    with contextlib.closing(g['db_connection']()) as con:
        for row in rows:
            if row['asset'] == 'crypto' or row['symbol'] in crypto38.PRODUCTS:
                product = row['symbol'] if row['symbol'] in crypto38.PRODUCTS else row['symbol'] + '-USD'
                if product not in crypto38.PRODUCTS:
                    books[row['symbol']] = []
                    continue
                try:
                    found = con.execute('SELECT ts_ms, price FROM crypto57_candles WHERE product=? AND interval_ms=86400000 ORDER BY ts_ms', (product,)).fetchall()
                except Exception:
                    found = []
                books[row['symbol']] = [{'date': dt.datetime.fromtimestamp(stamp / 1000, dt.timezone.utc).date().isoformat(),
                                         'price': price, 'source': 'Coinbase Exchange daily candle, UTC'}
                                        for stamp, price in found if start <= dt.datetime.fromtimestamp(stamp / 1000, dt.timezone.utc).date().isoformat() <= end]
            else:
                try:
                    found = con.execute('SELECT ts_ms, c FROM massive_daily_bars WHERE symbol=? ORDER BY ts_ms', (row['symbol'],)).fetchall()
                except Exception:
                    found = []
                books[row['symbol']] = [{'date': dt.datetime.fromtimestamp(stamp / 1000, events42.NY).date().isoformat(),
                                         'price': price, 'source': 'Massive split-adjusted daily close'}
                                        for stamp, price in found if isinstance(price, (int, float)) and price > 0
                                        and start <= dt.datetime.fromtimestamp(stamp / 1000, events42.NY).date().isoformat() <= end]
    return books


def run(g, obj, as_of=None):
    prepared = current(g, as_of)
    if obj.get('action') == 'history':
        books = obj.get('books')
        if books is None:
            books = _books(g, prepared['holdings'], obj.get('start') or '2000-01-01', obj.get('end') or prepared.get('asOf'))
        return replay(prepared['holdings'], prepared['cashUSD'], books, obj['start'], obj['end'], obj.get('weights'))
    return shock(prepared['holdings'], prepared['cashUSD'], obj.get('scope') or 'all', obj.get('percent') or 0,
                 obj.get('symbol'), obj.get('sector'), obj.get('weights'))


def save(g, obj, now_ms):
    request = dict(obj)
    request['action'] = 'history' if obj.get('mode') == 'history' else 'run'
    result = run(g, request)
    payload = {'method': METHOD, 'inputs': {key: obj.get(key) for key in ('action', 'scope', 'percent', 'symbol', 'sector', 'weights', 'start', 'end')},
               'result': result}
    ident = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('INSERT OR REPLACE INTO stress58 VALUES(?,?,?)', (ident, json.dumps(payload), int(now_ms)))
    payload['id'] = ident
    return payload


def read(g, ident):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        row = con.execute('SELECT body, created_at FROM stress58 WHERE id=?', (ident,)).fetchone()
    if not row:
        raise ValueError('That saved stress test was not found.')
    body = json.loads(row[0])
    body['id'] = ident
    body['savedAt'] = row[1]
    body['notice'] = 'Opened from the saved stress test. It was not recalculated.'
    return body
