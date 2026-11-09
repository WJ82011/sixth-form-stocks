"""Failure injection and generated cases. All state/market fixtures are synthetic."""
import concurrent.futures,contextlib,copy,datetime as dt,http.client,importlib.util,json,os,random,sqlite3,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
import portfolio3 as p,workspace3 as w,events3
spec=importlib.util.spec_from_file_location('v31_server',Path(__file__).parents[1]/'server.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class PrivateCase(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.home=Path(self.tmp.name)
  for name,value in [('USER_DIR',self.home),('DB_FILE',self.home/'data.sqlite3'),('WORKSPACE_FILE',self.home/'workspace.json'),('KEY_FILE',self.home/'no-key'),('MASSIVE_KEY_FILE',self.home/'no-massive')]:
   x=patch.object(s,name,value);x.start();self.addCleanup(x.stop)
  s.init_storage()
class RecoveryTests(PrivateCase):
 def test_corrupt_primary_recovers_previous_without_deleting_evidence(self):
  s.write_workspace({'notes':[{'title':'First valid generation'}]});s.write_workspace({'notes':[{'title':'Second generation'}]});s.WORKSPACE_FILE.write_bytes(b'{interrupted')
  result=s.read_workspace();self.assertTrue(result['recovered']);self.assertEqual(result['snapshot']['notes'][0]['title'],'First valid generation');self.assertEqual(s.WORKSPACE_FILE.read_bytes(),b'{interrupted');self.assertTrue(result['warning'])
  s.write_workspace({'notes':[{'title':'Reviewed recovery'}]});self.assertEqual(s.WORKSPACE_FILE.with_suffix('.damaged.json').read_bytes(),b'{interrupted');self.assertEqual(s.WORKSPACE_FILE.with_suffix('.previous.json').stat().st_mode&0o777,0o600)
  self.assertEqual(s.read_workspace()['snapshot']['notes'][0]['title'],'Reviewed recovery')
 def test_disk_full_fsync_failure_keeps_primary(self):
  s.write_workspace({'notes':[{'title':'Keep'}]});before=s.WORKSPACE_FILE.read_bytes()
  with patch.object(s.os,'fsync',side_effect=OSError('Synthetic disk full')):
   with self.assertRaises(OSError):s.write_workspace({'notes':[{'title':'Uncommitted'}]})
  self.assertEqual(s.WORKSPACE_FILE.read_bytes(),before);self.assertFalse(list(self.home.glob('*.tmp')))
 def test_replace_failure_keeps_primary(self):
  s.write_workspace({'watch':['AAPL']});before=s.WORKSPACE_FILE.read_bytes();original=s.os.replace
  def fail_primary(a,b):
   if b==s.WORKSPACE_FILE:raise OSError('Synthetic interrupted replace')
   return original(a,b)
  with patch.object(s.os,'replace',side_effect=fail_primary):
   with self.assertRaises(OSError):s.write_workspace({'watch':['TTWO']})
  self.assertEqual(s.WORKSPACE_FILE.read_bytes(),before);self.assertFalse(list(self.home.glob('*.tmp')))
 def test_malformed_backup_shapes_do_not_crash_reader(self):
  for value in (None,[],True,7,'text',{}, {'snapshot':[]},{'snapshot':{},'updated_at':float('inf')},{'snapshot':{},'updated_at':True}):
   with self.subTest(value=value):s.WORKSPACE_FILE.write_text(json.dumps(value));self.assertIsNone(s.read_workspace()['snapshot'])
 def test_oversized_existing_backup_not_replaced(self):
  s.WORKSPACE_FILE.write_bytes(b'x'*2500001)
  with self.assertRaises(ValueError):s.write_workspace({})
  self.assertEqual(s.WORKSPACE_FILE.stat().st_size,2500001)
 def test_parallel_saves_and_reads_remain_complete(self):
  def writer(i):s.write_workspace({'notes':[{'title':'Generation '+str(i),'thesis':'x'*4000}]});return s.read_workspace()
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(writer,range(80)))
  self.assertTrue(all(x['snapshot']['notes'][0]['title'].startswith('Generation ') for x in results));self.assertIsNotNone(s.read_workspace()['snapshot']);self.assertFalse(list(self.home.glob('*.tmp')))
  self.assertIsInstance(json.loads(s.WORKSPACE_FILE.with_suffix('.previous.json').read_text()),dict)
 def test_database_busy_does_not_erase_records(self):
  s.store_point('AAA',int(time.time()*1000)-1000,10,'finnhub_quote')
  with contextlib.closing(s.db_connection()) as reader:self.assertEqual(reader.execute('PRAGMA quick_check').fetchone()[0],'ok')
  s.init_storage();self.assertEqual(s.get_history('AAA')[0]['p'],10)
class BoundaryTests(PrivateCase):
 def test_inconsistent_finnhub_ohlc_rejected(self):
  t=int(time.time())-86400;base={'s':'ok','t':[t],'o':[10],'h':[12],'l':[8],'c':[11],'v':[100]};self.assertTrue(s.valid_provider_candles(base))
  for key,value in [('o',13),('c',7),('v',1e14),('h',True),('t',t+.5)]:
   with self.subTest(key=key):bad=copy.deepcopy(base);bad[key]=[value];self.assertFalse(s.valid_provider_candles(bad))
 def test_fractional_trade_timestamps_not_truncated(self):
  t=int(time.time()*1000)-1000
  self.assertEqual(s.store_points_batch([{'s':'AAA','p':10,'t':t+.5,'v':1}]),0);self.assertEqual(s.get_history('AAA'),[])
 def test_mutation_wrong_shapes_fail_without_modifying_state(self):
  original=w.normalise({})
  for action,key in [('mark.add','mark'),('event.add','event'),('legacy.import','portfolio')]:
   for value in [None,[],True,7,'bad']:
    with self.subTest(action=action,value=value):
     with self.assertRaises((ValueError,TypeError)):w.mutate(original,action,{key:value})
     self.assertEqual(original,w.normalise({}))
 def test_timezone_paths_rejected_as_validation_errors(self):
  for zone in ('../etc','/tmp','', 'Not/AZone'):
   with self.subTest(zone=zone):
    with self.assertRaises(ValueError):events3.normalise([{'id':'e','title':'Synthetic','date':'2025-01-01','zone':zone,'source':'Synthetic'}])
 def test_full_capacity_workspace_roundtrip(self):
  ledger=[{'id':'d'+str(i),'kind':'DEPOSIT','amount':1,'date':'2025-01-01','source':'Synthetic capacity fixture'} for i in range(750)]
  state=w.normalise({'ledger':ledger});s.write_workspace({'v3':state});self.assertEqual(len(s.read_workspace()['snapshot']['v3']['ledger']),750)
  with self.assertRaises(ValueError):w.normalise({'ledger':ledger+[dict(ledger[-1],id='overflow')]})
 def test_parallel_price_storage_and_restart(self):
  t=int(time.time()*1000)-10000
  def batch(i):return s.store_points_batch([{'s':'AAA','t':t+i*100+j,'p':10+i,'v':j%2} for j in range(100)])
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:self.assertEqual(sum(pool.map(batch,range(20))),2000)
  s.init_storage();self.assertEqual(len(s.get_history('AAA',0,5000)),2000)
  with contextlib.closing(s.db_connection()) as c:self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok');self.assertEqual(c.execute('SELECT count(*) FROM tape_events').fetchone()[0],2000)
class GeneratedAccountingTests(unittest.TestCase):
 def test_fifo_cash_conservation_250_seeded_ledgers(self):
  rng=random.Random(310)
  for i in range(250):
   with self.subTest(seed=i):
    quantity=rng.randint(2,100);sold=rng.randint(1,quantity);buy=rng.randint(1,200);sell=rng.randint(1,300);fee=rng.randint(0,5);capital=100000
    ledger=[{'id':'d','date':'2025-01-01','kind':'DEPOSIT','amount':capital,'source':'Synthetic'}, {'id':'b','date':'2025-01-02','kind':'BUY','symbol':'AAA','quantity':quantity,'price':buy,'fee':fee,'source':'Synthetic'}, {'id':'s','date':'2025-01-03','kind':'SELL','symbol':'AAA','quantity':sold,'price':sell,'fee':fee,'source':'Synthetic'}]
    result=p.calculate(ledger,[{'symbol':'AAA','date':'2025-01-04','price':sell,'source':'Synthetic'}],as_of='2025-01-04')
    expected=capital-quantity*buy-fee+sold*sell-fee+(quantity-sold)*sell
    self.assertAlmostEqual(result['totalValueUSD'],expected,places=6);self.assertAlmostEqual(result['gainAfterCashFlowsUSD'],quantity*(sell-buy)-2*fee,places=6)
    self.assertEqual(w.normalise({'ledger':ledger}),w.normalise(w.normalise({'ledger':ledger})))
 def test_250_external_cashflows_do_not_create_performance(self):
  rng=random.Random(311)
  for i in range(250):
   with self.subTest(seed=i):
    ledger=[{'id':'d','kind':'DEPOSIT','amount':10000,'date':'2025-01-01','source':'Synthetic'},{'id':'flow','kind':rng.choice(['DEPOSIT','WITHDRAW']),'amount':rng.randint(1,1000),'date':'2025-01-05','source':'Synthetic'}]
    a=p.checkpoint(ledger,[],'2025-01-01');b=p.checkpoint(ledger,[],'2025-01-10');self.assertEqual(p.performance(ledger,[a,b],[])['modifiedDietzPct'],0)
class HTTPFailures(PrivateCase):
 def setUp(self):
  super().setUp();self.http=s.ThreadingHTTPServer(('127.0.0.1',0),s.AppHandler);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start();self.addCleanup(self.stop)
 def stop(self):self.http.shutdown();self.http.server_close();self.thread.join(2)
 def request(self,path,body,headers=None):
  c=http.client.HTTPConnection('127.0.0.1',self.http.server_address[1],timeout=5)
  try:c.request('POST',path,body,{'X-MD-Request':'1','Content-Type':'application/json',**(headers or {})});r=c.getresponse();return r.status,json.loads(r.read())
  finally:c.close()
 def test_all_mutating_routes_reject_non_object_json(self):
  routes=('/api/token','/api/massive-token','/api/ticks','/api/workspace','/api/alerts','/api/ai/ask','/api/desk/refresh','/api/screener/refresh','/api/financials/refresh','/api/imported-history','/api/v3/calculate')
  for route in routes:
   for body in ('null','[]','true','1','"text"','{"value":NaN}','{broken'):
    with self.subTest(route=route,body=body):status,result=self.request(route,body);self.assertEqual(status,400);self.assertIn('error',result)
 def test_bad_v3_shapes_return_400_and_server_stays_alive(self):
  for obj in [{'state':[]},{'state':{},'action':'event.add','event':None},{'state':{},'action':'mark.add','mark':None},{'state':{},'action':'legacy.import','portfolio':None}]:
   with self.subTest(obj=obj):self.assertEqual(self.request('/api/v3/calculate',json.dumps(obj))[0],400)
  self.assertEqual(self.request('/api/v3/calculate','{"state":{}}')[0],200)
 def test_parallel_valid_requests_keep_server_responsive(self):
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(lambda _:self.request('/api/v3/calculate','{"state":{}}')[0],range(80)))
  self.assertEqual(results,[200]*80)
class AdditionalFailureTests(PrivateCase):
 def test_batch_database_failure_rolls_back_all_records(self):
  t=int(time.time()*1000)-1000
  with patch.object(s.price_alerts,'observe',side_effect=sqlite3.OperationalError('Synthetic write interruption')):
   with self.assertRaises(sqlite3.OperationalError):s.store_points_batch([{'s':'AAA','p':10,'t':t,'v':2},{'s':'AAA','p':11,'t':t+1,'v':3}])
  self.assertEqual(s.get_history('AAA'),[])
  with contextlib.closing(s.db_connection()) as c:self.assertEqual(c.execute('SELECT count(*) FROM tape_events').fetchone()[0],0)
 def test_abandoned_partial_temp_file_not_loaded(self):
  s.write_workspace({'notes':[{'title':'Committed'}]});s.WORKSPACE_FILE.with_suffix('.json.tmp').write_text('{interrupted')
  self.assertEqual(s.read_workspace()['snapshot']['notes'][0]['title'],'Committed');s.write_workspace({'notes':[{'title':'Next commit'}]});self.assertFalse(s.WORKSPACE_FILE.with_suffix('.json.tmp').exists())
 def test_corrupted_cached_bar_withheld_without_deleting_database(self):
  t=int(time.time())-86400
  with contextlib.closing(s.db_connection()) as c,c:c.execute('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)',('AAA',t*1000,10,12,8,1000,1,t))
  self.assertIsNone(s.read_massive_daily_bars('AAA',t-86400,t+86400))
  with contextlib.closing(s.db_connection()) as c:self.assertEqual(c.execute('SELECT count(*) FROM massive_daily_bars').fetchone()[0],1)
 def test_storage_pruning_is_per_symbol(self):
  t=int(time.time()*1000)-20000
  s.store_point('BBB',t,20,'finnhub_quote')
  for start in range(0,5400,150):s.store_points_batch([{'s':'AAA','t':t+j,'p':10,'v':0} for j in range(start,start+150)])
  self.assertEqual(len(s.get_history('AAA',0,5000)),5000);self.assertEqual(len(s.get_history('BBB')),1)
 def test_repeated_duplicate_observations_do_not_grow_chart_history(self):
  t=int(time.time()*1000)-1000
  for _ in range(50):s.store_points_batch([{'s':'AAA','p':10,'t':t,'v':0}])
  self.assertEqual(len(s.get_history('AAA')),1)
class GeneratedSourceChecks(unittest.TestCase):
 def test_100_cumulative_statement_sets_reconcile_without_gap_filling(self):
  import statements3
  from test_v3_statements import raw,books
  rng=random.Random(312)
  for i in range(100):
   with self.subTest(seed=i):
    quarters=[rng.randint(1,10000) for _ in range(4)];r=raw()
    for tag in r['facts']['us-gaap'].values():
     total=0
     for q,row in zip(quarters,tag['units']['USD']):total+=q;row['val']=total
    b=books(r)[0];self.assertEqual(b['ttmWithDerived'][-1]['metrics']['revenue']['value'],sum(quarters))
    r['facts']['us-gaap']['RevenueFromContractWithCustomerExcludingAssessedTax']['units']['USD'].pop(1)
    b=books(r)[0]
    self.assertFalse(b['ttmWithDerived'] and 'revenue' in b['ttmWithDerived'][-1]['metrics'])
 def test_100_invented_ai_numbers_and_quotes_are_rejected(self):
  import research_ai as a
  source={'id':'D1','title':'Synthetic','body':'Synthetic reported revenue of 120 million USD.','kind':'user source','url':'https://example.com/filing'}
  packet=a.packet('AAA',[source],int(time.time()*1000),'Check synthetic source')
  for i in range(100):
   with self.subTest(case=i):
    draft={'title':'Synthetic check','sections':[{'heading':'Revenue','bullets':[{'kind':'fact','text':'Revenue was '+str(90000+i)+' million USD.','evidence':[{'id':'D1','excerpt':'revenue of 120 million USD'}]}]}],'missing':[]}
    with self.assertRaises(a.AIError):a.verify(draft,packet)
    draft['sections'][0]['bullets'][0].update(text='Revenue was 120 million USD.',evidence=[{'id':'D1','excerpt':'Synthetic fabricated source phrase '+str(i)}])
    with self.assertRaises(a.AIError):a.verify(draft,packet)
class SymbolValidation(unittest.TestCase):
 def test_non_text_symbols_cannot_become_none_or_true_assets(self):
  for value in (None,True,False,123,[],{}):
   with self.subTest(value=value):
    with self.assertRaises(ValueError):s.valid_symbol(value)
    with self.assertRaises(ValueError):p.symbol(value)
class CachedTimestampChecks(PrivateCase):
 def test_invalid_cached_timestamp_withheld_as_unusable_history(self):
  for stamp in ('damaged-timestamp',1,-1,9999999999999999):
   with self.subTest(stamp=stamp):
    with contextlib.closing(s.db_connection()) as c,c:
     c.execute('DELETE FROM massive_daily_bars');c.execute('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)',('AAA',stamp,10,12,8,11,1,1))
    self.assertIsNone(s.read_massive_daily_bars('AAA',0,10000000000000))
