"""Connected Intelligence uses the same arithmetic as the screens. Figures are examples."""
import pathlib
import unittest

import ask48
import desk50
import intelligence64
import test_v3_api as fixture

s = fixture.s


class IntelligenceTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_chart_return_matches_the_two_prices(self):
        result = intelligence64.chart_return(100, 110)
        self.assertEqual(result['figures'][0]['value'], 10)
        self.assertEqual(result['kind'], 'observed fact')

    def test_a_forecast_win_must_agree_with_the_errors(self):
        bad = intelligence64.forecast_claim({'horizons': [{'horizon': 5, 'status': 'learned', 'modelErrorPP': 4, 'baselineErrorPP': 3}]})
        self.assertFalse(bad['supported'])
        closer = intelligence64.forecast_claim({'horizons': [{'horizon': 1, 'status': 'baseline', 'modelErrorPP': 3.76, 'baselineErrorPP': 3.79}]})
        self.assertIn('did not choose it', closer['answer'])
        worse = intelligence64.forecast_claim({'horizons': [{'horizon': 5, 'status': 'baseline', 'modelErrorPP': 4, 'baselineErrorPP': 3}]})
        self.assertIn('did not beat', worse['answer'])

    def test_mixed_currencies_are_not_ranked(self):
        result = intelligence64.contribution({'result': {'largest': {'symbol': 'AAA', 'contributionUSD': 5},
                                                        'holdings': [{'currency': 'USD'}, {'currency': 'EUR'}]}})
        self.assertIn('more than one currency', result['answer'])

    def test_operating_margin_is_not_subtracted_from_net_margin(self):
        report = {'annual': [
            {'type': 'annual', 'start': '2024-01-01', 'end': '2024-12-31', 'durationDays': 365, 'currency': 'USD',
             'metrics': {'revenue': {'value': 1000, 'tag': 'Revenues', 'unit': 'USD'}, 'profit': {'value': 100, 'tag': 'NetIncomeLoss', 'unit': 'USD'}}},
            {'type': 'annual', 'start': '2025-01-01', 'end': '2025-12-31', 'durationDays': 365, 'currency': 'USD',
             'metrics': {'revenue': {'value': 1100, 'tag': 'Revenues', 'unit': 'USD'}, 'profit': {'value': 80, 'tag': 'NetIncomeLoss', 'unit': 'USD'}}},
        ]}
        result = intelligence64.scenario_difference({'growthPct': 10, 'marginPct': 20}, report)
        self.assertEqual(result['figures'][0]['value'], 0)
        self.assertIn('not subtracted', result['answer'])

    def test_an_ambiguous_question_runs_no_tool(self):
        result = intelligence64.handle(vars(s), 'what about it?', {}, 10)
        self.assertFalse(result['supported'])
        self.assertIn('No calculation', result['answer'])

    def test_a_missing_scan_is_named(self):
        result = intelligence64.handle(vars(s), 'Why did this company match my scan?', {'symbol': 'AMD'}, 10)
        self.assertIn('saved scan', result['answer'])

    def test_confirmation_does_not_change_a_scenario(self):
        proposal = intelligence64.propose('scenario', 'Set growth to 12')
        self.assertFalse(proposal['saved'])
        saved = intelligence64.confirm(vars(s), proposal, True, 10)
        self.assertIn('no scenario number was changed', saved['notice'])
        opened = intelligence64.read(vars(s), saved['id'])
        self.assertIn('not rebuilt', opened['notice'])
        self.assertEqual(opened['answer'], 'Set growth to 12')

    def test_backup_restores_the_saved_investigation(self):
        saved = intelligence64.save(vars(s), {'symbol': 'AMD', 'answer': 'Up 10.00%.'}, 10)
        name = desk50.create_backup(vars(s))['file']
        with s.LOCK, s.db_connection() as con, con:
            con.execute('DELETE FROM intelligence64')
        desk50.restore_backup(vars(s), name, 'restore-this-backup')
        self.assertEqual(intelligence64.read(vars(s), saved['id'])['answer'], 'Up 10.00%.')

    def test_areas_label_facts_assumptions_and_models(self):
        self.assertEqual(intelligence64.chart_return(100, 100)['kind'], 'observed fact')
        self.assertEqual(intelligence64.contribution({'result': {'largest': {'symbol': 'AAA', 'contributionUSD': -2}, 'holdings': [{'currency': 'USD'}]}})['kind'], 'model output')
        self.assertEqual(intelligence64.scenario_difference({}, {})['kind'], 'user assumption')
        script = (pathlib.Path(__file__).resolve().parents[1] / 'site' / 'ask48.js').read_text()
        css = (pathlib.Path(__file__).resolve().parents[1] / 'site' / 'intelligence.css').read_text()
        self.assertIn('seq++', script)
        self.assertIn('id!==seq', script)
        self.assertIn('Use this page', script)
        self.assertIn('Back to investigation', script)
        self.assertIn('The answer on screen was kept', script)
        self.assertNotIn('clearAnswer', script.split('function closePanel')[1].split('function clearAnswer')[0])
        self.assertIn('prefers-reduced-motion', css)
        saved = ask48.answer(vars(s), 'How much did the stock move in the dates shown?', {'symbol': 'AAA', 'start': '2024-01-02', 'end': '2024-01-05', 'kind': 'chart'}, 10)
        self.assertTrue(saved.get('answer'))
        again = ask48.saved(vars(s), 'AAA')
        self.assertEqual(again[0]['question'], 'How much did the stock move in the dates shown?')
