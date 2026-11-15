"""Structural and trust-contract checks for the Professional Edition layer."""
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site'
class Inspector(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.scripts=[];self.styles=[]
    def handle_starttag(self,tag,attrs):
        x=dict(attrs)
        if x.get('id'):self.ids.append(x['id'])
        if tag=='script' and x.get('src'):self.scripts.append(x['src'].split('?',1)[0])
        if tag=='link' and x.get('rel')=='stylesheet':self.styles.append(x['href'].split('?',1)[0])
class ProfessionalDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inspector=Inspector();cls.inspector.feed((SITE/'index.html').read_text())
    def test_edition_controls_present(self):
        ids=set(self.inspector.ids)
        required={'edition-signal','edition-pro','pref-density','pref-chart-height','pref-contrast','pref-ticker','pref-motion','preferences-reset','pro-overview-metrics','pro-matrix-body','pro-tape-metrics','pref-colour-options','preferences-feedback','pro-matrix-sort'}
        self.assertTrue(required <= ids,required-ids)
        self.assertEqual(len(self.inspector.ids),len(ids),'Duplicate IDs can break UI selection')
    def test_existing_features_and_assets_preserved(self):
        required={'tape-quick-search','tape-canvas','company-select','forecast-select','save-note','diagnostic-refresh','api-key','overview-chart','markets-table','ticker-track','command-overlay'}
        self.assertTrue(required<=set(self.inspector.ids))
        loader=(SITE/'view-loader.js').read_text()
        for script in ('/market-hours.js','/chart-research.js','/app.js','/tape.js','/signal.js','/pro.js','/terminal.js','/compare.js','/reports.js'):
            self.assertIn(script,loader)
        self.assertIn('/view-loader.js',self.inspector.scripts)
        self.assertTrue({'/styles.css','/signal.css','/pro.css','/terminal.css'} <= set(self.inspector.styles))
        self.assertIn('/tape.css',loader)
    def test_local_server_serves_new_files(self):
        server=(ROOT/'server.py').read_text()
        for file in ['pro.js','pro.css']:
            self.assertIn(f"'/{file}':'{file}'",server)
            self.assertIn(f"'{file}':",server)
    def test_no_new_network_or_faked_provider_data(self):
        content=(SITE/'pro.js').read_text()
        self.assertNotRegex(content,r'(?<![a-z])fetch\s*\(')
        self.assertNotIn('WebSocket(',content)
        self.assertIn('E.quotes.get(sym)',content)
        self.assertIn('E.trades.get(sym)',content)
        self.assertIn('T.events.filter(',content)
    def test_source_integrity_rules_still_present(self):
        app=(SITE/'app.js').read_text()
        tape=(SITE/'tape.js').read_text()
        self.assertIn('FINNHUB QUOTE',app)
        self.assertIn('STALE FINNHUB QUOTE',app)
        self.assertIn('trade.v>0',tape)
        self.assertIn("'/api/tape?symbol='",tape)
if __name__=='__main__':unittest.main()
