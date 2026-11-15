"""Journal entries keep their original evidence and travel with older notes."""
import datetime as dt
import unittest
from pathlib import Path
from unittest.mock import patch

import journal49
import test_events42 as fixture
import workspace3

s = fixture.s
bars = fixture.bars


def entry(**changes):
    item = {
        'id': 'abc12345', 'symbol': 'TTWO', 'title': 'Week idea', 'createdAt': 1_000, 'updatedAt': 1_000,
        'status': 'open', 'origin': 'chart', 'range': '1W', 'start': '2026-05-22', 'end': '2026-05-26',
        'reviewDate': '2026-06-01', 'expectation': 'It may rise', 'reasons': 'Saved closes',
        'changeMind': 'A lower close', 'learned': '',
        'evidence': {'startPrice': 100, 'endPrice': 110, 'source': 'Massive · saved close', 'capturedAt': 1_000,
                     'links': [{'title': 'Filing', 'url': 'https://www.sec.gov/example'}], 'token': 'no'},
        'history': [], 'finnhub_key': 'SECRET',
    }
    item.update(changes)
    return item


class JournalTests(unittest.TestCase):
    setUp = fixture.EventResearchTests.setUp

    def test_backup_keeps_old_notes_projects_and_original_evidence(self):
        state = workspace3.mutate({}, 'research.project.save', {'project': {'id': 'p', 'symbol': 'TTWO', 'title': 'Older project'}})
        edited = entry(updatedAt=2_000, expectation='Edited view', history=[{'at': 1_500, 'status': 'open', 'expectation': 'It may rise'}])
        edited['evidence'] = {'endPrice': 999, 'source': 'replaced'}
        merged = journal49.merge([edited], [entry()])
        self.assertEqual(merged[0]['expectation'], 'Edited view')
        self.assertEqual(merged[0]['evidence']['endPrice'], 110)
        self.assertEqual(merged[0]['history'][0]['expectation'], 'It may rise')
        s.write_workspace({'notes': [{'title': 'Keep old note', 'thesis': 'Still here'}], 'journal': [entry()], 'v3': state, 'finnhub_key': 'SECRET'})
        s.init_storage()
        with patch.object(s, 'provider_get', side_effect=AssertionError('offline')), patch.object(s, 'massive_request', side_effect=AssertionError('offline')):
            saved = s.read_workspace()['snapshot']
        self.assertEqual(saved['notes'][0]['title'], 'Keep old note')
        self.assertEqual(saved['v3']['research']['projects'][0]['title'], 'Older project')
        self.assertEqual(saved['journal'][0]['evidence']['endPrice'], 110)
        self.assertEqual(saved['journal'][0]['evidence']['links'][0]['url'], 'https://www.sec.gov/example')
        self.assertNotIn('finnhub_key', saved['journal'][0])
        self.assertNotIn('token', saved['journal'][0]['evidence'])
        self.assertEqual(s.normalise_workspace({'notes': [{'title': 'Only a note'}]})['journal'], [])
        bars('TTWO', {'2026-05-22': 100, '2026-05-26': 110, '2026-05-27': 130})
        later = journal49.latest(s.__dict__, 'TTWO', fixture.at(dt.date(2026, 5, 28), 12))
        self.assertEqual(later['price'], 130)
        self.assertEqual(later['date'], '2026-05-27')
        self.assertEqual(saved['journal'][0]['evidence']['endPrice'], 110)
        text = journal49.export_text(saved['journal'])
        self.assertIn('https://www.sec.gov/example', text)
        self.assertIn('2026-05-22', text)
        source = Path('site/journal49.js').read_text()
        page = Path('site').joinpath('look43.js').read_text() + Path('site/move44.js').read_text() + Path('site/alerts.js').read_text() + Path('site/ask48.js').read_text() + Path('site/shell43.js').read_text()
        for origin in ('chart', 'move', 'alert', 'answer'):
            self.assertIn('data-journal="'+origin+'"' if origin != 'chart' else 'data-journal="chart"', page if origin != 'answer' else Path('site/ask48.js').read_text() + page)
        self.assertIn('draft.seq!==draftSeq', source)
        self.assertIn('older.evidence', source)
        self.assertIn('md-reborn-journal', Path('site/app.js').read_text())
