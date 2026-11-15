"""Decision practice hides a late spike, a timed event and a date-only record until the clock arrives."""
import json
import unittest

import practice67
import test_v3_api as fixture

s = fixture.s
PRICES = [{'t': 0, 'p': 100}, {'t': 60_000, 'p': 101}, {'t': 20 * 60_000, 'p': 180}]
EVENTS = [
    {'title': 'Timed filing', 'publishedAt': 12 * 60_000, 'source': 'https://www.sec.gov/Archives/example'},
    {'title': 'Date only notice', 'date': '2026-05-22'},
]


class PracticeTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def session(self, start=0):
        return practice67.open_records(vars(s), 'TTWO', '2026-05-22', PRICES, PRICES, EVENTS, start, 10)

    def test_future_spike_event_and_unverified_record_stay_out_of_the_response(self):
        opened = self.session()
        early = json.dumps(opened)
        self.assertNotIn('180', early)
        self.assertNotIn('Timed filing', early)
        self.assertNotIn('Date only notice', early)
        self.assertEqual(opened['frame']['high'], 100)
        self.assertGreater(opened['coverage']['gapCount'], 0)
        self.assertEqual(opened['frame']['unverifiedTiming'], 1)
        at_news = opened
        while at_news['frame']['cursor'] < 12 * 60_000:
            at_news = practice67.advance(vars(s), at_news['id'], 'step', 60, 11)
        shown = json.dumps(at_news)
        self.assertIn('Timed filing', shown)
        self.assertNotIn('180', shown)
        self.assertNotIn('Date only notice', shown)
        self.assertEqual(at_news['frame']['high'], 101)
        done = practice67.end(vars(s), at_news['id'], 12)
        self.assertEqual(done['frame']['prices'][-1]['p'], 180)
        self.assertEqual(done['status'], 'ended')

    def test_decision_stays_fixed_and_the_later_return_waits_for_the_review_time(self):
        opened = self.session()
        saved = practice67.decide(vars(s), opened['id'], {
            'expectation': 'I expect the price to stay near the open.',
            'evidence': 'Only the first price is visible.',
            'changeMind': 'A timed filing would change my mind.',
            'reviewAt': 20 * 60_000,
        }, 20)
        decision = saved['decisions'][0]
        waiting = practice67.outcome(vars(s), decision['id'])
        self.assertEqual(waiting['status'], 'waiting')
        self.assertNotIn('returnPct', waiting)
        practice67.end(vars(s), opened['id'], 21)
        ready = practice67.outcome(vars(s), decision['id'])
        self.assertAlmostEqual(ready['returnPct'], 80, places=5)
        self.assertEqual(ready['links'][0]['url'], 'https://www.sec.gov/Archives/example')
        reflected = practice67.reflect(vars(s), decision['id'], 'challenged', 'The later price was not visible when I decided.', 22)
        self.assertEqual(reflected['decisions'][0]['expectation'], decision['expectation'])
        self.assertEqual(reflected['decisions'][0]['assessment'], 'challenged')
        restarted = practice67.restart(vars(s), opened['id'], 23)
        self.assertEqual(restarted['frame']['cursor'], 0)
        self.assertEqual(restarted['decisions'][0]['expectation'], decision['expectation'])
        self.assertEqual(practice67.outcome(vars(s), decision['id'])['status'], 'waiting')
        paused = practice67.pause(vars(s), opened['id'], 24)
        self.assertEqual(paused['status'], 'paused')

    def test_intelligence_uses_the_replay_clock_until_the_session_ends(self):
        opened = self.session()
        during = practice67.handle(vars(s), 'How much did it move?', {'practiceId': opened['id']}, 30)
        self.assertNotIn('180', json.dumps(during))
        self.assertIn('not read', during['answer'])
        review = practice67.handle(vars(s), 'Review this practice session', {'practiceId': opened['id']}, 31)
        self.assertIn('still open', review['answer'])
        self.assertNotIn('180', json.dumps(review))
        practice67.end(vars(s), opened['id'], 32)
        after = practice67.handle(vars(s), 'Review this practice session', {'practiceId': opened['id']}, 33)
        self.assertIn('after the session', after['answer'])
        self.assertIn('180', after['answer'])
