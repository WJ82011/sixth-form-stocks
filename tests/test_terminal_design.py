"""Professional Terminal v1.4.0: structural and trust invariants."""
import unittest
from pathlib import Path
from html.parser import HTMLParser
root=Path(__file__).resolve().parents[1]
site=root/'site'
class Inspect(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.files=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.append(a['id'])
        if tag=='script' and a.get('src'):self.files.append(a['src'].split('?',1)[0])
        if tag=='link' and a.get('href'):self.files.append(a['href'].split('?',1)[0])
class TerminalEditionTests(unittest.TestCase):
    def test_unique_dom_ids_and_new_dashboard(self):
        inspector=Inspect();inspector.feed((site/'index.html').read_text())
        self.assertEqual(len(inspector.ids),len(set(inspector.ids)))
        wanted={'pro-console','pro-chart-mount','pro-ops-watch','pro-cross-body','pro-quote-strip','pro-focus-fields','pro-research-wire','pro-focus-source','edition-pro','edition-signal','main-chart-panel','tape-quick-search','forecast-select','company-select','save-note','diagnostic-refresh'}
        self.assertLessEqual(wanted,set(inspector.ids))
        loader=(site/'view-loader.js').read_text()
        self.assertIn('/terminal.js',loader)
        self.assertIn('/view-loader.js',inspector.files)
        self.assertIn('/terminal.css',inspector.files)
    def test_rendered_resources_are_local_only(self):
        s=(root/'server.py').read_text()
        for file in ['terminal.css','terminal.js']:
            self.assertIn(f"'/{file}':'{file}'",s)
            self.assertIn(f"'{file}':",s)
    def test_no_extra_provider_requests_or_synthetic_market_values(self):
        s=(site/'terminal.js').read_text()
        self.assertNotIn('fetch(',s)
        self.assertNotIn('new WebSocket(',s)
        self.assertIn('quoteFor(sym)',s)
        self.assertIn('E.quotes.get(sym)',s)
        self.assertIn('E.trades.get(sym)',s)
        self.assertIn("'NO DATA'",s)
        self.assertIn('validHttpLink(item.url)',s)
    def test_data_quality_preserved_after_reliability_fixes(self):
        app=(site/'app.js').read_text()
        server=(root/'server.py').read_text()
        self.assertIn('valid_provider_quote',server)
        self.assertIn('finnhub_websocket_trade',server)
        self.assertIn('finnhub_websocket',app)
        self.assertIn('No recorded prices are available for this period.',app)
        self.assertIn('FINNHUB HISTORICAL DAILY CLOSES',app)
        self.assertIn('Never splice locally recorded minute-level observations into historical DAILY',app)
