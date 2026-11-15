import math
import unittest

import strategy54
import test_v3_api as fixture

s = fixture.s


def bar(day, price, open_price=None, high=None, low=None):
    opened = price if open_price is None else open_price
    return {'date': day, 'open': opened, 'high': high if high is not None else max(opened, price),
            'low': low if low is not None else min(opened, price), 'close': price}


def rule(**extra):
    body = {'start': '2026-11-16', 'end': '2026-11-20', 'cash': 1000, 'sizePct': 100, 'costPct': 0, 'slippagePct': 0,
            'entry': {'kind': 'breakout', 'lookback': 1}, 'exit': {'kind': 'breakout', 'lookback': 1}}
    body.update(extra)
    return body


class StrategyTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_losing_round_trip_matches_the_hand_calculation(self):
        bars = [bar('2026-11-16', 10), bar('2026-11-17', 11), bar('2026-11-18', 12), bar('2026-11-19', 9), bar('2026-11-20', 8)]
        result = strategy54.run_rule(rule(), bars)['development']
        shares = math.floor(1000 / 12 * 10000) / 10000
        self.assertEqual(result['tradeCount'], 1)
        self.assertAlmostEqual(result['trades'][0]['fillPrice'], 12)
        self.assertAlmostEqual(result['trades'][0]['shares'], shares)
        self.assertAlmostEqual(result['trades'][1]['fillPrice'], 8)
        self.assertAlmostEqual(result['endingValue'], 1000 - shares * 12 + shares * 8)
        self.assertLess(result['endingValue'], 1000)
        self.assertGreater(result['maxDrawdown'], 0)
        self.assertIn('next saved session', result['trades'][0]['reason'] + strategy54.describe(rule())['plainEnglish'])
        self.assertEqual(result['trades'][0]['signalDate'], '2026-11-17')
        self.assertEqual(result['trades'][0]['executeDate'], '2026-11-18')
        self.assertIn('Dividends', result['dividendNote'])
        self.assertIn('practice portfolio', result['portfolioNote'])

    def test_no_trade_leaves_the_starting_cash(self):
        bars = [bar(day, 10) for day in ('2026-11-16', '2026-11-17', '2026-11-18', '2026-11-19', '2026-11-20')]
        result = strategy54.run_rule(rule(), bars)['development']
        self.assertEqual(result['tradeCount'], 0)
        self.assertEqual(result['fills'], 0)
        self.assertAlmostEqual(result['endingValue'], 1000)
        self.assertAlmostEqual(result['endingCash'], 1000)
        self.assertAlmostEqual(result['endingShares'], 0)

    def test_missing_session_is_flagged_and_the_next_saved_open_is_used(self):
        bars = [bar('2026-11-16', 10), bar('2026-11-17', 11), bar('2026-11-19', 12, open_price=12), bar('2026-11-20', 12)]
        result = strategy54.run_rule(rule(), bars)['development']
        self.assertEqual(result['trades'][0]['executeDate'], '2026-11-19')
        self.assertIn('gap', result['trades'][0]['flags'])
        self.assertIn('2026-11-18', result['coverage']['missing'])

    def test_costs_turn_a_higher_sale_into_a_loss(self):
        bars = [bar('2026-11-16', 10), bar('2026-11-17', 11),
                bar('2026-11-18', 12, open_price=10), bar('2026-11-19', 11), bar('2026-11-20', 11, open_price=10.5)]
        costly = strategy54.run_rule(rule(costPct=5), bars)['development']
        plain = strategy54.run_rule(rule(costPct=0), bars)['development']
        shares = math.floor(1000 / (10 * 1.05) * 10000) / 10000
        ending = 1000 - shares * 10 * 1.05 + shares * 10.5 * 0.95
        self.assertAlmostEqual(costly['endingValue'], ending, places=6)
        self.assertLess(costly['endingValue'], 1000)
        self.assertGreater(plain['endingValue'], 1000)
        self.assertGreater(costly['costs'], 0)

    def test_gap_through_a_stop_fills_at_the_open(self):
        bars = [bar('2026-11-16', 10), bar('2026-11-17', 11), bar('2026-11-18', 10), bar('2026-11-19', 8), bar('2026-11-20', 8)]
        result = strategy54.run_rule(rule(stopPct=10), bars)['development']
        sale = result['trades'][1]
        self.assertAlmostEqual(sale['executePrice'], 8)
        self.assertIn('gap', sale['flags'])
        self.assertIn('stop', sale['flags'])

    def test_unknown_intraday_order_uses_the_stop_price(self):
        bars = [bar('2026-11-16', 10), bar('2026-11-17', 11),
                bar('2026-11-18', 11, open_price=10, high=12, low=8), bar('2026-11-19', 11), bar('2026-11-20', 11)]
        result = strategy54.run_rule(rule(stopPct=10), bars)['development']
        sale = result['trades'][1]
        self.assertAlmostEqual(sale['executePrice'], 9)
        self.assertIn('intraday-order-unknown', sale['flags'])
        self.assertEqual(sale['executeDate'], '2026-11-18')

    def test_split_sized_jump_is_not_traded_as_a_normal_bar(self):
        bars = [bar('2026-11-16', 10), bar('2026-11-17', 11), bar('2026-11-18', 12), bar('2026-11-19', 40), bar('2026-11-20', 40)]
        result = strategy54.run_rule(rule(), bars)['development']
        self.assertTrue(any('split' in trade['flags'] for trade in result['trades']))
        self.assertTrue(any('split-sized' in note for note in result['notes']))
        self.assertNotEqual(result['trades'][-1]['executePrice'], 40)

    def test_later_period_stays_locked_and_a_change_is_identified(self):
        bars = [bar(day, price) for day, price in (('2026-11-16', 10), ('2026-11-17', 11), ('2026-11-18', 12), ('2026-11-19', 9), ('2026-11-20', 8))]
        body = rule(end='2026-11-18', laterStart='2026-11-19', laterEnd='2026-11-20')
        first = strategy54.run_rule(body, bars)
        self.assertIsNotNone(first['later'])
        self.assertFalse(first['changedAfterInspection'])
        changed = strategy54.run_rule({**body, 'inspectedLater': True, 'lockedFingerprint': 'older-rule', 'costPct': 1}, bars)
        self.assertTrue(changed['changedAfterInspection'])
        self.assertIn('differ', changed['changeNote'])
        text = PathText()
        self.assertIn('id!==seq', text)
        self.assertIn('data-journal="strategy"', text)

    def test_saved_experiment_reopens_without_rewriting_the_result(self):
        bars = [bar(day, 10) for day in ('2026-11-16', '2026-11-17', '2026-11-18', '2026-11-19', '2026-11-20')]
        def load(_g, _symbol):
            return bars
        original = strategy54.load_bars
        strategy54.load_bars = load
        try:
            saved = strategy54.save(vars(s), {'symbol': 'TTWO', **rule()}, 10)
            strategy54.load_bars = lambda _g, _symbol: [bar(day, 99) for day in ('2026-11-16', '2026-11-17', '2026-11-18', '2026-11-19', '2026-11-20')]
            opened = strategy54.read(vars(s), saved['id'], 20)
        finally:
            strategy54.load_bars = original
        self.assertAlmostEqual(opened['saved']['result']['development']['endingValue'], 1000)
        self.assertIn('not rewritten', opened['notice'])


def PathText():
    from pathlib import Path
    return Path('site/strategy54.js').read_text()
