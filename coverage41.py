"""Labels for chart coverage. Free daily history can fill some gaps; the rest stay visible."""
import datetime as dt
import math

import market37

NY = market37.NY
OPEN = dt.time(9, 30)
EARLY = {
    2025: {dt.date(2025, 7, 3), dt.date(2025, 11, 28), dt.date(2025, 12, 24)},
    2026: {dt.date(2026, 11, 27), dt.date(2026, 12, 24)},
    2027: {dt.date(2027, 11, 26)},
    2028: {dt.date(2028, 7, 3), dt.date(2028, 11, 24)},
}


def ms(value):
    value = int(value)
    return value if value > 10_000_000_000 else value * 1000


def as_date(value):
    return dt.datetime.fromtimestamp(ms(value) / 1000, NY).date()


def is_session(day):
    return day.weekday() < 5 and day not in market37.holidays(day.year)


def session_bounds(day):
    if not is_session(day):
        return None
    close_hour = 13 if day in EARLY.get(day.year, ()) else 16
    opened = dt.datetime.combine(day, OPEN, NY)
    closed = dt.datetime.combine(day, dt.time(close_hour), NY)
    return int(opened.timestamp() * 1000), int(closed.timestamp() * 1000)


def free_window(now_ms):
    today = dt.datetime.fromtimestamp(now_ms / 1000, NY).date()
    latest = today - dt.timedelta(days=1)
    try:
        earliest = today.replace(year=today.year - 2) + dt.timedelta(days=2)
    except ValueError:
        earliest = today.replace(year=today.year - 2, day=28) + dt.timedelta(days=2)
    return earliest, latest


def latest_eligible(now_ms):
    today = dt.datetime.fromtimestamp(now_ms / 1000, NY).date()
    if not 2025 <= today.year <= 2028:
        return None
    try:
        return dt.date.fromisoformat(market37.sessions(today, 1)[0])
    except ValueError:
        return None


def overlaps_open_session(start_ms, end_ms):
    if end_ms - start_ms <= 5 * 60 * 1000:
        return False
    day = dt.datetime.fromtimestamp(start_ms / 1000, NY).date()
    last = dt.datetime.fromtimestamp(end_ms / 1000, NY).date()
    steps = 0
    while day <= last and steps < 12:
        bounds = session_bounds(day)
        if bounds:
            opened, closed = bounds
            overlap = min(end_ms, closed) - max(start_ms, opened)
            if overlap > 5 * 60 * 1000:
                return True
        day += dt.timedelta(days=1)
        steps += 1
    return False


def split_note(prices, adjusted):
    if adjusted is None:
        return ''
    for left, right in zip(prices, prices[1:]):
        if left > 0 and abs(math.log(right / left)) > .7:
            if adjusted is False:
                return 'Unadjusted prices. A move this large can be a stock split. The saved prices were not changed.'
            return 'Split-adjusted source. This large move is kept as reported and was not rewritten.'
    return ''


def freshness(last_ms, now_ms, requested):
    if requested in ('live', 'delayed', 'saved'):
        return requested
    if last_ms is None:
        return 'saved'
    now = dt.datetime.fromtimestamp(now_ms / 1000, NY)
    last = dt.datetime.fromtimestamp(last_ms / 1000, NY)
    bounds = session_bounds(now.date())
    if last.date() != now.date() or not bounds or not bounds[0] <= now_ms <= bounds[1]:
        return 'saved'
    return 'live' if now_ms - last_ms <= 15 * 60 * 1000 else 'delayed'


def daily(points, now_ms, source, adjusted=True, tail='display'):
    rows = []
    for point in points or []:
        try:
            price = float(point['p'])
            stamp = ms(point['t'])
        except (TypeError, ValueError, KeyError):
            continue
        if math.isfinite(price) and price > 0:
            rows.append({'t': stamp, 'p': price, 'day': as_date(stamp)})
    rows.sort(key=lambda row: row['t'])
    seen = {}
    for row in rows:
        seen[row['day']] = row
    days = sorted(seen)
    earliest, latest_free = free_window(now_ms)
    eligible = latest_eligible(now_ms)
    end = days[-1] if days else None
    start = days[0] if days else None
    if tail == 'display' and eligible and days and days[-1] < eligible <= days[-1] + dt.timedelta(days=10):
        end = min(eligible, latest_free)
    elif tail == 'fill' and eligible and (end is None or eligible > end):
        end = min(eligible, latest_free)
    trading = []
    closures = 0
    if start and end and start <= end:
        day = start
        while day <= end:
            if day not in seen:
                if is_session(day):
                    trading.append({
                        'day': day.isoformat(),
                        'kind': 'trading',
                        'fillable': earliest <= day <= latest_free,
                    })
                else:
                    closures += 1
            day += dt.timedelta(days=1)
    fillable = any(gap['fillable'] for gap in trading)
    if not days:
        notice = 'No saved prices for this chart. Nothing was invented.'
    elif trading and not fillable:
        notice = 'These trading gaps are outside the free daily window, or the feed cannot replace them. They stay visible.'
    elif trading:
        notice = 'Supported daily gaps are requested first after a restart. Gaps the free feed cannot fill stay visible.'
    else:
        notice = 'Scheduled weekends and holidays are closures, not missing trades.'
    last = rows[-1]['t'] if rows else None
    return {
        'source': source,
        'asOf': last,
        'checkedAt': now_ms,
        'freshness': 'saved',
        'complete': not trading and bool(days),
        'tradingGapCount': len(trading),
        'tradingGaps': trading[:12],
        'closureCount': closures,
        'fillable': fillable,
        'adjusted': adjusted,
        'splitNote': split_note([row['p'] for row in rows], adjusted),
        'notice': notice,
    }


def intraday(points, now_ms, source):
    rows = []
    for point in points or []:
        try:
            price = float(point.get('p', point.get('price')))
            stamp = ms(point.get('t', point.get('time')))
        except (TypeError, ValueError, AttributeError):
            continue
        if math.isfinite(price) and price > 0:
            rows.append({'t': stamp, 'p': price})
    rows.sort(key=lambda row: row['t'])
    trading = []
    closures = 0
    for left, right in zip(rows, rows[1:]):
        if right['t'] - left['t'] <= 5 * 60 * 1000:
            continue
        if overlaps_open_session(left['t'], right['t']):
            trading.append({'from': left['t'], 'to': right['t'], 'kind': 'trading', 'fillable': False})
        else:
            closures += 1
    last = rows[-1]['t'] if rows else None
    if not rows:
        notice = 'No recorded prices in this view. Nothing was invented.'
    elif trading:
        notice = 'The free trade feed does not backfill minutes missed while this Mac was off or disconnected. Those gaps stay visible.'
    else:
        notice = 'Breaks that fall on nights, weekends or exchange holidays are scheduled closures.'
    return {
        'source': source,
        'asOf': last,
        'checkedAt': now_ms,
        'freshness': freshness(last, now_ms, None),
        'complete': bool(rows) and not trading,
        'tradingGapCount': len(trading),
        'tradingGaps': trading[:12],
        'closureCount': closures,
        'fillable': False,
        'adjusted': None,
        'splitNote': split_note([row['p'] for row in rows], None),
        'notice': notice,
    }


def from_candles(candles, now_ms, source, adjusted=True):
    if not candles or not candles.get('t'):
        return daily([], now_ms, source, adjusted)
    points = [{'t': stamp, 'p': price} for stamp, price in zip(candles.get('t', []), candles.get('c', []))]
    return daily(points, now_ms, source, adjusted)


def crypto(packet, product):
    points = packet.get('points') or []
    expected = packet.get('expected') or 0
    interval = packet.get('interval') or 0
    trading = []
    if interval:
        ordered = sorted(points, key=lambda row: row.get('t', 0))
        for left, right in zip(ordered, ordered[1:]):
            if right['t'] - left['t'] > interval * 1.5:
                trading.append({'from': left['t'], 'to': right['t'], 'kind': 'trading', 'fillable': False})
    missing = max(0, expected - len(points)) if expected else 0
    freshness_label = 'saved'
    last = points[-1]['t'] if points else packet.get('fetchedAt')
    return {
        'source': 'Coinbase Exchange public ' + product + ' candles',
        'asOf': last,
        'checkedAt': packet.get('fetchedAt'),
        'freshness': freshness_label,
        'complete': bool(points) and not trading and not missing,
        'tradingGapCount': len(trading) + (1 if missing else 0),
        'tradingGaps': trading[:12],
        'closureCount': 0,
        'fillable': False,
        'adjusted': None,
        'splitNote': '',
        'notice': 'Crypto has no exchange holiday in this chart. Missing candles stay missing. A saved copy is not a live trade.',
    }


def priority(g, symbols, now_ms=None):
    now_ms = int(g['time'].time() * 1000) if now_ms is None else now_ms
    earliest, _latest = free_window(now_ms)
    start = int(dt.datetime.combine(earliest, dt.time(), NY).timestamp())
    ranked = []
    for symbol in symbols:
        saved = g['read_massive_daily_bars'](symbol, start, now_ms // 1000)
        candles = saved['bars'] if saved else None
        report = daily([{'t': stamp, 'p': price} for stamp, price in zip(candles.get('t', []), candles.get('c', []))] if candles else [], now_ms, 'Massive saved daily bars', True, 'fill')
        if report['tradingGapCount'] or not (candles and candles.get('t')):
            ranked.append((report['tradingGapCount'] or 1, symbol))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [symbol for _, symbol in ranked]
