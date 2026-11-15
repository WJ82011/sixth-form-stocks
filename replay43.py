"""Reveal saved prices, trades and events only up to a replay cursor."""


GAP_MS = 5 * 60 * 1000


def frame(prices, trades, events, cursor_ms):
    """Return only records whose time is at or before the cursor.

    Date-only events stay in a separate list because their clock time is unknown.
    High, low and gaps are calculated from revealed prices alone.
    """
    cursor = int(cursor_ms)
    shown_prices = sorted(
        (row for row in prices or [] if _time(row) is not None and _time(row) <= cursor and _price(row) is not None),
        key=_time)
    shown_trades = [row for row in trades or [] if _time(row) is not None and _time(row) <= cursor]
    timed, undated = [], []
    for event in events or []:
        if not isinstance(event, dict):
            continue
        published = event.get('publishedAt')
        if isinstance(published, bool) or not isinstance(published, (int, float)):
            undated.append({**event, 'timing': 'unknown'})
        elif int(published) <= cursor:
            timed.append(event)
    gaps = []
    for earlier, later in zip(shown_prices, shown_prices[1:]):
        if _time(later) - _time(earlier) > GAP_MS:
            gaps.append({'from': _time(earlier), 'to': _time(later), 'open': False})
    if shown_prices and cursor - _time(shown_prices[-1]) > GAP_MS:
        gaps.append({'from': _time(shown_prices[-1]), 'to': cursor, 'open': True})
    values = [_price(row) for row in shown_prices]
    return {
        'cursor': cursor,
        'prices': shown_prices,
        'trades': shown_trades,
        'timedEvents': timed,
        'dateOnlyEvents': undated,
        'high': max(values) if values else None,
        'low': min(values) if values else None,
        'gaps': gaps,
        'separateFromAlerts': True,
    }


def _time(row):
    value = row.get('t') if isinstance(row, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _price(row):
    value = row.get('p') if isinstance(row, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        return None
    return float(value)
