"""Forecast path honesty. Prices in these tests are labelled records, not market quotes."""
import datetime as dt
import unittest

import events42
import forecast61
import test_v3_api as fixture

s = fixture.s
NOW = int(dt.datetime(2026, 1, 12, 18, tzinfo=events42.NY).timestamp() * 1000)


def sessions(count, end):
    days, cursor = [], end
    while len(days) < count:
        if events42.is_session(cursor):
            days.append(cursor)
        cursor -= dt.timedelta(days=1)
    return list(reversed(days))


def prices(count, end, value=100):
    return [{'t': int(dt.datetime.combine(day, dt.time(16), events42.NY).timestamp() * 1000), 'p': value}
            for day in sessions(count, end)]


def learned(points, horizon):
    if horizon == 1:
        return {'horizon': 1, 'status': 'baseline', 'modelErrorPP': 2, 'baselineErrorPP': 1.5, 'testCases': 10}
    price = points[-1]['p'] * (1.01 if horizon == 5 else 1.02)
    return {'horizon': horizon, 'status': 'learned', 'modelErrorPP': 1, 'baselineErrorPP': 1.4,
            'testCases': 12, 'price': price, 'low': price - 1, 'high': price + 1, 'returnPct': (price / points[-1]['p'] - 1) * 100}


class ForecastPathTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_only_justified_horizons_are_drawn_and_joins_are_labelled(self):
        end = dt.date(2026, 1, 12)
        built = forecast61.build(prices(240, end), NOW, 'TTWO', learned)
        self.assertEqual(built['status'], 'learned')
        self.assertEqual([row['day'] for row in built['rows']], [0, 5, 20])
        self.assertEqual(built['rows'][0]['kind'], 'recorded')
        self.assertTrue(all('straight join' in line for line in built['interpolation']))
        self.assertFalse(built['newsUsed'])
        self.assertIn('Daily closing prices only', built['inputs'])
        self.assertLess(built['rows'][1]['low'], built['rows'][1]['price'])
        self.assertGreater(built['rows'][1]['high'], built['rows'][1]['price'])

    def test_a_losing_model_short_history_a_split_and_stale_data_withhold_the_path(self):
        end = dt.date(2026, 1, 12)

        def lose(points, horizon):
            return {'horizon': horizon, 'status': 'baseline', 'modelErrorPP': 3, 'baselineErrorPP': 2, 'testCases': 10}

        lost = forecast61.build(prices(240, end), NOW, 'AMD', lose)
        self.assertEqual(lost['status'], 'withheld')
        self.assertEqual(lost['rows'], [])
        short = forecast61.build(prices(11, end), NOW, 'AAPL')
        self.assertEqual(short['status'], 'insufficient')
        jumped = prices(240, end)
        jumped[20]['p'] = 10
        jumped[21]['p'] = 40
        split = forecast61.build(jumped, NOW, 'AMD', learned)
        self.assertIn('split', split['notice'])
        self.assertEqual(split['rows'], [])
        old = prices(240, dt.date(2025, 12, 1))
        stale = forecast61.build(old, NOW, 'AAPL', learned)
        self.assertEqual(stale['status'], 'stale')
        self.assertEqual(stale['rows'], [])

    def test_reading_a_symbol_does_not_replace_an_issued_forecast(self):
        with s.db_connection() as con:
            before = con.execute("SELECT name FROM sqlite_master WHERE name='forecast35'").fetchone()
        packet = forecast61.for_symbol(vars(s), 'TTWO', NOW)
        self.assertEqual(packet['status'], 'insufficient')
        self.assertEqual(packet['issuedForecasts'], 'left unchanged')
        with s.db_connection() as con:
            after = con.execute("SELECT name FROM sqlite_master WHERE name='forecast35'").fetchone()
            learning = con.execute('SELECT count(*) FROM learning40').fetchone()[0]
        self.assertEqual(before, after)
        self.assertEqual(learning, 0)
        self.assertIn('Daily closing prices only', forecast61.explain(packet))
        self.assertEqual(len(forecast61.runs(vars(s), 'TTWO')), 1)
        again = forecast61.for_symbol(vars(s), 'TTWO', NOW)
        self.assertFalse(again['experiment']['stored'])
        self.assertEqual(len(forecast61.runs(vars(s), 'TTWO')), 1)
