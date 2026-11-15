"""Portfolio insights checked against a hand-worked ledger. Disposable records only."""
import unittest
from unittest.mock import patch

import insights46
import lab3
import portfolio3 as p
import test_v3_api as fixture
import workspace3 as w

s = fixture.s


def record(kind, ident, day='2025-01-02', **fields):
    item = {'id': ident, 'kind': kind, 'date': day, 'source': 'Hand-worked example', **fields}
    return item


def mark(symbol, day, price):
    return {'symbol': symbol, 'date': day, 'price': price, 'currency': 'USD', 'fx': 1, 'source': 'Hand-worked price'}


class InsightTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def worked(self):
        # Deposit 1,000. Buy 10 at 10, then 10 at 20. Sell 5 at 30 from the first lot.
        # Buy 4 more at 25. Mark the open shares at 20.
        # Open cost 350. Value 380. Realised 100. Unrealised 30. Cash 750. Total 1,130.
        ledger = [
            record('DEPOSIT', 'd', amount=1000),
            record('BUY', 'b1', symbol='AAA', quantity=10, price=10),
            record('BUY', 'b2', day='2025-01-03', symbol='AAA', quantity=10, price=20),
            record('SELL', 's', day='2025-01-06', symbol='AAA', quantity=5, price=30),
            record('BUY', 'b3', day='2025-01-07', symbol='AAA', quantity=4, price=25),
        ]
        marks = [mark('AAA', '2025-01-02', 10), mark('AAA', '2025-01-07', 20)]
        return ledger, marks

    def test_hand_worked_purchase_partial_sale_and_repeat_buy(self):
        ledger, marks = self.worked()
        account = p.calculate(ledger, marks, as_of='2025-01-07')
        holding = account['holdings'][0]
        self.assertEqual(account['cashUSD'], 750)
        self.assertEqual(account['realisedUSD'], 100)
        self.assertEqual(holding['quantity'], 19)
        self.assertEqual(holding['costBasisUSD'], 350)
        self.assertEqual(holding['valueUSD'], 380)
        self.assertEqual(holding['unrealisedUSD'], 30)
        self.assertEqual(holding['realisedUSD'], 100)
        self.assertEqual(account['totalValueUSD'], 1130)
        insight = insights46.build(ledger, marks, {'AAA': 'Technology'}, [
            {'date': '2025-01-02', 'price': 100}, {'date': '2025-01-07', 'price': 110}], as_of='2025-01-07')
        self.assertEqual(insight['openCostUSD'], 350)
        self.assertEqual(insight['recordedValueUSD'], 1130)
        self.assertEqual(insight['unrealisedUSD'], 30)
        self.assertEqual(insight['holdings'][0]['contributionUSD'], 130)
        self.assertEqual(insight['holdings'][0]['sector'], 'Technology')
        self.assertTrue(insight['holdings'][0]['large'])
        self.assertIn('2025-01-07', insight['holdings'][0]['priceNote'])
        self.assertAlmostEqual(insight['comparison']['modifiedDietzPct'], 13)
        self.assertAlmostEqual(insight['comparison']['benchmarkPriceChangePct'], 10)
        self.assertEqual(insight['comparison']['flows'], [])

    def test_missing_price_is_labelled_and_allocation_uses_cost(self):
        ledger, _marks = self.worked()
        insight = insights46.build(ledger, [], {'AAA': ''}, [], as_of='2025-01-07')
        self.assertFalse(insight['complete'])
        self.assertIsNone(insight['recordedValueUSD'])
        self.assertEqual(insight['shareBasis'], 'cost')
        self.assertEqual(insight['holdings'][0]['sector'], 'Sector not recorded')
        self.assertIn('No saved price', insight['holdings'][0]['priceNote'])
        self.assertIsNone(insight['holdings'][0]['contributionUSD'])
        self.assertEqual(insight['comparison']['status'], 'withheld')
        self.assertIn('SPY comparison waits', insight['comparison']['notice'])

    def test_missing_spy_close_keeps_the_portfolio_figure(self):
        ledger, marks = self.worked()
        insight = insights46.build(ledger, marks, {}, [{'date': '2025-01-02', 'price': 100}], as_of='2025-01-07')
        self.assertEqual(insight['comparison']['status'], 'ok')
        self.assertAlmostEqual(insight['comparison']['modifiedDietzPct'], 13)
        self.assertIsNone(insight['comparison']['benchmarkPriceChangePct'])
        self.assertIn('withheld', insight['comparison']['spyNote'])

    def test_older_record_survives_an_offline_restart(self):
        ledger, marks = self.worked()
        ledger[1].pop('note', None)
        state = w.normalise({'ledger': ledger, 'marks': marks})
        s.write_workspace({'watch': ['AAA'], 'v3': state})
        s.init_storage()
        saved = s.read_workspace()['snapshot']['v3']
        self.assertEqual(len(saved['ledger']), 5)
        self.assertEqual(saved['ledger'][1]['symbol'], 'AAA')
        with patch.object(s, 'provider_get', side_effect=AssertionError('offline')), patch.object(s, 'massive_request', side_effect=AssertionError('offline')):
            packet = lab3.post('/api/v3/calculate', {'state': saved}, vars(s))
        self.assertEqual(packet['portfolio']['cashUSD'], 750)
        self.assertEqual(packet['portfolio']['realisedUSD'], 100)
        self.assertIn('days old', packet['insights']['holdings'][0]['priceNote'])
        self.assertEqual(packet['state']['ledger'][3]['kind'], 'SELL')
        reloaded = insights46.build(saved['ledger'], saved['marks'], {}, [], as_of='2025-01-07')
        self.assertEqual(reloaded['recordedValueUSD'], 1130)
