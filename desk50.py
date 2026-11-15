"""Connected research checks from saved records. No provider call and no language model."""
import contextlib
import datetime as dt
import math
import os
import re
import shutil
import sqlite3

import events42
import journal49
import scorecard41

NY = events42.NY
BACKUP_RE = re.compile(r'^desk50-\d{8}T\d{6}Z(?:-\d+)?\.sqlite3$')


def _closes(g, symbol):
    try:
        with contextlib.closing(g['db_connection']()) as con:
            rows = con.execute('SELECT ts_ms,c,fetched_at FROM massive_daily_bars WHERE symbol=? ORDER BY ts_ms', (symbol,)).fetchall()
    except Exception:
        return []
    found = {}
    for ts, price, fetched in rows:
        if isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0:
            continue
        day = dt.datetime.fromtimestamp(ts / 1000, NY).date()
        found[day] = (float(price), int(ts), fetched)
    return sorted(found.items())


def _completed(points, now_ms):
    usable = []
    for day, payload in points:
        close = events42.close_on(day) if events42.is_session(day) else None
        if close is not None and int(close.timestamp() * 1000) <= now_ms:
            usable.append((day, payload))
    return usable


def unusual(g, symbol, now_ms):
    points = _completed(_closes(g, symbol), now_ms)
    if len(points) < 3:
        return {'status': 'withheld', 'reason': 'Not enough saved closes to compare this session with the company’s own history.', 'sampleSize': max(0, len(points) - 2)}
    *_, previous, last = points
    move = abs(last[1][0] / previous[1][0] - 1) * 100
    if abs(math.log(last[1][0] / previous[1][0])) > .7:
        return {'status': 'withheld', 'reason': 'The latest move is large enough to be a split or a bad print. It was not treated as unusual. Saved prices were not changed.', 'sampleSize': 0, 'start': previous[0].isoformat(), 'end': last[0].isoformat(), 'startPrice': previous[1][0], 'endPrice': last[1][0]}
    sample = []
    for left, right in zip(points, points[1:-1]):
        if left[1][0] > 0 and abs(math.log(right[1][0] / left[1][0])) <= .7:
            sample.append(abs(right[1][0] / left[1][0] - 1) * 100)
    if len(sample) < 20:
        return {'status': 'withheld', 'reason': f'Needs 20 valid earlier session moves. {len(sample)} are saved, so this comparison is not enabled.', 'sampleSize': len(sample), 'start': previous[0].isoformat(), 'end': last[0].isoformat(), 'startPrice': previous[1][0], 'endPrice': last[1][0]}
    ordered = sorted(sample)
    rank = ordered[max(0, math.ceil(.9 * len(ordered)) - 1)]
    gap = events42.previous_session(last[0]) != previous[0]
    return {
        'status': 'ready', 'unusual': move > rank, 'movePct': move, 'percentilePct': rank, 'sampleSize': len(sample),
        'start': previous[0].isoformat(), 'end': last[0].isoformat(), 'startPrice': previous[1][0], 'endPrice': last[1][0],
        'gap': gap, 'source': 'Massive · saved split-adjusted daily closes. Read from this Mac.',
    }


def changed_since(g, symbol, captured_at, original_price, now_ms):
    latest = journal49.latest(g, symbol, now_ms)
    events = []
    try:
        saved = events42.load(g, symbol) or {}
        for row in events42.dedupe([*(saved.get('events') or []), *events42.local_items(g, symbol)]):
            published = row.get('publishedAt')
            if isinstance(published, int) and captured_at and published > captured_at:
                events.append({'title': row.get('title') or '', 'source': row.get('source') or '', 'publishedAt': published})
    except Exception:
        events = []
    return {'latest': latest, 'newEvents': events[:8], 'newEventCount': len(events), 'originalPrice': original_price}


def model_report(g, symbol):
    card = scorecard41.read(g, symbol)
    cached = None
    try:
        with contextlib.closing(g['db_connection']()) as con:
            row = con.execute('SELECT body,trained_at FROM learning40 WHERE symbol=?', (symbol,)).fetchone()
        if row:
            import json
            cached = json.loads(row[0])
            cached['trainedAt'] = row[1]
    except Exception:
        cached = None
    return {'scorecard': card, 'cached': cached}


def price_status(g, symbol, now_ms=None):
    now_ms = int(g['time'].time() * 1000) if now_ms is None else int(now_ms)
    points = _closes(g, symbol)
    usable = _completed(points, now_ms)
    if not usable:
        return {'symbol': symbol, 'saved': 0, 'status': 'missing', 'detail': 'No saved daily close is available.', 'source': 'Massive · saved split-adjusted daily closes.'}
    first, last = usable[0], usable[-1]
    expected = []
    cursor = last[0]
    for _ in range(15):
        expected.append(cursor)
        cursor = events42.previous_session(cursor)
    have = {day for day, _ in usable}
    missing = [day.isoformat() for day in expected if day not in have]
    duplicate = len(points) != len({day for day, _ in points})
    stale_days = (dt.datetime.fromtimestamp(now_ms / 1000, NY).date() - last[0]).days
    state = 'current' if not missing and stale_days <= 5 else 'needs attention'
    detail = f'{len(usable)} saved closes from {first[0].isoformat()} to {last[0].isoformat()}.'
    if missing:
        detail += ' Missing ' + ', '.join(missing[:4]) + '.'
    if stale_days > 5:
        detail += f' The latest close is {stale_days} days old.'
    if duplicate:
        detail += ' More than one close was saved for a session. The latest saved close for that date is used.'
    return {'symbol': symbol, 'saved': len(usable), 'first': first[0].isoformat(), 'last': last[0].isoformat(), 'price': last[1][0], 'status': state, 'detail': detail, 'source': 'Massive · saved split-adjusted daily closes. Read from this Mac.', 'missing': missing[:8]}


def since(g, since_ms, symbols, now_ms):
    moves, gaps = [], []
    since_day = dt.datetime.fromtimestamp(since_ms / 1000, NY).date()
    for symbol in symbols[:12]:
        points = _completed(_closes(g, symbol), now_ms)
        if len(points) < 2:
            gaps.append(symbol + ': no saved close to compare.')
            continue
        before = [row for row in points if row[0] <= since_day]
        start = before[-1] if before else points[0]
        end = points[-1]
        if start[0] == end[0]:
            gaps.append(symbol + ': no newer saved close since ' + since_day.isoformat() + '.')
            continue
        moves.append({'symbol': symbol, 'start': start[0].isoformat(), 'end': end[0].isoformat(), 'startPrice': start[1][0], 'endPrice': end[1][0], 'returnPct': (end[1][0] / start[1][0] - 1) * 100, 'source': 'Massive · saved split-adjusted daily closes.'})
    alerts = []
    graded = []
    try:
        with contextlib.closing(g['db_connection']()) as con:
            alerts = [{'symbol': row[0], 'price': row[1], 'receivedAt': row[2], 'rule': row[3] or ''} for row in con.execute('SELECT symbol,price,received_at,rule_text FROM price_alert_events WHERE received_at>=? ORDER BY id DESC LIMIT 8', (since_ms,))]
    except Exception:
        alerts = []
    card = scorecard41.read(g, None)
    for row in (card.get('graded') or [])[:40]:
        graded_at = (row.get('outcome') or {}).get('gradedAt')
        if isinstance(graded_at, int) and graded_at >= since_ms:
            graded.append({'symbol': row.get('symbol'), 'anchorDay': row.get('anchorDay'), 'targetDay': row.get('targetDay'), 'forecastPrice': row.get('forecastPrice'), 'actualPrice': row['outcome'].get('actualPrice')})
    return {'since': since_ms, 'moves': moves[:8], 'alerts': alerts, 'graded': graded[:8], 'gaps': gaps[:8], 'notice': 'These are saved records from the last visit time. A gap means nothing newer was saved, not that the market was unchanged.'}


def _folder(g):
    folder = g['USER_DIR'] / 'backups'
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    return folder


def storage(g):
    database = g['DB_FILE']
    workspace = g['WORKSPACE_FILE']
    folder = g['USER_DIR'] / 'backups'
    backups = sorted(path.name for path in folder.glob('desk50-*.sqlite3')) if folder.exists() else []
    counts = {}
    try:
        with contextlib.closing(g['db_connection']()) as con:
            for table in ('observations', 'massive_daily_bars', 'price_alerts', 'price_alert_events', 'learning41_issued'):
                try:
                    counts[table] = con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                except Exception:
                    counts[table] = 0
    except Exception:
        pass
    return {
        'databaseBytes': database.stat().st_size if database.exists() else 0,
        'workspaceBytes': workspace.stat().st_size if workspace.exists() else 0,
        'backups': backups[-8:],
        'backupCount': len(backups),
        'counts': counts,
        'cleanup': 'Recorded prices already keep the latest 5,000 per company, and daily bars keep the latest 550. Old backups stay until you confirm “keep the newest 5”.',
    }


def create_backup(g):
    folder = _folder(g)
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    target = folder / f'desk50-{stamp}.sqlite3'
    suffix = 2
    while target.exists():
        target = folder / f'desk50-{stamp}-{suffix}.sqlite3'
        suffix += 1
    source = sqlite3.connect(g['DB_FILE'])
    copy = sqlite3.connect(target)
    try:
        source.backup(copy)
    finally:
        copy.close()
        source.close()
    os.chmod(target, 0o600)
    workspace = g['WORKSPACE_FILE']
    if workspace.exists():
        saved = target.with_name(target.stem + '.workspace.json')
        shutil.copyfile(workspace, saved)
        os.chmod(saved, 0o600)
    return {'file': target.name, 'bytes': target.stat().st_size}


def restore_backup(g, name, confirm):
    if confirm != 'restore-this-backup':
        raise ValueError('Restore was not confirmed. Nothing was changed.')
    if not BACKUP_RE.fullmatch(str(name or '')):
        raise ValueError('Choose one of the saved backup files.')
    folder = _folder(g)
    source_path = (folder / name).resolve()
    if source_path.parent != folder.resolve() or not source_path.exists():
        raise ValueError('That backup is not in the local backup folder.')
    create_backup(g)
    current = sqlite3.connect(g['DB_FILE'])
    incoming = sqlite3.connect(source_path)
    try:
        incoming.backup(current)
    finally:
        incoming.close()
        current.close()
    workspace = folder / name.replace('.sqlite3', '.workspace.json')
    if workspace.exists():
        shutil.copyfile(workspace, g['WORKSPACE_FILE'])
        os.chmod(g['WORKSPACE_FILE'], 0o600)
    return {'restored': name}


def trim_backups(g, confirm):
    if confirm != 'keep-newest-5':
        raise ValueError('Cleanup was not confirmed. No backup was deleted.')
    folder = _folder(g)
    files = sorted(folder.glob('desk50-*.sqlite3'))
    removed = []
    for path in files[:-5]:
        path.unlink()
        note = folder / path.name.replace('.sqlite3', '.workspace.json')
        if note.exists():
            note.unlink()
        removed.append(path.name)
    return {'removed': removed, 'kept': [path.name for path in files[-5:]]}
