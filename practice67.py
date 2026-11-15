"""Decision practice. The replay clock hides later prices, events and extremes."""
import contextlib
import datetime as dt
import hashlib
import json

import events42
import replay43

METHOD = 'decision-practice-v6.7'
ASSESSMENTS = {'supported', 'challenged', 'unclear'}


def init(con):
    con.execute('CREATE TABLE IF NOT EXISTS practice67_sessions(id TEXT PRIMARY KEY, symbol TEXT NOT NULL, body TEXT NOT NULL, updated_at INTEGER NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS practice67_decisions(id TEXT PRIMARY KEY, session_id TEXT NOT NULL, body TEXT NOT NULL, updated_at INTEGER NOT NULL)')


def _time(row):
    if not isinstance(row, dict):
        return None
    value = row.get('t')
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _price(row):
    value = row.get('p') if isinstance(row, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        return None
    return float(value)


def _records(prices, trades, events):
    clean_prices = sorted(({'t': _time(row), 'p': _price(row)} for row in prices or [] if _time(row) is not None and _price(row) is not None), key=lambda row: row['t'])
    clean_trades = [row for row in trades or [] if _time(row) is not None]
    clean_events = []
    for event in events or []:
        if not isinstance(event, dict) or not str(event.get('title') or '').strip():
            continue
        published = event.get('publishedAt')
        item = {'title': str(event.get('title'))[:240], 'source': str(event.get('source') or '')[:300]}
        if isinstance(published, (int, float)) and not isinstance(published, bool):
            item['publishedAt'] = int(published)
        clean_events.append(item)
    return {'prices': clean_prices, 'trades': clean_trades, 'events': clean_events}


def coverage(records):
    prices = records['prices']
    gaps = 0
    for earlier, later in zip(prices, prices[1:]):
        if later['t'] - earlier['t'] > replay43.GAP_MS:
            gaps += 1
    timed = sum(1 for event in records['events'] if 'publishedAt' in event)
    unverified = len(records['events']) - timed
    return {
        'tradeCount': len(prices),
        'first': prices[0]['t'] if prices else None,
        'last': prices[-1]['t'] if prices else None,
        'gapCount': gaps,
        'timedEvents': timed,
        'unverifiedTiming': unverified,
        'notice': 'Coverage is shown before the session starts. Prices, headlines and extremes stay hidden until the replay clock reaches them.',
    }


def visible(records, cursor):
    """A response built only from records at or before the cursor."""
    cursor = int(cursor)
    verified = [event for event in records['events'] if 'publishedAt' in event]
    unverified = len(records['events']) - len(verified)
    hidden = sum(1 for event in verified if event['publishedAt'] > cursor)
    frame = replay43.frame(records['prices'], records['trades'], verified, cursor)
    prices = [{'t': row['t'], 'p': row['p']} for row in frame['prices']]
    return {
        'cursor': cursor,
        'prices': prices,
        'high': frame['high'],
        'low': frame['low'],
        'gaps': frame['gaps'],
        'timedEvents': [{'title': event.get('title'), 'publishedAt': event.get('publishedAt'), 'source': event.get('source') or ''} for event in frame['timedEvents']],
        'unverifiedTiming': unverified,
        'notReached': hidden,
        'notice': 'Only records at or before the replay clock are included. A date without a publication time is not treated as known.',
    }


def _last_price(frame):
    return frame['prices'][-1]['p'] if frame.get('prices') else None


def _dump(value):
    return json.dumps(value, separators=(',', ':'), allow_nan=False)


def _load(con, ident):
    row = con.execute('SELECT body FROM practice67_sessions WHERE id=?', (ident,)).fetchone()
    if not row:
        raise ValueError('That practice session is not on this Mac.')
    body = json.loads(row[0])
    return body


def _save(con, body, now):
    con.execute('INSERT OR REPLACE INTO practice67_sessions VALUES(?,?,?,?)', (body['id'], body['symbol'], _dump(body), int(now)))


def _public(body):
    frame = visible(body['records'], body['cursor'])
    return {
        'method': METHOD, 'id': body['id'], 'symbol': body['symbol'], 'day': body['day'],
        'status': body['status'], 'speed': body['speed'], 'start': body['start'], 'end': body['end'],
        'coverage': body['coverage'], 'frame': frame,
        'decisions': [_decision_public(item) for item in body.get('decisions') or []],
    }


def _decision_public(item):
    shown = {key: item.get(key) for key in ('id', 'cursor', 'reviewAt', 'expectation', 'evidence', 'changeMind', 'createdAt', 'assessment', 'learned')}
    shown['visible'] = item.get('visible') or {}
    return shown


def open_records(g, symbol, day, prices, trades, events, start_ms, now):
    records = _records(prices, trades, events)
    if len(records['prices']) < 2:
        raise ValueError('This saved session does not have two prices to practice on.')
    cover = coverage(records)
    start = int(start_ms if start_ms is not None else cover['first'])
    if start < cover['first'] or start > cover['last']:
        raise ValueError('Choose a starting point inside the saved session.')
    ident = hashlib.sha256(f'{symbol}|{day}|{now}|{start}'.encode()).hexdigest()[:16]
    body = {
        'id': ident, 'symbol': symbol, 'day': day or '', 'records': records,
        'coverage': cover, 'start': start, 'end': cover['last'], 'cursor': start,
        'speed': 60, 'status': 'paused', 'decisions': [],
    }
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        _save(con, body, now)
    return _public(body)


def _day_bounds(day):
    start = dt.datetime.fromisoformat(day).replace(tzinfo=events42.NY)
    return int(start.timestamp() * 1000), int((start + dt.timedelta(days=1)).timestamp() * 1000) - 1


def preview(g, symbol, day):
    symbol = g['valid_symbol'](symbol)
    start, end = _day_bounds(day)
    trades = g['get_tape_events'](symbol, start, 5000, until_ms=end)
    prices = [{'t': row['t'], 'p': row['p']} for row in trades if row.get('p')]
    saved = events42.load(g, symbol) or {}
    events = []
    for event in saved.get('events') or []:
        published = event.get('publishedAt')
        if isinstance(published, (int, float)) and not isinstance(published, bool) and start <= int(published) <= end:
            events.append(event)
        elif event.get('date') == day:
            events.append({key: event.get(key) for key in ('title', 'source', 'date')})
    report = g.get('sec_saved', lambda _symbol: {})(symbol) or {}
    for period in (report.get('annual') or []) + (report.get('quarterly') or []):
        filed = ((period.get('revenue') or {}).get('filed')) or ''
        if filed and filed <= day:
            events.append({'title': 'Saved SEC fact filed ' + filed, 'source': (period.get('revenue') or {}).get('url') or ''})
    records = _records(prices, trades, events)
    if not records['prices']:
        raise ValueError('No saved trades were found for that company and session.')
    return {'method': METHOD, 'symbol': symbol, 'day': day, 'coverage': coverage(records), 'ready': len(records['prices']) >= 2}


def start(g, symbol, day, start_ms, now, start_mode='open'):
    symbol = g['valid_symbol'](symbol)
    begin, end = _day_bounds(day)
    trades = g['get_tape_events'](symbol, begin, 5000, until_ms=end)
    prices = [{'t': row['t'], 'p': row['p']} for row in trades if row.get('p')]
    saved = events42.load(g, symbol) or {}
    events = list(saved.get('events') or [])
    if start_mode == 'after-gap':
        for earlier, later in zip(prices, prices[1:]):
            if later['t'] - earlier['t'] > replay43.GAP_MS:
                start_ms = later['t']
                break
    return open_records(g, symbol, day, prices, trades, events, start_ms, now)


def _body(g, ident):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        return _load(con, ident)


def read(g, ident):
    return _public(_body(g, ident))


def _update(g, ident, now, change):
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        body = _load(con, ident)
        change(body)
        _save(con, body, now)
        return body


def pause(g, ident, now):
    body = _update(g, ident, now, lambda item: item.__setitem__('status', 'paused' if item['status'] != 'ended' else 'ended'))
    return _public(body)


def restart(g, ident, now):
    def change(item):
        item['cursor'] = item['start']
        item['status'] = 'paused'
    return _public(_update(g, ident, now, change))


def advance(g, ident, mode, speed, now):
    def change(item):
        if item['status'] == 'ended':
            return
        item['speed'] = speed if speed in (30, 60, 300) else item['speed']
        if mode == 'step':
            marks = [row['t'] for row in item['records']['prices'] if row['t'] > item['cursor']]
            marks += [event['publishedAt'] for event in item['records']['events'] if event.get('publishedAt', 0) > item['cursor']]
            item['cursor'] = min(marks) if marks else item['end']
            item['status'] = 'paused'
        else:
            item['cursor'] = min(item['end'], item['cursor'] + item['speed'] * 1000)
            item['status'] = 'playing'
        if item['cursor'] >= item['end']:
            item['cursor'] = item['end']
            item['status'] = 'ended'
    return _public(_update(g, ident, now, change))


def end(g, ident, now):
    def change(item):
        item['cursor'] = item['end']
        item['status'] = 'ended'
    return _public(_update(g, ident, now, change))


def decide(g, ident, fields, now):
    expectation = str(fields.get('expectation') or '').strip()
    if len(expectation) < 8:
        raise ValueError('Write what you expect before saving the decision.')
    review_at = fields.get('reviewAt')
    if isinstance(review_at, bool) or not isinstance(review_at, (int, float)):
        raise ValueError('Choose a review time inside this saved session.')

    def change(item):
        if item['status'] == 'ended':
            raise ValueError('This session has ended. Start again before saving another decision.')
        review = int(review_at)
        if review <= item['cursor'] or review > item['end']:
            raise ValueError('The review time has to be later in this session than the current clock.')
        item['status'] = 'paused'
        frame = visible(item['records'], item['cursor'])
        decision = {
            'id': hashlib.sha256(f"{item['id']}|{item['cursor']}|{now}|{expectation}".encode()).hexdigest()[:16],
            'cursor': item['cursor'], 'reviewAt': review, 'expectation': expectation[:2000],
            'evidence': str(fields.get('evidence') or '')[:2000],
            'changeMind': str(fields.get('changeMind') or '')[:2000],
            'createdAt': int(now), 'visible': frame, 'assessment': '', 'learned': '',
        }
        item['decisions'].append(decision)
    body = _update(g, ident, now, change)
    return _public(body)


def reflect(g, decision_id, assessment, learned, now):
    if assessment not in ASSESSMENTS:
        raise ValueError('Choose whether the evidence supported the idea, challenged it, or is still unclear.')

    def change(item):
        found = next((row for row in item['decisions'] if row['id'] == decision_id), None)
        if not found:
            raise ValueError('That decision is not in this session.')
        if item['cursor'] < found['reviewAt']:
            raise ValueError('The review time has not been reached. The original decision was kept.')
        found['assessment'] = assessment
        found['learned'] = str(learned or '')[:2000]
    # decision id is not the session id; search sessions
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        rows = con.execute('SELECT id, body FROM practice67_sessions').fetchall()
        host = None
        for ident, raw in rows:
            body = json.loads(raw)
            if any(row['id'] == decision_id for row in body.get('decisions') or []):
                host = body
                break
        if not host:
            raise ValueError('That decision is not on this Mac.')
        original = json.dumps([row['expectation'] for row in host['decisions']])
        change(host)
        if json.dumps([row['expectation'] for row in host['decisions']]) != original:
            raise ValueError('The original decision cannot be changed from a reflection.')
        _save(con, host, now)
    return _public(host)


def outcome(g, decision_id):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        rows = con.execute('SELECT body FROM practice67_sessions').fetchall()
    host = decision = None
    for (raw,) in rows:
        body = json.loads(raw)
        found = next((row for row in body.get('decisions') or [] if row['id'] == decision_id), None)
        if found:
            host, decision = body, found
            break
    if not decision:
        raise ValueError('That decision is not on this Mac.')
    if host['cursor'] < decision['reviewAt']:
        return {
            'status': 'waiting', 'id': decision_id, 'original': _decision_public(decision),
            'notice': 'The review time has not been reached. The later return was not calculated.',
        }
    before = decision['visible']
    after = visible(host['records'], decision['reviewAt'])
    start_price = _last_price(before)
    end_price = _last_price(after)
    change = None if not start_price or not end_price else (end_price / start_price - 1) * 100
    events = [event for event in after['timedEvents'] if event.get('publishedAt', 0) > decision['cursor']]
    links = [{'title': event['title'], 'url': event['source']} for event in events if str(event.get('source') or '').startswith('http')]
    return {
        'status': 'ready', 'id': decision_id, 'original': _decision_public(decision),
        'startPrice': start_price, 'endPrice': end_price, 'returnPct': change,
        'events': events, 'links': links,
        'notice': 'The return uses the recorded price at the decision and the recorded price at the review time. It is not a cause.',
    }


def journal_entry(g, decision_id, now):
    result = outcome(g, decision_id)
    if result['status'] != 'ready':
        raise ValueError(result['notice'])
    original = result['original']
    symbol = _body_for_decision(g, decision_id)['symbol']
    return {
        'id': decision_id, 'symbol': symbol, 'title': 'Practice · ' + symbol,
        'createdAt': int(original.get('createdAt') or now), 'updatedAt': int(now),
        'status': 'open', 'origin': 'practice', 'range': 'replay',
        'start': '', 'end': '', 'reviewDate': '',
        'expectation': original.get('expectation') or '',
        'reasons': original.get('evidence') or '',
        'changeMind': original.get('changeMind') or '',
        'learned': original.get('learned') or '',
        'evidence': {
            'startPrice': result.get('startPrice'), 'endPrice': result.get('endPrice'),
            'priceTs': original.get('cursor'), 'source': 'Decision practice replay clock. Later prices were hidden when this was saved.',
            'links': result.get('links') or [],
        },
    }


def _body_for_decision(g, decision_id):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        for (raw,) in con.execute('SELECT body FROM practice67_sessions').fetchall():
            body = json.loads(raw)
            if any(row['id'] == decision_id for row in body.get('decisions') or []):
                return body
    raise ValueError('That decision is not on this Mac.')


def handle(g, question, context, now_ms):
    context = context or {}
    ident = str(context.get('practiceId') or '')
    if not ident:
        return None
    try:
        body = _body(g, ident)
    except ValueError:
        return {'question': question, 'kind': 'practice', 'offline': True, 'supported': False,
                'answer': 'That practice session is not on this Mac. No later price was read.',
                'evidence': {'gaps': ['The practice session was not found.']},
                'context': {'kind': 'practice', 'symbol': context.get('symbol') or ''}}
    text = str(question or '').lower()
    review = 'review this practice' in text
    if body['status'] != 'ended':
        frame = visible(body['records'], body['cursor'])
        if review:
            answer = 'The session is still open. Later results were not read.'
        else:
            price = _last_price(frame)
            answer = f"Replay clock {frame['cursor']}. The latest revealed price is {price}. {len(frame['timedEvents'])} timed records have been reached. {frame['notReached']} later records were not read. {frame['unverifiedTiming']} records have no verified publication time and were left out."
        return _packet(question, body, answer, frame, review=False)
    frame = visible(body['records'], body['end'])
    if review:
        names = ', '.join(item['expectation'] for item in body['decisions']) or 'No decision was saved.'
        price = _last_price(frame)
        answer = f"This is a review after the session. It uses the prices revealed by the end. The last revealed price is {price}. Original decisions: {names}"
    else:
        answer = 'The session has ended. Ask to review this practice session before the later results are used.'
    return _packet(question, body, answer, frame, review=review)


def _packet(question, body, answer, frame, review):
    gaps = []
    if frame.get('notReached'):
        gaps.append(str(frame['notReached']) + ' records are later than the replay clock and were not read.')
    if frame.get('unverifiedTiming'):
        gaps.append(str(frame['unverifiedTiming']) + ' records have no verified publication time and were left out.')
    if not review and body['status'] != 'ended':
        gaps.append('A review of the whole session is available only after the session ends.')
    return {
        'question': question, 'kind': 'practice', 'offline': True, 'supported': True,
        'answer': answer,
        'evidence': {'sampleSize': len(frame.get('prices') or []), 'endPrice': _last_price(frame), 'gaps': gaps, 'source': METHOD},
        'context': {'kind': 'practice', 'symbol': body['symbol'], 'practiceId': body['id']},
    }
