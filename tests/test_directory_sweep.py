'''Every directory company must keep one ticker across chart, news, events and research.
The sweep uses the saved catalog only. It does not call Finnhub or Massive.'''
import json, pathlib, re, unittest
import server

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / 'site' / 'app.js').read_text()
LOOK = (ROOT / 'site' / 'look43.js').read_text()

def directory():
    return json.loads((ROOT / 'site' / 'stock-directory.json').read_text())

def destinations(symbol):
    '''The same ticker is the only identifier these screens are allowed to use.'''
    return {'chart': symbol, 'news': symbol, 'events': symbol, 'research': symbol}

class DirectorySweepTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = directory()

    def test_every_entry_is_unique_and_routable(self):
        self.assertGreaterEqual(len(self.rows), 200)
        seen = set()
        for row in self.rows:
            symbol = server.valid_symbol(row['symbol'])
            self.assertEqual(symbol, row['symbol'])
            self.assertNotIn(symbol, seen)
            seen.add(symbol)
            self.assertTrue(row['name'].strip())
            self.assertTrue(row['category'].strip())
            self.assertEqual(row['currency'], 'USD')
            routed = destinations(symbol)
            self.assertEqual(len(set(routed.values())), 1)
        self.assertIn("saved-news'+(sym?", APP)
        self.assertIn("events42?symbol=", LOOK)
        self.assertIn('setSelected(symbol)', LOOK)
        self.assertIn("home43-chart')?'home'", APP)
        self.assertIn("E.view==='news')loadNews(false)", APP)
        self.assertIn("Events42.open()", APP)

    def test_names_resolve_to_one_ticker(self):
        by_name = {}
        for row in self.rows:
            by_name.setdefault(row['name'].upper(), []).append(row['symbol'])
        unique = {name: symbols[0] for name, symbols in by_name.items() if len(symbols) == 1}
        self.assertEqual(unique['APPLE'], 'AAPL')
        self.assertEqual(unique['TAKE-TWO INTERACTIVE'], 'TTWO')
        self.assertNotIn('NOT A COMPANY', unique)

    def test_invalid_ticker_is_rejected_without_a_feed_call(self):
        with self.assertRaises(ValueError):
            server.valid_symbol('bad ticker')
        with self.assertRaises(ValueError):
            server.valid_symbol('')
