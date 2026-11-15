"""New workspace backup + 1.7 local-only routes (no provider keys required)."""
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('md_server_v17',ROOT/'server.py')
s=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(s)
class ResearchV17Tests(unittest.TestCase):
 def test_report_backup_roundtrip_and_fields(self):
  report={'id':'abcd','symbol':'aapl','title':'Apple research','status':'Completed','summary':'Based on filings','business':'Consumer electronics',
  'financial':'Revenue cited with period','valuation':'PE assumption','catalysts':'Product launches','risks':'Competition','sources':'Company annual report',
  'checks':{'primary':True,'counter':True,'periods':True},'created':'2026-11-02','updated':'2026-11-02'}
  clean=s.normalise_workspace({'watch':['AAPL'],'reports':[report]})
  self.assertEqual(len(clean['reports']),1)
  self.assertEqual(clean['reports'][0]['symbol'],'AAPL')
  self.assertTrue(clean['reports'][0]['checks']['periods'])
  self.assertEqual(clean['reports'][0]['sources'],'Company annual report')
  self.assertEqual(s.normalise_workspace({'watch':[]})['reports'],[])
 def test_report_backup_rejects_secrets_and_bounds_size(self):
  record={'symbol':'AAPL','title':'x'*500,'summary':'x'*10000,'checks':['bad','input']}
  clean=s.normalise_workspace({'reports':[record]*80, 'finnhub_key':'SECRET','massive_key':'SECRET'})
  self.assertEqual(len(clean['reports']),40)
  self.assertLessEqual(len(clean['reports'][0]['title']),150)
  self.assertLessEqual(len(clean['reports'][0]['summary']),5000)
  self.assertNotIn('finnhub_key',clean)
  self.assertNotIn('massive_key',clean)
  self.assertFalse(clean['reports'][0]['checks']['primary'])
 def test_report_symbols_and_status_sanitised(self):
  clean=s.normalise_workspace({'reports':[{'symbol':'BAD/../PATH','title':'not okay'},{'symbol':'MSFT','status':'<script>'}]})
  self.assertEqual(len(clean['reports']),1)
  self.assertEqual(clean['reports'][0]['status'],'Draft')
 def test_static_assets_allowed_and_selftest_checks(self):
  source=(ROOT/'server.py').read_text()
  for asset in ['compare.js','reports.js','research-v17.css']:
   self.assertTrue((ROOT/'site'/asset).exists())
   self.assertIn("'/"+asset+"':'"+asset+"'",source)
   self.assertIn("'"+asset+"'",source)
 def test_version_and_nav(self):
  html=(ROOT/'site/index.html').read_text()
  self.assertIn('6.8.0',html)
  for view in ['comparison','reports']:
   self.assertIn('data-view="'+view+'"',html)
   self.assertIn('id="view-'+view+'"',html)
if __name__=='__main__':unittest.main()

class ResearchV17StaticTests(unittest.TestCase):
 def test_new_assets_reachable_with_correct_content_type(self):
  import threading, urllib.request
  from http.server import ThreadingHTTPServer
  httpd=ThreadingHTTPServer(('127.0.0.1',0),s.AppHandler)
  t=threading.Thread(target=httpd.serve_forever,daemon=True);t.start()
  try:
   port=httpd.server_address[1]
   for path,mime in [('/compare.js','text/javascript'),('/reports.js','text/javascript'),('/research-v17.css','text/css')]:
    with urllib.request.urlopen('http://127.0.0.1:'+str(port)+path,timeout=5) as resp:
     self.assertEqual(resp.status,200)
     self.assertIn(mime,resp.headers['Content-Type'])
     self.assertGreater(len(resp.read()),100)
  finally:
   httpd.shutdown();t.join(3);httpd.server_close()
