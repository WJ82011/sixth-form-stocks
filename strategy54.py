"""Strategy Lab. Rules are tested on saved daily bars and kept apart from the practice portfolio.

A signal uses only bars that already exist. The order is filled at the next saved
session's open. A daily bar does not say whether the high or the low came first.
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
FREQUENCY = 'One saved daily bar per completed New York session. Open, high, low and close are the saved values. The minute of each price is not recorded.'
MODEL = 'strategy-lab-v5.4'
SPLIT = 0.7


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS strategy54(
        id TEXT PRIMARY KEY, symbol TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, created_at INTEGER NOT NULL)''')


def _num(value, lo, hi, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(label + ' needs a finite number.')
    if not lo <= value <= hi:
        raise ValueError(label + ' is outside the supported range.')
    return float(value)


def _day(value, label):
    if not isinstance(value, str) or not DAY.fullmatch(value):
        raise ValueError(label + ' needs a YYYY-MM-DD date.')
    return dt.date.fromisoformat(value)


def _rule(raw):
    if not isinstance(raw, dict):
        raise ValueError('A strategy needs a rule.')
    entry = _side(raw.get('entry'), 'Entry')
    exit_rule = _side(raw.get('exit'), 'Exit')
    stop = raw.get('stopPct')
    stop = None if stop in (None, '', 0) else _num(stop, 0.1, 80, 'Stop-loss')
    start = _day(raw.get('start'), 'Development start')
    end = _day(raw.get('end'), 'Development end')
    if end <= start:
        raise ValueError('The development period needs a later end date.')
    later_start = raw.get('laterStart') or ''
    later_end = raw.get('laterEnd') or ''
    if later_start or later_end:
        later_start = _day(later_start, 'Later start')
        later_end = _day(later_end, 'Later end')
        if later_end <= later_start:
            raise ValueError('The later period needs a later end date.')
        if later_start <= end:
            raise ValueError('The later period starts after the development period ends.')
    else:
        later_start = later_end = None
    rule = {
        'entry': entry, 'exit': exit_rule, 'stopPct': stop,
        'start': start.isoformat(), 'end': end.isoformat(),
        'laterStart': later_start.isoformat() if later_start else '',
        'laterEnd': later_end.isoformat() if later_end else '',
        'cash': _num(raw.get('cash', 10000), 1, 1e9, 'Starting cash'),
        'sizePct': _num(raw.get('sizePct', 100), 1, 100, 'Position size'),
        'costPct': _num(raw.get('costPct', 0), 0, 20, 'Transaction cost'),
        'slippagePct': _num(raw.get('slippagePct', 0), 0, 10, 'Slippage'),
    }
    return rule


def _side(raw, label):
    if not isinstance(raw, dict):
        raise ValueError(label + ' needs a condition.')
    kind = raw.get('kind')
    if kind == 'sma_cross':
        fast = int(_num(raw.get('fast'), 2, 200, label + ' fast average'))
        slow = int(_num(raw.get('slow'), 3, 400, label + ' slow average'))
        if fast >= slow:
            raise ValueError(label + ' uses a shorter average and a longer average.')
        return {'kind': kind, 'fast': fast, 'slow': slow}
    if kind == 'breakout':
        return {'kind': kind, 'lookback': int(_num(raw.get('lookback'), 1, 250, label + ' lookback'))}
    raise ValueError(label + ' can be a moving-average crossing or a price breakout.')


def fingerprint(rule):
    return json.dumps(rule, sort_keys=True, separators=(',', ':'))


def _phrase(side, buying):
    if side['kind'] == 'sma_cross':
        direction = 'crosses above' if buying else 'crosses below'
        return 'the ' + str(side['fast']) + '-day average ' + direction + ' the ' + str(side['slow']) + '-day average'
    direction = 'closes above the highest close' if buying else 'closes below the lowest close'
    return 'the price ' + direction + ' of the previous ' + str(side['lookback']) + ' sessions'


def describe(raw):
    rule = _rule(raw)
    stop = ''
    if rule['stopPct']:
        stop = ' A stop-loss closes the position if the price falls ' + format(rule['stopPct'], '.2f') + '% below the entry open.'
    text = 'Buy when ' + _phrase(rule['entry'], True) + '. Close the position when ' + _phrase(rule['exit'], False) + '.' + stop
    text += ' Use ' + format(rule['sizePct'], '.2f') + '% of the cash that is available. Starting cash is ' + format(rule['cash'], '.2f') + '.'
    text += ' Transaction costs are ' + format(rule['costPct'], '.2f') + '% of each fill and slippage is ' + format(rule['slippagePct'], '.2f') + '%.'
    text += ' A signal waits until the bars it needs are saved, then the order is filled at the next saved session open.'
    text += ' The development dates are ' + rule['start'] + ' to ' + rule['end'] + '.'
    if rule['laterStart']:
        text += ' The same locked settings are then evaluated from ' + rule['laterStart'] + ' to ' + rule['laterEnd'] + '.'
    return {'plainEnglish': text, 'assumptions': _assumptions(rule), 'fingerprint': fingerprint(rule), 'model': MODEL}


def _assumptions(rule):
    return [
        FREQUENCY,
        'A signal is created only after every bar it needs has been saved. It is filled at the next saved session open, not at the signal close.',
        'The order of the high and the low inside a daily bar is unknown. If the low reaches a stop and the open does not, the stop price is used and the trade is flagged. If the open is already through the stop, the open is used because that is a worse gap fill.',
        'A close-to-close move with absolute log change above 0.7 is treated as a split-sized jump. No signal is taken from that bar. An open position is closed at the previous close and flagged.',
        'Shares are rounded down to four decimal places so the cash spent cannot exceed the cash available. One position is open at a time. Short sales are not used.',
        'Dividends and other corporate actions are not in these bars. The result is a price result. The practice portfolio is not changed.',
        'Companies that failed or left the market are absent from today\'s directory, so this test cannot represent them.',
        'Transaction cost ' + format(rule['costPct'], '.2f') + '%. Slippage ' + format(rule['slippagePct'], '.2f') + '%. Position size ' + format(rule['sizePct'], '.2f') + '%.',
    ]


def _sessions(start, end):
    out = []
    day = start
    while day <= end:
        if day.weekday() < 5 and day not in market37.holidays(day.year):
            out.append(day.isoformat())
        day += dt.timedelta(days=1)
    return out


def _coverage(bars, start, end):
    wanted = _sessions(dt.date.fromisoformat(start), dt.date.fromisoformat(end))
    have = {bar['date'] for bar in bars if start <= bar['date'] <= end}
    missing = [day for day in wanted if day not in have]
    return {
        'frequency': FREQUENCY, 'source': SOURCE, 'sessions': len(wanted), 'saved': len(have),
        'missing': missing[:12], 'missingCount': len(missing),
        'first': min(have) if have else '', 'last': max(have) if have else '',
        'notice': 'Testing a company that is still in today\'s directory leaves out companies that failed or were delisted. These results are not a record of every company that existed.',
    }


def _sma(closes, index, length):
    if index + 1 < length:
        return None
    return sum(closes[index - length + 1:index + 1]) / length


def _hit(side, closes, split, index, buying):
    if split[index]:
        return False
    if side['kind'] == 'sma_cross':
        before_fast = _sma(closes, index - 1, side['fast'])
        before_slow = _sma(closes, index - 1, side['slow'])
        now_fast = _sma(closes, index, side['fast'])
        now_slow = _sma(closes, index, side['slow'])
        if None in (before_fast, before_slow, now_fast, now_slow):
            return False
        if buying:
            return before_fast <= before_slow and now_fast > now_slow
        return before_fast >= before_slow and now_fast < now_slow
    prior = closes[index - side['lookback']:index]
    if len(prior) < side['lookback']:
        return False
    if buying:
        return closes[index] > max(prior)
    return closes[index] < min(prior)


def _observations(side, bars, index):
    if side['kind'] == 'breakout':
        start = max(0, index - side['lookback'])
    else:
        start = max(0, index - side['slow'])
    return [{'date': bars[i]['date'], 'close': bars[i]['close']} for i in range(start, index + 1)]


def _shares(cash, size_pct, fill, cost_pct):
    budget = cash * size_pct / 100
    unit = fill * (1 + cost_pct / 100)
    if unit <= 0 or budget < unit / 10000:
        return 0.0
    return math.floor(budget / unit * 10000) / 10000


def _buy(state, bar, signal, rule, flags):
    raw = bar['open']
    fill = raw * (1 + rule['slippagePct'] / 100)
    shares = _shares(state['cash'], rule['sizePct'], fill, rule['costPct'])
    if shares <= 0:
        state['notes'].append(bar['date'] + ': the available cash could not buy a position after costs.')
        return
    notional = shares * fill
    commission = notional * rule['costPct'] / 100
    state['cash'] -= notional + commission
    state['shares'] = shares
    state['stop'] = raw * (1 - rule['stopPct'] / 100) if rule['stopPct'] else None
    state['entryOpen'] = raw
    state['costs'] += commission
    state['slippage'] += shares * (fill - raw)
    state['trades'].append(_trade('buy', signal, bar, raw, fill, shares, commission, shares * (fill - raw), flags, state, rule))


def _sell(state, bar, signal, rule, raw, flags):
    fill = raw * (1 - rule['slippagePct'] / 100)
    shares = state['shares']
    notional = shares * fill
    commission = notional * rule['costPct'] / 100
    state['cash'] += notional - commission
    state['costs'] += commission
    state['slippage'] += shares * (raw - fill)
    state['shares'] = 0.0
    state['stop'] = None
    state['completed'] += 1
    state['trades'].append(_trade('sell', signal, bar, raw, fill, shares, commission, shares * (raw - fill), flags, state, rule))


def _trade(side, signal, bar, raw, fill, shares, commission, slip, flags, state, rule):
    return {
        'side': side, 'signalDate': signal['date'] if signal else bar['date'],
        'signalIndex': signal['index'] if signal else None,
        'reason': signal['reason'] if signal else 'Stop-loss',
        'observations': signal['observations'] if signal else [],
        'executeDate': bar['date'], 'executeTs': bar.get('ts'),
        'executePrice': raw, 'fillPrice': fill, 'shares': shares,
        'commission': commission, 'slippageCash': slip, 'flags': flags,
        'cashAfter': state['cash'], 'sharesAfter': state['shares'],
        'calculation': side + ' ' + format(shares, '.4f') + ' shares at ' + format(fill, '.4f') + ' after ' + format(rule['slippagePct'], '.2f') + '% slippage. Commission ' + format(commission, '.4f') + '. Cash left ' + format(state['cash'], '.4f') + '.',
    }


def _stop_raw(state, bar):
    stop = state['stop']
    if stop is None or bar['low'] > stop:
        return None
    if bar['open'] <= stop:
        return bar['open'], ['gap', 'stop']
    return stop, ['intraday-order-unknown', 'stop']


def simulate(bars, rule, start, end):
    rows = [dict(bar) for bar in bars if bar['date'] <= end]
    rows.sort(key=lambda bar: bar['date'])
    closes = [bar['close'] for bar in rows]
    split = [False] * len(rows)
    for index in range(1, len(rows)):
        if closes[index - 1] > 0 and abs(math.log(closes[index] / closes[index - 1])) > SPLIT:
            split[index] = True
    state = {'cash': rule['cash'], 'shares': 0.0, 'stop': None, 'trades': [], 'costs': 0.0, 'slippage': 0.0, 'completed': 0, 'notes': [], 'curve': []}
    for index, flagged in enumerate(split):
        if flagged and start <= rows[index]['date'] <= end:
            state['notes'].append(rows[index]['date'] + ': a split-sized jump is flagged. Signals from that bar are not used.')
    pending_buy = pending_sell = None
    window = [bar for bar in rows if start <= bar['date'] <= end]
    if len(window) < 2:
        return _result(state, rule, rows, start, end, 'insufficient', 'Fewer than two saved daily bars are available in this period. No trades were invented.')
    needed = _needed(rule)
    warmup = [bar for bar in rows if bar['date'] < start]
    if len(warmup) + len(window) < needed:
        state['notes'].append('The saved history does not contain enough earlier bars for this rule. No signal was invented.')
    for index, bar in enumerate(rows):
        if bar['date'] < start:
            continue
        if bar['date'] > end:
            break
        flags = []
        if index > 0 and _gap(rows[index - 1]['date'], bar['date']):
            flags.append('gap')
        if state['shares'] > 0 and split[index]:
            _sell(state, {'date': rows[index - 1]['date'], 'open': rows[index - 1]['close'], 'ts': rows[index - 1].get('ts')}, {'date': bar['date'], 'index': index, 'reason': 'Closed before a split-sized jump.', 'observations': _observations(rule['exit'], rows, index)}, rule, rows[index - 1]['close'], ['split'])
            pending_sell = None
        elif state['shares'] > 0:
            stop = _stop_raw(state, bar)
            signaled = pending_sell is not None and pending_sell['index'] == index - 1
            if signaled or stop:
                raw = bar['open']
                used = list(flags)
                reason_signal = pending_sell if signaled else None
                if stop and stop[0] <= raw:
                    raw, used = stop[0], used + stop[1]
                elif signaled:
                    used = used + ['signal']
                _sell(state, bar, reason_signal or {'date': bar['date'], 'index': index, 'reason': 'Stop-loss', 'observations': []}, rule, raw, used)
        if pending_buy is not None and pending_buy['index'] == index - 1:
            if state['shares'] == 0 and not split[index]:
                _buy(state, bar, pending_buy, rule, flags)
                stop = _stop_raw(state, bar)
                if state['shares'] > 0 and stop:
                    _sell(state, bar, {'date': bar['date'], 'index': index, 'reason': 'Stop-loss on the entry session.', 'observations': []}, rule, stop[0], flags + stop[1])
            elif split[index]:
                state['notes'].append(bar['date'] + ': the buy was not filled because the next bar is a split-sized jump.')
        pending_buy = pending_sell = None
        if not split[index] and _hit(rule['entry'], closes, split, index, True) and state['shares'] == 0:
            pending_buy = {'index': index, 'date': bar['date'], 'reason': 'Entry: ' + _phrase(rule['entry'], True) + '.', 'observations': _observations(rule['entry'], rows, index)}
        if not split[index] and _hit(rule['exit'], closes, split, index, False) and state['shares'] > 0:
            pending_sell = {'index': index, 'date': bar['date'], 'reason': 'Exit: ' + _phrase(rule['exit'], False) + '.', 'observations': _observations(rule['exit'], rows, index)}
        mark = state['cash'] + state['shares'] * bar['close']
        state['curve'].append({'date': bar['date'], 'equity': mark})
        if state['cash'] < -1e-6 or state['shares'] < -1e-9:
            raise ValueError('The simulated cash or shares became negative.')
    if pending_buy or pending_sell:
        state['notes'].append('A signal formed at the end of the period and had no later saved price to trade.')
    status = 'ok'
    if not window:
        status = 'insufficient'
    return _result(state, rule, rows, start, end, status, '')


def _gap(left, right):
    return len(_sessions(dt.date.fromisoformat(left), dt.date.fromisoformat(right))) > 2


def _needed(rule):
    lengths = []
    for side in (rule['entry'], rule['exit']):
        lengths.append(side['slow'] + 1 if side['kind'] == 'sma_cross' else side['lookback'] + 1)
    return max(lengths)


def _result(state, rule, rows, start, end, status, reason):
    ending = state['curve'][-1]['equity'] if state['curve'] else rule['cash']
    peak = rule['cash']
    drawdown = 0.0
    for point in state['curve']:
        peak = max(peak, point['equity'])
        drawdown = max(drawdown, peak - point['equity'])
    hold = _hold(rows, rule, start, end)
    return {
        'status': status, 'reason': reason, 'start': start, 'end': end,
        'endingValue': ending, 'totalReturn': ending / rule['cash'] - 1 if rule['cash'] else 0,
        'maxDrawdown': drawdown, 'maxDrawdownPct': drawdown / peak if peak else 0,
        'costs': state['costs'] + state['slippage'], 'commissions': state['costs'], 'slippage': state['slippage'],
        'tradeCount': state['completed'], 'fills': len(state['trades']), 'trades': state['trades'],
        'endingCash': state['cash'], 'endingShares': state['shares'], 'curve': state['curve'],
        'notes': state['notes'], 'buyAndHold': hold, 'coverage': _coverage(rows, start, end),
        'dividendNote': 'Dividends, spin-offs and other unsupported events are not in these daily bars. Both this result and the buy-and-hold comparison are price results. A shareholder who received a dividend would have cash that this comparison does not show.',
        'portfolioNote': 'This simulation is stored with Strategy Lab. It is not added to the practice portfolio.',
    }


def _hold(rows, rule, start, end):
    window = [bar for bar in rows if start <= bar['date'] <= end]
    if not window:
        return {'status': 'insufficient', 'endingValue': rule['cash'], 'totalReturn': 0, 'costs': 0, 'note': 'Buy and hold has no saved bar in the same dates.'}
    state = {'cash': rule['cash'], 'shares': 0.0, 'stop': None, 'trades': [], 'costs': 0.0, 'slippage': 0.0, 'completed': 0, 'notes': []}
    _buy(state, window[0], {'date': window[0]['date'], 'index': 0, 'reason': 'Buy and hold enters at the first saved open in the same dates.', 'observations': []}, rule, [])
    ending = state['cash'] + state['shares'] * window[-1]['close']
    return {
        'status': 'ok', 'endingValue': ending, 'totalReturn': ending / rule['cash'] - 1,
        'costs': state['costs'] + state['slippage'], 'shares': state['shares'],
        'entryDate': window[0]['date'], 'entryPrice': window[0]['open'], 'markDate': window[-1]['date'], 'markPrice': window[-1]['close'],
        'note': 'Buy and hold uses the same starting cash, position size, costs and slippage, and buys at the first saved open. The shares are marked at the last saved close. No exit cost is charged on that mark. A strategy that has already closed its position has paid its exit cost.',
    }


def _clean_bars(raw):
    bars = []
    for item in raw or []:
        if not isinstance(item, dict) or not DAY.fullmatch(str(item.get('date') or '')):
            continue
        try:
            prices = [_num(item.get(name), 0.0001, 1e7, name) for name in ('open', 'high', 'low', 'close')]
        except ValueError:
            continue
        opened, high, low, close = prices
        if low > min(opened, close) or high < max(opened, close) or low > high:
            continue
        bars.append({'date': item['date'], 'open': opened, 'high': high, 'low': low, 'close': close, 'ts': item.get('ts')})
    bars.sort(key=lambda bar: bar['date'])
    return bars


def run_rule(raw, bars):
    rule = _rule(raw)
    described = describe(raw)
    changed = bool(raw.get('inspectedLater')) and raw.get('lockedFingerprint') not in ('', None, described['fingerprint'])
    development = simulate(_clean_bars(bars), rule, rule['start'], rule['end'])
    later = None
    if rule['laterStart']:
        later = simulate(_clean_bars(bars), rule, rule['laterStart'], rule['laterEnd'])
    return {
        'model': MODEL, 'rule': rule, 'plainEnglish': described['plainEnglish'], 'assumptions': described['assumptions'],
        'fingerprint': described['fingerprint'], 'development': development, 'later': later,
        'changedAfterInspection': changed,
        'changeNote': 'These settings differ from the locked rule that was evaluated on the later period.' if changed else 'The settings match the locked rule.',
        'portfolioNote': development['portfolioNote'],
    }


def load_bars(g, symbol):
    with contextlib.closing(g['db_connection']()) as con:
        rows = con.execute('SELECT ts_ms,o,h,l,c FROM massive_daily_bars WHERE symbol=? ORDER BY ts_ms', (symbol,)).fetchall()
    found = {}
    for stamp, opened, high, low, close in rows:
        if any(not isinstance(price, (int, float)) or isinstance(price, bool) or not math.isfinite(price) or price <= 0 for price in (opened, high, low, close)):
            continue
        day = market37.dt.datetime.fromtimestamp(stamp / 1000, market37.NY).date().isoformat()
        found[day] = {'date': day, 'open': float(opened), 'high': float(high), 'low': float(low), 'close': float(close), 'ts': int(stamp)}
    return [found[day] for day in sorted(found)]


def evaluate(g, body):
    symbol = g['valid_symbol'](body.get('symbol') or '')
    if not g['ai_catalog_entry'](symbol):
        raise ValueError(symbol + ' is not in the supported directory.')
    result = run_rule(body, load_bars(g, symbol))
    result['symbol'] = symbol
    return result


def save(g, body, now_ms):
    result = evaluate(g, body)
    ident = __import__('secrets').token_hex(8)
    payload = {'symbol': result['symbol'], 'model': MODEL, 'title': str(body.get('title') or result['symbol'] + ' strategy')[:160],
               'rule': result['rule'], 'result': result, 'savedAt': int(now_ms)}
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('INSERT INTO strategy54 VALUES(?,?,?,?,?)', (ident, result['symbol'], payload['title'], json.dumps(payload, allow_nan=False), int(now_ms)))
        con.execute('DELETE FROM strategy54 WHERE id NOT IN (SELECT id FROM strategy54 ORDER BY created_at DESC LIMIT 40)')
    return {'id': ident, 'saved': payload}


def read(g, ident, now_ms):
    if not IDENT.fullmatch(str(ident or '')):
        raise ValueError('Choose a saved strategy.')
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        row = con.execute('SELECT body FROM strategy54 WHERE id=?', (ident,)).fetchone()
    if not row:
        raise ValueError('That strategy is not saved on this Mac.')
    saved = json.loads(row[0])
    return {'saved': saved, 'openedAt': int(now_ms), 'notice': 'The saved rules and results are reopened from this Mac. They are not rewritten from newer prices.'}


def listed(g):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        rows = con.execute('SELECT id,symbol,title,created_at FROM strategy54 ORDER BY created_at DESC LIMIT 40').fetchall()
    return [{'id': ident, 'symbol': symbol, 'title': title, 'createdAt': created} for ident, symbol, title, created in rows]
