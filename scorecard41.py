"""Issued learning forecasts. Retraining can add a later forecast; it cannot rewrite an earlier one."""
import contextlib
import datetime as dt
import hashlib
import json
import math

import lab45
import market37

NY = market37.NY


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS learning41_issued (
        id TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        method TEXT NOT NULL,
        horizon INTEGER NOT NULL,
        anchor_day TEXT NOT NULL,
        target_day TEXT NOT NULL,
        issued_at INTEGER NOT NULL,
        body TEXT NOT NULL,
        outcome TEXT,
        UNIQUE(symbol, method, horizon, anchor_day))''')


def day_of(stamp_ms):
    return dt.datetime.fromtimestamp(stamp_ms / 1000, NY).date()


def forward(anchor, horizon):
    if not isinstance(horizon, int) or isinstance(horizon, bool) or horizon < 1 or horizon > 60:
        raise ValueError('Unsupported forecast horizon.')
    day = dt.date.fromisoformat(anchor)
    found = 0
    for _ in range(horizon * 5 + 14):
        day += dt.timedelta(days=1)
        if day.weekday() < 5 and day not in market37.holidays(day.year):
            found += 1
            if found == horizon:
                return day.isoformat()
    raise ValueError('The session calendar could not place this target.')


def identity(symbol, method, horizon, anchor):
    raw = '|'.join((symbol, method, str(horizon), anchor))
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def closes(points):
    found = {}
    for point in points or []:
        try:
            stamp = int(point['t'])
            price = float(point['p'])
        except (TypeError, ValueError, KeyError):
            continue
        if stamp > 10_000_000_000 and math.isfinite(price) and price > 0:
            found[day_of(stamp).isoformat()] = price
    return found


def message(report):
    if report.get('quality'):
        return report['quality'] + ' No forecast was issued.'
    if report.get('stale'):
        return 'No new forecast was issued. The latest eligible close is missing.'
    rows = report.get('rows') or []
    if not rows:
        return 'Not enough saved closes to issue a forecast.'
    if any(row.get('status') == 'learned' for row in rows):
        return 'A forecast is saved only when this run beats the unchanged-price baseline. The original record is kept if you train again.'
    if any(row.get('status') == 'baseline' for row in rows):
        return 'No forecast was issued. Predicting no change did at least as well on the checks that decide a release.'
    return 'Not enough saved closes to issue a forecast.'


def score(body, actual):
    base = body['anchorPrice']
    error = abs(actual - body['forecastPrice']) / base * 100
    unchanged = abs(actual - body['baselinePrice']) / base * 100
    return {
        'status': 'scored',
        'actualPrice': actual,
        'absoluteErrorPP': error,
        'unchangedErrorPP': unchanged,
        'inRange': body['low'] <= actual <= body['high'],
        'beatBaseline': error < unchanged,
    }


def summarise(rows):
    graded = [row for row in rows if (row.get('outcome') or {}).get('status') == 'scored']
    if not graded:
        return {'count': 0, 'averageErrorPP': None, 'baselineAverageErrorPP': None,
                'rangeCoveragePct': None, 'rangeCount': 0, 'beatBaselineCount': 0, 'beatBaseline': None}
    errors = [row['outcome']['absoluteErrorPP'] for row in graded]
    baseline = [row['outcome']['unchangedErrorPP'] for row in graded]
    covered = [row['outcome']['inRange'] for row in graded if row['outcome']['inRange'] is not None]
    beats = sum(1 for row in graded if row['outcome']['beatBaseline'])
    return {
        'count': len(graded),
        'averageErrorPP': sum(errors) / len(errors),
        'baselineAverageErrorPP': sum(baseline) / len(baseline),
        'rangeCoveragePct': sum(covered) / len(covered) * 100 if covered else None,
        'rangeCount': len(covered),
        'beatBaselineCount': beats,
        'beatBaseline': sum(errors) < sum(baseline),
    }


def public_row(body, outcome):
    item = dict(body)
    item['outcome'] = outcome
    item['state'] = 'graded' if outcome else 'pending'
    return item


def read(g, symbol=None):
    with contextlib.closing(g['db_connection']()) as con:
        if symbol:
            stored = con.execute('''SELECT body,outcome FROM learning41_issued
                WHERE symbol=? ORDER BY issued_at DESC, anchor_day DESC, horizon''', (symbol,)).fetchall()
        else:
            stored = con.execute('SELECT body,outcome FROM learning41_issued ORDER BY issued_at DESC').fetchall()
    rows = []
    for body, outcome in stored:
        try:
            parsed = json.loads(body)
            graded = json.loads(outcome) if outcome else None
            rows.append(public_row(parsed, graded))
        except (ValueError, TypeError):
            continue
    pending = [row for row in rows if row['state'] == 'pending']
    graded = [row for row in rows if row['state'] == 'graded']
    return {'pending': pending, 'graded': graded, 'summary': summarise(rows),
            'notice': 'Pending and graded rows are forecasts saved when they were issued. The table above is a historical backtest and is not part of this score.'}


def sync(g, symbol, report, points):
    init_needed = True
    now = int(g['time'].time() * 1000)
    known = closes(points)
    issue = not report.get('stale') and not report.get('quality')
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        if init_needed:
            init(con)
        if issue and report.get('anchor') and report.get('anchorDate'):
            for row in report.get('rows') or []:
                if row.get('status') != 'learned':
                    continue
                try:
                    target = forward(report['anchorDate'], row['horizon'])
                    price = float(row['price'])
                    low = float(row['low'])
                    high = float(row['high'])
                    anchor_price = float(report['anchor']['p'])
                except (TypeError, ValueError, KeyError):
                    continue
                if not (0 < low <= price <= high <= 1e9 and 0 < anchor_price <= 1e9):
                    continue
                body = {
                    'id': identity(symbol, report['method'], row['horizon'], report['anchorDate']),
                    'symbol': symbol,
                    'method': report['method'],
                    'horizon': row['horizon'],
                    'anchorDay': report['anchorDate'],
                    'targetDay': target,
                    'issuedAt': now,
                    'anchorPrice': anchor_price,
                    'forecastPrice': price,
                    'low': low,
                    'high': high,
                    'returnPct': row.get('returnPct'),
                    'baselinePrice': anchor_price,
                    'knownThrough': report['anchorDate'],
                    'knownCloses': report.get('knownCloses') or lab45.known_closes(points, report['anchorDate']),
                    'calibrationCases': row.get('calibrationCases'),
                    'testCases': row.get('testCases'),
                    'modelErrorPP': row.get('modelErrorPP'),
                    'baselineErrorPP': row.get('baselineErrorPP'),
                }
                con.execute('''INSERT OR IGNORE INTO learning41_issued
                    (id,symbol,method,horizon,anchor_day,target_day,issued_at,body)
                    VALUES(?,?,?,?,?,?,?,?)''', (
                    body['id'], symbol, report['method'], row['horizon'], report['anchorDate'], target, now,
                    json.dumps(body, allow_nan=False)))
        if issue and report.get('anchor') and report.get('anchorDate'):
            for item in report.get('lab') or []:
                released = item.get('released') or None
                if not released or released.get('model') != 'volatility':
                    continue
                try:
                    target = forward(report['anchorDate'], int(released['horizon']))
                    price = float(released['price'])
                    low = float(released['low'])
                    high = float(released['high'])
                    anchor_price = float(report['anchor']['p'])
                except (TypeError, ValueError, KeyError):
                    continue
                if not (0 < low <= price <= high <= 1e9 and 0 < anchor_price <= 1e9):
                    continue
                body = {
                    'id': identity(symbol, released['method'], int(released['horizon']), report['anchorDate']),
                    'symbol': symbol, 'method': released['method'], 'horizon': int(released['horizon']),
                    'anchorDay': report['anchorDate'], 'targetDay': target, 'issuedAt': now,
                    'anchorPrice': anchor_price, 'forecastPrice': price, 'low': low, 'high': high,
                    'returnPct': released.get('returnPct'), 'baselinePrice': anchor_price,
                    'knownThrough': report['anchorDate'],
                    'knownCloses': report.get('knownCloses') or lab45.known_closes(points, report['anchorDate']),
                    'shrinkage': released.get('shrinkage'),
                }
                con.execute('''INSERT OR IGNORE INTO learning41_issued
                    (id,symbol,method,horizon,anchor_day,target_day,issued_at,body)
                    VALUES(?,?,?,?,?,?,?,?)''', (
                    body['id'], symbol, released['method'], int(released['horizon']), report['anchorDate'], target, now,
                    json.dumps(body, allow_nan=False)))
        pending = con.execute('''SELECT id,body FROM learning41_issued
            WHERE symbol=? AND outcome IS NULL''', (symbol,)).fetchall()
        for ident, raw in pending:
            body = json.loads(raw)
            saved_anchor = known.get(body['anchorDay'])
            actual = known.get(body['targetDay'])
            if saved_anchor is not None and not math.isclose(saved_anchor, body['anchorPrice'], rel_tol=1e-8, abs_tol=1e-6):
                outcome = {'status': 'withheld', 'gradedAt': now,
                           'reason': 'The saved close for the issue session changed after this forecast was recorded. The original forecast was kept and was not scored.'}
            elif actual is None:
                continue
            else:
                outcome = {**score(body, actual), 'gradedAt': now}
            con.execute('UPDATE learning41_issued SET outcome=? WHERE id=? AND outcome IS NULL',
                        (json.dumps(outcome, allow_nan=False), ident))
    card = read(g, symbol)
    card['message'] = message(report)
    card['backtestNotice'] = 'Historical backtests can change when new closes arrive. An issued forecast above does not.'
    return card
