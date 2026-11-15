"""Purple-line forecast from the chronological price model.

The path contains only horizons that beat an unchanged price on both the
calibration block and a later block. Straight joins between those horizons are
labelled as joins. News and accounts are not inputs. This read does not replace
a forecast that was already issued.
"""
import contextlib
import datetime as dt
import hashlib
import json
import math

import events42
import learning40
import market34
import market37

METHOD = learning40.METHOD
HORIZONS = (1, 5, 20)
SOURCE = 'Massive · saved daily closes. Read from this Mac. No network call for this test.'
INPUTS = 'Daily closing prices only. News and financial statements are not inputs, because no timestamped test of those variables is saved for this model.'


def _dates(points):
    return [dt.datetime.fromtimestamp(point['t'] / 1000, events42.NY).date().isoformat() for point in points]


def _prepare(g, symbol, now_ms):
    history = g['read_massive_daily_bars'](symbol, 946684800, now_ms // 1000)
    closes = history['bars'] if history else {'t': [], 'c': []}
    saved = market34.clean([{'t': stamp * 1000, 'p': price} for stamp, price in zip(closes['t'], closes['c'])], now_ms)
    dates = _dates(saved)
    points = list(saved)
    if dates:
        expected = market37.sessions(dt.date.fromisoformat(dates[-1]) + dt.timedelta(days=1), len(dates))
        count = 0
        for actual, wanted in zip(reversed(dates), expected):
            if actual != wanted:
                break
            count += 1
        points = points[-count:] if count else []
    return saved, points


def _split(points):
    return any(older['p'] > 0 and abs(math.log(newer['p'] / older['p'])) > 0.7 for older, newer in zip(points, points[1:]))


def _rows(anchor, scored):
    rows = [{'day': 0, 'price': anchor['p'], 'low': anchor['p'], 'high': anchor['p'],
             'kind': 'recorded', 'evaluated': True}]
    for item in scored:
        if item.get('status') != 'learned':
            continue
        rows.append({'day': item['horizon'], 'price': item['price'], 'low': item['low'], 'high': item['high'],
                     'kind': 'evaluated', 'evaluated': True, 'returnPct': item.get('returnPct')})
    gaps = []
    for left, right in zip(rows, rows[1:]):
        if right['day'] - left['day'] > 1:
            gaps.append(f"Sessions {left['day'] + 1} to {right['day'] - 1} are a straight join, not a separate forecast.")
    return rows, gaps


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS forecast61_runs(
        id TEXT PRIMARY KEY, symbol TEXT NOT NULL, body TEXT NOT NULL, created_at INTEGER NOT NULL)''')


def _plain(scored):
    parts = []
    for item in scored:
        horizon = item.get('horizon')
        status = item.get('status')
        if item.get('modelErrorPP') is None:
            parts.append(f'After {horizon} sessions there were not enough later tests ({status}).')
            continue
        sentence = (
            f'After {horizon} sessions the model missed by {item["modelErrorPP"]:.2f} percentage points. '
            f'An unchanged price missed by {item["baselineErrorPP"]:.2f}.')
        if item.get('driftErrorPP') is not None:
            sentence += f' Continuing the recent average move missed by {item["driftErrorPP"]:.2f}.'
        if item.get('rangeCoveragePct') is not None:
            sentence += f' The shaded band, built from earlier misses, covered {item["rangeCoveragePct"]:.0f}% of the later closes. About {item.get("expectedCoveragePct", 80):.0f}% would be expected if the band were well matched.'
        if status == 'learned':
            sentence += ' This horizon may be drawn.'
        else:
            sentence += ' This horizon is not drawn.'
        parts.append(sentence)
    return ' '.join(parts)


def remember(g, packet, now_ms):
    body = {key: packet.get(key) for key in ('symbol', 'status', 'anchorDate', 'observations', 'horizons', 'notice')}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:16]
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        if con.execute('SELECT 1 FROM forecast61_runs WHERE id=?', (digest,)).fetchone():
            return {'id': digest, 'stored': False}
        con.execute('INSERT INTO forecast61_runs VALUES(?,?,?,?)',
                    (digest, packet.get('symbol') or '', json.dumps(body, default=str), int(now_ms)))
    return {'id': digest, 'stored': True}


def runs(g, symbol=None):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        if symbol:
            rows = con.execute('SELECT body FROM forecast61_runs WHERE symbol=? ORDER BY created_at', (symbol,)).fetchall()
        else:
            rows = con.execute('SELECT body FROM forecast61_runs ORDER BY created_at').fetchall()
    return [json.loads(row[0]) for row in rows]


def build(points, now_ms, symbol='TEST', evaluate=None):
    evaluate = evaluate or learning40.evaluate
    dates = _dates(points)
    anchor = points[-1] if points else None
    base = {
        'method': METHOD, 'symbol': symbol, 'inputs': INPUTS, 'source': SOURCE,
        'trainedAt': int(now_ms), 'newsUsed': False, 'kind': 'model',
        'observations': len(points), 'first': dates[0] if dates else None, 'anchorDate': dates[-1] if dates else None,
        'anchor': anchor, 'horizons': [], 'rows': [], 'interpolation': [], 'issuedForecasts': 'left unchanged',
    }
    if len(points) < 220:
        return {**base, 'status': 'insufficient', 'rows': [],
                'notice': f'{symbol} has {len(points)} usable closes. The learned path is withheld.'}
    if _split(points):
        return {**base, 'status': 'withheld', 'rows': [],
                'notice': 'A one-day move is large enough to be a split or a bad print. The learned path is withheld. Saved prices were not changed.'}
    latest = None
    probe = dt.datetime.fromtimestamp(now_ms / 1000, events42.NY).date()
    for _ in range(12):
        if events42.is_session(probe):
            close = events42.close_on(probe)
            if close is not None and int(close.timestamp() * 1000) <= now_ms:
                latest = probe.isoformat()
                break
        probe -= dt.timedelta(days=1)
    stale = bool(dates) and latest is not None and dates[-1] != latest
    scored = [evaluate(points, horizon) for horizon in HORIZONS]
    for item in scored:
        item['horizon'] = item.get('horizon')
    rows, gaps = _rows(anchor, scored)
    learned = [item for item in scored if item.get('status') == 'learned']
    if stale:
        return {**base, 'status': 'stale', 'horizons': scored, 'rows': [],
                'notice': f"The last used close is {dates[-1]}. A learned path is withheld until the saved history reaches the latest completed session."}
    detail = _plain(scored)
    if not learned:
        return {**base, 'status': 'withheld', 'horizons': scored, 'rows': [],
                'notice': 'No purple line is drawn. A horizon is drawn only when the earlier dates choose it and a later, separate block still agrees. Otherwise an unchanged price stays the working method. ' + detail}
    return {**base, 'status': 'learned', 'horizons': scored, 'rows': rows, 'interpolation': gaps,
            'notice': 'The purple line shows only the horizons that stayed ahead of an unchanged price on later dates. ' + detail + ' ' + ' '.join(gaps)}


def for_symbol(g, symbol, now_ms=None, *, remember_result=True):
    symbol = g['valid_symbol'](symbol)
    now_ms = int(g['time'].time() * 1000) if now_ms is None else int(now_ms)
    saved, points = _prepare(g, symbol, now_ms)
    result = build(points, now_ms, symbol)
    result['coverage'] = {
        'savedCloses': len(saved), 'usedCloses': len(points),
        'droppedForGap': max(0, len(saved) - len(points)),
        'source': SOURCE,
    }
    with contextlib.closing(g['db_connection']()) as con:
        prior = None
        try:
            learning40.init(con)
            prior = con.execute('SELECT trained_at FROM learning40 WHERE symbol=?', (symbol,)).fetchone()
        except Exception:
            prior = None
        issued = 0
        try:
            issued = con.execute('SELECT count(*) FROM forecast35 WHERE symbol=?', (symbol,)).fetchone()[0]
        except Exception:
            issued = 0
    if prior:
        result['trainedAt'] = prior[0]
        result['trainingNote'] = 'Last saved training time for this company. This chart check did not replace that record.'
    else:
        result['trainingNote'] = 'No earlier training record was saved for this company. This check did not write one.'
    result['issuedCount'] = issued
    if remember_result:
        result['experiment'] = remember(g, result, now_ms)
    else:
        result['experiment'] = {'stored': False, 'reason': 'This read did not save a new experiment.'}
    return result


def question(text):
    words = str(text or '').lower()
    return 'forecast' in words and ('chosen' in words or 'purple' in words or 'reliable' in words or 'uncertainty' in words)


def explain(packet):
    if not packet:
        return 'No forecast check was included.'
    horizons = packet.get('horizons') or []
    bits = []
    for item in horizons:
        if item.get('modelErrorPP') is None:
            bits.append(f"{item.get('horizon')}-session {item.get('status')}")
        else:
            bits.append(f"{item.get('horizon')}-session {item.get('status')}, model {item['modelErrorPP']:.2f} pp, unchanged {item.get('baselineErrorPP', 0):.2f} pp, {item.get('testCases', 0)} later tests")
    return ' '.join([
        'The forecast looks only at daily closing prices. It keeps a horizon when that horizon was closer than an unchanged price on earlier dates and again on a later block that was not used to make the choice. The shaded band is the middle range of those earlier misses, not a promise.',
        f"Method {packet.get('method')}. {packet.get('inputs')}",
        f"Observations {packet.get('observations')} from {packet.get('first')} to {packet.get('anchorDate')}.",
        packet.get('trainingNote') or '',
        'Historical checks: ' + ('; '.join(bits) or 'none') + '.',
        packet.get('notice') or '',
    ])
