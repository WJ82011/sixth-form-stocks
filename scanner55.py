"""Market Scanner. Conditions are checked against saved daily bars.

The latest observation is never used to build its own historical threshold.
A missing session, a split-sized jump, or a missing volume is omitted.
"""
import contextlib
import datetime as dt
import json
import math
import re

import market37

IDENT = re.compile(r'^[a-f0-9]{16}$')
DAY = re.compile(r'^\d{4}-\d{2}-\d{2}$')
SOURCE = 'Massive split-adjusted daily bar'
MODEL = 'market-scanner-v5.5'
SPLIT = 0.7
STALE_AFTER = 3
HISTORY_SAMPLE = 20

PRESETS = {
    'large-move': {'title': 'Large daily move', 'conditions': [{'kind': 'session_move', 'threshold': 'history', 'percentile': 90}]},
    'above-average': {'title': 'Above its recent average', 'conditions': [{'kind': 'above_average', 'sessions': 20}]},
    'closing-high': {'title': 'New closing high', 'conditions': [{'kind': 'closing_high', 'sessions': 20}]},
}


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS scanner55_scans(
        id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL, created_at INTEGER NOT NULL)''')
    con.execute('''CREATE TABLE IF NOT EXISTS scanner55_runs(
        id TEXT PRIMARY KEY, scan_id TEXT NOT NULL, day TEXT NOT NULL, body TEXT NOT NULL, created_at INTEGER NOT NULL)''')
    con.execute('''CREATE TABLE IF NOT EXISTS scanner55_members(
        scan_id TEXT NOT NULL, symbol TEXT NOT NULL, observation_date TEXT NOT NULL, PRIMARY KEY(scan_id, symbol))''')
    con.execute('''CREATE TABLE IF NOT EXISTS scanner55_alerts(
        id TEXT PRIMARY KEY, scan_id TEXT NOT NULL, symbol TEXT NOT NULL, observation_date TEXT NOT NULL,
        body TEXT NOT NULL, created_at INTEGER NOT NULL, UNIQUE(scan_id, symbol, observation_date))''')
    con.execute('''CREATE TABLE IF NOT EXISTS scanner55_day(id INTEGER PRIMARY KEY, day TEXT NOT NULL)''')


def _num(value, lo, hi, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(label + ' needs a finite number.')
    if not lo <= value <= hi:
        raise ValueError(label + ' is outside the supported range.')
    return float(value)


def _conditions(raw):
    if not isinstance(raw, list) or not 1 <= len(raw) <= 4:
        raise ValueError('Choose one to four conditions.')
    chosen = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError('Each condition needs a supported kind.')
        kind = item.get('kind')
        if kind == 'session_move':
            if item.get('threshold', 'history') == 'history':
                chosen.append({'kind': kind, 'threshold': 'history', 'percentile': _num(item.get('percentile', 90), 50, 99, 'Move percentile')})
            else:
                chosen.append({'kind': kind, 'threshold': _num(item.get('threshold'), 0.1, 100, 'Move threshold')})
        elif kind == 'above_average':
            chosen.append({'kind': kind, 'sessions': int(_num(item.get('sessions', 20), 2, 200, 'Average length'))})
        elif kind == 'closing_high':
            chosen.append({'kind': kind, 'sessions': int(_num(item.get('sessions', 20), 1, 250, 'Earlier closes'))})
        elif kind == 'unusual_volume':
            chosen.append({'kind': kind, 'percentile': _num(item.get('percentile', 90), 50, 99, 'Volume percentile')})
        else:
            raise ValueError('That condition is not supported by the saved daily bars.')
    return chosen


def _rule(raw):
    if isinstance(raw, str) and raw in PRESETS:
        raw = PRESETS[raw]
    if not isinstance(raw, dict):
        raise ValueError('Choose a scan.')
    return {'title': str(raw.get('title') or 'Saved scan')[:80], 'conditions': _conditions(raw.get('conditions')),
            'alert': bool(raw.get('alert')), 'schedule': bool(raw.get('schedule'))}


def _percentile(values, pct):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(pct / 100 * len(ordered)) - 1)]


def _session(day):
    return day.weekday() < 5 and day not in market37.holidays(day.year)


def _between(left, right):
    found = []
    day = left + dt.timedelta(days=1)
    while day < right:
        if _session(day):
            found.append(day.isoformat())
        day += dt.timedelta(days=1)
    return found


def _behind(last, as_of):
    count = 0
    day = last + dt.timedelta(days=1)
    while day <= as_of:
        if _session(day):
            count += 1
        day += dt.timedelta(days=1)
    return count


def explain(raw):
    rule = _rule(raw)
    lines = []
    for condition in rule['conditions']:
        if condition['kind'] == 'session_move' and condition['threshold'] == 'history':
            lines.append('Large daily move: the latest completed-session percentage move is at least the ' + format(condition['percentile'], '.0f') + 'th percentile of earlier absolute session moves. The latest move is not part of that sample. This needs ' + str(HISTORY_SAMPLE) + ' earlier moves. A gap or a split-sized jump is omitted.')
        elif condition['kind'] == 'session_move':
            lines.append('Completed-session move: the latest close is at least ' + format(condition['threshold'], '.2f') + '% away from the previous saved close. This needs two saved sessions with no missing session between them.')
        elif condition['kind'] == 'above_average':
            lines.append('Above its recent average: the latest close is above the ' + str(condition['sessions']) + '-session average, including that close. This needs ' + str(condition['sessions']) + ' saved closes.')
        elif condition['kind'] == 'closing_high':
            lines.append('New closing high: the latest close is above every one of the previous ' + str(condition['sessions']) + ' closes. This needs ' + str(condition['sessions'] + 1) + ' saved closes.')
        else:
            lines.append('Unusual daily volume: the latest volume is at least the ' + format(condition['percentile'], '.0f') + 'th percentile of earlier volumes. The latest volume is not part of that sample. A missing or zero volume is omitted. This needs ' + str(HISTORY_SAMPLE) + ' earlier volumes.')
    return {'model': MODEL, 'plainEnglish': ' '.join(lines), 'conditions': rule['conditions']}


def presets():
    return [{'id': key, 'title': value['title'], 'plainEnglish': explain(value)['plainEnglish'], 'conditions': value['conditions']} for key, value in PRESETS.items()]


def _moves(closes):
    sample = []
    for left, right in zip(closes, closes[1:]):
        if left <= 0 or abs(math.log(right / left)) > SPLIT:
            continue
        sample.append(abs(right / left - 1) * 100)
    return sample


def _one(symbol, bars, conditions, as_of, name):
    rows = [bar for bar in bars if bar.get('date') and bar['date'] <= as_of.isoformat()]
    rows.sort(key=lambda bar: bar['date'])
    if len(rows) < 2:
        return None, {'symbol': symbol, 'name': name, 'reason': 'insufficient', 'detail': 'Fewer than two saved daily bars.'}
    last = dt.date.fromisoformat(rows[-1]['date'])
    if _behind(last, as_of) > STALE_AFTER:
        return None, {'symbol': symbol, 'name': name, 'reason': 'stale', 'detail': 'The latest saved session is ' + rows[-1]['date'] + ', more than ' + str(STALE_AFTER) + ' completed sessions before ' + as_of.isoformat() + '.'}
    previous = dt.date.fromisoformat(rows[-2]['date'])
    missing = _between(previous, last)
    if missing:
        return None, {'symbol': symbol, 'name': name, 'reason': 'gap', 'detail': 'A completed session is missing between ' + rows[-2]['date'] + ' and ' + rows[-1]['date'] + ': ' + ', '.join(missing[:4]) + '.'}
    if rows[-2]['close'] > 0 and abs(math.log(rows[-1]['close'] / rows[-2]['close'])) > SPLIT:
        return None, {'symbol': symbol, 'name': name, 'reason': 'split', 'detail': 'The latest close-to-close move is large enough to be a split or a bad print. It was not treated as a match.'}
    parts = []
    start = rows[-1]['date']
    for condition in conditions:
        if condition['kind'] == 'session_move':
            move = (rows[-1]['close'] / rows[-2]['close'] - 1) * 100
            if condition['threshold'] == 'history':
                earlier = _moves([bar['close'] for bar in rows[:-1]])
                if len(earlier) < HISTORY_SAMPLE:
                    return None, {'symbol': symbol, 'name': name, 'reason': 'insufficient', 'detail': 'A historical move threshold needs ' + str(HISTORY_SAMPLE) + ' earlier moves. ' + str(len(earlier)) + ' are saved.'}
                comparison = _percentile(earlier, condition['percentile'])
                label = format(condition['percentile'], '.0f') + 'th percentile of earlier absolute moves'
            else:
                comparison = condition['threshold']
                label = 'fixed threshold'
            if abs(move) < comparison:
                return None, None
            start = rows[-2]['date']
            parts.append('The session move is ' + format(move, '.4f') + '% from ' + format(rows[-2]['close'], '.4f') + ' on ' + rows[-2]['date'] + ' to ' + format(rows[-1]['close'], '.4f') + ' on ' + rows[-1]['date'] + '. The comparison is ' + format(comparison, '.4f') + '% (' + label + ').')
            measured, compared = move, comparison
        elif condition['kind'] == 'above_average':
            length = condition['sessions']
            if len(rows) < length:
                return None, {'symbol': symbol, 'name': name, 'reason': 'insufficient', 'detail': 'The average needs ' + str(length) + ' closes. ' + str(len(rows)) + ' are saved.'}
            window = rows[-length:]
            average = sum(bar['close'] for bar in window) / length
            if rows[-1]['close'] <= average:
                return None, None
            start = window[0]['date']
            parts.append('The close ' + format(rows[-1]['close'], '.4f') + ' is above the ' + str(length) + '-session average ' + format(average, '.4f') + '.')
            measured, compared = rows[-1]['close'], average
        elif condition['kind'] == 'closing_high':
            length = condition['sessions']
            if len(rows) < length + 1:
                return None, {'symbol': symbol, 'name': name, 'reason': 'insufficient', 'detail': 'A new high needs ' + str(length + 1) + ' closes. ' + str(len(rows)) + ' are saved.'}
            earlier = rows[-(length + 1):-1]
            ceiling = max(bar['close'] for bar in earlier)
            if rows[-1]['close'] <= ceiling:
                return None, None
            start = earlier[0]['date']
            parts.append('The close ' + format(rows[-1]['close'], '.4f') + ' is above the previous ' + str(length) + ' closes. Their highest close was ' + format(ceiling, '.4f') + '.')
            measured, compared = rows[-1]['close'], ceiling
        else:
            if rows[-1].get('volume') in (None, 0):
                return None, {'symbol': symbol, 'name': name, 'reason': 'incomplete-volume', 'detail': 'The latest daily volume is missing or zero, so it was not treated as a low-volume match.'}
            earlier = [bar['volume'] for bar in rows[:-1] if isinstance(bar.get('volume'), (int, float)) and not isinstance(bar.get('volume'), bool) and bar['volume'] > 0]
            if len(earlier) < HISTORY_SAMPLE:
                return None, {'symbol': symbol, 'name': name, 'reason': 'insufficient', 'detail': 'A volume threshold needs ' + str(HISTORY_SAMPLE) + ' earlier volumes. ' + str(len(earlier)) + ' are saved.'}
            comparison = _percentile(earlier, condition['percentile'])
            if rows[-1]['volume'] < comparison:
                return None, None
            parts.append('The volume ' + format(rows[-1]['volume'], '.0f') + ' is at least the ' + format(condition['percentile'], '.0f') + 'th percentile of earlier volumes, ' + format(comparison, '.4f') + '.')
            measured, compared = rows[-1]['volume'], comparison
    return {
        'symbol': symbol, 'name': name, 'date': rows[-1]['date'], 'source': SOURCE,
        'measured': measured, 'comparison': compared, 'start': start, 'end': rows[-1]['date'],
        'startTs': rows[-2]['ts'] if rows[-2].get('ts') else None, 'endTs': rows[-1].get('ts'),
        'close': rows[-1]['close'], 'calculation': ' '.join(parts), 'conditions': [part for part in parts],
    }, None


def scan_books(books, raw, as_of, names=None):
    rule = _rule(raw)
    day = dt.date.fromisoformat(as_of) if isinstance(as_of, str) else as_of
    names = names or {}
    matches, omissions = [], []
    checked = 0
    for symbol in sorted(books):
        checked += 1
        match, omission = _one(symbol, books.get(symbol) or [], rule['conditions'], day, names.get(symbol) or symbol)
        if match:
            matches.append(match)
        elif omission:
            omissions.append(omission)
    counts = {'checked': checked, 'matched': len(matches), 'insufficient': sum(item['reason'] == 'insufficient' for item in omissions),
              'stale': sum(item['reason'] == 'stale' for item in omissions), 'gap': sum(item['reason'] == 'gap' for item in omissions),
              'split': sum(item['reason'] == 'split' for item in omissions), 'incompleteVolume': sum(item['reason'] == 'incomplete-volume' for item in omissions)}
    counts['unmatched'] = checked - counts['matched'] - len(omissions)
    return {'model': MODEL, 'asOf': day.isoformat(), 'plainEnglish': explain(raw)['plainEnglish'], 'conditions': rule['conditions'],
            'matches': matches, 'omissions': omissions, 'counts': counts, 'source': SOURCE,
            'notice': 'Companies were checked from the saved directory and locally saved daily bars. Sorting the cards does not rerun the scan.'}


def _previous(con, scan_id):
    return {symbol: day for symbol, day in con.execute('SELECT symbol, observation_date FROM scanner55_members WHERE scan_id=?', (scan_id,))}


def _changes(previous, matches):
    current = {match['symbol']: match['date'] for match in matches}
    changes = []
    for match in matches:
        state = 'new' if match['symbol'] not in previous else 'continued'
        changes.append({**match, 'change': state})
    for symbol, day in sorted(previous.items()):
        if symbol not in current:
            changes.append({'symbol': symbol, 'date': day, 'change': 'dropped', 'calculation': symbol + ' qualified on ' + day + ' and does not qualify in this run.'})
    return changes


def _directory(g):
    try:
        rows = json.loads((g['ROOT'] / 'ai_catalog.json').read_text())
    except (OSError, ValueError, KeyError):
        return {}
    return {row['symbol']: row.get('name') or row['symbol'] for row in rows if row.get('symbol')}


def load_books(g, symbols):
    books = {symbol: [] for symbol in symbols}
    if not symbols:
        return books
    marks = ','.join('?' for _ in symbols)
    with contextlib.closing(g['db_connection']()) as con:
        rows = con.execute('SELECT symbol, ts_ms, c, v FROM massive_daily_bars WHERE symbol IN (' + marks + ') ORDER BY symbol, ts_ms', tuple(symbols)).fetchall()
    for symbol, stamp, close, volume in rows:
        if isinstance(close, bool) or not isinstance(close, (int, float)) or not math.isfinite(close) or close <= 0:
            continue
        day = market37.dt.datetime.fromtimestamp(stamp / 1000, market37.NY).date().isoformat()
        vol = volume if isinstance(volume, (int, float)) and not isinstance(volume, bool) and math.isfinite(volume) else None
        books.setdefault(symbol, []).append({'date': day, 'close': float(close), 'volume': vol, 'ts': int(stamp)})
    return books


def run(g, body, now_ms, record=False):
    rule = _rule(body.get('preset') or body)
    names = _directory(g)
    wanted = list(names) or list(body.get('symbols') or [])
    as_of = body.get('asOf') or market37.dt.datetime.fromtimestamp(now_ms / 1000, market37.NY).date().isoformat()
    result = scan_books(load_books(g, wanted), rule, as_of, names)
    result['title'] = rule['title']
    scan_id = body.get('id') if IDENT.fullmatch(str(body.get('id') or '')) else ''
    if scan_id and record:
        with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
            init(con)
            previous = _previous(con, scan_id)
            changes = _changes(previous, result['matches'])
            result['changes'] = changes
            run_id = __import__('secrets').token_hex(8)
            result['runId'] = run_id
            con.execute('INSERT INTO scanner55_runs VALUES(?,?,?,?,?)', (run_id, scan_id, as_of, json.dumps(result, allow_nan=False), int(now_ms)))
            con.execute('DELETE FROM scanner55_members WHERE scan_id=?', (scan_id,))
            con.executemany('INSERT INTO scanner55_members VALUES(?,?,?)', [(scan_id, match['symbol'], match['date']) for match in result['matches']])
            created = 0
            if rule['alert']:
                for change in changes:
                    if change['change'] != 'new':
                        continue
                    inserted = con.execute('INSERT OR IGNORE INTO scanner55_alerts VALUES(?,?,?,?,?,?)',
                                           (__import__('secrets').token_hex(8), scan_id, change['symbol'], change['date'], change.get('calculation') or '', int(now_ms)))
                    created += inserted.rowcount
            result['alertsCreated'] = created
            result['scanId'] = scan_id
    else:
        result['changes'] = [{**match, 'change': 'unsaved'} for match in result['matches']]
        result['alertsCreated'] = 0
        result['notice'] += ' Save the scan before membership changes and alerts are recorded.'
    return result


def save(g, body, now_ms):
    rule = _rule(body.get('preset') or body)
    ident = body.get('id') if IDENT.fullmatch(str(body.get('id') or '')) else __import__('secrets').token_hex(8)
    payload = {'title': rule['title'], 'conditions': rule['conditions'], 'alert': rule['alert'], 'schedule': rule['schedule'], 'model': MODEL}
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('INSERT OR REPLACE INTO scanner55_scans VALUES(?,?,?,?)', (ident, rule['title'], json.dumps(payload, allow_nan=False), int(now_ms)))
    recorded = run(g, {**payload, 'id': ident, 'asOf': body.get('asOf')}, now_ms, record=True)
    return {'id': ident, 'saved': payload, 'result': recorded}


def read(g, ident, now_ms):
    if not IDENT.fullmatch(str(ident or '')):
        raise ValueError('Choose a saved scan.')
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        row = con.execute('SELECT body FROM scanner55_scans WHERE id=?', (ident,)).fetchone()
        run = con.execute('SELECT body, created_at FROM scanner55_runs WHERE scan_id=? ORDER BY created_at DESC LIMIT 1', (ident,)).fetchone()
    if not row:
        raise ValueError('That scan is not saved on this Mac.')
    return {'saved': json.loads(row[0]), 'result': json.loads(run[0]) if run else None, 'openedAt': int(now_ms),
            'notice': 'The saved scan and its latest result are reopened from this Mac. They were not recalculated.'}


def listed(g):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        rows = con.execute('SELECT id, title, created_at FROM scanner55_scans ORDER BY created_at DESC LIMIT 40').fetchall()
    return [{'id': ident, 'title': title, 'createdAt': created} for ident, title, created in rows]


def answer(g, ident, symbol):
    opened = read(g, ident, 0)
    result = opened.get('result') or {}
    found = next((match for match in result.get('matches') or [] if match.get('symbol') == symbol), None)
    if not found:
        omission = next((item for item in result.get('omissions') or [] if item.get('symbol') == symbol), None)
        if omission:
            return omission['symbol'] + ' did not match. ' + omission['detail'], {'sampleSize': 0, 'qualification': 'The saved scan result was not recalculated.', 'source': SOURCE}
        return symbol + ' is not in the saved scan result.', {'sampleSize': 0, 'qualification': 'The saved scan result was not recalculated.', 'source': SOURCE}
    return found['symbol'] + ' matched on ' + found['date'] + '. ' + found['calculation'], {'sampleSize': 1, 'endPrice': found.get('close'), 'end': found['date'], 'start': found.get('start'), 'qualification': 'This answer uses the calculation stored with the scan.', 'source': SOURCE}


def scheduled(g, now_ms):
    day = market37.dt.datetime.fromtimestamp(now_ms / 1000, market37.NY).date().isoformat()
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        found = con.execute('SELECT day FROM scanner55_day WHERE id=1').fetchone()
        if found and found[0] == day:
            return {'ran': False, 'reason': 'This calendar day was already scanned.'}
        rows = con.execute('SELECT id, body FROM scanner55_scans').fetchall()
        due = []
        for ident, body in rows:
            saved = json.loads(body)
            if saved.get('schedule'):
                due.append((ident, saved))
        con.execute('INSERT OR REPLACE INTO scanner55_day VALUES(1,?)', (day,))
    for ident, saved in due:
        run(g, {**saved, 'id': ident, 'asOf': day}, now_ms, record=True)
    return {'ran': True, 'scans': len(due)}


def refresh(g, symbols, room):
    room = max(0, min(5, int(room)))
    chosen = [g['valid_symbol'](symbol) for symbol in (symbols or [])[:room]]
    if room == 0:
        return {'requested': 0, 'symbols': [], 'notice': 'The shared free-plan budget has no room for a history refresh. Saved bars were left as they are.'}
    calls = 0
    done = []
    end = int(g['time'].time())
    start = end - 86400 * 400
    for symbol in chosen:
        if calls >= room:
            break
        try:
            g['massive_daily_candles'](symbol, start, end)
            calls += 1
            done.append(symbol)
        except Exception as error:
            done.append(symbol + ': ' + str(error)[:120])
            break
    return {'requested': calls, 'symbols': done, 'notice': 'At most five companies are refreshed, and only while the shared request budget has room.'}
