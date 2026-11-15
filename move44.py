"""Review one completed-session price move from saved closes and saved events."""
import contextlib
import datetime as dt

import events42

BASIS = events42.BASIS
SOURCE = 'Massive · saved split-adjusted daily closes. Read from this Mac.'


def _day(value):
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError as error:
        raise ValueError('Choose a start and end date.') from error


def _link(url):
    text = str(url or '')
    return text if text.startswith('http://') or text.startswith('https://') else ''


def _event_view(row):
    return {
        'title': row['title'],
        'kind': row.get('kind'),
        'kindLabel': row['kindLabel'],
        'reason': row.get('reason') or '',
        'publisher': row['publisher'],
        'timeLabel': row['timeLabel'],
        'timing': row['timing'],
        'source': _link(row.get('source')),
        'note': row.get('note') or '',
    }


def _classify(events, start, end, end_close_ms):
    before, after, uncertain = [], [], []
    for row in events:
        if row.get('timing') == 'date' or not row.get('publishedAt'):
            uncertain.append(_event_view(row))
            continue
        view = _event_view(row)
        if row['publishedAt'] <= end_close_ms:
            before.append(view)
        else:
            after.append(view)
    # Saved events arrive newest first. Keep the ones closest to this move.
    return before[:8], list(reversed(after[-8:])), uncertain[:8], len(before), len(after), len(uncertain)


def review(g, symbol, start, end, now_ms=None):
    symbol = g['valid_symbol'](symbol)
    now_ms = int(g['time'].time() * 1000) if now_ms is None else int(now_ms)
    start_day = _day(start)
    end_day = _day(end)
    if not events42.is_session(start_day) or not events42.is_session(end_day):
        raise ValueError('Choose completed US trading sessions. Weekends and exchange holidays are not a move.')
    if start_day >= end_day:
        raise ValueError('The move needs an earlier session and a later session.')
    finished = events42.close_on(end_day)
    if finished is None or int(finished.timestamp() * 1000) > now_ms:
        return {
            'status': 'withheld', 'symbol': symbol, 'start': start_day.isoformat(), 'end': end_day.isoformat(),
            'reason': 'This session is still open. The review waits until the New York close.',
            'basis': BASIS, 'source': SOURCE, 'offline': True,
            'gaps': ['No return is shown for an unfinished session.'],
        }
    stock = events42.closes(g, symbol, now_ms)
    spy = stock if symbol == 'SPY' else events42.closes(g, 'SPY', now_ms)
    start_price = stock.get(start_day.isoformat())
    end_price = stock.get(end_day.isoformat())
    gaps = []
    if start_price is None or end_price is None:
        missing = []
        if start_price is None:
            missing.append(start_day.isoformat())
        if end_price is None:
            missing.append(end_day.isoformat())
        gaps.append('Missing saved ' + symbol + ' close on ' + ' and '.join(missing) + '. Nothing was filled in.')
        return {
            'status': 'withheld', 'symbol': symbol, 'start': start_day.isoformat(), 'end': end_day.isoformat(),
            'reason': gaps[0], 'basis': BASIS, 'source': SOURCE, 'offline': True, 'gaps': gaps,
        }
    stock_return = (end_price / start_price - 1) * 100
    spy_start = spy.get(start_day.isoformat())
    spy_end = spy.get(end_day.isoformat())
    comparison = {'status': 'withheld', 'benchmark': 'SPY', 'reason': 'SPY is not used when the stock is SPY.' if symbol == 'SPY' else ''}
    if symbol != 'SPY':
        if spy_start is None or spy_end is None:
            missing = []
            if spy_start is None:
                missing.append(start_day.isoformat())
            if spy_end is None:
                missing.append(end_day.isoformat())
            comparison['reason'] = 'SPY comparison is unavailable. Missing saved SPY close on ' + ' and '.join(missing) + '.'
            gaps.append(comparison['reason'])
        else:
            spy_return = (spy_end / spy_start - 1) * 100
            difference = stock_return - spy_return
            comparison = {
                'status': 'ready', 'benchmark': 'SPY', 'basis': BASIS,
                'start': start_day.isoformat(), 'end': end_day.isoformat(),
                'startPrice': spy_start, 'endPrice': spy_end,
                'returnPct': spy_return, 'differencePP': difference,
            }
    with contextlib.closing(g['db_connection']()) as con:
        events42.init(con)
    saved = events42.load(g, symbol) or {}
    events = events42.explain(symbol, events42.dedupe([*(saved.get('events') or []), *events42.local_items(g, symbol)]), events42.issuer_name(g, symbol))
    before, after, uncertain, before_count, after_count, uncertain_count = _classify(events, start_day, end_day, int(finished.timestamp() * 1000))
    explains = any(row['kindLabel'] in ('Company announcement', 'Regulatory filing') for row in before)
    if not before and not uncertain:
        evidence = 'No saved filing, announcement or news falls before or during this move. The saved records do not explain it.'
    elif not explains:
        evidence = 'The saved items do not explain this move. A headline or a price comparison is not a cause.'
    else:
        evidence = 'A saved filing or company announcement falls before the end of this move. That shows timing only. It does not prove the filing caused the price change.'
    sessions = []
    cursor = start_day
    while cursor <= end_day:
        if events42.is_session(cursor):
            sessions.append(cursor.isoformat())
        cursor += dt.timedelta(days=1)
    return {
        'status': 'ready', 'symbol': symbol, 'offline': True,
        'start': start_day.isoformat(), 'end': end_day.isoformat(),
        'startPrice': start_price, 'endPrice': end_price, 'returnPct': stock_return,
        'sessions': sessions, 'basis': BASIS, 'source': SOURCE,
        'comparison': comparison, 'gaps': gaps,
        'before': before, 'after': after, 'uncertain': uncertain,
        'beforeCount': before_count, 'afterCount': after_count, 'uncertainCount': uncertain_count,
        'evidence': evidence,
    }
