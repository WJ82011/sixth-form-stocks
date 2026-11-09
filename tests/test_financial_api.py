"""SEC accounts are local reads unless explicitly refreshed; source links reach AI safely."""
import contextlib,importlib.util,json,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
import financials,sec_accounts
from test_financials import fixture,TODAY,NOW
spec=importlib.util.spec_from_file_location('financial_api_server',Path(__file__).parents[1]/'server.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class APITests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  for attr,name in [('USER_DIR',''),('DB_FILE','data.sqlite3'),('KEY_FILE','no-key'),('MASSIVE_KEY_FILE','no-massive-key')]:
   p=patch.object(s,attr,Path(self.tmp.name)/name);p.start();self.addCleanup(p.stop)
  s.init_storage()
 def save(self):
  r=financials.normalise_facts(fixture(),320193,{'cik':'320193','name':'Synthetic'},TODAY)
  with contextlib.closing(s.db_connection()) as con,con:
   con.execute('INSERT INTO sec_accounts VALUES(?,?,?)',('0000320193',json.dumps(r),NOW));con.execute('INSERT INTO sec_links VALUES(?,?)',('AAPL','0000320193'))
 def test_offline_health_and_mdi_evidence_need_no_provider_key(self):
  self.save()
  with patch.object(sec_accounts,'fetch_json',side_effect=AssertionError('No network on read')):
   r=s.handle_api('/api/financials',{'symbol':['AAPL']});self.assertEqual(r['fetchedAt'],NOW)
   d=s.handle_api('/api/intelligence',{'symbol':['AAPL']});self.assertIn('Revenue: USD 1,200',d['financial']['summary'])
   evidence=s.ai_evidence('AAPL','Is profit improving?');self.assertTrue(any(x['id']=='S1' for x in evidence['sources']))
   self.assertFalse(any('SHOULD-NOT' in x['body'] for x in evidence['sources']))
 def test_non_equity_intelligence_is_preserved(self):
  r=s.handle_api('/api/intelligence',{'symbol':['BINANCE:BTCUSDT']});self.assertIn('hour',r);self.assertIn('No supported annual',r['financial']['summary'])
 def test_same_issuer_comparison_rejected(self):
  self.save()
  with contextlib.closing(s.db_connection()) as con,con:con.execute('INSERT INTO sec_links VALUES(?,?)',('OTHER','0000320193'))
  with self.assertRaisesRegex(ValueError,'same SEC issuer'):s.handle_api('/api/financials/compare',{'symbols':['AAPL,OTHER']})
 def test_empty_and_duplicate_comparisons_rejected(self):
  for symbols in ('AAPL','AAPL,AAPL','AAPL,MSFT,TTWO,NVDA',''):
   with self.assertRaises(ValueError):s.handle_api('/api/financials/compare',{'symbols':[symbols]})
 def test_refresh_post_requires_local_header_and_origin(self):
  http=s.ThreadingHTTPServer(('127.0.0.1',0),s.AppHandler);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start();url='http://127.0.0.1:'+str(http.server_address[1])+'/api/financials/refresh'
  try:
   with patch.object(s,'sec_refresh',return_value={'status':'synthetic-test'}) as refresh:
    for headers in ({},{'X-MD-Request':'1','Origin':'https://example.com'}):
     with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(urllib.request.Request(url,data=b'{"symbol":"AAPL"}',headers=headers))
     self.assertEqual(e.exception.code,403)
    refresh.assert_not_called()
    with urllib.request.urlopen(urllib.request.Request(url,data=b'{"symbol":"AAPL"}',headers={'X-MD-Request':'1'})) as response:self.assertEqual(json.load(response)['status'],'synthetic-test')
    refresh.assert_called_once_with({'symbol':'AAPL'})
  finally:http.shutdown();http.server_close();thread.join(2)
