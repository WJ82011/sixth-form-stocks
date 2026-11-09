import contextlib,json,sqlite3,tempfile,time,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
import screening as f
import server as s
NOW=1793720000000
class ScreenerTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  for key,val in [('USER_DIR',Path(self.tmp.name)),('DB_FILE',Path(self.tmp.name)/'screen.sqlite3'),('KEY_FILE',Path(self.tmp.name)/'key')]:
   p=patch.object(s,key,val);p.start();self.addCleanup(p.stop)
  s.init_storage()
 def put(self,kind,body,symbol='AAPL',at=NOW):
  with contextlib.closing(s.db_connection()) as con,con:return f.remember(con,symbol,kind,body,at,NOW)
 def row(self,symbol='AAPL'):
  with contextlib.closing(s.db_connection()) as con:return f.rows(con,[{'symbol':symbol,'name':'Test Company','category':'Test','currency':'USD'}],[],NOW)['rows'][0]
 def quote(self,**extra):return dict(c=110,pc=100,t=NOW//1000,**extra)
 def test_price_change_is_from_same_quote_pair_not_untrusted_dp(self):
  self.put('quote',self.quote(dp=999));r=self.row();self.assertAlmostEqual(r['change'],10);self.assertEqual(r['quoteTime'],NOW)
 def test_missing_previous_close_is_missing_change_not_zero(self):
  self.put('quote',{'c':110,'t':NOW//1000});self.assertIsNone(self.row()['change']);self.assertEqual(self.row()['price'],110)
 def test_invalid_price_or_time_never_becomes_a_quote(self):
  for q in [{'c':True,'t':NOW//1000},{'c':float('nan'),'t':NOW//1000},{'c':100,'t':True},{'c':0,'t':NOW//1000},{'c':100,'t':NOW//1000+1000}]:self.assertFalse(self.put('quote',q))
 def test_keys_unknown_fields_and_nonfinite_metrics_are_not_saved(self):
  self.put('metrics',{'symbol':'AAPL','token':'SECRET','metric':{'peTTM':20,'secret':'SECRET','netProfitMarginTTM':float('inf'),'revenueGrowthTTMYoy':True}})
  with contextlib.closing(s.db_connection()) as con:
   text=con.execute('SELECT body FROM screen_snapshots').fetchone()[0];self.assertNotIn('SECRET',text);self.assertNotIn('Infinity',text)
  self.assertEqual(self.row()['pe'],20);self.assertIsNone(self.row()['growth'])
 def test_empty_refresh_does_not_make_old_figures_look_new(self):
  self.put('metrics',{'metric':{'peTTM':20}},at=NOW-1000);self.assertFalse(self.put('metrics',{'metric':{}}));self.assertEqual(self.row()['financialsFetchedAt'],NOW-1000)
 def test_older_retrieval_cannot_replace_newer_snapshot(self):
  self.put('metrics',{'metric':{'peTTM':20}});self.assertFalse(self.put('metrics',{'metric':{'peTTM':99}},at=NOW-1000));self.assertEqual(self.row()['pe'],20)
 def test_older_quote_time_cannot_replace_newer_quote(self):
  self.put('quote',self.quote(),at=NOW-1000);self.assertFalse(self.put('quote',{'c':99,'pc':98,'t':NOW//1000-100}));self.assertEqual(self.row()['price'],110)
 def test_mismatched_company_and_metric_symbols_are_rejected(self):
  self.assertFalse(self.put('profile',{'ticker':'MSFT','name':'Wrong'}));self.assertFalse(self.put('metrics',{'symbol':'MSFT','metric':{'peTTM':20}}))
 def test_unknown_or_future_retrieval_time_is_not_claimed(self):
  self.assertFalse(self.put('quote',self.quote(),at=None));self.assertFalse(self.put('quote',self.quote(),at=NOW+100000))
 def test_profile_filings_currency_does_not_convert_listing_price(self):
  self.put('profile',{'ticker':'AAPL','currency':'JPY','name':'Test'});self.put('quote',self.quote());r=self.row();self.assertEqual(r['listingCurrency'],'USD');self.assertEqual(r['filingCurrency'],'JPY');self.assertEqual(r['price'],110)
 def test_snapshots_survive_restart_and_report_no_inferred_financial_period(self):
  self.put('metrics',{'metric':{'peTTM':0,'revenueGrowthTTMYoy':-10,'netProfitMarginTTM':0}});s.init_storage();r=self.row();self.assertEqual(r['pe'],0);self.assertEqual(r['margin'],0);self.assertEqual(r['growth'],-10);self.assertIn('Not supplied',r['financialPeriod'])
 def test_snapshot_retention_is_bounded(self):
  with patch.object(f,'MAX_RECORDS',3):
   for i in range(5):self.put('quote',self.quote(),symbol='TEST'+str(i),at=NOW-i)
  with contextlib.closing(s.db_connection()) as con:self.assertEqual(con.execute('SELECT count(*) FROM screen_snapshots').fetchone()[0],3)
 def test_directory_plus_extra_symbols_and_limit_are_explicit(self):
  d=s.screen_data(['TEST','AAPL']);self.assertEqual(d['directoryCount'],221);self.assertEqual(len(d['rows']),222);self.assertFalse(next(x for x in d['rows'] if x['symbol']=='TEST')['inDirectory'])
  with self.assertRaises(ValueError):s.screen_data(['AAPL']*61)
  with self.assertRaises(ValueError):s.screen_data(['../etc'])
 def test_reading_the_screener_makes_no_provider_requests(self):
  with patch.object(s,'provider_get',side_effect=AssertionError('No network')):self.assertEqual(s.handle_api('/api/screener',{})['directoryCount'],221)
 def test_existing_quote_api_captures_real_source_pair(self):
  with patch.object(s,'provider_get',return_value=({'c':110,'pc':100,'t':int(time.time())},False)):s.handle_api('/api/quote',{'symbol':['AAPL']})
  with contextlib.closing(s.db_connection()) as con:self.assertEqual(f.snapshot(con,'AAPL','quote')[1]['pc'],100)
 def test_unknown_cached_timestamp_is_not_renewed(self):
  with patch.dict(s.CACHE,{},clear=True),patch.dict(s.CACHE_FETCHED_AT,{},clear=True):self.assertIsNone(s.screen_source_time('quote',{'symbol':'AAPL'},self.quote(),True))
 def test_cached_timestamp_is_preserved_exactly(self):
  q=self.quote();key=('quote',(('symbol','AAPL'),))
  with patch.dict(s.CACHE,{key:(0,q)}),patch.dict(s.CACHE_FETCHED_AT,{key:NOW-10000}):self.assertEqual(s.screen_source_time('quote',{'symbol':'AAPL'},q,True),NOW-10000)
 def test_refresh_is_three_existing_provider_requests(self):
  def provider(endpoint,params,**kwargs):
   return ({'quote':{'c':110,'pc':100,'t':int(time.time())},'stock/profile2':{'name':'Test','ticker':'AAPL','currency':'USD'},'stock/metric':{'symbol':'AAPL','metric':{'peTTM':20}}}[endpoint],False)
  with patch.object(s,'provider_get',side_effect=provider) as call:
   result=s.screen_refresh({'symbol':'AAPL'});self.assertFalse(result['stop']);self.assertEqual([x.args[0] for x in call.call_args_list],['quote','stock/profile2','stock/metric'])
  with contextlib.closing(s.db_connection()) as con:self.assertEqual(f.snapshot(con,'AAPL','metrics')[1]['metric']['peTTM'],20)
 def test_permission_or_rate_limit_stops_remaining_stock_requests(self):
  for code in [401,403,429]:
   with patch.object(s,'provider_get',side_effect=s.ProviderError(code,'Unavailable')) as call:
    result=s.screen_refresh({'symbol':'AAPL'});self.assertTrue(result['stop']);self.assertEqual(call.call_count,1)
 def test_partial_company_permission_failure_stops_the_batch(self):
  def provider(endpoint,params,**kwargs):
   if endpoint=='stock/metric':raise s.ProviderError(403,'Financial endpoint denied')
   return ({'c':110,'pc':100,'t':int(time.time())} if endpoint=='quote' else {'name':'Test','ticker':'AAPL'},False)
  with patch.object(s,'provider_get',side_effect=provider):
   result=s.screen_refresh({'symbol':'AAPL'});self.assertTrue(result['stop']);self.assertTrue(result['warnings'])
 def test_two_refreshes_cannot_run_together(self):
  s.SCREEN_REFRESH_LOCK.acquire()
  try:
   with self.assertRaises(ValueError):s.screen_refresh({'symbol':'AAPL'})
  finally:s.SCREEN_REFRESH_LOCK.release()
 def test_ai_can_reuse_saved_financials_with_original_timestamp(self):
  self.put('metrics',{'metric':{'peTTM':20}},at=NOW-1000)
  with patch.dict(s.CACHE,{},clear=True):
   stamp,body=s.ai_cache('stock/metric','AAPL');self.assertEqual(stamp,NOW-1000);self.assertEqual(body['metric']['peTTM'],20)
 def test_refresh_post_requires_local_header_and_origin(self):
  http=s.ThreadingHTTPServer(('127.0.0.1',0),s.AppHandler);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  try:
   with patch.object(s,'provider_get',side_effect=AssertionError('No network')):
    for headers in ({'Content-Type':'application/json'},{'Content-Type':'application/json','X-MD-Request':'1','Origin':'https://example.com'}):
     with self.assertRaises(urllib.error.HTTPError) as exc:urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:'+str(http.server_port)+'/api/screener/refresh',data=b'{"symbol":"AAPL"}',headers=headers))
     self.assertEqual(exc.exception.code,403)
  finally:http.shutdown();http.server_close();thread.join()
if __name__=='__main__':unittest.main()
