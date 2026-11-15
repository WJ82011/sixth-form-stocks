"""Bundled listing index for static deploy discovery."""
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
INDEX = ROOT / 'site' / 'listings-index.json'
SYMBOL = re.compile(r'^[A-Z0-9][A-Z0-9.\-]{0,23}$')


class ListingsIndexTest(unittest.TestCase):
    def test_index_is_well_formed(self):
        data = json.loads(INDEX.read_text())
        self.assertGreaterEqual(data['total'], 5000)
        self.assertEqual(data['total'], len(data['rows']))
        seen = set()
        for row in data['rows']:
            self.assertIn('symbol', row)
            self.assertIn('name', row)
            self.assertNotIn(row['symbol'], seen)
            seen.add(row['symbol'])
            self.assertRegex(row['symbol'], SYMBOL)
            self.assertTrue(row['name'].strip())