"""V3 data boundaries, backup validation and source-aware cached API paths."""
import contextlib,importlib.util,json,sqlite3,tempfile,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
import lab3,workspace3,sec_accounts,macro3
spec=importlib.util.spec_from_file_location('v3_test_server',Path(__file__).parents[1]/'server.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class V3APITests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  for attr,name in [('USER_DIR',''),('DB_FILE','data.sqlite3'),('WORKSPACE_FILE','workspace.json'),('KEY_FILE','no-key'),('MASSIVE_KEY_FILE','no-massive-key')]:
   p=patch.object(s,attr,Path(self.tmp.name)/name);p.start();self.addCleanup(p.stop)
  s.init_storage()
 def test_all_new_reads_are_local(self):
  with patch.object(sec_accounts,'fetch_json',side_effect=AssertionError('No network')),patch.object(macro3,'fetch',side_effect=AssertionError('No network')):
   for path in ('state','overview','events','listings','screen','macro','sources','statements'):
    result=s.handle_api('/api/v3/'+path,{});self.assertIsInstance(result,dict)
 def test_empty_portfolio_is_not_seeded_with_demo_money(self):
  d=lab3.post('/api/v3/calculate',{'state':{}},vars(s));self.assertEqual(d['portfolio']['cashUSD'],0);self.assertEqual(d['state']['ledger'],[])
 def test_v3_backup_roundtrip_and_unknown_fields_removed(self):
  state=workspace3.mutate({},'focus',{'text':'Synthetic research question'});state['token']='DO-NOT-SAVE';s.write_workspace({'watch':['AAPL'],'v3':state});clean=s.read_workspace()['snapshot']['v3'];self.assertEqual(clean['researchFocus'],'Synthetic research question');self.assertNotIn('token',clean)
 def test_invalid_v3_does_not_replace_research_backup(self):
  s.write_workspace({'watch':['AAPL'],'notes':[{'title':'Keep this note'}]});before=s.WORKSPACE_FILE.read_bytes()
  with self.assertRaises(ValueError):s.write_workspace({'watch':['MSFT'],'v3':{'ledger':[{'kind':'SELL'}]}})
  self.assertEqual(s.WORKSPACE_FILE.read_bytes(),before)
 def test_old_backup_still_loads_with_v3_defaults(self):
  r=s.normalise_workspace({'watch':['TTWO']});self.assertEqual(r['watch'],['TTWO']);self.assertEqual(r['v3']['ledger'],[])
 def test_layout_whitelist_and_hidden_modules(self):
  r=workspace3.normalise({'home':{'order':['research','unknown','research'],'hidden':['portfolio','unknown']}});self.assertEqual(r['home']['order'][0],'research');self.assertEqual(r['home']['hidden'],['portfolio']);self.assertEqual(len(r['home']['order']),5)
 def test_no_provider_quote_relabelled_with_wrong_currency(self):
  ledger=[{'id':'d','date':'2025-01-01','kind':'DEPOSIT','amount':1000,'source':'Synthetic'},{'id':'b','date':'2025-01-01','kind':'BUY','symbol':'AAA','quantity':1,'price':10,'currency':'GBP','fx':1.2,'fxSource':'Synthetic FX','source':'Synthetic'}]
  with patch.object(s,'screen_data',return_value={'rows':[]}) as screen:
   d=lab3.post('/api/v3/marks-from-quotes',{'state':{'ledger':ledger}},vars(s));self.assertEqual(d['added'],[]);screen.assert_called_once_with([])
 def test_chart_compare_only_shared_observed_dates(self):
  with contextlib.closing(s.db_connection()) as c,c:
   for sym,prices in [('AAA',[(1609459200000,10),(1609545600000,20),(1609632000000,30)]),('BBB',[(1609459200000,20),(1609632000000,30)])]:
    c.executemany('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)',[(sym,t,p,p,p,p,0,1) for t,p in prices])
  d=s.handle_api('/api/v3/chart-compare',{'symbols':['AAA,BBB']});self.assertEqual(len(d['dates']),2);self.assertEqual(d['rows'][0]['points'][0]['index'],100);self.assertEqual(d['rows'][1]['points'][-1]['index'],150)
 def test_macro_cache_preserves_original_retrieval_time(self):
  r=macro3.parse('UNRATE','DATE,UNRATE\n2026-09-01,4.2');now=int(s.time.time()*1000);lab3.remember(vars(s),'macro:UNRATE',r,now)
  with patch.object(macro3,'fetch',side_effect=AssertionError('No repeat fetch')):d=lab3.post('/api/v3/macro-refresh',{'id':'UNRATE'},vars(s))
  self.assertEqual(d['fetchedAt'],now);self.assertTrue(d['cached'])
 def test_new_posts_require_same_origin_header(self):
  http=s.ThreadingHTTPServer(('127.0.0.1',0),s.AppHandler);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start();url='http://127.0.0.1:'+str(http.server_address[1])+'/api/v3/calculate'
  try:
   with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(urllib.request.Request(url,data=b'{"state":{}}'))
   self.assertEqual(e.exception.code,403)
   with urllib.request.urlopen(urllib.request.Request(url,data=b'{"state":{}}',headers={'X-MD-Request':'1'})) as response:self.assertEqual(json.load(response)['state']['version'],3)
  finally:http.shutdown();http.server_close();thread.join(2)
