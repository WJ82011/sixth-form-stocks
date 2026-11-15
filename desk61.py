"""Local evidence, a four-chart board, investigations, model notes and repairs.

Calculations use saved records and the existing review tools. Nothing here
calls a provider. A repair changes only duplicate Massive daily bars, and
only after those bars have been inspected. User-imported history is not written.
"""
import contextlib
import datetime as dt
import hashlib
import json
import math
import sqlite3

import events42
import learning40
import move44

METHOD = 'evidence-v6.0'
BOARD = 'chart-board-v6.0'
INVESTIGATION = 'investigation-v6.0'
LEDGER = 'model-ledger-v6.0'
REPAIR = 'data-repair-v6.0'
CRITERIA = (
    'The calibration block must beat an unchanged price.',
    'A later block, unused for that fit, must also beat an unchanged price.',
    'At least 8 calibration cases and 8 later cases are required.',
    'Every candidate on the same observations is kept, including unsuccessful ones.',
    'The unchanged-price baseline stays active when any rule fails.',
    'Forecasts already issued by the forecast record are not replaced.',
)
STEPS = (
    ('week', 'Find the latest completed week'),
    ('return', 'Calculate the saved return'),
    ('benchmark', 'Compare that return with SPY'),
    ('events', 'Read dated events already saved'),
    ('finding', 'Write the sourced finding'),
)


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS desk61_jobs(
        id TEXT PRIMARY KEY, question TEXT NOT NULL, status TEXT NOT NULL,
        body TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL)''')
    con.execute('''CREATE TABLE IF NOT EXISTS desk61_boards(
        id TEXT PRIMARY KEY, body TEXT NOT NULL, created_at INTEGER NOT NULL)''')
    con.execute('''CREATE TABLE IF NOT EXISTS desk61_models(
        id TEXT PRIMARY KEY, name TEXT NOT NULL, body TEXT NOT NULL, created_at INTEGER NOT NULL)''')
    con.execute('''CREATE TABLE IF NOT EXISTS desk61_repairs(
        id TEXT PRIMARY KEY, symbol TEXT NOT NULL, body TEXT NOT NULL, created_at INTEGER NOT NULL)''')
    con.execute('''CREATE TABLE IF NOT EXISTS desk61_removed(
        id INTEGER PRIMARY KEY AUTOINCREMENT, batch TEXT NOT NULL, symbol TEXT NOT NULL,
        ts_ms INTEGER NOT NULL, o REAL NOT NULL, h REAL NOT NULL, l REAL NOT NULL,
        c REAL NOT NULL, v REAL NOT NULL, fetched_at INTEGER NOT NULL)''')


def question(text):
    words = str(text or '').lower()
    return words.startswith('investigate ') and 'weekly move' in words


def reference(kind, symbol, **fields):
    core = {
        'kind': kind, 'symbol': str(symbol or '').upper(),
        'publishedAt': fields.get('publishedAt'), 'retrievedAt': fields.get('retrievedAt'),
        'periodStart': fields.get('periodStart'), 'periodEnd': fields.get('periodEnd'),
        'source': fields.get('source') or '', 'method': fields.get('method') or METHOD,
        'value': fields.get('value'),
    }
    digest = hashlib.sha256(json.dumps(core, sort_keys=True, default=str).encode()).hexdigest()[:16]
    return {**core, 'id': f"md:{kind}:{core['symbol']}:{digest}"}


def _now(g, now_ms):
    return int(g['time'].time() * 1000) if now_ms is None else int(now_ms)


def _completed(now_ms):
    probe = dt.datetime.fromtimestamp(now_ms / 1000, events42.NY).date() + dt.timedelta(days=1)
    for _ in range(12):
        probe -= dt.timedelta(days=1)
        if not events42.is_session(probe):
            continue
        close = events42.close_on(probe)
        if close is not None and int(close.timestamp() * 1000) <= now_ms:
            return probe
    raise ValueError('No completed session is available.')


def _week(now_ms):
    end = _completed(now_ms)
    days = [end]
    while len(days) < 5:
        days.append(events42.previous_session(days[-1]))
    return days[-1].isoformat(), end.isoformat()


def _sessions(start, end):
    days = []
    cursor = dt.date.fromisoformat(start)
    last = dt.date.fromisoformat(end)
    while cursor <= last:
        if events42.is_session(cursor):
            days.append(cursor.isoformat())
        cursor += dt.timedelta(days=1)
    return days


def propose(g, text, now_ms=None):
    if not question(text):
        raise ValueError('Ask to investigate a company’s latest completed weekly move.')
    token = str(text).replace('’', "'").split()[1].split("'")[0].rstrip('.,')
    symbol = g['valid_symbol'](token)
    now_ms = _now(g, now_ms)
    return {
        'method': INVESTIGATION, 'question': str(text).strip(), 'symbol': symbol,
        'status': 'proposed', 'calculated': False, 'offline': True,
        'summary': f'{symbol}: five steps are ready. No return has been calculated yet.',
        'steps': [{'id': ident, 'title': title, 'status': 'pending', 'detail': '', 'refs': []} for ident, title in STEPS],
        'retrievedAt': now_ms,
    }


def _job_id(question, now_ms):
    return hashlib.sha256(f'{question}|{now_ms}'.encode()).hexdigest()[:16]


def _write(g, row):
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('INSERT OR REPLACE INTO desk61_jobs VALUES(?,?,?,?,?,?)', (
            row['id'], row['question'], row['status'], json.dumps(row, allow_nan=False),
            row['createdAt'], row['updatedAt']))
    return row


def read(g, ident):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        row = con.execute('SELECT body FROM desk61_jobs WHERE id=?', (str(ident or ''),)).fetchone()
    if not row:
        raise ValueError('That investigation is not saved on this Mac.')
    saved = json.loads(row[0])
    saved['notice'] = 'Opened from the saved investigation. It was not recalculated.'
    return saved


def start(g, text, now_ms=None):
    plan = propose(g, text, now_ms)
    now_ms = plan['retrievedAt']
    plan.update(id=_job_id(plan['question'], now_ms), status='running', createdAt=now_ms, updatedAt=now_ms)
    return _write(g, plan)


def _bars(g, symbol):
    with contextlib.closing(g['db_connection']()) as con:
        return con.execute(
            'SELECT ts_ms,o,h,l,c,v,fetched_at FROM massive_daily_bars WHERE symbol=? ORDER BY ts_ms',
            (symbol,)).fetchall()


def _points(g, symbol, start, end):
    found = {}
    for ts, _o, _h, _l, close, _v, fetched in _bars(g, symbol):
        if not isinstance(close, (int, float)) or isinstance(close, bool) or close <= 0:
            continue
        day = dt.datetime.fromtimestamp(ts / 1000, events42.NY).date().isoformat()
        if start and day < start or end and day > end:
            continue
        published = events42.close_on(dt.date.fromisoformat(day))
        retrieved = int(fetched)
        if retrieved < 10_000_000_000:
            retrieved *= 1000
        item = {
            'date': day, 'price': float(close), 'retrievedAt': retrieved,
            'publishedAt': int(published.timestamp() * 1000) if published else None,
        }
        if day not in found or item['retrievedAt'] >= found[day]['retrievedAt']:
            found[day] = item
    return [found[day] for day in sorted(found)]


def _fingerprint(points):
    rows = [(item['date'], item['price']) for item in points if item.get('price')]
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()[:16]


def _step(job, ident):
    return next(item for item in job['steps'] if item['id'] == ident)


def _advance(g, job, now_ms):
    pending = next((item for item in job['steps'] if item['status'] == 'pending'), None)
    if pending is None:
        job['status'] = 'done'
        return job
    symbol = job['symbol']
    if pending['id'] == 'week':
        start, end = _week(now_ms)
        job['start'], job['end'] = start, end
        pending['detail'] = f'{start} to {end}, five completed New York sessions.'
        pending['refs'] = [reference('period', symbol, periodStart=start, periodEnd=end,
                                      retrievedAt=now_ms, method=INVESTIGATION, source='New York equity calendar')]
        pending['status'] = 'done'
    elif pending['id'] == 'return':
        try:
            review = move44.review(g, symbol, job['start'], job['end'], now_ms)
        except (OSError, ValueError) as error:
            review = {'status': 'withheld', 'reason': str(error), 'gaps': [str(error)]}
        job['review'] = review
        points = _points(g, symbol, job['start'], job['end'])
        job['fingerprint'] = _fingerprint(points)
        if review.get('status') != 'ready':
            pending['status'] = 'gap'
            pending['detail'] = review.get('reason') or 'The saved closes do not support a return.'
        else:
            pending['status'] = 'done'
            pending['detail'] = f"{review['returnPct']:.2f}% from {review['startPrice']:g} to {review['endPrice']:g}."
            pending['refs'] = [
                reference('price', symbol, value=item['price'], periodStart=item['date'], periodEnd=item['date'],
                          publishedAt=item['publishedAt'], retrievedAt=item['retrievedAt'],
                          source=move44.SOURCE, method=INVESTIGATION)
                for item in points if item['date'] in (job['start'], job['end'])]
    elif pending['id'] == 'benchmark':
        review = job.get('review') or {}
        comparison = review.get('comparison') or {}
        if comparison.get('status') == 'ready':
            pending['status'] = 'done'
            pending['detail'] = f"SPY {comparison['returnPct']:.2f}%. Difference {comparison['differencePP']:.2f} percentage points."
            pending['refs'] = [reference('price', 'SPY', value=comparison.get('endPrice'),
                                          periodStart=job.get('start'), periodEnd=job.get('end'),
                                          retrievedAt=now_ms, source=move44.SOURCE, method='move44')]
        else:
            pending['status'] = 'gap'
            pending['detail'] = comparison.get('reason') or review.get('reason') or 'SPY comparison is unavailable.'
    elif pending['id'] == 'events':
        review = job.get('review') or {}
        rows = [*(review.get('before') or []), *(review.get('uncertain') or []), *(review.get('after') or [])]
        saved = events42.load(g, symbol) or {}
        by_title = {row.get('title'): row for row in (saved.get('events') or [])}
        pending['refs'] = [reference('news' if row.get('kindLabel') != 'Regulatory filing' else 'filing', symbol,
                                      periodStart=job.get('start'), periodEnd=job.get('end'),
                                      publishedAt=(by_title.get(row.get('title')) or {}).get('publishedAt'),
                                      retrievedAt=saved.get('updatedAt'),
                                      source=row.get('source') or row.get('publisher') or '',
                                      value=((row.get('kindLabel') or 'Saved item') + ' · ' + (row.get('title') or '')),
                                      method=INVESTIGATION) for row in rows[:8]]
        pending['status'] = 'done' if rows else 'gap'
        counts = {}
        for row in rows:
            label = row.get('kindLabel') or 'Saved item'
            counts[label] = counts.get(label, 0) + 1
        breakdown = '. '.join(f'{count} {label}' for label, count in counts.items())
        pending['detail'] = (f'{len(rows)} saved items. {breakdown}.') if rows else 'No saved filing, announcement or news is attached to this move.'
    else:
        review = job.get('review') or {}
        if review.get('status') == 'ready':
            pending['status'] = 'done'
            pending['detail'] = (
                f"{symbol} {review['returnPct']:.2f}% from {job['start']} to {job['end']}. "
                + (review.get('evidence') or '') + ' ' + (_step(job, 'benchmark')['detail'] or ''))
        else:
            pending['status'] = 'gap'
            pending['detail'] = 'No return is included. ' + (review.get('reason') or 'The saved records are incomplete.')
        job['status'] = 'done'
    if pending['id'] != 'finding' and all(item['status'] != 'pending' for item in job['steps']):
        job['status'] = 'done'
    job['updatedAt'] = now_ms
    return job


def step(g, ident, now_ms=None):
    job = read(g, ident)
    now_ms = _now(g, now_ms)
    if job['status'] == 'cancelled':
        raise ValueError('Resume the investigation before the next step.')
    if job['status'] == 'done':
        return job
    job['status'] = 'running'
    _advance(g, job, now_ms)
    return _write(g, job)


def run_all(g, ident, now_ms=None):
    job = read(g, ident)
    now_ms = _now(g, now_ms)
    while job['status'] not in ('done', 'cancelled'):
        job = step(g, job['id'], now_ms)
    return job


def cancel(g, ident, now_ms=None):
    job = read(g, ident)
    job['status'] = 'cancelled'
    job['updatedAt'] = _now(g, now_ms)
    job['notice'] = 'Cancelled. Completed steps stay as they were.'
    return _write(g, job)


def resume(g, ident, now_ms=None):
    job = read(g, ident)
    if job['status'] == 'done':
        job['notice'] = 'This investigation is already complete.'
        return job
    job['status'] = 'running'
    job['updatedAt'] = _now(g, now_ms)
    job['notice'] = 'Resumed from the next unfinished step.'
    return _write(g, job)


def trace(job):
    if not job or not job.get('steps'):
        raise ValueError('Save an investigation before tracing it.')
    return {
        'method': job.get('method') or INVESTIGATION, 'question': job.get('question'),
        'status': job.get('status'), 'offline': True,
        'steps': [{
            'title': item['title'], 'status': item['status'], 'detail': item.get('detail') or '',
            'references': item.get('refs') or [],
        } for item in job['steps'] if item['status'] != 'pending'],
    }


def affected(g, ident, now_ms=None):
    job = read(g, ident)
    if not job.get('start'):
        return {**job, 'affected': False, 'notice': 'The week has not been chosen yet.'}
    current = _fingerprint(_points(g, job['symbol'], job['start'], job['end']))
    changed = bool(job.get('fingerprint')) and current != job.get('fingerprint')
    return {**job, 'affected': changed, 'currentFingerprint': current,
            'notice': 'Saved closes in this week have changed.' if changed else 'The saved closes match this investigation.'}


def refresh(g, ident, now_ms=None):
    previous = read(g, ident)
    now_ms = _now(g, now_ms)
    check = affected(g, ident, now_ms)
    if not check['affected']:
        return {**previous, 'notice': 'The saved observations are unchanged. The original investigation was kept.'}
    fresh = start(g, previous['question'], now_ms)
    fresh['previousId'] = previous['id']
    _write(g, fresh)
    finished = run_all(g, fresh['id'], now_ms)
    finished['previousId'] = previous['id']
    finished['notice'] = 'A new calculation was saved. The original investigation was not changed.'
    stored = _write(g, finished)
    original = read(g, previous['id'])
    if original.get('fingerprint') != previous.get('fingerprint'):
        raise ValueError('The original investigation changed.')
    return stored


def assemble(symbols, books, start, end, shared, mode, events=None, annotations=None):
    if not 1 <= len(symbols) <= 4 or len(set(symbols)) != len(symbols):
        raise ValueError('Choose one to four different companies.')
    if mode not in ('price', 'percent'):
        raise ValueError('Choose price or percentage.')
    calendar = _sessions(start, end) if start and end else []
    panels = []
    for symbol in symbols:
        points = sorted(books.get(symbol) or [], key=lambda item: item['date'])
        if shared and calendar:
            have = {item['date']: item for item in points}
            aligned, missing = [], []
            for day in calendar:
                if day in have:
                    aligned.append(have[day])
                else:
                    missing.append(day)
                    aligned.append({'date': day, 'price': None, 'plot': None})
            points = aligned
        else:
            missing = []
            if points:
                for day in _sessions(points[0]['date'], points[-1]['date']):
                    if not any(item['date'] == day for item in points):
                        missing.append(day)
        base = next((item['price'] for item in points if item.get('price')), None)
        plotted = []
        for item in points:
            price = item.get('price')
            plot = None if price is None or base is None else (price / base * 100 if mode == 'percent' else price)
            plotted.append({**item, 'plot': plot})
        panels.append({
            'symbol': symbol, 'points': plotted, 'missing': missing,
            'events': [row for row in (events or {}).get(symbol) or []],
            'annotations': [row for row in (annotations or {}).get(symbol) or []],
            'calendar': 'New York equity sessions',
        })
    return {'method': BOARD, 'symbols': list(symbols), 'start': start, 'end': end,
            'shared': bool(shared), 'mode': mode, 'panels': panels, 'offline': True}


def build(g, body, now_ms=None):
    symbols = []
    for item in body.get('symbols') or []:
        symbol = g['valid_symbol'](item)
        if '-' in symbol:
            raise ValueError('This board uses US equity sessions. Crypto keeps its own calendar.')
        if symbol not in symbols:
            symbols.append(symbol)
    now_ms = _now(g, now_ms)
    start = str(body.get('start') or '')
    end = str(body.get('end') or '')
    if not start or not end:
        end_day = _completed(now_ms)
        days = [end_day]
        while len(days) < 21:
            days.append(events42.previous_session(days[-1]))
        start, end = days[-1].isoformat(), end_day.isoformat()
    books = {symbol: _points(g, symbol, start, end) for symbol in symbols}
    events, annotations = {}, {}
    try:
        import annotate60
    except ImportError:
        annotate60 = None
    for symbol in symbols:
        saved = events42.load(g, symbol) or {}
        marked = []
        for row in saved.get('events') or []:
            published = row.get('publishedAt')
            if not isinstance(published, (int, float)):
                continue
            marked.append({'date': dt.datetime.fromtimestamp(published / 1000, events42.NY).date().isoformat(),
                           'title': row.get('title') or '', 'publishedAt': int(published),
                           'retrievedAt': saved.get('updatedAt')})
        events[symbol] = [row for row in marked if (not start or row['date'] >= start) and (not end or row['date'] <= end)]
        annotations[symbol] = annotate60.for_symbol(g, symbol) if annotate60 else []
    built = assemble(symbols, books, start, end, bool(body.get('shared')), body.get('mode') or 'price',
                     events, annotations)
    built['fingerprint'] = _fingerprint([point for panel in built['panels'] for point in panel['points']])
    built['retrievedAt'] = now_ms
    return built


def save_board(g, body, now_ms=None):
    built = build(g, body, now_ms)
    now_ms = built['retrievedAt']
    built['id'] = hashlib.sha256(json.dumps(built['fingerprint'] + str(now_ms)).encode()).hexdigest()[:16]
    built['createdAt'] = now_ms
    built['notice'] = 'Saved on this Mac.'
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('INSERT INTO desk61_boards VALUES(?,?,?)', (built['id'], json.dumps(built, allow_nan=False), now_ms))
    return built


def read_board(g, ident):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        row = con.execute('SELECT body FROM desk61_boards WHERE id=?', (str(ident or ''),)).fetchone()
    if not row:
        raise ValueError('That chart board is not saved on this Mac.')
    saved = json.loads(row[0])
    saved['notice'] = 'Opened from the saved board. It was not rebuilt.'
    return saved


def evaluate_candidate(g, name, params, prices, now_ms=None):
    name = str(name or '').strip()[:40]
    if not name:
        raise ValueError('Name the candidate.')
    now_ms = _now(g, now_ms)
    horizon = int((params or {}).get('horizon') or 5)
    full = learning40.evaluate(prices, horizon)
    mid = max(1, len(prices) // 2)
    windows = []
    for label, part in (('earlier', prices[:mid]), ('later', prices[mid:])):
        windows.append({'label': label, 'observations': len(part), 'result': learning40.evaluate(part, horizon)})
    digest = hashlib.sha256(json.dumps([(item.get('t'), item.get('p')) for item in prices]).encode()).hexdigest()[:16]
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        trials = con.execute('SELECT count(*) FROM desk61_models WHERE body LIKE ?', (f'%{digest}%',)).fetchone()[0] + 1
        useful = full.get('status') == 'learned' and all(
            item['result'].get('status') in ('learned', 'insufficient') for item in windows) and any(
            item['result'].get('status') == 'learned' for item in windows)
        active = name if useful and all(item['result'].get('status') != 'baseline' for item in windows if item['result'].get('status') != 'insufficient') else 'baseline'
        body = {
            'method': LEDGER, 'name': name, 'params': params or {}, 'observations': digest,
            'trials': trials, 'full': full, 'windows': windows, 'activeMethod': active,
            'criteria': list(CRITERIA), 'issuedForecasts': 'left unchanged',
            'note': f'This is candidate {trials} on these observations. Earlier results stay saved.',
        }
        ident = hashlib.sha256(f'{name}|{digest}|{trials}'.encode()).hexdigest()[:16]
        body['id'] = ident
        con.execute('INSERT INTO desk61_models VALUES(?,?,?,?)', (ident, name, json.dumps(body, allow_nan=False), now_ms))
    return body


def evaluate_symbol(g, symbol, now_ms=None):
    symbol = g['valid_symbol'](symbol)
    now_ms = _now(g, now_ms)
    points = _points(g, symbol, '', '')
    prices = [{'t': item.get('publishedAt') or index, 'p': item['price']} for index, item in enumerate(points)]
    if len(prices) < 220:
        body = {
            'method': LEDGER, 'name': symbol, 'observations': len(prices), 'trials': 1,
            'full': {'status': 'insufficient', 'testCases': 0}, 'windows': [],
            'activeMethod': 'baseline', 'criteria': list(CRITERIA), 'issuedForecasts': 'left unchanged',
            'note': f'{symbol} has {len(prices)} saved closes. The baseline stays active and no forecast was issued.',
        }
        ident = hashlib.sha256(f'{symbol}|short|{now_ms}'.encode()).hexdigest()[:16]
        body['id'] = ident
        with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
            init(con)
            con.execute('INSERT INTO desk61_models VALUES(?,?,?,?)', (ident, symbol, json.dumps(body), now_ms))
        return body
    return evaluate_candidate(g, symbol + ' sessions', {'horizon': 5}, prices, now_ms)


def experiments(g):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        rows = con.execute('SELECT body FROM desk61_models ORDER BY created_at').fetchall()
    return [json.loads(row[0]) for row in rows]


def inspect(g, symbol, now_ms=None):
    symbol = g['valid_symbol'](symbol)
    now_ms = _now(g, now_ms)
    grouped = {}
    for ts, o, h, low, close, volume, fetched in _bars(g, symbol):
        day = dt.datetime.fromtimestamp(ts / 1000, events42.NY).date().isoformat()
        grouped.setdefault(day, []).append(
            {'ts': ts, 'o': o, 'h': h, 'l': low, 'c': close, 'v': volume, 'fetchedAt': fetched})
    problems = []
    for day, rows in grouped.items():
        if len(rows) > 1:
            problems.append({'kind': 'duplicate', 'date': day, 'count': len(rows)})
    dates = sorted(grouped)
    if dates:
        for day in _sessions(dates[0], dates[-1]):
            if day not in grouped:
                problems.append({'kind': 'missing', 'date': day})
        ordered = [grouped[day][-1]['c'] for day in dates if grouped[day][-1]['c'] > 0]
        for older, newer, day in zip(ordered, ordered[1:], dates[1:]):
            if older > 0 and abs(math.log(newer / older)) > 0.7:
                problems.append({'kind': 'adjustment', 'date': day})
        try:
            latest = _completed(now_ms)
            cursor, behind = latest, 0
            while cursor.isoformat() > dates[-1] and behind <= 6:
                cursor = events42.previous_session(cursor)
                behind += 1
            if behind >= 5:
                problems.append({'kind': 'stale', 'date': dates[-1], 'sessionsBehind': behind})
        except ValueError:
            problems.append({'kind': 'collection', 'date': '', 'detail': 'No completed session could be checked.'})
    with contextlib.closing(g['db_connection']()) as con:
        imported = con.execute('SELECT payload FROM imported_daily_history WHERE symbol=?', (symbol,)).fetchone()
    if imported:
        problems.append({'kind': 'imported', 'date': '', 'detail': 'User-imported history is present and will not be changed.'})
    digest = hashlib.sha256(json.dumps(problems, sort_keys=True).encode()).hexdigest()[:16]
    report = {'id': digest, 'method': REPAIR, 'symbol': symbol, 'problems': problems, 'retrievedAt': now_ms,
              'notice': 'Inspected only. Nothing was changed.'}
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('INSERT OR REPLACE INTO desk61_repairs VALUES(?,?,?,?)',
                    (digest, symbol, json.dumps(report), now_ms))
    return report


def repair(g, symbol, inspect_id, now_ms=None):
    current = inspect(g, symbol, now_ms)
    if current['id'] != str(inspect_id or ''):
        raise ValueError('Inspect the current records before repairing them.')
    duplicates = [item for item in current['problems'] if item['kind'] == 'duplicate']
    if not duplicates:
        raise ValueError('No duplicate sessions are waiting.')
    now_ms = current['retrievedAt']
    batch = hashlib.sha256(f'{symbol}|{inspect_id}|{now_ms}'.encode()).hexdigest()[:16]
    removed = 0
    try:
        with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
            init(con)
            rows = con.execute(
                'SELECT ts_ms,o,h,l,c,v,fetched_at FROM massive_daily_bars WHERE symbol=? ORDER BY ts_ms', (symbol,)).fetchall()
            for item in duplicates:
                same = [row for row in rows
                        if dt.datetime.fromtimestamp(row[0] / 1000, events42.NY).date().isoformat() == item['date']]
                keep = max(same, key=lambda row: (row[6], row[0]))
                for row in same:
                    if row == keep:
                        continue
                    con.execute('INSERT INTO desk61_removed(batch,symbol,ts_ms,o,h,l,c,v,fetched_at) VALUES(?,?,?,?,?,?,?,?,?)',
                                (batch, symbol, *row))
                    con.execute('DELETE FROM massive_daily_bars WHERE symbol=? AND ts_ms=?', (symbol, row[0]))
                    removed += 1
            if g.get('desk61_fail'):
                raise sqlite3.OperationalError('interrupted write')
    except sqlite3.OperationalError:
        raise ValueError('The repair was interrupted and the original bars were kept.')
    return {'id': batch, 'symbol': symbol, 'removed': removed, 'method': REPAIR,
            'notice': 'Duplicate Massive bars were collapsed. User-imported history was not written.'}


def undo_repair(g, symbol):
    symbol = g['valid_symbol'](symbol)
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        batch = con.execute('SELECT batch FROM desk61_removed WHERE symbol=? ORDER BY id DESC LIMIT 1', (symbol,)).fetchone()
        if not batch:
            raise ValueError('No repair is waiting to be undone.')
        rows = con.execute('SELECT ts_ms,o,h,l,c,v,fetched_at FROM desk61_removed WHERE batch=?', (batch[0],)).fetchall()
        for row in rows:
            con.execute('INSERT OR REPLACE INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)', (symbol, *row))
        con.execute('DELETE FROM desk61_removed WHERE batch=?', (batch[0],))
    return {'symbol': symbol, 'restored': len(rows), 'notice': 'The removed bars were put back.'}
