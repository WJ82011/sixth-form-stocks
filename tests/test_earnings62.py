"""Earnings Lab arithmetic. The figures are worked examples, not company filings."""
import datetime as dt
import unittest

import earnings62
import events42
import test_v3_api as fixture

s = fixture.s


def fact(value, tag='Revenue', filed='2026-02-01'):
    return {'value': value, 'unit': 'USD', 'tag': tag, 'filed': filed, 'form': '10-K', 'accession': '0000000000-26-000001'}


def year(start, end, revenue, profit, **extra):
    return {'type': 'annual', 'start': start, 'end': end, 'durationDays': 365, 'currency': 'USD',
            'metrics': {'revenue': fact(revenue, 'Revenues'), 'profit': fact(profit, 'NetIncomeLoss')}, **extra}


class EarningsTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_year_over_year_growth_and_a_lower_net_margin(self):
        report = {'name': 'Example Co', 'annual': [
            year('2024-01-01', '2024-12-31', 1000, 100),
            year('2025-01-01', '2025-12-31', 1100, 80),
        ]}
        card = earnings62.review(report)['cards'][0]
        self.assertAlmostEqual(card['revenueChange']['changePct'], 10)
        self.assertAlmostEqual(card['netMarginPct'], 80 / 1100 * 100)
        self.assertAlmostEqual(card['netMarginChangePP'], 80 / 1100 * 100 - 10)
        self.assertIn('not an operating margin', card['note'])
        self.assertIn('10.00%', earnings62.answer(report, 'How does this compare with last year?'))

    def test_negative_profit_stays_negative(self):
        card = earnings62.review({'annual': [year('2025-01-01', '2025-12-31', 1000, -50)]})['cards'][0]
        self.assertEqual(card['profit']['value'], -50)
        self.assertAlmostEqual(card['netMarginPct'], -5)

    def test_a_quarter_is_not_compared_with_a_year(self):
        quarter = dict(year('2025-10-01', '2025-12-31', 300, 30), type='quarterly', durationDays=92)
        annual = year('2025-01-01', '2025-12-31', 1100, 80)
        self.assertFalse(earnings62._change(quarter, annual, 'revenue')['available'])
        self.assertIn('full year', earnings62._change(quarter, annual, 'revenue')['reason'])

    def test_year_to_date_is_not_called_a_quarter(self):
        built = earnings62.review({'annual': [], 'quarterly': [], 'yearToDate': [
            {'start': '2025-01-01', 'end': '2025-09-30', 'durationDays': 273}]})
        self.assertEqual(built['status'], 'unavailable')
        labelled = earnings62._year_to_date([{'start': '2025-01-01', 'end': '2025-09-30', 'durationDays': 273}])
        self.assertIn('not shown as a single quarter', labelled[0]['note'])

    def test_a_restatement_is_named_and_the_latest_value_is_kept(self):
        revised = year('2025-01-01', '2025-12-31', 1100, 80)
        revised['metrics']['revenue']['valuesDifferAcrossFilings'] = True
        revised['warnings'] = ['Revenue: values differ across filings; the latest filed version is shown.']
        card = earnings62.review({'annual': [year('2024-01-01', '2024-12-31', 1000, 100), revised]})['cards'][0]
        self.assertEqual(card['revenue']['value'], 1100)
        self.assertTrue(any('later filing' in line for line in card['warnings']))

    def test_different_year_ends_are_not_forced_together(self):
        apple = year('2024-09-29', '2025-09-27', 1000, 100)
        take_two = year('2024-04-01', '2025-03-31', 1100, 80)
        self.assertFalse(earnings62._change(take_two, apple, 'revenue')['available'])

    def test_a_missing_quarter_is_not_invented(self):
        first = dict(year('2025-01-01', '2025-03-31', 100, 10), type='quarterly', durationDays=90)
        later = dict(year('2025-07-01', '2025-09-30', 120, 12), type='quarterly', durationDays=92)
        built = earnings62.review({'quarterly': [first, later]})
        self.assertTrue(built['missingQuarters'])

    def test_after_close_release_uses_the_next_session(self):
        published = int(dt.datetime(2026, 1, 9, 18, tzinfo=events42.NY).timestamp() * 1000)
        now = int(dt.datetime(2026, 1, 12, 18, tzinfo=events42.NY).timestamp() * 1000)
        window = earnings62.reaction_window(published, now)
        self.assertEqual(window['timing'], 'after the close')
        self.assertEqual((window['start'], window['end']), ('2026-01-09', '2026-01-12'))
        self.assertIn('No price reaction', earnings62.reaction_window(None, now)['notice'])

    def test_simulator_growth_can_be_compared_and_the_margin_cannot(self):
        report = {'annual': [year('2024-01-01', '2024-12-31', 1000, 100), year('2025-01-01', '2025-12-31', 1100, 80)]}
        compared = earnings62.assumptions({'growthPct': 10, 'marginPct': 20}, report)
        self.assertEqual(compared['original']['growthPct'], 10)
        self.assertEqual(compared['comparisons'][0]['differencePP'], 0)
        self.assertIn('not subtracted', compared['margin'])

    def test_a_saved_review_reopens_without_being_rebuilt(self):
        report = {'name': 'Example', 'annual': [year('2025-01-01', '2025-12-31', 1000, -50)]}
        saved = earnings62.save(vars(s), 'AAPL', report, 10)
        opened = earnings62.read(vars(s), saved['id'])
        self.assertIn('not rebuilt', opened['notice'])
        self.assertEqual(opened['cards'][0]['profit']['value'], -50)
        self.assertIn('None is shown', opened['analystExpectations'])
