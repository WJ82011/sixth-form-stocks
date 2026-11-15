"""Research packs from labelled test records. Not a Take-Two filing."""
import unittest

import desk50
import pack59
import test_v3_api as fixture

s = fixture.s

PRICES = [
    {'date': '2026-01-05', 'price': 100, 'source': 'Test close'},
    {'date': '2026-01-06', 'price': 110, 'source': 'Test close'},
]


def parts(**extra):
    base = {'prices': PRICES, 'move': None, 'events': [], 'financials': None,
            'comparison': None, 'scenario': None, 'forecast': None, 'journal': []}
    base.update(extra)
    return base


class PackTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_saved_comparison_uses_the_stored_return(self):
        body = pack59.build('ABNB', 'Airbnb', {'comparison': {
            'symbols': ['ABNB', 'BKNG'], 'start': '2026-11-12', 'end': '2026-11-13',
            'rows': [{'symbol': 'ABNB', 'returnPct': 3.12}, {'symbol': 'BKNG', 'returnPct': 1}],
        }})
        section = next(item for item in body['sections'] if item['id'] == 'comparison')
        self.assertIn('3.12%', section['finding'])
        self.assertEqual(section['kind'], 'historical fact')

    def test_missing_sections_are_left_out(self):
        body = pack59.build('TTWO', 'Take-Two Interactive', parts())
        names = [section['id'] for section in body['sections']]
        self.assertEqual(names, ['prices'])
        self.assertIn('financials', [row['id'] for row in body['omitted']])
        self.assertIn('100', body['sections'][0]['finding'])
        self.assertEqual(body['sections'][0]['kind'], 'historical fact')

    def test_edited_wording_keeps_the_source(self):
        body = pack59.build('TTWO', 'Take-Two Interactive', parts())
        saved = pack59.store(vars(s), body, 10)
        edited = pack59.edit_wording(vars(s), saved['id'], 'My summary of the test closes.', 20)
        self.assertEqual(edited['id'], saved['id'])
        self.assertEqual(pack59.display_text(edited), 'My summary of the test closes.')
        self.assertEqual(edited['sections'][0]['figures'][0]['source'], 'Test close')
        document = pack59.html_export(edited)
        self.assertIn('My summary of the test closes.', document)
        self.assertIn('Test close', document)
        self.assertIn('data-prices="100,110"', document)
        self.assertIn('@media print', document)
        self.assertNotIn('finnhub_key', document.lower())

    def test_two_editions_and_offline_reopen(self):
        first = pack59.store(vars(s), pack59.build('TTWO', 'Take-Two Interactive', parts(
            events=[{'title': 'Test announcement', 'date': '2026-01-05', 'source': 'Test filing'}],
            forecast={'pending': [{'forecastPrice': 120, 'targetDate': '2026-06-01', 'method': 'test-model'}], 'graded': []},
            scenario={'id': 'abc', 'model': 'scenario-multiple-v5.3', 'assumptions': {'growthPct': 10}, 'result': {'perShare': 237.68}},
        )), 10)
        changed = dict(PRICES[1])
        changed['price'] = 90
        second_parts = parts(
            prices=[PRICES[0], changed],
            events=[{'title': 'Test announcement', 'date': '2026-01-05', 'source': 'Test filing'},
                    {'title': 'Later test announcement', 'date': '2026-02-01', 'source': 'Test filing'}],
            financials={'period': 'FY test', 'currency': 'USD', 'source': 'Test statement', 'rows': [{'name': 'revenue', 'valueM': 1000}]},
            forecast={'graded': [{'targetDate': '2026-06-01', 'method': 'test-model', 'outcome': {'absoluteErrorPP': 1.5}}], 'pending': []},
            scenario={'id': 'abc', 'model': 'scenario-multiple-v5.3', 'assumptions': {'growthPct': 12}, 'result': {'perShare': 240}},
        )
        second = pack59.new_edition(vars(s), first['id'], second_parts, '', 30)
        self.assertEqual(second['edition'], 2)
        self.assertEqual(second['previousId'], first['id'])
        opened = pack59.read(vars(s), first['id'])
        self.assertIn('110', opened['sections'][0]['finding'])
        self.assertIn('not rebuilt', opened['notice'])
        changes = pack59.diff(opened, second)
        self.assertEqual(changes['newAnnouncements'][0]['title'], 'Later test announcement')
        self.assertEqual(changes['changedFinancials'][0]['name'], 'revenue')
        self.assertEqual(changes['changedFinancials'][0]['to'], 1000)
        self.assertEqual(changes['changedAssumptions'][0]['from'], 10)
        self.assertEqual(changes['changedAssumptions'][0]['to'], 12)
        self.assertTrue(changes['newlyGraded'])

    def test_backup_restores_the_saved_pack(self):
        saved = pack59.store(vars(s), pack59.build('TTWO', 'Take-Two Interactive', parts()), 10)
        name = desk50.create_backup(vars(s))['file']
        import contextlib
        with s.LOCK, contextlib.closing(s.db_connection()) as con, con:
            con.execute('DELETE FROM pack59')
        self.assertRaises(ValueError, pack59.read, vars(s), saved['id'])
        desk50.restore_backup(vars(s), name, 'restore-this-backup')
        restored = pack59.read(vars(s), saved['id'])
        self.assertEqual(restored['sections'][0]['figures'][1]['value'], 110)
