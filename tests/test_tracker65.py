"""Research change tracker. Figures are controlled examples, not live filings."""
import json
import pathlib
import unittest
from unittest.mock import patch

import desk50
import scorecard41
import test_v3_api as fixture
import tracker65

s = fixture.s
ANNUAL = {
    'type': 'annual', 'start': '2024-01-01', 'end': '2024-12-31', 'durationDays': 366, 'currency': 'USD',
    'metrics': {'revenue': {'value': 1000, 'tag': 'Revenues', 'unit': 'USD', 'filedAt': 10},
                'profit': {'value': 100, 'tag': 'NetIncomeLoss', 'unit': 'USD'}},
}


def report(revenue=1000, currency='USD', extra=None):
    period = json.loads(json.dumps(ANNUAL))
    period['currency'] = currency
    period['metrics']['revenue']['value'] = revenue
    period['metrics']['revenue']['unit'] = currency
    rows = [period]
    if extra:
        rows.append(extra)
    return {'annual': rows}


class TrackerTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def follow(self, now=1_000, **note):
        body = {'symbol': 'TTWO', 'journalId': 'abc12345', 'title': 'Take-Two investigation', 'status': 'open',
                'expectation': 'The original thesis stays.', 'reviewDate': '2026-11-01', **note}
        with patch.object(s, 'sec_saved', return_value=note.get('report') or {}):
            return tracker65.follow(vars(s), body, now)

    def test_take_two_follow_names_missing_data_once(self):
        saved = self.follow()
        self.assertIn('not edited', saved['notice'])
        first = tracker65.sweep(vars(s), 2_000)
        again = tracker65.sweep(vars(s), 3_000)
        self.assertEqual(again['added'], 0)
        shown = tracker65.review_list(vars(s), 'TTWO')
        missing = [item for item in shown['companies'][0]['items'] if item['kind'] == 'missing']
        self.assertEqual(len(missing), 1)
        self.assertIn('was invented', missing[0]['calculation'])
        self.assertEqual(shown['companies'][0]['expectation'], 'The original thesis stays.')
        self.assertGreaterEqual(first['checked'], 1)

    def test_new_filing_revision_forecast_and_unlike_currency(self):
        self.follow()
        with patch.object(s, 'sec_saved', return_value=report(1000)):
            tracker65.sweep(vars(s), 5_000)
        shown = tracker65.review_list(vars(s), 'TTWO')
        filing = [item for item in shown['companies'][0]['items'] if item['kind'] == 'filing']
        self.assertEqual(filing[0]['updated'], 1000)
        self.assertEqual(filing[0]['original'], 'No saved statement for this period')
        with patch.object(s, 'sec_saved', return_value=report(1100)):
            tracker65.sweep(vars(s), 6_000)
        shown = tracker65.review_list(vars(s), 'TTWO')
        revised = [item for item in shown['companies'][0]['items'] if item['kind'] == 'revision' and item['updated'] == 1100]
        self.assertEqual(revised[0]['original'], 1000)
        self.assertIn('100', revised[0]['calculation'])
        quarter = {'type': 'quarterly', 'start': '2024-10-01', 'end': '2024-12-31', 'durationDays': 92, 'currency': 'USD',
                   'metrics': {'revenue': {'value': 300, 'tag': 'Revenues', 'unit': 'USD'}}}
        with patch.object(s, 'sec_saved', return_value=report(1100, extra=quarter)):
            tracker65.sweep(vars(s), 7_000)
        shown = tracker65.review_list(vars(s), 'TTWO')
        quarters = [item for item in shown['companies'][0]['items'] if item.get('dates') == '2024-10-01 to 2024-12-31']
        self.assertIn('different period length', quarters[0]['calculation'])
        with patch.object(s, 'sec_saved', return_value=report(1100, currency='EUR')):
            tracker65.sweep(vars(s), 8_000)
        shown = tracker65.review_list(vars(s), 'TTWO')
        unlike = [item for item in shown['companies'][0]['items'] if 'not subtracted' in item.get('calculation', '') or 'not compared' in item.get('title', '').lower() or 'differs' in item.get('calculation', '')]
        self.assertTrue(any('not subtracted' in item['calculation'] or 'No conversion' in item['calculation'] for item in unlike))
        with s.LOCK, s.db_connection() as con, con:
            scorecard41.init(con)
            con.execute('INSERT INTO learning41_issued VALUES(?,?,?,?,?,?,?,?,?)', (
                'f1', 'TTWO', 'test', 1, '2026-11-10', '2026-11-12', 9_000,
                json.dumps({'symbol': 'TTWO', 'anchorDay': '2026-11-10', 'targetDay': '2026-11-12', 'horizon': 1, 'forecastPrice': 200}),
                json.dumps({'status': 'scored', 'actualPrice': 210, 'gradedAt': 9_000, 'absoluteErrorPP': 1, 'unchangedErrorPP': 1, 'inRange': True, 'beatBaseline': False})))
        tracker65.sweep(vars(s), 10_000)
        shown = tracker65.review_list(vars(s), 'TTWO')
        graded = [item for item in shown['companies'][0]['items'] if item['kind'] == 'forecast']
        self.assertEqual(graded[0]['original'], 200)
        self.assertEqual(graded[0]['updated'], 210)
        before = len(shown['companies'][0]['items'])
        tracker65.sweep(vars(s), 11_000)
        self.assertEqual(len(tracker65.review_list(vars(s), 'TTWO')['companies'][0]['items']), before)

    def test_gap_acknowledgement_backup_and_assumption(self):
        saved = self.follow(now=1_000, assumptions={'growthPct': 20, 'marginPct': 15})
        prior = {'type': 'annual', 'start': '2023-01-01', 'end': '2023-12-31', 'durationDays': 365, 'currency': 'USD',
                 'metrics': {'revenue': {'value': 1000, 'tag': 'Revenues', 'unit': 'USD'}, 'profit': {'value': 100, 'tag': 'NetIncomeLoss', 'unit': 'USD'}}}
        later = json.loads(json.dumps(ANNUAL))
        later['metrics']['revenue']['value'] = 1100
        with patch.object(s, 'sec_saved', return_value={'annual': [prior, later]}):
            tracker65.sweep(vars(s), 1_000 + 60 * 60 * 1000)
        shown = tracker65.review_list(vars(s), 'TTWO')
        assumption = [item for item in shown['companies'][0]['items'] if item['kind'] == 'assumption' and item['updated'] != 'No comparable revenue change']
        self.assertEqual(assumption[0]['original'], 20)
        self.assertTrue(any(item['gap'] for item in shown['companies'][0]['items']))
        acked = tracker65.acknowledge(vars(s), saved['id'], 9_000)
        self.assertIn('not edited', acked['notice'])
        self.assertEqual(acked['status'], 'open')
        self.assertEqual(acked['expectation'], 'The original thesis stays.')
        name = desk50.create_backup(vars(s))['file']
        with s.LOCK, s.db_connection() as con, con:
            con.execute('DELETE FROM tracker65_follows')
        self.assertEqual(tracker65.review_list(vars(s), 'TTWO')['companies'], [])
        desk50.restore_backup(vars(s), name, 'restore-this-backup')
        restored = tracker65.review_list(vars(s), 'TTWO')
        self.assertEqual(restored['companies'][0]['expectation'], 'The original thesis stays.')
        self.assertTrue(restored['reviews'])
        script = pathlib.Path(__file__).resolve().parents[1].joinpath('site/tracker65.js').read_text()
        self.assertIn('id!==seq', script)
