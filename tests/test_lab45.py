"""Forecast Lab uses earlier dates to choose and later dates to score. Fixture prices only."""
import datetime as dt
import math
import unittest
from unittest.mock import patch

import lab45
import learning40
import market37
import scorecard41
import test_v3_api as fixture

s = fixture.s
NY = market37.NY


def stamp(day, hour=16):
    return int(dt.datetime.combine(dt.date.fromisoformat(day), dt.time(hour), NY).timestamp() * 1000)


class ForecastLabTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_models_share_dates_and_the_current_model_matches_its_own_score(self):
        prices = [{'p': 100 * math.exp(.001 * i)} for i in range(320)]
        current = learning40.evaluate(prices, 5)
        row = next(item for item in lab45.challenge(prices) if item['horizon'] == 5)
        by_name = {item['key']: item for item in row['models']}
        self.assertEqual(by_name['current']['count'], by_name['volatility']['count'])
        self.assertEqual(by_name['current']['count'], by_name['unchanged']['count'])
        self.assertEqual(by_name['current']['start'], by_name['volatility']['start'])
        self.assertEqual(by_name['current']['end'], by_name['unchanged']['end'])
        self.assertAlmostEqual(by_name['current']['averageErrorPP'], current['modelErrorPP'], places=6)
        self.assertAlmostEqual(by_name['unchanged']['averageErrorPP'], current['baselineErrorPP'], places=6)
        self.assertGreaterEqual(row['calibration']['count'], 8)
        self.assertEqual(row['test']['count'], current['testCases'])

    def test_a_later_price_cannot_change_an_earlier_decision(self):
        prices = [{'p': 50 * math.exp(.0008 * i)} for i in range(340)]
        before = lab45.walk(prices, 5)
        changed = [dict(row) for row in prices]
        changed[-1]['p'] = 1
        after = lab45.walk(changed, 5)
        shared = [row for row in before if row['target'] < len(prices) - 1]
        self.assertGreater(len(shared), 8)
        for left, right in zip(shared, after):
            self.assertEqual(left['anchor'], right['anchor'])
            self.assertEqual(left['ridge'], right['ridge'])
            self.assertEqual(left['drift'], right['drift'])
            self.assertEqual(left['actual'], right['actual'])
            self.assertLessEqual(left['anchor'], left['target'] - 5)

    def test_flat_prices_do_not_release_a_forecast(self):
        prices = [{'p': 100.0} for _ in range(280)]
        row = next(item for item in lab45.challenge(prices) if item['horizon'] == 5)
        self.assertEqual(row['status'], 'withheld')
        self.assertIsNone(row['released'])
        self.assertIn('unchanged price', row['reason'].lower())

    def test_a_model_that_loses_the_later_test_is_withheld(self):
        prices = []
        price = 100.0
        for _ in range(220):
            price *= 1.004
            prices.append({'p': price})
        prices.extend({'p': price} for _ in range(200))
        row = next(item for item in lab45.challenge(prices) if item['horizon'] == 5)
        scored = {item['key']: item for item in row['models']}
        self.assertGreater(scored['current']['averageErrorPP'], scored['unchanged']['averageErrorPP'])
        self.assertGreaterEqual(scored['volatility']['averageErrorPP'], scored['unchanged']['averageErrorPP'])
        self.assertEqual(row['status'], 'withheld')
        self.assertIsNone(row['released'])
        self.assertIn('later test', row['reason'])
        self.assertTrue(all(miss['target'] == miss['anchor'] + 5 for miss in row['misses']))
        self.assertTrue(all(miss['inputs'][-1]['price'] == miss['anchorPrice'] for miss in row['misses']))

    def test_too_little_history_releases_nothing(self):
        row = lab45.challenge([{'p': 10 + i} for i in range(40)])[0]
        self.assertEqual(row['status'], 'insufficient')
        self.assertIsNone(row['released'])
        self.assertEqual(row['models'], [])
        self.assertIn('Too little', row['reason'])

    def test_a_split_sized_jump_is_withheld_and_prices_stay_as_saved(self):
        day = dt.date(2026, 9, 1)
        rows = []
        while len(rows) < 12:
            if day.weekday() < 5 and day not in market37.holidays(day.year):
                price = 100 if len(rows) < 11 else 30
                rows.append((day.isoformat(), price))
            day += dt.timedelta(days=1)
        import contextlib
        with contextlib.closing(s.db_connection()) as con, con:
            con.executemany('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)', [
                ('AAPL', stamp(day), price, price, price, price, 1, 1) for day, price in rows])
        with patch.object(s, 'provider_get', side_effect=AssertionError('offline')), patch.object(
                s, 'massive_request', side_effect=AssertionError('offline')), patch.object(
                market37, 'today', return_value=dt.date(2026, 11, 10)):
            report = learning40.report(vars(s), 'AAPL')
        self.assertTrue(report['quality'])
        self.assertEqual(report['rows'], [])
        self.assertTrue(all(item['released'] is None for item in report['lab']))
        self.assertIn('not changed', report['lab'][0]['reason'])
        saved = s.read_massive_daily_bars('AAPL', 946684800, 2000000000)
        self.assertEqual(saved['bars']['c'], [price for _, price in rows])

    def test_a_missing_session_is_left_out_of_the_test(self):
        day = dt.date(2026, 1, 2)
        rows = []
        while day <= dt.date(2026, 11, 6):
            if day.weekday() < 5 and day not in market37.holidays(day.year) and day != dt.date(2026, 6, 15):
                rows.append((day.isoformat(), 80 + len(rows) * .1))
            day += dt.timedelta(days=1)
        import contextlib
        with contextlib.closing(s.db_connection()) as con, con:
            con.executemany('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)', [
                ('AMD', stamp(day), price, price, price, price, 1, 1) for day, price in rows])
        with patch.object(s, 'provider_get', side_effect=AssertionError('offline')), patch.object(
                market37, 'today', return_value=dt.date(2026, 11, 10)):
            report = learning40.report(vars(s), 'AMD')
        self.assertGreater(report['coverage']['droppedForGap'], 0)
        self.assertGreater(report['coverage']['usedCloses'], 20)
        self.assertGreater(report['coverage']['firstUsed'], '2026-06-15')
        self.assertTrue(all(row['date'] > '2026-06-15' for row in report['knownCloses']))
        self.assertEqual(report['coverage']['source'].startswith('Massive'), True)
        self.assertIsNotNone(report['coverage']['latestSavedPrice'])
        self.assertTrue(report['trainedAt'])

    def test_retraining_keeps_the_prices_the_forecast_was_issued_with(self):
        issued = {
            'method': 'ridge-sessions-v4.1', 'stale': False, 'quality': '',
            'anchorDate': '2026-10-30', 'anchor': {'t': stamp('2026-10-30'), 'p': 100},
            'knownCloses': [{'date': '2026-10-29', 'price': 99}, {'date': '2026-10-30', 'price': 100}],
            'rows': [{'status': 'learned', 'horizon': 1, 'price': 101, 'low': 99, 'high': 103,
                      'returnPct': 1, 'calibrationCases': 10, 'testCases': 9,
                      'modelErrorPP': 1, 'baselineErrorPP': 2}],
            'lab': [],
        }
        points = [{'t': stamp('2026-10-30'), 'p': 100}]
        now = stamp('2026-11-09', 15) / 1000
        with patch.object(s.time, 'time', return_value=now):
            first = scorecard41.sync(vars(s), 'TTWO', issued, points)
        self.assertEqual(first['pending'][0]['knownCloses'][0]['price'], 99)
        revised = dict(issued)
        revised['knownCloses'] = [{'date': '2026-10-30', 'price': 50}]
        revised['rows'] = [dict(issued['rows'][0], price=140)]
        with patch.object(s.time, 'time', return_value=now + 10):
            second = scorecard41.sync(vars(s), 'TTWO', revised, points)
        self.assertEqual(second['pending'][0]['forecastPrice'], 101)
        self.assertEqual(second['pending'][0]['knownCloses'][0]['price'], 99)
        self.assertEqual(second['pending'][0]['baselinePrice'], 100)
