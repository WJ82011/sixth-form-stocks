"""Explain saved SEC results without inventing a missing figure.

Operating profit is not in the selected facts. Net profit is never relabelled
as operating profit. A quarter is not compared with a full year. A nine-month
total is not treated as a quarter.
"""
import contextlib
import datetime as dt
import hashlib
import json

import events42
import move44

METHOD = 'earnings-lab-v6.2'


def question(text):
    words = str(text or '').lower()
    return 'these results' in words or ('revenue' in words and 'profit' in words) or ('compare' in words and 'last year' in words)


def _fact(period, key):
    fact = (period.get('metrics') or {}).get(key) or {}
    if 'value' not in fact:
        return None
    return fact


def _comparable(current, previous):
    if not current or not previous:
        return 'A comparison needs two saved periods.'
    if current.get('type') != previous.get('type'):
        return 'A quarter is not compared with a full year.'
    if current.get('currency') != previous.get('currency'):
        return 'The currencies differ. No conversion was applied.'
    if abs(int(current.get('durationDays') or 0) - int(previous.get('durationDays') or 0)) > 14:
        return 'The reporting periods have different lengths, so the change is not shown.'
    gap = (dt.date.fromisoformat(current['end']) - dt.date.fromisoformat(previous['end'])).days
    if current.get('type') == 'annual' and not 350 <= gap <= 380:
        return 'These annual periods are not about a year apart, so year-over-year growth is not shown.'
    if current.get('type') == 'quarterly' and not 80 <= gap <= 120 and not 350 <= gap <= 380:
        return 'These quarters are not a prior quarter or the same quarter a year earlier, so the change is not shown.'
    return ''


def _change(current, previous, key):
    reason = _comparable(current, previous)
    if reason:
        return {'available': False, 'reason': reason}
    now, then = _fact(current, key), _fact(previous, key)
    if not now or not then:
        return {'available': False, 'reason': 'One of the two periods has no saved ' + key + '.'}
    if now.get('tag') != then.get('tag'):
        return {'available': False, 'reason': 'The two periods use different reporting tags, so they are not treated as the same figure.'}
    if then['value'] == 0:
        return {'available': False, 'reason': 'The earlier figure is zero, so a percentage change is not shown.'}
    if then['value'] < 0 and key == 'revenue':
        return {'available': False, 'reason': 'Revenue was negative in the earlier period, so growth is not shown.'}
    return {'available': True, 'from': then['value'], 'to': now['value'],
            'changePct': (now['value'] / then['value'] - 1) * 100, 'unit': now.get('unit') or 'USD'}


def _card(period, previous):
    if not period:
        return None
    revenue, profit = _fact(period, 'revenue'), _fact(period, 'profit')
    margin = profit['value'] / revenue['value'] * 100 if revenue and profit and revenue['value'] > 0 else None
    growth = _change(period, previous, 'revenue') if previous else {'available': False, 'reason': 'No earlier comparable period is saved.'}
    profit_change = _change(period, previous, 'profit') if previous else {'available': False, 'reason': 'No earlier comparable period is saved.'}
    margin_change = None
    previous_margin = None
    if previous:
        old_revenue, old_profit = _fact(previous, 'revenue'), _fact(previous, 'profit')
        if old_revenue and old_profit and old_revenue['value'] > 0:
            previous_margin = old_profit['value'] / old_revenue['value'] * 100
    if previous_margin is not None and margin is not None and not _comparable(period, previous):
        margin_change = margin - previous_margin
    warnings = list(period.get('warnings') or [])
    for fact in (revenue, profit):
        if fact and fact.get('valuesDifferAcrossFilings'):
            warnings.append('A later filing reports a different value for the same period. The latest filed value is shown. The earlier value is not overwritten.')
    return {
        'type': period.get('type'), 'start': period.get('start'), 'end': period.get('end'),
        'durationDays': period.get('durationDays'), 'currency': period.get('currency') or 'USD',
        'revenue': revenue, 'profit': profit, 'netMarginPct': margin,
        'revenueChange': growth, 'profitChange': profit_change, 'netMarginChangePP': margin_change,
        'warnings': warnings,
        'note': 'Figures are US dollars as reported. They are not converted to millions. Net margin is net profit divided by revenue. It is not an operating margin.',
    }


def _year_to_date(rows):
    found = []
    for row in rows or []:
        days = row.get('durationDays')
        if isinstance(days, int) and 150 <= days <= 320:
            found.append({'start': row.get('start'), 'end': row.get('end'), 'durationDays': days,
                          'note': 'This is a year-to-date total. It is not shown as a single quarter and it is not split into a missing quarter.'})
    return found


def review(report):
    annual = list((report or {}).get('annual') or [])
    quarterly = list((report or {}).get('quarterly') or [])
    if not annual and not quarterly:
        return {'method': METHOD, 'status': 'unavailable', 'cards': [],
                'notice': 'No supported SEC statement is saved for this company. No revenue, profit or margin was invented.',
                'analystExpectations': 'No dated analyst estimate is saved. None is shown.'}
    cards = []
    if len(annual) >= 1:
        cards.append(_card(annual[-1], annual[-2] if len(annual) > 1 else None))
    if len(quarterly) >= 1:
        year_ago = None
        latest = quarterly[-1]
        for older in reversed(quarterly[:-1]):
            gap = (dt.date.fromisoformat(latest['end']) - dt.date.fromisoformat(older['end'])).days
            if 350 <= gap <= 380:
                year_ago = older
                break
        cards.append(_card(latest, year_ago or (quarterly[-2] if len(quarterly) > 1 else None)))
    ends = [row.get('end') for row in quarterly]
    missing = []
    if len(ends) >= 2:
        gap = (dt.date.fromisoformat(ends[-1]) - dt.date.fromisoformat(ends[-2])).days
        if gap > 120:
            missing.append('The saved quarters jump by ' + str(gap) + ' days. The missing quarter was not created.')
    return {
        'method': METHOD, 'status': 'ready', 'name': (report or {}).get('name') or '',
        'cards': [card for card in cards if card], 'yearToDate': _year_to_date((report or {}).get('yearToDate')),
        'missingQuarters': missing, 'operatingProfit': 'Operating profit is not in the selected SEC facts. Net profit is shown on its own.',
        'analystExpectations': 'No dated analyst estimate is saved. None is shown.',
        'notice': 'Opened from the saved SEC facts. A headline is not a cause of the price move.',
    }


def answer(report, text):
    built = review(report)
    words = str(text or '').lower()
    if built['status'] != 'ready':
        return built['notice']
    annual = next((card for card in built['cards'] if card['type'] == 'annual'), None)
    if not annual:
        return 'No annual period is saved, so the comparison with last year is not shown.'
    revenue = annual.get('revenue') or {}
    profit = annual.get('profit') or {}
    source = f"Source {revenue.get('form') or profit.get('form') or 'filing'} filed {revenue.get('filed') or profit.get('filed') or 'on an unsaved date'}, {annual['start']} to {annual['end']}, {annual['currency']}."
    if 'together' in words:
        if revenue.get('value') is None or profit.get('value') is None:
            return 'Revenue and net profit are not both saved for the latest year. ' + source
        same = 'both higher than the comparable earlier year' if (annual['revenueChange'].get('changePct') or 0) > 0 and (annual['profitChange'].get('changePct') or 0) > 0 else 'not both higher than the comparable earlier year'
        if not annual['revenueChange'].get('available') or not annual['profitChange'].get('available'):
            same = 'a together comparison is unavailable'
        return f"Revenue {revenue['value']:.0f} and net profit {profit['value']:.0f}. They are {same}. {source} Net profit is not operating profit."
    if 'last year' in words or 'changed' in words or 'change' in words:
        growth = annual['revenueChange']
        if not growth.get('available'):
            return growth.get('reason', 'The year-over-year comparison is unavailable.') + ' ' + source
        return f"Revenue changed by {growth['changePct']:.2f}% from {growth['from']:.0f} to {growth['to']:.0f}. {source}"
    return built['notice'] + ' ' + source


def assumptions(saved, report):
    built = review(report)
    annual = next((card for card in built.get('cards') or [] if card['type'] == 'annual'), None)
    original = {'growthPct': (saved or {}).get('growthPct'), 'marginPct': (saved or {}).get('marginPct')}
    result = {'original': original, 'preserved': True, 'comparisons': []}
    if original['growthPct'] is None and original['marginPct'] is None:
        result['notice'] = 'No numeric simulator assumption was saved. Journal wording is not turned into a figure.'
        return result
    if not annual or not annual['revenueChange'].get('available'):
        result['notice'] = 'The saved assumption is kept. The filing does not have a comparable revenue change.'
        return result
    result['comparisons'].append({
        'label': 'Revenue growth', 'assumption': original['growthPct'],
        'reported': round(annual['revenueChange']['changePct'], 2),
        'differencePP': None if original['growthPct'] is None else round(annual['revenueChange']['changePct'] - original['growthPct'], 2),
        'period': annual['start'] + ' to ' + annual['end'],
    })
    result['margin'] = 'The saved margin is an operating-margin assumption. The filing shows net margin. Those two margins are not subtracted.'
    result['notice'] = 'The original assumptions are unchanged.'
    return result


def _next_session(day):
    probe = day + dt.timedelta(days=1)
    for _ in range(12):
        if events42.is_session(probe):
            return probe
        probe += dt.timedelta(days=1)
    raise ValueError('No following session was found.')


def reaction_window(published_ms, now_ms):
    if published_ms is None:
        return {'status': 'uncertain', 'notice': 'No publication time is saved. No price reaction is calculated.'}
    moment = dt.datetime.fromtimestamp(int(published_ms) / 1000, events42.NY)
    day = moment.date()
    close = events42.close_on(day) if events42.is_session(day) else None
    if close is not None and moment <= close:
        start, end, timing = events42.previous_session(day), day, 'during the session'
    else:
        if close is not None and moment > close:
            start = day
        else:
            probe = day
            while not events42.is_session(probe):
                probe -= dt.timedelta(days=1)
            start = probe
        end, timing = _next_session(start), 'after the close'
    finished = events42.close_on(end)
    if finished is None or int(finished.timestamp() * 1000) > int(now_ms):
        return {'status': 'withheld', 'start': start.isoformat(), 'end': end.isoformat(), 'timing': timing,
                'notice': 'The later session is still open. No return is shown.'}
    return {'status': 'ready', 'start': start.isoformat(), 'end': end.isoformat(), 'timing': timing,
            'publishedAt': int(published_ms), 'notice': 'The price window uses the saved closes around the publication time. It does not explain the results.'}


def reaction(g, symbol, published_ms, now_ms):
    window = reaction_window(published_ms, now_ms)
    if window['status'] != 'ready':
        return window
    try:
        move = move44.review(g, symbol, window['start'], window['end'], now_ms)
    except (OSError, ValueError) as error:
        return {**window, 'status': 'withheld', 'notice': str(error)}
    return {**window, 'move': move, 'returnPct': move.get('returnPct') if move.get('status') == 'ready' else None}


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS earnings62(
        id TEXT PRIMARY KEY, symbol TEXT NOT NULL, body TEXT NOT NULL, created_at INTEGER NOT NULL)''')


def save(g, symbol, report, now_ms):
    symbol = g['valid_symbol'](symbol)
    built = review(report)
    built.update(symbol=symbol, savedAt=int(now_ms))
    ident = hashlib.sha256(json.dumps(built, sort_keys=True, default=str).encode()).hexdigest()[:16]
    built['id'] = ident
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('INSERT OR REPLACE INTO earnings62 VALUES(?,?,?,?)', (ident, symbol, json.dumps(built, default=str), int(now_ms)))
    built['notice'] = 'Saved on this Mac. Reopening reads this copy and does not rebuild it.'
    return built


def read(g, ident):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        row = con.execute('SELECT body FROM earnings62 WHERE id=?', (str(ident or ''),)).fetchone()
    if not row:
        raise ValueError('That results review is not saved on this Mac.')
    saved = json.loads(row[0])
    saved['notice'] = 'Opened from the saved results review. It was not rebuilt.'
    return saved
