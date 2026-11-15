"""Chart questions use the same saved closes and forecasts as the reviews."""
import datetime as dt
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import ask48
import events42
import move44
import scorecard41
import test_events42 as fixture

s = fixture.s
at = fixture.at
bars = fixture.bars
NOW = at(dt.date(2026, 5, 27), 12)


def fill(symbol, start, end, first=100):
    day, prices, index = start, {}, 0
    while day <= end:
        if events42.is_session(day):
            prices[day.isoformat()] = first + index
            index += 1
        day += dt.timedelta(days=1)
    bars(symbol, prices)


class AskChartTests(unittest.TestCase):
    setUp = fixture.EventResearchTests.setUp

    def answer(self, question, **context):
        with patch.object(s, 'provider_get', side_effect=AssertionError('provider')), patch.object(s, 'massive_request', side_effect=AssertionError('provider')):
            return ask48.answer(s.__dict__, question, context, NOW)

    def test_examples_match_the_saved_move_and_switch_company(self):
        fill('TTWO', dt.date(2026, 1, 2), dt.date(2026, 5, 26))
        fill('AMD', dt.date(2026, 1, 2), dt.date(2026, 5, 26), 50)
        fill('SPY', dt.date(2026, 1, 2), dt.date(2026, 5, 26), 400)
        week = self.answer('How much did TTWO move this week?', symbol='AAPL')
        review = move44.review(s.__dict__, 'TTWO', week['context']['start'], week['context']['end'], NOW)
        self.assertEqual(week['context']['symbol'], 'TTWO')
        self.assertEqual(week['context']['range'], '1W')
        self.assertAlmostEqual(week['evidence']['returnPct'], review['returnPct'])
        self.assertIn(f"{review['returnPct']:.2f}%", week['answer'])
        compared = self.answer('How did it compare with SPY?', **week['context'])
        self.assertEqual(compared['context']['symbol'], 'TTWO')
        self.assertAlmostEqual(compared['evidence']['comparison']['differencePP'], review['comparison']['differencePP'])
        during = events42.normalise({'title': 'Morning filing', 'source': 'https://www.sec.gov/Archives/edgar/data/1/example', 'datetime': int(dt.datetime(2026, 5, 26, 10, tzinfo=fixture.NY).timestamp()), 'publisher': 'SEC', 'origin': 'SEC filing'})
        events42.store(s.__dict__, 'TTWO', {'events': [during]}, NOW)
        news = self.answer('What announcements were published during this move?', **week['context'])
        self.assertIn('does not prove', news['answer'])
        self.assertEqual(news['evidence']['items'][0]['source'], 'https://www.sec.gov/Archives/edgar/data/1/example')
        switched = self.answer('What about AMD?', **{**week['context'], 'kind': 'move'})
        amd = move44.review(s.__dict__, 'AMD', switched['context']['start'], switched['context']['end'], NOW)
        self.assertEqual(switched['context']['symbol'], 'AMD')
        self.assertEqual(switched['context']['start'], week['context']['start'])
        self.assertAlmostEqual(switched['evidence']['returnPct'], amd['returnPct'])
        self.assertNotIn('TTWO', switched['answer'])
        earlier = self.answer('Show the previous month', **{**week['context'], 'kind': 'move'})
        self.assertEqual(earlier['context']['range'], '1M')
        self.assertLess(earlier['context']['end'], week['context']['start'])
        again = move44.review(s.__dict__, 'TTWO', earlier['context']['start'], earlier['context']['end'], NOW)
        self.assertAlmostEqual(earlier['evidence']['returnPct'], again['returnPct'])
        self.assertGreaterEqual(earlier['evidence']['sampleSize'], 21)

    def test_ambiguous_missing_benchmark_empty_forecast_and_restart(self):
        bars('AMD', {'2026-05-22': 80, '2026-05-26': 72})
        vague = self.answer('Is this a good stock?', symbol='AMD', start='2026-05-22', end='2026-05-26', range='1W')
        self.assertFalse(vague['supported'])
        self.assertIn('does not calculate', vague['answer'])
        compared = self.answer('How did it compare with SPY?', symbol='AMD', start='2026-05-22', end='2026-05-26')
        review = move44.review(s.__dict__, 'AMD', '2026-05-22', '2026-05-26', NOW)
        self.assertAlmostEqual(compared['evidence']['returnPct'], review['returnPct'])
        self.assertIn('SPY', compared['answer'])
        self.assertEqual(compared['evidence']['comparison']['status'], 'withheld')
        empty = self.answer('How accurate have its forecasts been?', symbol='AMD')
        self.assertIn('No issued forecast', empty['answer'])
        self.assertEqual(empty['evidence']['sampleSize'], 0)
        body = {'symbol': 'TTWO', 'method': 'ridge-sessions-v4.1', 'horizon': 1, 'anchorDay': '2026-05-22', 'targetDay': '2026-05-26', 'anchorPrice': 100, 'forecastPrice': 101, 'baselinePrice': 100, 'low': 90, 'high': 110}
        outcome = scorecard41.score(body, 110)
        with s.LOCK, s.db_connection() as con, con:
            scorecard41.init(con)
            con.execute('INSERT INTO learning41_issued (id,symbol,method,horizon,anchor_day,target_day,issued_at,body,outcome) VALUES(?,?,?,?,?,?,?,?,?)',
                        ('t1', 'TTWO', body['method'], 1, '2026-05-22', '2026-05-26', NOW, json.dumps(body), json.dumps(outcome)))
        scored = self.answer('How accurate have its forecasts been?', symbol='TTWO')
        card = scorecard41.read(s.__dict__, 'TTWO')
        self.assertAlmostEqual(scored['evidence']['summary']['averageErrorPP'], card['summary']['averageErrorPP'])
        self.assertEqual(scored['evidence']['sampleSize'], 1)
        kept = scored['answer']
        s.init_storage()
        with patch.object(s, 'provider_get', side_effect=AssertionError('offline')), patch.object(s, 'massive_request', side_effect=AssertionError('offline')):
            reopened = ask48.saved(s.__dict__, 'TTWO')
        self.assertEqual(reopened[0]['answer'], kept)
        self.assertEqual(reopened[0]['evidence']['sampleSize'], 1)
        source = Path('site/ask48.js').read_text()
        self.assertIn('id!==seq', source)
        self.assertIn('symbol!==current.symbol', source)
