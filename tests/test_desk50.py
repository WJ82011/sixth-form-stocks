"""V5 connections use the same saved closes as Move Review and the scorecard."""
import datetime as dt
import unittest
from pathlib import Path
from unittest.mock import patch

import ask48
import desk50
import events42
import move44
import test_events42 as fixture

s = fixture.s
bars = fixture.bars
NOW = fixture.at(dt.date(2026, 6, 2), 12)


def fill(symbol, start, end, first=100):
    day, prices, index = start, {}, 0
    while day <= end:
        if events42.is_session(day):
            prices[day.isoformat()] = first + index
            index += 1
        day += dt.timedelta(days=1)
    bars(symbol, prices)


class ConnectedDeskTests(unittest.TestCase):
    setUp = fixture.EventResearchTests.setUp

    def test_questions_match_saved_records_and_backup_restores_older_notes(self):
        fill('AMD', dt.date(2026, 1, 2), dt.date(2026, 6, 1), 50)
        fill('TTWO', dt.date(2026, 5, 22), dt.date(2026, 6, 1), 100)
        fill('SPY', dt.date(2026, 5, 22), dt.date(2026, 6, 1), 400)
        with patch.object(s, 'provider_get', side_effect=AssertionError('offline')), patch.object(s, 'massive_request', side_effect=AssertionError('offline')):
            unusual = ask48.answer(s.__dict__, 'Was AMD’s move unusual compared with its own history?', {'symbol': 'AMD'}, NOW)
            direct = desk50.unusual(s.__dict__, 'AMD', NOW)
            self.assertAlmostEqual(unusual['evidence']['movePct'], direct['movePct'])
            self.assertEqual(unusual['evidence']['sampleSize'], direct['sampleSize'])
            self.assertGreaterEqual(direct['sampleSize'], 20)
            week = ask48.answer(s.__dict__, 'How much did TTWO move this week?', {'symbol': 'TTWO'}, NOW)
            review = move44.review(s.__dict__, 'TTWO', week['context']['start'], week['context']['end'], NOW)
            self.assertAlmostEqual(week['evidence']['returnPct'], review['returnPct'])
            compared = ask48.answer(s.__dict__, 'How did it compare with SPY?', week['context'], NOW)
            self.assertAlmostEqual(compared['evidence']['comparison']['differencePP'], review['comparison']['differencePP'])
            changed = ask48.answer(s.__dict__, 'What changed since my last review of Take-Two?', {'symbol': 'TTWO', 'capturedAt': fixture.at(dt.date(2026, 5, 20), 12), 'originalPrice': 100}, NOW)
            self.assertEqual(changed['evidence']['startPrice'], 100)
            self.assertEqual(changed['evidence']['endPrice'], desk50.price_status(s.__dict__, 'TTWO', NOW)['price'])
            idea = ask48.answer(s.__dict__, 'Which evidence supports or challenges my saved idea?', {'symbol': 'TTWO', 'capturedAt': 1, 'originalPrice': 100, 'expectation': 'It may rise', 'journalStatus': 'open'}, NOW)
            self.assertIn('does not change that judgement', idea['answer'])
            self.assertIn('higher', idea['answer'])
            model = ask48.answer(s.__dict__, 'How has this model performed on this stock?', {'symbol': 'TTWO'}, NOW)
            self.assertIn('No issued forecast', model['answer'])
            vague = ask48.answer(s.__dict__, 'Should I buy it?', {'symbol': 'TTWO'}, NOW)
            self.assertFalse(vague['supported'])
            s.write_workspace({'notes': [{'title': 'Older note'}], 'watch': ['TTWO']})
            first = desk50.create_backup(s.__dict__)
            bars('TTWO', {'2026-06-02': 999})
            s.write_workspace({'notes': [{'title': 'Newer note'}], 'journal': [{'id': 'abc12345', 'symbol': 'TTWO', 'title': 'Idea', 'createdAt': 1, 'updatedAt': 1, 'origin': 'chart', 'evidence': {'endPrice': 110}}]})
            with self.assertRaises(ValueError):
                desk50.restore_backup(s.__dict__, first['file'], 'no')
            self.assertEqual(s.read_workspace()['snapshot']['notes'][0]['title'], 'Newer note')
            desk50.restore_backup(s.__dict__, first['file'], 'restore-this-backup')
            self.assertEqual(s.read_workspace()['snapshot']['notes'][0]['title'], 'Older note')
            self.assertEqual(s.read_workspace()['snapshot']['journal'], [])
            self.assertNotEqual(desk50.price_status(s.__dict__, 'TTWO', NOW)['price'], 999)
            with self.assertRaises(ValueError):
                desk50.trim_backups(s.__dict__, 'please')
            self.assertGreaterEqual(desk50.storage(s.__dict__)['backupCount'], 1)
        source = Path('site/desk50.js').read_text()
        self.assertIn("before!==sym", source)
        self.assertIn('restore-this-backup', source)
        self.assertIn('keep-newest-5', source)

if __name__ == '__main__':
    unittest.main()
