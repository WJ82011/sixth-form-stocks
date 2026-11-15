"""Crypto forecast horizons, withheld models and issued records."""
import contextlib
import datetime as dt
import math
import unittest
from unittest.mock import patch

import crypto57
import events42
import test_v3_api as fixture

s = fixture.s
HOUR = 3600000
DAY = 86400000


def persistent(interval, count=120, start=1_700_000_000_000):
    """Each completed return is 0.7 times the previous return plus a small wave."""
    start -= start % interval
    price, rate, points = 100.0, 0.04, []
    for index in range(count):
        points.append({'t': start + index * interval, 'p': price})
        price *= math.exp(rate)
        rate = 0.7 * rate + 0.01 * math.sin(index)
    return points


def halving(interval, count=80, start=1_700_000_000_000):
    start -= start % interval
    price, rate, points = 100.0, 0.04, []
    for index in range(count):
        points.append({'t': start + index * interval, 'p': price})
        price *= math.exp(rate)
        rate *= 0.5
    return points


def alternating(interval, count=80, start=1_700_000_000_000):
    start -= start % interval
    price, points = 100.0, []
    for index in range(count):
        points.append({'t': start + index * interval, 'p': price})
        price *= 1.05 if index % 2 == 0 else 1 / 1.05
    return points


def series(hourly, daily):
    return {HOUR: hourly, DAY: daily}


class CryptoForecastTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_missing_conflict_and_order(self):
        daily = halving(DAY)
        removed = daily[:10] + daily[11:]
        gapped = crypto57.report(vars(s), 'BTC-USD', series(halving(HOUR), removed))
        day = next(row for row in gapped['horizons'] if row['id'] == '24H')
        self.assertGreater(day['dropped'], 0)
        self.assertTrue(day['gaps'])
        conflict = daily[:20] + [{'t': daily[20]['t'], 'p': daily[20]['p'] + 1}] + daily[20:]
        withheld = crypto57.evaluate(conflict, crypto57.HORIZONS[1])
        self.assertEqual(withheld['status'], 'withheld')
        messy = crypto57.align(list(reversed(halving(HOUR))), HOUR)
        clean = crypto57.align(halving(HOUR), HOUR)
        self.assertTrue(messy['reordered'])
        self.assertEqual(messy['points'], clean['points'])
        ordered = crypto57.walk(clean['points'], 1)
        self.assertEqual(ordered[0]['target'], ordered[1]['anchor'])

    def test_utc_day_boundary_is_kept(self):
        start = int(dt.datetime(2026, 11, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
        points = halving(DAY, 50, start)
        rows = crypto57.walk(crypto57.align(points, DAY)['points'], 1)
        saturday = next(row for row in rows if row['targetMs'] == int(dt.datetime(2026, 11, 14, tzinfo=dt.timezone.utc).timestamp() * 1000))
        self.assertEqual(crypto57._utc(saturday['targetMs'])[:10], '2026-11-14')
        self.assertFalse(events42.is_session(dt.date(2026, 11, 14)))
        self.assertTrue(events42.is_session(dt.date(2026, 11, 13)))

    def test_a_model_that_loses_is_withheld_and_a_persistent_model_can_be_issued(self):
        lost = crypto57.report(vars(s), 'ETH-USD', series(alternating(HOUR), alternating(DAY)))
        weak = next(row for row in lost['horizons'] if row['id'] == '1H')
        self.assertEqual(weak['status'], 'baseline')
        self.assertGreaterEqual(weak['modelErrorPP'], weak['unchangedErrorPP'])
        self.assertEqual(lost['issued'], [])
        gained = crypto57.report(vars(s), 'SOL-USD', series(persistent(HOUR), persistent(DAY)))
        strong = next(row for row in gained['horizons'] if row['id'] == '1H')
        self.assertEqual(strong['status'], 'learned')
        self.assertLess(strong['modelErrorPP'], strong['unchangedErrorPP'])
        self.assertLess(strong['modelErrorPP'], strong['driftErrorPP'])
        self.assertGreaterEqual(strong['tuneCount'], 8)
        self.assertGreaterEqual(strong['testCount'], 8)
        first = next(row['forecastPrice'] for row in gained['issued'] if row['horizon'] == '1H')
        changed = persistent(HOUR)
        changed[-1] = {'t': changed[-1]['t'], 'p': changed[-1]['p'] * 1.01}
        again = crypto57.report(vars(s), 'SOL-USD', series(changed, persistent(DAY)))
        self.assertEqual(next(row['forecastPrice'] for row in again['issued'] if row['horizon'] == '1H'), first)
        target = next(row['targetMs'] for row in gained['issued'] if row['horizon'] == '1H')
        crypto57._save_candles(vars(s), 'SOL-USD', HOUR, [{'t': target, 'p': first * 1.001}])
        self.assertEqual(crypto57.grade(vars(s), 'SOL-USD')['graded'], 1)
        saved = crypto57.issued(vars(s), 'SOL-USD')
        self.assertEqual(saved[0]['outcome']['rule'], crypto57.GRADE_RULE)
        self.assertEqual(saved[0]['record'], 'issued forecast')

    def test_interrupted_training_keeps_the_stored_report(self):
        crypto57.report(vars(s), 'BTC-USD', series(persistent(HOUR), persistent(DAY)))
        with patch.object(crypto57, 'build', side_effect=RuntimeError('stopped')):
            kept = crypto57.report(vars(s), 'BTC-USD', series(persistent(HOUR, 140), persistent(DAY)))
        self.assertIn('unchanged', kept['notice'])
        with contextlib.closing(s.db_connection()) as con:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM crypto57_reports').fetchone()[0], 1)

    def test_short_history_and_intelligence_use_the_saved_report(self):
        short = crypto57.report(vars(s), 'SOL-USD', series(halving(HOUR, 5), halving(DAY, 5)))
        self.assertTrue(all(row['status'] == 'insufficient' for row in short['horizons']))
        text, evidence = crypto57.explain(vars(s), 'SOL-USD')
        self.assertIn('not enough', text)
        self.assertIn('separately', text)
        self.assertEqual(evidence['source'].startswith('Saved Coinbase'), True)
        opened = crypto57.read(vars(s), 'SOL-USD')
        self.assertIn('not retrained', opened['notice'])
