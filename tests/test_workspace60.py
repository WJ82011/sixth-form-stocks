"""Workspaces, annotations and the coverage overview. Figures are labelled test records."""
import datetime as dt
import json
import unittest

import annotate60
import collector40
import crypto57
import desk50
import events42
import overview60
import pack59
import workspace60
import test_v3_api as fixture

s = fixture.s


def stamp(day):
    return int(dt.datetime.combine(day, dt.time(16), events42.NY).timestamp() * 1000)


class WorkspaceTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_switching_keeps_the_saved_copy(self):
        gaming = workspace60.save(vars(s), {'name': 'Gaming companies', 'symbols': ['TTWO', 'RBLX']}, 10)
        other = workspace60.save(vars(s), {'name': 'Daily review', 'symbols': ['AAPL'], 'useWatchlist': True}, 20)
        draft = dict(gaming)
        draft['symbols'] = ['MSFT']
        opened = workspace60.activate(vars(s), other['id'])
        self.assertEqual(opened['symbols'], ['AAPL'])
        stored = workspace60.read(vars(s), gaming['id'])
        self.assertEqual(stored['symbols'], ['TTWO', 'RBLX'])
        self.assertNotEqual(draft['symbols'], stored['symbols'])
        self.assertRaises(ValueError, workspace60.save, vars(s), {'name': 'Too narrow', 'layout': {'side': 100}}, 30)

    def test_measure_undo_and_report(self):
        saved = annotate60.replace(vars(s), 'TTWO', [
            {'kind': 'level', 'price': 200, 'label': 'Test level'},
            {'kind': 'measure', 't1': 0, 'p1': 100, 't2': 172800000, 'p2': 110},
        ], 10)
        measure = next(item for item in saved['items'] if item['kind'] == 'measure')
        self.assertEqual(measure['changePct'], 10)
        self.assertEqual(measure['elapsedDays'], 2)
        annotate60.remove(vars(s), 'TTWO', measure['id'])
        self.assertEqual(len(annotate60.for_symbol(vars(s), 'TTWO')), 1)
        restored = annotate60.undo(vars(s), 'TTWO')
        self.assertEqual(len(restored['items']), 2)
        body = pack59.build('TTWO', 'Take-Two Interactive', {'prices': [
            {'date': '2026-01-05', 'price': 100, 'source': 'Test close'},
            {'date': '2026-01-06', 'price': 110, 'source': 'Test close'}],
            'annotations': restored['items']})
        names = [section['id'] for section in body['sections']]
        self.assertIn('annotations', names)
        self.assertIn('user assumption', next(section['kind'] for section in body['sections'] if section['id'] == 'annotations'))

    def test_overview_keeps_stock_and_crypto_apart(self):
        now = dt.datetime(2026, 1, 12, 12, tzinfo=events42.NY)
        days = (dt.date(2026, 1, 5), dt.date(2026, 1, 6))
        books = {
            'AAA': (100, 110), 'BBB': (100, 90), 'CCC': (50, None), 'DDD': (10, 40), 'EEE': (100, 103),
        }
        with s.LOCK, s.db_connection() as con, con:
            for symbol, (start, end) in books.items():
                con.execute('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)',
                            (symbol, stamp(days[0]), start, start, start, start, 1, 1))
                if end is not None:
                    con.execute('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)',
                                (symbol, stamp(days[1]), end, end, end, end, 1, 1))
            crypto57.init(con)
            for day, price in ((dt.date(2026, 1, 10), 200), (dt.date(2026, 1, 11), 220)):
                moment = int(dt.datetime.combine(day, dt.time(0), dt.timezone.utc).timestamp() * 1000)
                con.execute('INSERT INTO crypto57_candles VALUES(?,?,?,?)', ('BTC-USD', 86400000, moment, price))
            con.execute('INSERT INTO crypto57_candles VALUES(?,?,?,?)', ('ETH-USD', 86400000,
                        int(dt.datetime(2026, 1, 10, tzinfo=dt.timezone.utc).timestamp() * 1000), 100))
        built = overview60.build(vars(s), int(now.timestamp() * 1000),
                                 {'AAA': 'Technology', 'BBB': 'Technology', 'EEE': 'Technology', 'DDD': 'Technology'})
        equity, crypto = built['equity'], built['crypto']
        self.assertEqual(equity['end'], '2026-01-06')
        self.assertEqual(equity['advancing'], 2)
        self.assertEqual(equity['declining'], 1)
        self.assertEqual(equity['evaluated'], 5)
        self.assertEqual(sorted(row['reason'] for row in equity['excluded']), ['missing-close', 'split-sized'])
        self.assertEqual(equity['sectors'][0]['changePct'], 1)
        self.assertEqual(crypto['calendar'], 'UTC days')
        self.assertEqual(crypto['end'], '2026-01-11')
        self.assertEqual(crypto['companies'][0]['changePct'], 10)
        self.assertEqual(crypto['excluded'][0]['symbol'], 'ETH-USD')
        self.assertNotEqual(equity['end'], crypto['end'])

    def test_backup_restores_workspace_and_annotation(self):
        workspace60.save(vars(s), {'name': 'Gaming companies', 'symbols': ['TTWO']}, 10)
        annotate60.replace(vars(s), 'TTWO', [{'kind': 'note', 't': 10, 'price': 100, 'text': 'Test note'}], 10)
        name = desk50.create_backup(vars(s))['file']
        with s.LOCK, s.db_connection() as con, con:
            con.execute('DELETE FROM workspace60')
            con.execute('DELETE FROM annotate60')
        desk50.restore_backup(vars(s), name, 'restore-this-backup')
        restored = workspace60.listed(vars(s))
        gaming = next(row for row in restored['workspaces'] if row['name'] == 'Gaming companies')
        self.assertEqual(gaming['symbols'], ['TTWO'])
        self.assertEqual(annotate60.for_symbol(vars(s), 'TTWO')[0]['text'], 'Test note')

    def test_collector_starts_once_and_inventory_files_exist(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        for _area, relative in workspace60.AREAS:
            self.assertTrue((root / relative).exists(), relative)
        collector = collector40.Collector({'read_workspace': lambda: {'snapshot': None}})
        calls = []
        collector._launch = lambda: calls.append(1)
        self.assertTrue(collector.start())
        self.assertFalse(collector.start())
        self.assertEqual(calls, [1])
