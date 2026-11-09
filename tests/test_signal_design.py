"""Lightweight contract checks for the additive Signal Edition design layer."""
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site'

class Inspector(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=[];self.nav=[];self.scripts=[];self.styles=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('id'):self.ids.append(a['id'])
        if tag=='button' and a.get('data-view'):self.nav.append(a['data-view'])
        if tag=='script' and a.get('src'):self.scripts.append(a['src'].split('?',1)[0])
        if tag=='link' and a.get('rel')=='stylesheet':self.styles.append(a.get('href').split('?',1)[0])

class SignalDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dom=Inspector();cls.dom.feed((SITE/'index.html').read_text())
    def test_all_workspaces_still_present(self):
        self.assertEqual(set(self.dom.nav),{'home','calendar','sources','learning','heatmap','crypto','screener','alerts','intelligence','overview','markets','tape','company','comparison','macro','accuracy','indicators','valuation','portfolio','forecast','news','research','reports','settings'})
        for n in self.dom.nav:self.assertIn('view-'+n,self.dom.ids)
    def test_features_preserve_required_anchors(self):
        for n in ('tape-quick-search','tape-quick-results','tape-symbol-list','tape-export','tape-reconnect','forecast-select','company-select','save-note','saved-notes','diagnostic-refresh','api-key','overview-chart','chart-expand','markets-table','ticker-track'):
            self.assertIn(n,self.dom.ids)
        self.assertEqual(len(self.dom.ids),len(set(self.dom.ids)),'Duplicate IDs can break stock selection')
    def test_additive_design_resources_are_local(self):
        self.assertTrue({'/signal.css','/tape.css','/styles.css'}<=set(self.dom.styles))
        self.assertTrue({'/signal.js','/market-hours.js','/app.js','/tape.js'}<=set(self.dom.scripts))
        for path in self.dom.styles+self.dom.scripts:
            self.assertTrue((SITE/path.lstrip('/')).exists(),path)
    def test_private_storage_strings_not_changed(self):
        server=(ROOT/'server.py').read_text()
        self.assertIn('.marketdesk-reborn',server)
        self.assertIn('finnhub_key',server)
        self.assertIn("'/signal.css':'signal.css'",server)
        self.assertIn("'/signal.js':'signal.js'",server)

if __name__=='__main__':unittest.main()
