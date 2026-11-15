"""Replay reveals a late spike, a timed event and a gap only when the cursor reaches them."""
import unittest

import replay43


PRICES = [
    {'t': 0, 'p': 100},
    {'t': 60_000, 'p': 101},
    {'t': 20 * 60_000, 'p': 180},
]
TRADES = [{'t': 0, 'p': 100, 'v': 1}, {'t': 20 * 60_000, 'p': 180, 'v': 5}]
EVENTS = [
    {'title': 'Timed filing', 'publishedAt': 12 * 60_000},
    {'title': 'Date only notice', 'date': '2026-05-23'},
]


class ReplayFrameTests(unittest.TestCase):
    def test_future_spike_event_and_gap_stay_hidden_until_the_cursor_arrives(self):
        early = replay43.frame(PRICES, TRADES, EVENTS, 10 * 60_000)
        self.assertEqual([row['p'] for row in early['prices']], [100, 101])
        self.assertEqual(early['high'], 101)
        self.assertEqual(early['low'], 100)
        self.assertEqual(early['timedEvents'], [])
        self.assertEqual(early['dateOnlyEvents'][0]['timing'], 'unknown')
        self.assertTrue(early['gaps'] and early['gaps'][-1]['open'])
        self.assertNotIn(180, [row['p'] for row in early['prices']])
        self.assertTrue(early['separateFromAlerts'])

        at_event = replay43.frame(PRICES, TRADES, EVENTS, 12 * 60_000)
        self.assertEqual(at_event['timedEvents'][0]['title'], 'Timed filing')
        self.assertNotIn(180, [row['p'] for row in at_event['prices']])

        done = replay43.frame(PRICES, TRADES, EVENTS, 20 * 60_000)
        self.assertEqual(done['high'], 180)
        self.assertEqual(done['prices'][-1]['p'], 180)
        self.assertEqual(len(done['trades']), 2)
        self.assertFalse(done['gaps'][-1]['open'])
        self.assertEqual(done['dateOnlyEvents'][0]['title'], 'Date only notice')


if __name__ == '__main__':
    unittest.main()
