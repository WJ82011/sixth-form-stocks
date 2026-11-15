import unittest
from pathlib import Path
from unittest.mock import patch

import scenario53
import test_v3_api as fixture

s = fixture.s


def payload(**extra):
    body = {'currency': 'USD', 'start': '2025-04-01', 'end': '2026-03-31', 'rows': [
        {'name': 'revenue', 'valueM': 1000, 'kind': 'sourced'},
        {'name': 'cash', 'valueM': 100, 'kind': 'sourced'},
        {'name': 'debt', 'valueM': 300, 'kind': 'sourced'},
        {'name': 'shares', 'valueM': None, 'kind': 'missing'}],
        'manual': {'shares': {'valueM': 10, 'unit': 'millions', 'currency': 'USD', 'source': 'Synthetic diluted share count'}},
        'scenarios': [{'name': name, 'growthPct': 10, 'marginPct': 20, 'multiple': 8, 'method': 'EV/Operating profit'} for name in ('cautious', 'central', 'optimistic')]}
    body.update(extra)
    return body


class ScenarioTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_hand_worked_multiple_and_the_limits(self):
        result = scenario53.calculate(payload())
        central = result['cases'][1]
        revenue = 1000 * (1.1 ** 5)
        self.assertEqual(len(central['years']), 5)
        self.assertAlmostEqual(central['years'][0]['revenueM'], 1100)
        self.assertAlmostEqual(central['revenueM'], revenue)
        self.assertAlmostEqual(central['operatingProfitM'], revenue * 0.2)
        self.assertAlmostEqual(central['enterpriseM'], revenue * 0.2 * 8)
        self.assertAlmostEqual(central['equityM'], revenue * 0.2 * 8 - 200)
        self.assertAlmostEqual(central['valuePerShare'], (revenue * 0.2 * 8 - 200) / 10)
        solved = scenario53.solve({**payload(), 'price': central['valuePerShare'], 'unknown': 'growthPct'})
        self.assertEqual(solved['status'], 'solved')
        self.assertAlmostEqual(solved['value'], 10, places=6)
        multiple = scenario53.solve({**payload(), 'price': central['valuePerShare'], 'unknown': 'multiple'})
        self.assertAlmostEqual(multiple['value'], 8, places=6)
        blocked = scenario53.solve({**payload(), 'price': 1, 'unknown': 'growthPct', 'case': {'name': 'central', 'growthPct': 10, 'marginPct': -5, 'multiple': 8, 'method': 'EV/Operating profit'}})
        self.assertEqual(blocked['status'], 'unsolved')
        self.assertEqual(result['sensitivity']['strongest'] in ('revenue growth', 'operating margin', 'valuation multiple'), True)
        negative = scenario53.calculate(payload(scenarios=[{'name': name, 'growthPct': 10, 'marginPct': -5, 'multiple': 8, 'method': 'EV/Operating profit'} for name in ('cautious', 'central', 'optimistic')]))
        self.assertIsNone(negative['cases'][1]['enterpriseM'])
        missing_debt = payload()
        missing_debt['rows'] = [row for row in missing_debt['rows'] if row['name'] != 'debt']
        self.assertIsNone(scenario53.calculate(missing_debt)['cases'][1]['equityM'])
        self.assertIsNone(scenario53.calculate(missing_debt)['cases'][1]['valuePerShare'])
        mixed = payload()
        mixed['manual']['debt'] = {'valueM': 10, 'unit': 'millions', 'currency': 'EUR', 'source': 'Synthetic euro debt note'}
        mixed['rows'] = [row for row in mixed['rows'] if row['name'] != 'debt']
        with self.assertRaises(ValueError):
            scenario53.calculate(mixed)
        extreme = payload()
        extreme['scenarios'][1]['growthPct'] = 500
        with self.assertRaises(ValueError):
            scenario53.calculate(extreme)

    def test_saved_scenario_keeps_the_original_revenue(self):
        def accounts(symbol):
            revenue = 2000e6 if symbol == 'TTWO' and accounts.calls else 1000e6
            accounts.calls += 1
            return {'annual': [{'start': '2025-04-01', 'end': '2026-03-31', 'currency': 'USD', 'longTermDebt': 300e6,
                                'metrics': {'revenue': {'value': revenue, 'unit': 'USD', 'url': 'https://www.sec.gov/Archives/example', 'tag': 'Revenues'},
                                            'cash': {'value': 100e6, 'unit': 'USD'}}}]}
        accounts.calls = 0
        with patch.object(s, 'sec_saved', side_effect=accounts):
            saved = scenario53.save(vars(s), {'symbol': 'TTWO', 'title': 'Original', 'scenarios': payload()['scenarios'], 'manual': payload()['manual']}, 10)
            opened = scenario53.read(vars(s), saved['id'], 20)
            changed, _evidence = scenario53.answer(vars(s), 'What changed this result?', saved['id'])
        self.assertAlmostEqual(opened['saved']['result']['baseline']['revenueM'], 1000)
        self.assertAlmostEqual(opened['comparison']['latestRevenueM'], 2000)
        self.assertAlmostEqual(opened['saved']['result']['cases'][1]['enterpriseM'], 1000 * (1.1 ** 5) * 0.2 * 8)
        text, evidence = scenario53.answer(vars(s), 'What assumptions produce this value?', saved['id'])
        self.assertIn('your assumptions', text)
        self.assertAlmostEqual(evidence['cases'][1]['enterpriseM'], 1000 * (1.1 ** 5) * 0.2 * 8)
        self.assertIn('was not rewritten', changed)
        effect, _evidence = scenario53.answer(vars(s), 'Which assumption has the largest effect?', saved['id'])
        self.assertIn('central case', effect)
        source = Path('site/scenario53.js').read_text()
        self.assertIn('id!==seq', source)
        self.assertIn('data-journal="scenario"', source)
