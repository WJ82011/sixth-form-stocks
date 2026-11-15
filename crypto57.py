"""Crypto Forecast Lab. Completed Coinbase candles, UTC horizons, local shrinkage.

The shrinkage is chosen on the tuning dates only. Later dates are scored and are
not used to choose it. A target window ends before the next decision starts.
The learned price is withheld unless it is closer than both an unchanged price
and the average of earlier horizon returns on those later dates.
"""
import contextlib
import datetime as dt
import hashlib
import json
import math
import threading

import crypto38

METHOD = 'crypto-shrinkage-v5.7'
HORIZONS = (
    {'id': '1H', 'label': '1 hour', 'interval': 3600000, 'steps': 1, 'frequency': '1-hour candles'},
    {'id': '24H', 'label': '24 hours', 'interval': 86400000, 'steps': 1, 'frequency': '1-day candles'},
    {'id': '7D', 'label': '7 days', 'interval': 86400000, 'steps': 7, 'frequency': '1-day candles'},
)
SHRINKAGE = (0, 0.25, 0.5, 0.75, 1)
PRIOR = 4
MIN_BLOCK = 8
CORE = ('BTC-USD', 'ETH-USD')
LOCK = threading.Lock()
GRADE_RULE = 'Graded on the completed candle whose end time is the decision time plus the horizon. A missing candle stays ungraded. No later candle is substituted.'


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS crypto57_candles(
        product TEXT NOT NULL, interval_ms INTEGER NOT NULL, ts_ms INTEGER NOT NULL,
        price REAL NOT NULL, PRIMARY KEY(product, interval_ms, ts_ms))''')
    con.execute('''CREATE TABLE IF NOT EXISTS crypto57_reports(
        product TEXT PRIMARY KEY, revision TEXT NOT NULL, body TEXT NOT NULL, trained_at INTEGER NOT NULL)''')
    con.execute('''CREATE TABLE IF NOT EXISTS crypto57_issued(
        id TEXT PRIMARY KEY, product TEXT NOT NULL, horizon TEXT NOT NULL,
        decision_ms INTEGER NOT NULL, target_ms INTEGER NOT NULL, issued_at INTEGER NOT NULL,
        model TEXT NOT NULL, forecast REAL NOT NULL, low REAL NOT NULL, high REAL NOT NULL,
        unchanged REAL NOT NULL, drift REAL NOT NULL, interval_ms INTEGER NOT NULL,
        exchange TEXT NOT NULL, quote TEXT NOT NULL, outcome TEXT,
        UNIQUE(product, horizon, decision_ms))''')
    con.execute('''CREATE TABLE IF NOT EXISTS crypto57_cursor(id INTEGER PRIMARY KEY, pos INTEGER NOT NULL)''')


def _utc(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).isoformat()


def _clip(value):
    return max(-0.35, min(0.35, value))


def _error(pred, actual):
    return abs(math.expm1(pred) - math.expm1(actual)) * 100


def _mean(rows):
    return sum(rows) / len(rows) if rows else None


def quantile(values, portion):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    pos = (len(ordered) - 1) * portion
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def align(raw, interval):
    """Sort observations, reject conflicting timestamps, and keep the continuous suffix."""
    rows = []
    stamps = []
    for point in raw or []:
        if not isinstance(point, dict):
            continue
        stamp, price = point.get('t'), point.get('p')
        if type(stamp) is not int or isinstance(price, bool) or not isinstance(price, (int, float)):
            continue
        if stamp % interval or not math.isfinite(price) or not 0 < price <= 1e9:
            continue
        stamps.append(stamp)
        rows.append({'t': stamp, 'p': float(price)})
    rows.sort(key=lambda row: row['t'])
    ordered = []
    for row in rows:
        if ordered and ordered[-1]['t'] == row['t']:
            if ordered[-1]['p'] != row['p']:
                return {'points': [], 'status': 'conflict', 'gaps': [], 'dropped': 0,
                        'reordered': stamps != sorted(stamps)}
            continue
        ordered.append(row)
    gaps = []
    start = 0
    for index in range(1, len(ordered)):
        if ordered[index]['t'] - ordered[index - 1]['t'] != interval:
            gaps.append({'from': ordered[index - 1]['t'], 'to': ordered[index]['t']})
            start = index
    return {'points': ordered[start:], 'status': 'ok' if ordered else 'empty', 'gaps': gaps,
            'dropped': start, 'reordered': stamps != sorted(stamps)}


def walk(points, steps):
    """Non-overlapping decisions. Each target ends at or before the next decision."""
    horizon = steps
    rows = []
    anchor = PRIOR * horizon
    while anchor + horizon < len(points):
        if anchor - horizon < 0:
            raise RuntimeError('A feature used a price before the series started.')
        last = math.log(points[anchor]['p'] / points[anchor - horizon]['p'])
        earlier = []
        for step in range(PRIOR):
            end = anchor - step * horizon
            earlier.append(math.log(points[end]['p'] / points[end - horizon]['p']))
        actual_index = anchor + horizon
        actual = math.log(points[actual_index]['p'] / points[anchor]['p'])
        if actual_index <= anchor:
            raise RuntimeError('A training result used a price after the decision.')
        rows.append({
            'anchor': anchor, 'target': actual_index, 'last': last,
            'drift': sum(earlier) / len(earlier), 'actual': actual,
            'anchorPrice': points[anchor]['p'], 'actualPrice': points[actual_index]['p'],
            'anchorMs': points[anchor]['t'], 'targetMs': points[actual_index]['t'],
        })
        anchor += horizon
    for left, right in zip(rows, rows[1:]):
        if left['target'] > right['anchor']:
            raise RuntimeError('Target windows overlap.')
    return rows


def _predict(row, weight):
    return _clip(weight * row['last'])


def evaluate(points, spec):
    aligned = align(points, spec['interval'])
    base = {'id': spec['id'], 'label': spec['label'], 'frequency': spec['frequency'],
            'interval': spec['interval'], 'exchange': 'Coinbase Exchange', 'quote': 'USD',
            'timezone': 'UTC', 'gaps': aligned['gaps'], 'dropped': aligned['dropped'],
            'used': len(aligned['points']), 'reordered': aligned['reordered'],
            'record': 'historical test'}
    if aligned['status'] == 'conflict':
        return {**base, 'status': 'withheld', 'reason': 'Two prices share a timestamp and disagree. No forecast was trained.'}
    series = aligned['points']
    if any(series and abs(math.log(right['p'] / left['p'])) > 0.7 for left, right in zip(series, series[1:])):
        return {**base, 'status': 'withheld', 'reason': 'A move is large enough to be a bad print. The learned forecast was withheld. Saved prices were not changed.'}
    rows = walk(series, spec['steps']) if series else []
    train_end = len(rows) // 2
    tune_end = train_end + (len(rows) - train_end) // 2
    train, tune, test = rows[:train_end], rows[train_end:tune_end], rows[tune_end:]
    counts = {'trainCount': len(train), 'tuneCount': len(tune), 'testCount': len(test)}
    if len(tune) < MIN_BLOCK or len(test) < MIN_BLOCK:
        return {**base, **counts, 'status': 'insufficient',
                'reason': 'Not enough continuous completed candles for a training block, a tuning block and a later test of 8 forecasts each.'}
    def score(block, weight):
        return _mean([_error(_predict(row, weight), row['actual']) for row in block])
    weight = min(SHRINKAGE, key=lambda item: (score(tune, item), item))
    model_error = score(test, weight)
    unchanged = score(test, 0)
    drift = _mean([_error(_clip(row['drift']), row['actual']) for row in test])
    residuals = [row['actual'] - _predict(row, weight) for row in tune]
    low_q, high_q = quantile(residuals, 0.1), quantile(residuals, 0.9)
    inside = sum(low_q <= row['actual'] - _predict(row, weight) <= high_q for row in test)
    coverage = inside / len(test) * 100
    result = {**base, **counts, 'shrinkage': weight, 'modelErrorPP': model_error,
              'unchangedErrorPP': unchanged, 'driftErrorPP': drift,
              'rangeCoveragePct': coverage, 'rangeCount': len(test),
              'baselines': 'Unchanged price, and the average of the four earlier horizon returns.'}
    if not (model_error < unchanged and model_error < drift):
        return {**result, 'status': 'baseline',
                'reason': 'The learned forecast was withheld. On the later dates it was not closer than both the unchanged price and the historical average return.'}
    decision = len(series) - 1
    last = math.log(series[decision]['p'] / series[decision - spec['steps']]['p'])
    earlier = [math.log(series[decision - step * spec['steps']]['p'] / series[decision - (step + 1) * spec['steps']]['p'])
               for step in range(PRIOR)]
    pred = _clip(weight * last)
    price = series[decision]['p']
    return {**result, 'status': 'learned', 'forecast': {
        'price': price * math.exp(pred),
        'low': price * math.exp(min(pred, pred + low_q)),
        'high': price * math.exp(max(pred, pred + high_q)),
        'unchanged': price, 'drift': price * math.exp(_clip(sum(earlier) / len(earlier))),
        'decisionMs': series[decision]['t'],
        'targetMs': series[decision]['t'] + spec['steps'] * spec['interval'],
        'decision': _utc(series[decision]['t']), 'target': _utc(series[decision]['t'] + spec['steps'] * spec['interval']),
    }}


def build(series):
    return [evaluate(series.get(spec['interval']) or [], spec) for spec in HORIZONS]


def _stored(g, product, interval):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        rows = con.execute('SELECT ts_ms, price FROM crypto57_candles WHERE product=? AND interval_ms=? ORDER BY ts_ms',
                           (product, interval)).fetchall()
    return [{'t': row[0], 'p': row[1]} for row in rows]


def _save_candles(g, product, interval, points):
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.executemany('INSERT OR REPLACE INTO crypto57_candles VALUES(?,?,?,?)',
                        [(product, interval, point['t'], point['p']) for point in points])


def _previous(g, product):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        row = con.execute('SELECT body, trained_at FROM crypto57_reports WHERE product=?', (product,)).fetchone()
    if not row:
        return None
    body = json.loads(row[0])
    body['trainedAt'] = row[1]
    return body


def _issue(g, product, horizons, now):
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        for row in horizons:
            forecast = row.get('forecast')
            if row.get('status') != 'learned' or not forecast:
                continue
            ident = hashlib.sha256(f"{product}|{row['id']}|{forecast['decisionMs']}|{METHOD}".encode()).hexdigest()[:16]
            con.execute('''INSERT OR IGNORE INTO crypto57_issued
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)''', (
                ident, product, row['id'], forecast['decisionMs'], forecast['targetMs'], int(now), METHOD,
                forecast['price'], forecast['low'], forecast['high'], forecast['unchanged'], forecast['drift'],
                row['interval'], 'Coinbase Exchange', 'USD'))


def grade(g, product):
    if product not in crypto38.PRODUCTS:
        raise ValueError('Choose a supported Coinbase USD market.')
    graded = 0
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        pending = con.execute('SELECT id, target_ms, interval_ms, forecast, unchanged, drift FROM crypto57_issued WHERE product=? AND outcome IS NULL',
                              (product,)).fetchall()
        for ident, target, interval, forecast, unchanged, drift in pending:
            candle = con.execute('SELECT price FROM crypto57_candles WHERE product=? AND interval_ms=? AND ts_ms=?',
                                 (product, interval, target)).fetchone()
            if not candle:
                continue
            actual = candle[0]
            model = _error(math.log(forecast / unchanged), math.log(actual / unchanged)) if unchanged else None
            unchanged_error = _error(0, math.log(actual / unchanged)) if unchanged else None
            drift_error = _error(math.log(drift / unchanged), math.log(actual / unchanged)) if unchanged and drift else None
            outcome = {'actualPrice': actual, 'actualTime': _utc(target), 'modelErrorPP': model,
                       'unchangedErrorPP': unchanged_error, 'driftErrorPP': drift_error,
                       'inRange': None, 'rule': GRADE_RULE, 'record': 'issued forecast'}
            row = con.execute('SELECT low, high FROM crypto57_issued WHERE id=?', (ident,)).fetchone()
            outcome['inRange'] = bool(row and row[0] <= actual <= row[1])
            con.execute('UPDATE crypto57_issued SET outcome=? WHERE id=?', (json.dumps(outcome), ident))
            graded += 1
    return {'graded': graded}


def issued(g, product):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        rows = con.execute('''SELECT horizon, decision_ms, target_ms, issued_at, model, forecast, low, high,
            unchanged, drift, outcome FROM crypto57_issued WHERE product=? ORDER BY issued_at''', (product,)).fetchall()
    result = []
    for row in rows:
        outcome = json.loads(row[10]) if row[10] else None
        result.append({'horizon': row[0], 'decision': _utc(row[1]), 'target': _utc(row[2]), 'targetMs': row[2], 'issuedAt': row[3],
                       'model': row[4], 'forecastPrice': row[5], 'low': row[6], 'high': row[7],
                       'unchanged': row[8], 'drift': row[9], 'outcome': outcome, 'record': 'issued forecast'})
    return result


def report(g, product, series=None):
    if product not in crypto38.PRODUCTS:
        raise ValueError('Choose a supported Coinbase USD market.')
    previous = _previous(g, product)
    try:
        if series is None:
            series = {spec['interval']: _stored(g, product, spec['interval']) for spec in HORIZONS}
        else:
            for interval, points in series.items():
                _save_candles(g, product, interval, align(points, interval)['points'])
        horizons = build(series)
    except Exception:
        if previous:
            return {**previous, 'notice': 'Training stopped before a new report was saved. The stored report is unchanged.'}
        raise
    now = int(g['time'].time() * 1000)
    body = {'method': METHOD, 'product': product, 'name': crypto38.PRODUCTS[product],
            'exchange': 'Coinbase Exchange', 'quote': 'USD', 'timezone': 'UTC',
            'record': 'historical test', 'horizons': horizons,
            'limits': 'One asset is trained at a time. A refresh requests at most two Coinbase candle pages.'}
    revision = hashlib.sha256(json.dumps(['v57', METHOD, horizons], default=str).encode()).hexdigest()
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('INSERT OR REPLACE INTO crypto57_reports VALUES(?,?,?,?)',
                    (product, revision, json.dumps(body), now))
    _issue(g, product, horizons, now)
    grade(g, product)
    body['trainedAt'] = now
    body['issued'] = issued(g, product)
    return body


def read(g, product):
    body = _previous(g, product)
    if not body:
        return {'product': product, 'name': crypto38.PRODUCTS.get(product, product), 'horizons': [], 'issued': [],
                'notice': 'No crypto forecast report is saved for this market.'}
    body['issued'] = issued(g, product)
    body['notice'] = 'Opened from the saved report. It was not retrained.'
    return body


def refresh(g, product, interval, requests=2):
    """Fetch at most `requests` completed-candle pages. An open candle is excluded."""
    if product not in crypto38.PRODUCTS:
        raise ValueError('Choose a supported Coinbase USD market.')
    step = interval // 1000
    now = int(g['time'].time())
    end = (now // step) * step
    points = []
    for page in range(max(0, min(2, requests))):
        right = end - page * step * 290
        left = right - step * 290
        rows = crypto38.public_get(g, product, 'candles', {'start': crypto38.iso(left), 'end': crypto38.iso(right), 'granularity': step})
        points.extend(crypto38.normalise_candles(rows, left, right, step))
    if points:
        _save_candles(g, product, interval, points)
    return {'fetched': len(points), 'requests': max(0, min(2, requests))}


def scheduled(g):
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        row = con.execute('SELECT pos FROM crypto57_cursor WHERE id=1').fetchone()
        pos = row[0] if row else 0
        con.execute('INSERT OR REPLACE INTO crypto57_cursor VALUES(1,?)', (pos + 1,))
    order = list(CORE) + [product for product in crypto38.PRODUCTS if product not in CORE]
    product = order[pos % len(order)]
    interval = 3600000 if product in CORE and pos % 2 else 86400000
    try:
        refresh(g, product, interval, 2)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    body = report(g, product)
    return {'product': product, 'interval': interval, 'statuses': [row.get('status') for row in body.get('horizons', [])]}


def question(text):
    words = text.lower()
    return any(word in words for word in ('forecast', 'model', 'accurate', 'accuracy'))


def named_product(text):
    words = text.lower()
    for product, name in crypto38.PRODUCTS.items():
        if name.lower() in words or product.lower() in words:
            return product
    return ''


def explain(g, product):
    body = read(g, product)
    lines = []
    if not body.get('horizons'):
        lines.append(body.get('notice') or 'No saved crypto report.')
    for row in body.get('horizons') or []:
        if row.get('status') == 'insufficient':
            lines.append(f"{row['label']}: not enough continuous {row['frequency']}. Tuning sample {row.get('tuneCount', 0)}, later test {row.get('testCount', 0)}.")
        elif row.get('status') == 'withheld':
            lines.append(f"{row['label']}: {row.get('reason')}")
        else:
            lines.append(
                f"{row['label']}: later test of {row.get('testCount', 0)} forecasts. "
                f"Average error {row.get('modelErrorPP', 0):.2f} percentage points, "
                f"unchanged price {row.get('unchangedErrorPP', 0):.2f}, historical average {row.get('driftErrorPP', 0):.2f}. "
                f"The range contained the candle in {row.get('rangeCoveragePct', 0):.0f}% of {row.get('rangeCount', 0)} tests. "
                f"{'A forecast was saved.' if row.get('status') == 'learned' else 'No forecast was issued.'}"
            )
        if row.get('gaps'):
            lines.append(f"{row['label']} has {len(row['gaps'])} gap{'s' if len(row['gaps']) != 1 else ''} in the saved candles. The missing stretch was not filled.")
    issued_rows = body.get('issued') or []
    lines.append(f"{len(issued_rows)} issued forecast{'s' if len(issued_rows) != 1 else ''} kept separately from the historical test.")
    lines.append('Candles are Coinbase Exchange USD prices on a continuous UTC clock. Equity holidays are not removed. Training again does not replace an issued forecast.')
    return ' '.join(lines), {
        'sampleSize': sum(row.get('testCount') or 0 for row in body.get('horizons') or []),
        'rows': issued_rows[:8], 'gaps': [row.get('reason') for row in body.get('horizons') or [] if row.get('status') != 'learned'],
        'qualification': 'Historical tests and issued forecasts are stored separately. A forecast is issued only after it beats both baselines on later dates.',
        'source': 'Saved Coinbase candles and the crypto forecast report on this Mac.',
    }
