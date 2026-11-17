"""Guard the public demo snapshot against flat synthetic % moves."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ExportDemoSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads((ROOT / 'site' / 'demo' / 'snapshot.json').read_text(encoding='utf-8'))
        cls.export_src = (ROOT / 'tools' / 'export-demo-snapshot.py').read_text(encoding='utf-8')
        cls.fixture = json.loads((ROOT / 'tools' / 'demo_fixtures' / 'equity_bars.json').read_text(encoding='utf-8'))

    def test_export_does_not_force_flat_prev_close(self):
        self.assertNotIn('price(sym) * 0.99', self.export_src)
        self.assertNotIn('* 0.99, 2)} for sym', self.export_src)

    def test_aapl_and_nvda_day_moves_differ(self):
        aapl = self.snapshot['quotes']['AAPL']
        nvda = self.snapshot['quotes']['NVDA']
        a_pct = round((aapl['c'] - aapl['pc']) / aapl['pc'] * 100, 2)
        n_pct = round((nvda['c'] - nvda['pc']) / nvda['pc'] * 100, 2)
        self.assertNotEqual(a_pct, n_pct)
        self.assertNotAlmostEqual(a_pct, 1.01, delta=0.05)
        self.assertNotAlmostEqual(n_pct, 1.01, delta=0.05)

    def test_watchlist_moves_are_mostly_unique(self):
        pcts = []
        for sym in self.snapshot['watchlist']:
            q = self.snapshot['quotes'][sym]
            pcts.append(round((q['c'] - q['pc']) / q['pc'] * 100, 2))
        self.assertGreaterEqual(len(set(pcts)), 8)

    def test_fixture_has_directory_coverage(self):
        self.assertGreaterEqual(len(self.fixture.get('quotes') or {}), 200)
        self.assertIn('AAPL', self.fixture['quotes'])
        self.assertIn('NVDA', self.fixture['quotes'])

    def test_snapshot_label_is_honest(self):
        label = self.snapshot.get('label') or ''
        self.assertRegex(label, r'DEMO DATA|not live')


if __name__ == '__main__':
    unittest.main()
