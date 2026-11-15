'''Everyday workflows on disposable data. No provider calls and no personal files.'''
import datetime as dt
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('everyday_server', ROOT / 'server.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class EverydayWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        home = Path(self.tmp.name)
        for name, value in (
            ('USER_DIR', home),
            ('DB_FILE', home / 'observations.sqlite3'),
            ('KEY_FILE', home / 'finnhub_key'),
            ('MASSIVE_KEY_FILE', home / 'massive_key'),
            ('WORKSPACE_FILE', home / 'workspace.json'),
        ):
            patcher = patch.object(server, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.now = 1793700000000
        clock = patch.object(server.time, 'time', side_effect=lambda: self.now / 1000)
        clock.start()
        self.addCleanup(clock.stop)
        server.init_storage()

    def test_follow_remove_alert_range_replay_and_offline_reopen(self):
        server.write_workspace({'watch': ['TTWO', 'AMD'], 'names': {'TTWO': 'Take-Two'}, 'preferences': {'edition': 'professional'}})
        self.assertEqual(server.read_workspace()['snapshot']['watch'], ['TTWO', 'AMD'])
        server.write_workspace({'watch': ['AMD'], 'names': {'AMD': 'Advanced Micro Devices'}, 'preferences': {'edition': 'signal'}})
        saved = server.read_workspace()['snapshot']
        self.assertEqual(saved['watch'], ['AMD'])
        self.assertEqual(saved['preferences']['edition'], 'signal')
        self.assertNotIn('TTWO', saved['watch'])

        created = server.change_alerts({'action': 'create', 'symbol': 'AMD', 'direction': 'above', 'target': 100, 'unit': 'USD'})
        self.assertEqual(len(server.read_alerts()['alerts']), 1)
        server.change_alerts({'action': 'delete', 'id': created['id']})
        self.assertEqual(server.read_alerts()['alerts'], [])

        day = int(dt.datetime(2026, 1, 2, tzinfo=dt.timezone.utc).timestamp())
        server.store_point('AMD', (day + 3600) * 1000, 101, 'finnhub_quote')
        server.store_point('AMD', (day + 86400) * 1000, 110, 'finnhub_quote')
        short = server.handle_api('/api/history', {'symbol': ['AMD'], 'since': [str((day + 80000) * 1000)]})
        self.assertEqual([point['p'] for point in short['points']], [110])
        server.store_massive_daily_bars('AMD', {'t': [day, day + 86400], 'o': [100, 108], 'h': [104, 112], 'l': [99, 107], 'c': [101, 110], 'v': [10, 12]})
        with patch.object(server, 'provider_get', side_effect=AssertionError('offline')), patch.object(server, 'massive_request', side_effect=AssertionError('offline')):
            server.init_storage()
            reopened = server.read_workspace()['snapshot']
            daily = server.handle_api('/api/saved-daily', {'symbol': ['AMD'], 'from': [str(day - 10)], 'to': [str(day + 3 * 86400)]})
        self.assertEqual(reopened['watch'], ['AMD'])
        self.assertEqual(reopened['preferences']['edition'], 'signal')
        self.assertEqual(daily['candles']['c'], [101, 110])
        self.assertTrue(daily['cached'])

        import replay43
        hidden = replay43.frame([{'t': 0, 'p': 100}, {'t': 60000, 'p': 180}], [], [], 0)
        self.assertEqual(hidden['prices'], [{'t': 0, 'p': 100}])
        live = replay43.frame([{'t': 0, 'p': 100}, {'t': 60000, 'p': 180}], [], [], 60000)
        self.assertEqual(live['prices'][-1]['p'], 180)
