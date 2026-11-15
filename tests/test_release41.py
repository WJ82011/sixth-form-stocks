"""V4.1 coverage labels and issued-forecast scorecard. Fixture prices only."""
import datetime as dt
import unittest
from unittest.mock import patch

import collector40
import coverage41
import learning40
import market37
import scorecard41
import test_v3_api as fixture

s = fixture.s
NOW = int(dt.datetime(2026, 11, 9, 15, tzinfo=market37.NY).timestamp() * 1000)


def stamp(day, hour=16, minute=0):
    return int(dt.datetime.combine(dt.date.fromisoformat(day), dt.time(hour, minute), market37.NY).timestamp() * 1000)


def points(*rows):
    return [{'t': stamp(day, hour), 'p': price} for day, price, hour in rows]


class CoverageTests(unittest.TestCase):
    def test_holiday_is_a_closure_and_a_missing_session_is_a_trading_gap(self):
        holiday = coverage41.daily(points(('2026-11-25', 100, 16), ('2026-11-27', 101, 16)), NOW, 'Massive', True, 'none')
        self.assertEqual(holiday['tradingGapCount'], 0)
        self.assertGreaterEqual(holiday['closureCount'], 1)
        self.assertEqual(holiday['freshness'], 'saved')
        self.assertIn('Massive', holiday['source'])
        self.assertEqual(holiday['asOf'], stamp('2026-11-27'))

        missing = coverage41.daily(points(
            ('2026-10-26', 100, 16), ('2026-10-27', 100, 16), ('2026-10-29', 101, 16)), NOW, 'Massive', True, 'none')
        self.assertEqual([gap['day'] for gap in missing['tradingGaps']], ['2026-10-28'])
        self.assertTrue(missing['tradingGaps'][0]['fillable'])
        self.assertFalse(missing['complete'])

    def test_trading_hour_outage_stays_visible_and_unfilled(self):
        report = coverage41.intraday([
            {'t': stamp('2026-10-27', 14, 0), 'p': 50},
            {'t': stamp('2026-10-27', 14, 40), 'p': 51},
        ], NOW, 'Locally recorded Finnhub trades')
        self.assertEqual(report['tradingGapCount'], 1)
        self.assertFalse(report['fillable'])
        self.assertIn('does not backfill', report['notice'])
        self.assertEqual(report['freshness'], 'saved')
        same_day = coverage41.intraday([
            {'t': stamp('2026-11-09', 14, 0), 'p': 50},
            {'t': stamp('2026-11-09', 14, 40), 'p': 51},
        ], NOW, 'Locally recorded Finnhub trades')
        self.assertEqual(same_day['freshness'], 'delayed')
        self.assertEqual(same_day['tradingGapCount'], 1)
        self.assertFalse(same_day['fillable'])

    def test_split_is_labelled_and_prices_are_not_rewritten(self):
        raw = points(('2026-10-26', 100, 16), ('2026-10-27', 40, 16))
        before = [dict(row) for row in raw]
        report = coverage41.daily(raw, NOW, 'Imported daily file', False, 'none')
        self.assertEqual(raw, before)
        self.assertIn('stock split', report['splitNote'])
        self.assertIn('were not changed', report['splitNote'])


class ScorecardTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def issued(self, price=101, anchor=100):
        return {
            'method': 'ridge-sessions-v4.1', 'stale': False, 'quality': '',
            'anchorDate': '2026-10-30', 'anchor': {'t': stamp('2026-10-30'), 'p': anchor},
            'rows': [{
                'status': 'learned', 'horizon': 1, 'price': price, 'low': 99, 'high': 103,
                'returnPct': 1, 'calibrationCases': 10, 'testCases': 9,
                'modelErrorPP': 1.2, 'baselineErrorPP': 2.4,
            }],
        }

    def test_retraining_cannot_rewrite_or_rescore_an_issued_forecast(self):
        original = points(('2026-10-30', 100, 16))
        with patch.object(s.time, 'time', return_value=NOW / 1000):
            first = scorecard41.sync(vars(s), 'AAPL', self.issued(), original)
        self.assertEqual(len(first['pending']), 1)
        self.assertEqual(first['pending'][0]['forecastPrice'], 101)
        self.assertEqual(first['pending'][0]['baselinePrice'], 100)
        self.assertEqual(first['pending'][0]['targetDay'], '2026-11-02')
        self.assertEqual(first['graded'], [])
        with patch.object(s.time, 'time', return_value=NOW / 1000 + 5000):
            second = scorecard41.sync(vars(s), 'AAPL', self.issued(price=150), original)
        self.assertEqual(second['pending'][0]['forecastPrice'], 101)
        self.assertEqual(second['pending'][0]['issuedAt'], first['pending'][0]['issuedAt'])
        graded_prices = original + [{'t': stamp('2026-11-02'), 'p': 102}]
        with patch.object(s.time, 'time', return_value=NOW / 1000 + 8000):
            graded = scorecard41.sync(vars(s), 'AAPL', self.issued(price=150), graded_prices)
        outcome = graded['graded'][0]['outcome']
        self.assertEqual(outcome['status'], 'scored')
        self.assertEqual(outcome['actualPrice'], 102)
        self.assertTrue(outcome['inRange'])
        self.assertTrue(outcome['beatBaseline'])
        self.assertEqual(graded['summary']['count'], 1)
        self.assertTrue(graded['summary']['beatBaseline'])
        moved = [{'t': stamp('2026-10-30'), 'p': 100}, {'t': stamp('2026-11-02'), 'p': 80}]
        with patch.object(s.time, 'time', return_value=NOW / 1000 + 9000):
            again = scorecard41.sync(vars(s), 'AAPL', self.issued(price=150), moved)
        self.assertEqual(again['graded'][0]['forecastPrice'], 101)
        self.assertEqual(again['graded'][0]['outcome'], outcome)

    def test_a_changed_issue_price_withholds_scoring_without_replacing_the_forecast(self):
        issued = points(('2026-10-30', 100, 16))
        with patch.object(s.time, 'time', return_value=NOW / 1000):
            scorecard41.sync(vars(s), 'AMD', self.issued(), issued)
            revised = scorecard41.sync(vars(s), 'AMD', self.issued(), points(('2026-10-30', 80, 16), ('2026-11-02', 70, 16)))
        self.assertEqual(revised['graded'][0]['forecastPrice'], 101)
        self.assertEqual(revised['graded'][0]['outcome']['status'], 'withheld')
        self.assertEqual(revised['summary']['count'], 0)

    def test_no_forecast_is_stated_when_the_model_does_not_issue_one(self):
        with patch.object(market37, 'today', return_value=dt.date(2026, 11, 9)):
            report = learning40.report(vars(s), 'AAPL')
        self.assertEqual(report['scorecard']['pending'], [])
        self.assertIn('No new forecast was issued', report['scorecard']['message'])

    def test_restart_asks_for_the_gapped_stock_before_the_rotation(self):
        latest = dt.date.fromisoformat(market37.sessions(dt.date(2026, 11, 9), 1)[0])
        day = dt.date(2026, 10, 1)
        rows = []
        while day <= latest:
            if day.weekday() < 5 and day not in market37.holidays(day.year):
                stamp_ms = stamp(day.isoformat())
                rows.append(('AAPL', stamp_ms, 10, 10, 10, 10, 1, 1))
                if day != dt.date(2026, 10, 28):
                    rows.append(('AMD', stamp_ms, 10, 10, 10, 10, 1, 1))
            day += dt.timedelta(days=1)
        import contextlib
        with contextlib.closing(s.db_connection()) as con, con:
            con.executemany('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)', rows)
        order = coverage41.priority(vars(s), ['AAPL', 'AMD'], NOW)
        self.assertEqual(order[0], 'AMD')
        self.assertNotIn('AAPL', order)
        worker = collector40.Collector(vars(s))
        worker.gap_queue = ['AMD', 'AAPL']
        seen = []
        with patch.object(s, 'get_massive_key', return_value='fixture'), patch.object(
                s, 'massive_daily_candles', lambda sym, start, end: seen.append(sym) or {'status': 'ok'}):
            worker.refresh('history')
        self.assertEqual(seen, ['AMD'])
        self.assertEqual(worker.gap_queue, ['AAPL'])
        self.assertIn('gap fill', worker.status['history'])


if __name__ == '__main__':
    unittest.main()
