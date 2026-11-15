"""Forecast Lab. The current model and a volatility adjustment share every test date.

The shrinkage is chosen on the earlier half of the walk. The later half is only scored.
A training target may use the close on the decision date. It may not use a later close.
"""
import datetime as dt
import math

import market34
import market37

METHOD = 'volatility-scaled-drift-v4.5'
SHRINKAGE = (0, 0.25, 0.5, 0.75, 1)
NY = market37.NY


def _clip(value):
    return max(-.35, min(.35, value))


def _error(pred, actual):
    return abs(math.expm1(pred) - math.expm1(actual)) * 100


def _mean(rows):
    return sum(rows) / len(rows) if rows else None


def _day(point):
    stamp = point.get('t')
    if not isinstance(stamp, (int, float)) or isinstance(stamp, bool):
        return None
    return dt.datetime.fromtimestamp(stamp / 1000, NY).date().isoformat()


def _price(anchor, log_return):
    return anchor * math.exp(log_return)


def walk(prices, horizon):
    """One row per decision the current model already makes. No later close is an input."""
    if horizon not in (1, 5, 20) or len(prices) < 160 + horizon:
        return []
    features = [market34.features(prices, i) if i >= 60 else None for i in range(len(prices))]
    targets = [{'x': features[i], 'y': math.log(prices[i + horizon]['p'] / prices[i]['p'])}
               for i in range(60, len(prices) - horizon)]
    rows = []
    for anchor in range(160, len(prices) - horizon, horizon):
        train = targets[:anchor - horizon - 59]
        if len(train) < 75:
            continue
        last_known = 60 + len(train) - 1
        if last_known + horizon > anchor:
            raise RuntimeError('A training result used a price after the decision.')
        if anchor < 20:
            continue
        ridge = _clip(market34.predict(market34.fit(train), features[anchor]))
        returns = [math.log(prices[j]['p'] / prices[j - 1]['p']) for j in range(anchor - 19, anchor + 1)]
        drift = (sum(returns) / len(returns)) * horizon
        actual = math.log(prices[anchor + horizon]['p'] / prices[anchor]['p'])
        rows.append({
            'anchor': anchor,
            'target': anchor + horizon,
            'anchorPrice': prices[anchor]['p'],
            'actualPrice': prices[anchor + horizon]['p'],
            'anchorDate': _day(prices[anchor]),
            'targetDate': _day(prices[anchor + horizon]),
            'ridge': ridge,
            'drift': drift,
            'actual': actual,
        })
    return rows


def _coverage(rows, pred, residuals):
    if len(residuals) < 8 or not rows:
        return None
    low = market34.quantile(residuals, .1)
    high = market34.quantile(residuals, .9)
    hits = 0
    for row in rows:
        guess = pred(row)
        if min(guess, guess + low) <= row['actual'] <= max(guess, guess + high):
            hits += 1
    return hits / len(rows) * 100


def _band(pred, residuals):
    if len(residuals) < 8:
        return None
    low = market34.quantile(residuals, .1)
    high = market34.quantile(residuals, .9)
    return min(pred, pred + low), max(pred, pred + high)


def challenge(prices):
    """Score 1, 5 and 20 sessions. The candidate is tuned only on the earlier dates."""
    reports = []
    for horizon in (1, 5, 20):
        rows = walk(prices, horizon)
        split = len(rows) // 2
        calibration, test = rows[:split], rows[split:]
        base = {
            'horizon': horizon,
            'calibration': _window(calibration),
            'test': _window(test),
            'separate': 'The later block was not used to choose the shrinkage or to decide the current model.',
        }
        if len(calibration) < 8 or len(test) < 8:
            reports.append({
                **base, 'status': 'insufficient', 'released': None,
                'reason': 'Too little saved history for a separate later test. No learned forecast was released.',
                'models': [], 'misses': [],
            })
            continue
        best = None
        for shrinkage in SHRINKAGE:
            error = _mean([_error(_clip(shrinkage * row['drift']), row['actual']) for row in calibration])
            if best is None or error < best[0]:
                best = (error, shrinkage)
        shrinkage = best[1]
        def vol(row, chosen=shrinkage):
            return _clip(chosen * row['drift'])
        cal_residuals = {
            'current': [row['actual'] - row['ridge'] for row in calibration],
            'volatility': [row['actual'] - vol(row) for row in calibration],
            'unchanged': [row['actual'] for row in calibration],
        }
        names = (
            ('current', 'Current model', lambda row: row['ridge']),
            ('volatility', 'Volatility adjustment', vol),
            ('unchanged', 'Unchanged price', lambda row: 0),
        )
        models = []
        for key, label, pred in names:
            guesses = [pred(row) for row in test]
            models.append({
                'key': key,
                'name': label,
                'start': test[0]['anchorDate'],
                'end': test[-1]['targetDate'],
                'count': len(test),
                'averageErrorPP': _mean([_error(guess, row['actual']) for guess, row in zip(guesses, test)]),
                'rangeCoveragePct': _coverage(test, pred, cal_residuals[key]),
            })
        by_key = {row['key']: row for row in models}
        candidate = by_key['volatility']
        unchanged = by_key['unchanged']['averageErrorPP']
        earlier_unchanged = _mean([_error(0, row['actual']) for row in calibration])
        released = None
        if best[0] >= earlier_unchanged:
            status = 'withheld'
            reason = 'The volatility model was not chosen on the earlier dates, because an unchanged price did at least as well there. No volatility forecast was released.'
        elif candidate['averageErrorPP'] >= unchanged:
            status = 'withheld'
            reason = 'The volatility model does not beat an unchanged price on the later test. Its forecast was withheld.'
        else:
            status = 'ready'
            reason = 'The volatility model beat an unchanged price on the earlier dates and again on the later dates. The shrinkage was not refit on the later dates.'
            latest = prices[-1]['p']
            drift = (sum(math.log(prices[j]['p'] / prices[j - 1]['p']) for j in range(len(prices) - 20, len(prices))) / 20) * horizon
            guess = _clip(shrinkage * drift)
            band = _band(guess, cal_residuals['volatility'])
            if band:
                low, high = _price(latest, band[0]), _price(latest, band[1])
                price = _price(latest, guess)
                if 0 < low <= price <= high:
                    released = {
                        'model': 'volatility', 'method': METHOD, 'horizon': horizon,
                        'price': price, 'low': low, 'high': high,
                        'returnPct': math.expm1(guess) * 100, 'shrinkage': shrinkage,
                    }
                else:
                    status = 'withheld'
                    reason = 'The volatility range was not ordered around the forecast. Nothing was released.'
                    released = None
        misses = []
        for row in test:
            guess = vol(row)
            band = _band(guess, cal_residuals['volatility'])
            low = high = None
            if band:
                low, high = _price(row['anchorPrice'], band[0]), _price(row['anchorPrice'], band[1])
            error = _error(guess, row['actual'])
            base_error = _error(0, row['actual'])
            if error + 1e-9 < base_error:
                continue
            start = max(0, row['anchor'] - 11)
            misses.append({
                'anchor': row['anchor'], 'target': row['target'],
                'anchorDate': row['anchorDate'], 'targetDate': row['targetDate'],
                'anchorPrice': row['anchorPrice'], 'actualPrice': row['actualPrice'],
                'forecastPrice': _price(row['anchorPrice'], guess),
                'baselinePrice': row['anchorPrice'],
                'low': low, 'high': high,
                'currentPrice': _price(row['anchorPrice'], row['ridge']),
                'errorPP': error, 'baselineErrorPP': base_error,
                'inRange': low is not None and low <= row['actualPrice'] <= high,
                'inputs': [{'date': _day(prices[i]), 'price': prices[i]['p']} for i in range(start, row['anchor'] + 1)],
            })
        misses.sort(key=lambda row: row['errorPP'] - row['baselineErrorPP'], reverse=True)
        mid = max(1, len(test) // 2)
        early, late = test[:mid], test[mid:] or test[:mid]
        early_error = _mean([_error(vol(row), row['actual']) for row in early])
        late_error = _mean([_error(vol(row), row['actual']) for row in late])
        late_base = _mean([_error(0, row['actual']) for row in late])
        coverage = candidate['rangeCoveragePct']
        reliable = late_error < late_base and (coverage is None or coverage >= 50)
        durability = {
            'earlyErrorPP': early_error, 'lateErrorPP': late_error, 'lateBaselineErrorPP': late_base,
            'early': _window(early), 'late': _window(late),
            'rangeCoveragePct': coverage, 'expectedCoveragePct': 80,
            'reliable': reliable,
            'method': METHOD,
        }
        if status == 'ready' and not reliable:
            status = 'withheld'
            released = None
            if late_error >= late_base:
                reason = 'The volatility model beat the full later test, but its most recent dates did not beat an unchanged price. No forecast was released.'
            else:
                reason = 'The forecast range contained the later outcomes less often than this check allows. No forecast was released.'
        reports.append({
            **base, 'status': status, 'reason': reason, 'released': released,
            'shrinkage': shrinkage,
            'models': models,
            'path': [{'date': row['targetDate'], 'actualPrice': row['actualPrice']} for row in test],
            'misses': misses[:8],
            'missCount': len(misses),
            'durability': durability,
        })
    return reports


def _window(rows):
    if not rows:
        return {'start': None, 'end': None, 'count': 0}
    return {'start': rows[0]['anchorDate'], 'end': rows[-1]['targetDate'], 'count': len(rows)}


def known_closes(points, anchor_day, limit=80):
    rows = []
    for point in points or []:
        day = _day(point)
        if not day or (anchor_day and day > anchor_day):
            continue
        try:
            price = float(point['p'])
        except (TypeError, ValueError):
            continue
        if price > 0:
            rows.append({'date': day, 'price': price})
    return rows[-limit:]
