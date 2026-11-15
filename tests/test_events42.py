"""Company event timeline and price windows. Fixture prices, no live providers."""
import datetime as dt
import unittest
from unittest.mock import patch

import events42
import market37
import test_v3_api as fixture

s = fixture.s
NY = market37.NY


def at(day, hour, minute=0):
    return int(dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=NY).timestamp() * 1000)


def bars(symbol, prices):
    import contextlib
    rows = []
    for day, price in prices.items():
        stamp = at(dt.date.fromisoformat(day), 16)
        rows.append((symbol, stamp, price, price, price, price, 1, 1))
    with contextlib.closing(s.db_connection()) as con, con:
        con.executemany('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)', rows)


class EventResearchTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_after_hours_before_a_holiday_starts_on_the_next_open_session(self):
        published = int(dt.datetime(2026, 5, 22, 17, tzinfo=NY).timestamp())
        event = events42.normalise({'title': 'After-hours release', 'source': 'https://www.businesswire.com/news/example', 'datetime': published, 'publisher': 'Business Wire'})
        self.assertEqual(event['kindLabel'], 'Company announcement')
        stock = {'2026-05-22': 100, '2026-05-26': 110}
        spy = {'2026-05-22': 500, '2026-05-26': 505}
        result = events42.reaction('TTWO', event, 1, stock, spy, at(dt.date(2026, 5, 27), 12))
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['timing'], 'after_close')
        self.assertEqual(result['anchor'], '2026-05-22')
        self.assertEqual(result['target'], '2026-05-26')
        self.assertAlmostEqual(result['differencePP'], 9, places=5)
        self.assertIn('more than SPY', result['sentence'])
        self.assertIn('does not show why', result['explanation'])

    def test_date_only_event_is_uncertain_and_starts_after_that_date(self):
        event = events42.normalise({'title': 'Date only notice', 'source': 'https://example.com/notice', 'date': '2026-05-23', 'publisher': 'Example News'})
        self.assertEqual(event['timing'], 'date')
        self.assertIn('date only', event['timeLabel'])
        result = events42.reaction('TTWO', event, 1, {'2026-05-22': 100, '2026-05-26': 90}, {'2026-05-22': 100, '2026-05-26': 100}, at(dt.date(2026, 5, 27), 12))
        self.assertEqual(result['timing'], 'uncertain')
        self.assertEqual(result['anchor'], '2026-05-22')
        self.assertEqual(result['target'], '2026-05-26')
        self.assertIn('less than SPY', result['sentence'])

    def test_missing_benchmark_open_window_and_duplicate_source_are_explicit(self):
        event = events42.normalise({'title': 'Shared article', 'source': 'https://www.reuters.com/story', 'datetime': int(dt.datetime(2026, 5, 22, 17, tzinfo=NY).timestamp()), 'publisher': 'Reuters'})
        self.assertEqual(event['kindLabel'], 'Third-party reporting')
        missing = events42.reaction('TTWO', event, 1, {'2026-05-22': 10, '2026-05-26': 11}, {}, at(dt.date(2026, 5, 27), 12))
        self.assertEqual(missing['status'], 'withheld')
        self.assertIn('SPY', missing['reason'])
        open_window = events42.reaction('TTWO', event, 1, {'2026-05-22': 10, '2026-05-26': 11}, {'2026-05-22': 10, '2026-05-26': 10}, at(dt.date(2026, 5, 22), 18))
        self.assertIn('still open', open_window['reason'])
        rows = events42.dedupe([
            {'title': 'Shared article', 'source': 'https://www.reuters.com/story', 'datetime': 1, 'publisher': 'Reuters'},
            {'title': 'Shared article copy', 'source': 'https://www.reuters.com/story?utm=1', 'datetime': 2, 'publisher': 'Reuters'},
        ])
        self.assertEqual(len(rows), 1)
        separate = events42.dedupe([
            {'title': 'First provider story', 'source': 'https://finnhub.io/api/news?id=aaa', 'datetime': 10, 'publisher': 'Example'},
            {'title': 'Second provider story', 'source': 'https://finnhub.io/api/news?id=bbb', 'datetime': 11, 'publisher': 'Example'},
        ])
        self.assertEqual(len(separate), 2)
        crowded = [{'title': 'Story ' + str(i), 'source': 'https://example.com/' + str(i), 'datetime': 1_700_000_000 + i, 'publisher': 'Example'} for i in range(70)]
        crowded.append({'title': '10-K filed', 'source': 'https://www.sec.gov/Archives/edgar/data/1/a.htm', 'date': '2026-05-22', 'origin': 'SEC filing'})
        kept = events42.dedupe(crowded)
        self.assertTrue(any(row['kind'] == 'filing' for row in kept))
        self.assertLessEqual(len(kept), 60)

    def test_a_provider_ticker_link_is_labelled_when_the_title_does_not_name_the_company(self):
        named = events42.explain('TTWO', [{'title': 'Forget Take-Two: a preview', 'source': 'https://finance.yahoo.com/a', 'datetime': int(dt.datetime(2026, 5, 22, 17, tzinfo=NY).timestamp()), 'publisher': 'Yahoo'}], 'TAKE TWO INTERACTIVE SOFTWARE INC')[0]
        broad = events42.explain('TTWO', [{'title': 'Is Citi Wrong to Give Up on Roblox?', 'source': 'https://finance.yahoo.com/b', 'datetime': int(dt.datetime(2026, 5, 22, 17, tzinfo=NY).timestamp()), 'publisher': 'Yahoo'}], 'TAKE TWO INTERACTIVE SOFTWARE INC')[0]
        self.assertEqual(named['kindLabel'], 'Third-party reporting')
        self.assertIn('names the company', named['reason'])
        self.assertEqual(broad['kindLabel'], 'Broader market coverage')
        self.assertIn('associated this item with TTWO', broad['reason'])
        self.assertIn('does not name', broad['reason'])

    def test_third_party_gta_mention_is_not_called_a_company_announcement(self):
        event = events42.normalise({'title': 'Preview: GTA VI is close', 'source': 'https://www.reuters.com/gta', 'datetime': int(dt.datetime(2026, 5, 22, 17, tzinfo=NY).timestamp()), 'publisher': 'Reuters'})
        notes = events42.gaps('TTWO', [event], [])
        self.assertEqual(event['kindLabel'], 'Third-party reporting')
        self.assertTrue(any('third-party reports' in note for note in notes))
        self.assertFalse(any('No saved headline' in note for note in notes))

    def test_saved_event_and_comparison_reopen_when_the_connection_is_blocked(self):
        bars('TTWO', {'2026-05-22': 100, '2026-05-26': 110})
        bars('SPY', {'2026-05-22': 500, '2026-05-26': 505})
        published = int(dt.datetime(2026, 5, 22, 17, tzinfo=NY).timestamp())
        news = [{'headline': 'Take-Two hosts a call', 'url': 'https://www.businesswire.com/ttwo-call', 'source': 'Business Wire', 'datetime': published}]

        def provider(path, params, ttl=0):
            if path == 'company-news':
                return news, False
            raise s.ProviderError(403, 'calendar unavailable')

        with patch.object(s, 'provider_get', side_effect=provider), patch.object(s.time, 'time', return_value=at(dt.date(2026, 5, 27), 12) / 1000):
            first = events42.refresh(vars(s), 'TTWO')
        self.assertEqual(len(first['events']), 1)
        self.assertTrue(any('GTA VI' in note for note in first['gaps']))
        self.assertEqual(first['comparisons'][first['events'][0]['id']]['1']['status'], 'ready')

        def blocked(*args, **kwargs):
            raise AssertionError('The connection should stay blocked')

        with patch.object(s, 'provider_get', side_effect=blocked):
            again = events42.packet(vars(s), 'TTWO')
        self.assertEqual(again['events'][0]['source'], news[0]['url'])
        self.assertEqual(again['comparisons'][again['events'][0]['id']]['1']['target'], '2026-05-26')
        self.assertIn('more than SPY', again['comparisons'][again['events'][0]['id']]['1']['sentence'])


if __name__ == '__main__':
    unittest.main()
