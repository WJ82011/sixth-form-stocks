"""Move reviews use saved closes only. Fixture prices, no provider calls."""
import datetime as dt
import unittest
from pathlib import Path
from unittest.mock import patch

import events42
import move44
import test_events42 as fixture

s = fixture.s
at = fixture.at
bars = fixture.bars


class MoveReviewTests(unittest.TestCase):
    setUp = fixture.EventResearchTests.setUp

    def test_multi_day_move_uses_the_exact_dates_and_spy(self):
        bars('TTWO', {'2026-05-22': 100, '2026-05-26': 110, '2026-05-27': 90})
        bars('SPY', {'2026-05-22': 500, '2026-05-26': 505, '2026-05-27': 510})
        with patch.object(s, 'provider_get', side_effect=AssertionError('provider')), patch.object(s, 'massive_request', side_effect=AssertionError('provider')):
            result = move44.review(s.__dict__, 'TTWO', '2026-05-22', '2026-05-26', at(dt.date(2026, 5, 27), 12))
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['sessions'], ['2026-05-22', '2026-05-26'])
        self.assertEqual(result['startPrice'], 100)
        self.assertEqual(result['endPrice'], 110)
        self.assertAlmostEqual(result['returnPct'], 10)
        self.assertAlmostEqual(result['comparison']['differencePP'], 9)
        self.assertTrue(result['offline'])
        self.assertNotIn(90, (result['startPrice'], result['endPrice']))

    def test_missing_benchmark_keeps_the_stock_and_names_the_gap(self):
        bars('AMD', {'2026-05-22': 80, '2026-05-26': 72})
        with patch.object(s, 'provider_get', side_effect=AssertionError('provider')):
            result = move44.review(s.__dict__, 'AMD', '2026-05-22', '2026-05-26', at(dt.date(2026, 5, 27), 12))
        self.assertEqual(result['status'], 'ready')
        self.assertAlmostEqual(result['returnPct'], -10)
        self.assertEqual(result['comparison']['status'], 'withheld')
        self.assertIn('SPY', result['comparison']['reason'])
        self.assertTrue(any('SPY' in gap for gap in result['gaps']))

    def test_after_hours_item_is_separated_and_date_only_stays_uncertain(self):
        bars('TTWO', {'2026-05-22': 100, '2026-05-26': 110})
        bars('SPY', {'2026-05-22': 500, '2026-05-26': 500})
        during = events42.normalise({'title': 'Morning filing', 'source': 'https://www.sec.gov/Archives/edgar/data/1/example', 'datetime': int(dt.datetime(2026, 5, 26, 10, tzinfo=fixture.NY).timestamp()), 'publisher': 'SEC', 'origin': 'SEC filing'})
        later = events42.normalise({'title': 'After-hours announcement', 'source': 'https://www.businesswire.com/news/later', 'datetime': int(dt.datetime(2026, 5, 26, 17, tzinfo=fixture.NY).timestamp()), 'publisher': 'Business Wire'})
        dated = events42.normalise({'title': 'Date only notice', 'source': 'https://example.com/notice', 'date': '2026-05-26', 'publisher': 'Example News'})
        events42.store(s.__dict__, 'TTWO', {'events': [during, later, dated]}, at(dt.date(2026, 5, 27), 12))
        result = move44.review(s.__dict__, 'TTWO', '2026-05-22', '2026-05-26', at(dt.date(2026, 5, 27), 12))
        self.assertEqual([row['title'] for row in result['before']], ['Morning filing'])
        self.assertEqual([row['title'] for row in result['after']], ['After-hours announcement'])
        self.assertEqual(result['after'][0]['source'], 'https://www.businesswire.com/news/later')
        self.assertEqual([row['title'] for row in result['uncertain']], ['Date only notice'])
        self.assertIn('does not prove', result['evidence'])

    def test_offline_reload_reads_the_same_saved_move(self):
        bars('AMD', {'2026-05-22': 40, '2026-05-27': 44})
        bars('SPY', {'2026-05-22': 400, '2026-05-27': 404})
        first = move44.review(s.__dict__, 'AMD', '2026-05-22', '2026-05-27', at(dt.date(2026, 5, 28), 12))
        s.init_storage()
        with patch.object(s, 'provider_get', side_effect=AssertionError('offline')), patch.object(s, 'massive_request', side_effect=AssertionError('offline')):
            again = move44.review(s.__dict__, 'AMD', '2026-05-22', '2026-05-27', at(dt.date(2026, 5, 28), 12))
        root = Path(__file__).parents[1]
        self.assertEqual((root / 'site' / 'app.js').read_text().count('Move44?.clear()'), 2)
        self.assertIn('id!==request||key!==next', (root / 'site' / 'move44.js').read_text())
        self.assertEqual(first['returnPct'], again['returnPct'])
        self.assertEqual(first['comparison']['differencePP'], again['comparison']['differencePP'])
        self.assertTrue(again['offline'])
