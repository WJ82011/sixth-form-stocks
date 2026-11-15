"""One recoverable research schedule for the existing local collector."""
import contextlib
import threading
import time

import coverage41
import desk50
import learning40
import market37

KINDS = ('history', 'grade', 'learn')
BUSY = threading.Lock()
GAP_MS = 12 * 60 * 1000


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS overnight51_schedule(
        id INTEGER PRIMARY KEY CHECK(id=1), symbols TEXT NOT NULL, start_hour INTEGER NOT NULL,
        end_hour INTEGER NOT NULL, research_hour INTEGER NOT NULL, quiet INTEGER NOT NULL,
        paused INTEGER NOT NULL, quiet_learn_day TEXT, updated_at INTEGER NOT NULL)''')
    con.execute('''CREATE TABLE IF NOT EXISTS overnight51_jobs(
        id TEXT PRIMARY KEY, day TEXT NOT NULL, kind TEXT NOT NULL, symbol TEXT NOT NULL,
        status TEXT NOT NULL, progress TEXT NOT NULL, detail TEXT NOT NULL,
        started_at INTEGER, finished_at INTEGER, updated_at INTEGER NOT NULL)''')
    con.execute('CREATE TABLE IF NOT EXISTS overnight51_beats(at_ms INTEGER PRIMARY KEY)')


def _row(con):
    found = con.execute('SELECT symbols,start_hour,end_hour,research_hour,quiet,paused,quiet_learn_day,updated_at FROM overnight51_schedule WHERE id=1').fetchone()
    if not found:
        return {'symbols': [], 'startHour': 0, 'endHour': 24, 'researchHour': 6, 'quiet': 0, 'paused': 0, 'quietLearnDay': '', 'updatedAt': 0}
    symbols = [part for part in found[0].split(',') if part]
    return {'symbols': symbols, 'startHour': found[1], 'endHour': found[2], 'researchHour': found[3],
            'quiet': found[4], 'paused': found[5], 'quietLearnDay': found[6] or '', 'updatedAt': found[7]}


def schedule(g):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        return _row(con)


def save_schedule(g, body, now_ms):
    symbols = []
    for item in body.get('symbols') or []:
        symbol = g['valid_symbol'](item)
        if not g['ai_catalog_entry'](symbol):
            raise ValueError(symbol + ' is not in the supported US stock list.')
        if symbol not in symbols:
            symbols.append(symbol)
    if len(symbols) > 16:
        raise ValueError('Choose up to 16 followed companies. Leave the list empty to use the watchlist.')
    try:
        start, end, research = (int(body[key]) for key in ('startHour', 'endHour', 'researchHour'))
    except (KeyError, TypeError, ValueError):
        raise ValueError('Collection hours and the research hour need whole hours.')
    if not (0 <= start <= 24 and 0 <= end <= 24 and 0 <= research <= 23):
        raise ValueError('Collection hours run from 0 to 24. The research hour runs from 0 to 23.')
    if start == end:
        raise ValueError('Choose a collection window longer than zero hours.')
    quiet = 1 if body.get('quiet') else 0
    paused = 1 if body.get('paused') else 0
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        current = _row(con)
        con.execute('''INSERT OR REPLACE INTO overnight51_schedule
            VALUES(1,?,?,?,?,?,?,?,?)''', (','.join(symbols), start, end, research, quiet, paused, current['quietLearnDay'], int(now_ms)))
    saved = schedule(g)
    saved['notice'] = 'Scheduled work runs only while this Mac is awake and Market Desk is running.'
    return saved


def set_paused(g, paused, now_ms):
    current = schedule(g)
    current['paused'] = 1 if paused else 0
    return save_schedule(g, current, now_ms)


def ny(now_ms):
    return market37.dt.datetime.fromtimestamp(now_ms / 1000, market37.NY)


def in_window(saved, moment):
    hour = moment.hour + moment.minute / 60
    start, end = saved['startHour'], saved['endHour']
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end


def research_reachable(saved):
    probe = ny(0).replace(hour=saved['researchHour'], minute=0, second=0, microsecond=0)
    return in_window(saved, probe)


def followed(g, saved):
    raw = list(saved['symbols'])
    if not raw:
        snapshot = g['read_workspace']().get('snapshot') or {}
        raw = snapshot.get('watch') or []
    chosen = []
    for item in raw:
        try:
            symbol = g['valid_symbol'](item)
        except (TypeError, ValueError):
            continue
        if g['ai_catalog_entry'](symbol) and symbol not in chosen:
            chosen.append(symbol)
    ranked = coverage41.priority(g, chosen[:16])
    ordered = ranked + [symbol for symbol in chosen if symbol not in ranked]
    return ordered[:16]


def _finish(con, ident, status, detail, now_ms):
    con.execute('''UPDATE overnight51_jobs SET status=?, detail=?, progress=?, finished_at=?, updated_at=?
        WHERE id=?''', (status, detail[:500], status, now_ms, now_ms, ident))


def recover(g, now_ms):
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('''UPDATE overnight51_jobs SET status='waiting', progress='resume', updated_at=?,
            detail=substr(detail || ' Interrupted by a restart. The same job resumes. No second forecast record is created.', 1, 500)
            WHERE status='running' ''', (int(now_ms),))


def enqueue(g, now_ms):
    saved = schedule(g)
    moment = ny(now_ms)
    if not in_window(saved, moment):
        return saved
    day = moment.date().isoformat()
    symbols = followed(g, saved)
    research = moment.hour >= saved['researchHour']
    reachable = research_reachable(saved)
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('''UPDATE overnight51_jobs SET status='attention', progress='attention', updated_at=?,
            detail='Not finished before the next research day. No second forecast was written.'
            WHERE day<? AND status='waiting' ''', (int(now_ms), day))
        if symbols:
            marks = ','.join('?' for _ in symbols)
            con.execute('''UPDATE overnight51_jobs SET status='attention', progress='attention', updated_at=?,
                detail='Left out of today’s 16-company schedule so the free feed stays within its limit.'
                WHERE day=? AND status='waiting' AND symbol NOT IN (''' + marks + ')', (int(now_ms), day, *symbols))
        for symbol in symbols:
            kinds = ['history']
            if research:
                kinds.extend(['grade', 'learn'])
            for kind in kinds:
                ident = day + ':' + kind + ':' + symbol
                detail = 'Waiting for ' + symbol + '.'
                status = 'waiting'
                if kind != 'history' and not reachable:
                    status = 'attention'
                    detail = 'The research hour is outside the collection hours, so this job will not run. Change one of those times in Settings.'
                con.execute('''INSERT OR IGNORE INTO overnight51_jobs
                    VALUES(?,?,?,?,?,?,?,?,?,?)''', (ident, day, kind, symbol, status, status, detail, None, None, int(now_ms)))
    return saved


def _bars(g, symbol):
    with contextlib.closing(g['db_connection']()) as con:
        return con.execute('SELECT COUNT(*) FROM massive_daily_bars WHERE symbol=?', (symbol,)).fetchone()[0]


def _graded(g, symbol):
    with contextlib.closing(g['db_connection']()) as con:
        return con.execute("SELECT COUNT(*) FROM learning41_issued WHERE symbol=? AND outcome IS NOT NULL", (symbol,)).fetchone()[0]


def _run(g, job, now_ms):
    symbol = job['symbol']
    if job['kind'] == 'history':
        if not g['get_massive_key']():
            raise RuntimeError('Free daily history is not connected. Saved prices were kept.')
        before = _bars(g, symbol)
        end = int(now_ms / 1000)
        result = g['massive_daily_candles'](symbol, end - 731 * 86400, end)
        if result.get('status') != 'ok':
            raise RuntimeError(result.get('message') or 'The price provider did not return usable data. Saved prices were kept.')
        after = _bars(g, symbol)
        return symbol + ' daily history saved. Closes ' + str(before) + ' then ' + str(after) + '. Source: ' + str(result.get('source') or 'Massive') + '.'
    before = _graded(g, symbol)
    report = learning40.report(g, symbol)
    after = _graded(g, symbol)
    pending = len((report.get('scorecard') or {}).get('pending') or [])
    return symbol + ' report used ' + str(report.get('closes')) + ' closes. Newly graded forecasts: ' + str(after - before) + '. Still waiting: ' + str(pending) + '.'


def step(g, now_ms=None):
    now_ms = int(g['time'].time() * 1000) if now_ms is None else int(now_ms)
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('INSERT OR IGNORE INTO overnight51_beats VALUES(?)', (now_ms,))
        con.execute('DELETE FROM overnight51_beats WHERE at_ms<?', (now_ms - 14 * 86400000,))
    try:
        import tracker65
        tracker65.sweep(g, now_ms)
    except Exception:
        pass
    saved = enqueue(g, now_ms)
    moment = ny(now_ms)
    if saved['paused'] or not in_window(saved, moment):
        return {'state': 'idle', 'reason': 'paused' if saved['paused'] else 'outside'}
    try:
        import scanner55
        scanner55.scheduled(g, now_ms)
    except Exception:
        pass
    if not BUSY.acquire(blocking=False):
        return {'state': 'busy'}
    try:
        day = moment.date().isoformat()
        with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
            init(con)
            found = con.execute('''SELECT id,kind,symbol FROM overnight51_jobs
                WHERE status='waiting' AND day=? ORDER BY CASE kind WHEN 'history' THEN 0 WHEN 'grade' THEN 1 ELSE 2 END, symbol LIMIT 1''', (day,)).fetchone()
            if not found:
                return {'state': 'idle'}
            changed = con.execute("UPDATE overnight51_jobs SET status='running', progress='running', started_at=?, updated_at=? WHERE id=? AND status='waiting'",
                                  (now_ms, now_ms, found[0]))
            if changed.rowcount != 1:
                return {'state': 'idle'}
            job = {'id': found[0], 'kind': found[1], 'symbol': found[2]}
        if saved['quiet'] and job['kind'] == 'learn' and saved['quietLearnDay'] == day:
            detail = job['symbol'] + ' training was left for another day. Quiet mode already trained one company today. Issued forecasts were not changed.'
            status = 'completed'
        else:
            try:
                detail = _run(g, job, now_ms)
                status = 'completed'
            except Exception as error:
                detail = str(error)[:500] or 'This job needs attention.'
                status = 'attention'
        with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
            _finish(con, job['id'], status, detail, now_ms)
            if saved['quiet'] and job['kind'] in ('grade', 'learn') and status == 'completed' and 'left for another day' not in detail:
                con.execute('UPDATE overnight51_schedule SET quiet_learn_day=? WHERE id=1', (day,))
        return {'state': status, 'id': job['id'], 'detail': detail}
    finally:
        BUSY.release()


def loop(g, stop):
    recover(g, int(time.time() * 1000))
    while not stop.is_set():
        try:
            step(g)
        except Exception:
            pass
        saved = schedule(g)
        stop.wait(90 if saved['quiet'] else 12)


def jobs(g, day=None):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        if day:
            rows = con.execute('''SELECT id,day,kind,symbol,status,progress,detail,started_at,finished_at,updated_at
                FROM overnight51_jobs WHERE day=? ORDER BY updated_at''', (day,)).fetchall()
        else:
            rows = con.execute('''SELECT id,day,kind,symbol,status,progress,detail,started_at,finished_at,updated_at
                FROM overnight51_jobs ORDER BY updated_at DESC LIMIT 80''').fetchall()
    return [{'id': row[0], 'day': row[1], 'kind': row[2], 'symbol': row[3], 'status': row[4], 'progress': row[5],
             'detail': row[6], 'startedAt': row[7], 'finishedAt': row[8], 'updatedAt': row[9]} for row in rows]


def gaps(g, since_ms, now_ms):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        beats = [row[0] for row in con.execute('SELECT at_ms FROM overnight51_beats WHERE at_ms>=? AND at_ms<=? ORDER BY at_ms', (int(since_ms), int(now_ms)))]
    points = [int(since_ms)] + beats + [int(now_ms)]
    found = []
    for left, right in zip(points, points[1:]):
        if right - left > GAP_MS:
            found.append({'from': left, 'to': right,
                          'note': 'No heartbeat for this stretch. The Mac was asleep, offline, or Market Desk was stopped. This log cannot tell those apart.'})
    return found[:12]


def morning(g, since_ms, now_ms):
    saved = schedule(g)
    storage = desk50.storage(g)
    with contextlib.closing(g['db_connection']()) as con:
        history = con.execute("SELECT finished_at FROM overnight51_jobs WHERE kind='history' AND status='completed' ORDER BY finished_at DESC LIMIT 1").fetchone()
        trained = con.execute("SELECT finished_at FROM overnight51_jobs WHERE kind='learn' AND status='completed' AND detail NOT LIKE '%left for another day%' ORDER BY finished_at DESC LIMIT 1").fetchone()
        fresh = con.execute('SELECT symbol,COUNT(*) FROM massive_daily_bars WHERE fetched_at>=? GROUP BY symbol ORDER BY symbol', (int(since_ms) // 1000,)).fetchall()
    rows = [row for row in jobs(g) if row['updatedAt'] and row['updatedAt'] >= int(since_ms)]
    return {'since': int(since_ms), 'schedule': saved, 'jobs': rows, 'gaps': gaps(g, since_ms, now_ms),
            'savedBars': [{'symbol': symbol, 'rowsTouched': count} for symbol, count in fresh],
            'lastHistoryAt': history[0] if history else None, 'lastTrainingAt': trained[0] if trained else None,
            'databaseBytes': storage['databaseBytes'], 'workspaceBytes': storage['workspaceBytes'],
            'notice': 'Scheduled work runs only while this Mac is awake and Market Desk is running. Closing the browser tab does not stop the server.'}


def status(g, now_ms):
    saved = schedule(g)
    report = morning(g, now_ms - 36 * 3600000, now_ms)
    return {'schedule': saved, 'inWindow': in_window(saved, ny(now_ms)), 'researchReachable': research_reachable(saved),
            'lastHistoryAt': report['lastHistoryAt'], 'lastTrainingAt': report['lastTrainingAt'],
            'databaseBytes': report['databaseBytes'], 'jobs': jobs(g, ny(now_ms).date().isoformat()),
            'notice': report['notice']}


def gate(g, now_ms=None):
    now_ms = int(g['time'].time() * 1000) if now_ms is None else int(now_ms)
    saved = schedule(g)
    if saved['paused']:
        return 'paused'
    if not in_window(saved, ny(now_ms)):
        return 'outside'
    if saved['quiet']:
        return 'quiet'
    return 'ok'
