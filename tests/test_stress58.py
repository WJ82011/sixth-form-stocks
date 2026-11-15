"""Hand-worked portfolio stress tests. The practice ledger is not edited."""
import datetime as dt
import unittest

import events42
import stress58
import test_v3_api as fixture
import workspace3 as w

s = fixture.s


def holding(symbol, value, sector, asset='stock', currency='USD'):
    return {'symbol': symbol, 'valueUSD': value, 'currency': currency, 'fx': 1 if currency == 'USD' else None,
            'sector': sector, 'asset': asset, 'quantity': 1}


class StressTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_hand_worked_shocks_weights_and_cash(self):
        rows = [holding('AAA', 200, 'Technology'), holding('BBB', 100, 'Health')]
        everything = stress58.shock(rows, 50, 'all', 10)
        self.assertEqual(everything['cashUSD'], 50)
        self.assertEqual(everything['stressedUSD'], 380)
        self.assertEqual(everything['changeUSD'], 30)
        self.assertEqual(everything['holdings'][0]['stressedUSD'], 220)
        self.assertEqual(everything['holdings'][0]['contributionUSD'], 20)
        self.assertEqual(everything['holdings'][1]['stressedUSD'], 110)
        one = stress58.shock(rows, 50, 'symbol', -50, symbol='AAA')
        self.assertEqual(one['holdings'][0]['stressedUSD'], 100)
        self.assertEqual(one['stressedUSD'], 250)
        self.assertEqual(one['changeUSD'], -100)
        sector = stress58.shock(rows, 50, 'sector', 25, sector='Technology')
        self.assertEqual(sector['holdings'][0]['stressedUSD'], 250)
        self.assertEqual(sector['holdings'][1]['stressedUSD'], 100)
        self.assertEqual(sector['stressedUSD'], 400)
        weighted = stress58.shock(rows, 50, 'symbol', 100, symbol='AAA', weights={'AAA': 25, 'BBB': 75})
        aaa = next(row for row in weighted['holdings'] if row['symbol'] == 'AAA')
        bbb = next(row for row in weighted['holdings'] if row['symbol'] == 'BBB')
        self.assertEqual(aaa['allocatedUSD'], 75)
        self.assertEqual(aaa['stressedUSD'], 150)
        self.assertEqual(aaa['contributionUSD'], 75)
        self.assertEqual(bbb['stressedUSD'], 225)
        self.assertEqual(weighted['stressedUSD'], 425)
        cash = stress58.shock([], 1000, 'all', 10)
        self.assertEqual(cash['stressedUSD'], 1000)
        self.assertEqual(cash['changeUSD'], 0)
        self.assertTrue(cash['cashChanged'] is False)

    def test_missing_prices_currencies_and_unknown_sectors(self):
        missing = stress58.shock([holding('AAA', None, 'Technology'), holding('BBB', 100, 'Health')], 50, 'all', 10)
        self.assertEqual(missing['status'], 'withheld')
        self.assertIsNone(missing['stressedUSD'])
        self.assertIn('AAA', missing['missing'])
        foreign = stress58.shock([holding('AAA', None, 'Technology', currency='EUR')], 50, 'all', 10)
        self.assertEqual(foreign['status'], 'withheld')
        self.assertIn('AAA', foreign['fxMissing'])
        self.assertIn('exchange rate', ' '.join(foreign['assumptions']).lower())
        unknown = stress58.shock([holding('AAA', 200, 'Sector not recorded')], 0, 'sector', -20, sector='Energy')
        self.assertEqual(unknown['status'], 'ok')
        self.assertEqual(unknown['holdings'][0]['stressedUSD'], 200)
        self.assertIn('No holding is classified as Energy', ' '.join(unknown['assumptions']))

    def test_history_uses_today_allocation_and_shows_gaps(self):
        rows = [holding('AAA', 200, 'Technology'), holding('BBB', 100, 'Health')]
        books = {
            'AAA': [{'date': '2026-01-05', 'price': 100, 'source': 'Massive split-adjusted daily close'},
                    {'date': '2026-01-07', 'price': 80, 'source': 'Massive split-adjusted daily close'}],
            'BBB': [{'date': '2026-01-05', 'price': 50, 'source': 'Massive split-adjusted daily close'}],
        }
        result = stress58.replay(rows, 50, books, '2026-01-05', '2026-01-07')
        aaa = result['holdings'][0]
        self.assertEqual(aaa['stressedUSD'], 160)
        self.assertEqual(aaa['contributionUSD'], -40)
        self.assertEqual(aaa['history']['observations'][0]['price'], 100)
        self.assertEqual(aaa['history']['observations'][1]['price'], 80)
        self.assertIn('2026-01-06', aaa['history']['gaps'])
        self.assertEqual(result['status'], 'withheld')
        self.assertIn('BBB', result['missing'])
        self.assertIn("today's holdings", ' '.join(result['assumptions']).lower())
        covered = {
            'AAA': books['AAA'] + [{'date': '2026-01-08', 'price': 90, 'source': 'saved'}],
            'BBB': [{'date': '2026-01-07', 'price': 40, 'source': 'saved'}, {'date': '2026-01-08', 'price': 44, 'source': 'saved'}],
        }
        offered = stress58.common_period(rows, covered, '2026-01-05', '2026-01-08')
        self.assertEqual(offered['start'], '2026-01-07')
        self.assertEqual(offered['end'], '2026-01-08')

    def test_equity_sessions_and_crypto_weekends_stay_separate(self):
        saturday = dt.date(2026, 1, 10)
        self.assertFalse(events42.is_session(saturday))
        equity = stress58.replay([holding('AAA', 100, 'Technology')], 0, {
            'AAA': [{'date': '2026-01-09', 'price': 10}, {'date': '2026-01-12', 'price': 11}]},
            '2026-01-10', '2026-01-12')
        self.assertEqual(equity['holdings'][0]['history']['status'], 'missing')
        self.assertIn('not a New York equity session', equity['holdings'][0]['history']['reason'])
        crypto = stress58.replay([holding('BTC-USD', 100, 'Sector not recorded', asset='crypto')], 0, {
            'BTC-USD': [{'date': '2026-01-09', 'price': 100, 'source': 'Coinbase Exchange daily candle, UTC'},
                        {'date': '2026-01-10', 'price': 110, 'source': 'Coinbase Exchange daily candle, UTC'}]},
            '2026-01-09', '2026-01-10')
        self.assertEqual(crypto['status'], 'ok')
        self.assertEqual(crypto['holdings'][0]['stressedUSD'], 110)
        self.assertEqual(crypto['holdings'][0]['history']['calendar'], 'UTC days')
        self.assertEqual(crypto['holdings'][0]['history']['observations'][1]['date'], '2026-01-10')

    def test_saved_stress_reopens_without_rewriting_the_ledger(self):
        ledger = [
            {'id': 'd', 'kind': 'DEPOSIT', 'date': '2026-11-10', 'source': 'Hand-worked example', 'amount': 1000},
            {'id': 'b', 'kind': 'BUY', 'date': '2026-11-10', 'source': 'Hand-worked example', 'symbol': 'AAA',
             'quantity': 10, 'price': 10, 'currency': 'USD', 'fx': 1, 'assetType': 'stock'},
        ]
        marks = [{'symbol': 'AAA', 'date': '2026-11-13', 'price': 20, 'currency': 'USD', 'fx': 1, 'source': 'Hand-worked price'}]
        s.write_workspace({'watch': ['AAA'], 'v3': w.normalise({'ledger': ledger, 'marks': marks})})
        before = s.read_workspace()['snapshot']['v3']['ledger']
        saved = stress58.save(vars(s), {'action': 'run', 'scope': 'all', 'percent': 10}, 20)
        self.assertEqual(saved['result']['cashUSD'], 900)
        self.assertEqual(saved['result']['stressedUSD'], 1120)
        self.assertTrue(saved['result']['ledgerUntouched'])
        marks[0]['price'] = 50
        s.write_workspace({'watch': ['AAA'], 'v3': w.normalise({'ledger': ledger, 'marks': marks})})
        opened = stress58.read(vars(s), saved['id'])
        self.assertEqual(opened['result']['stressedUSD'], 1120)
        self.assertIn('not recalculated', opened['notice'])
        self.assertEqual(s.read_workspace()['snapshot']['v3']['ledger'], before)
        text, evidence = stress58.explain(opened)
        self.assertIn('1120.00', text)
        self.assertIn('AAA', text)
        self.assertGreaterEqual(evidence['sampleSize'], 1)
