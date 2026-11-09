"""Saved briefing and refresh boundaries, with synthetic fixtures and no live data."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import desk
spec=importlib.util.spec_from_file_location('md_desk_server',Path(__file__).parents[1]/'server.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
NOW=1793790000000
class DeskTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  for attr,name in [('USER_DIR',''),('DB_FILE','prices.sqlite3'),('KEY_FILE','no-key'),('MASSIVE_KEY_FILE','no-massive-key')]:
   fix=patch.object(s,attr,Path(self.tmp.name)/name);fix.start();self.addCleanup(fix.stop)
  s.init_storage()
 def news(self,**changes):
  value={'headline':'Synthetic test headline','source':'Test publisher','url':'https://example.com/test','datetime':NOW//1000-60,'summary':'Body not retained','token':'DO-NOT-SAVE','image':'https://example.com/image'};value.update(changes);return value
 def test_news_filters_dates_links_and_keeps_only_headlines(self):
  invalid=[self.news(url='javascript:alert(1)'),self.news(url='https://name:secret@example.com'),self.news(datetime=NOW//1000+30),self.news(datetime=NOW//1000-8*86400),self.news(datetime=True),self.news(source=''),self.news(headline='')]
  rows=desk.news_rows([self.news(),*invalid],NOW)
  self.assertEqual(len(rows),1);self.assertEqual(set(rows[0]),{'headline','source','url','datetime'})
  self.assertNotIn('DO-NOT-SAVE',str(rows))
 def test_news_deduplicates_and_limits(self):
  rows=desk.news_rows([self.news(),self.news(datetime=NOW//1000-10),*[self.news(url=f'https://example.com/{i}') for i in range(100)]],NOW)
  self.assertEqual(len(rows),36);self.assertEqual(rows[0]['datetime'],NOW//1000-10)
 def test_saved_news_survives_reopen_and_preserves_fetch_time(self):
  with s.contextlib.closing(s.db_connection()) as con,con:
   self.assertTrue(desk.remember_news(con,'TTWO',[self.news()],NOW,NOW))
   self.assertFalse(desk.remember_news(con,'TTWO',[],NOW-1,NOW))
  with s.contextlib.closing(s.db_connection()) as con:
   saved=desk.read_news(con,['TTWO','AAPL'],NOW)
  self.assertEqual(saved['TTWO']['fetchedAt'],NOW);self.assertEqual(len(saved['TTWO']['items']),1);self.assertIsNone(saved['AAPL']['fetchedAt'])
 def test_get_snapshot_has_no_network_and_is_scoped_to_watchlist(self):
  with patch.object(s,'provider_get',side_effect=AssertionError('Network on saved read')),patch.object(s,'massive_request',side_effect=AssertionError('Network on saved read')):
   result=s.handle_api('/api/desk',{'symbols':['TTWO,AAPL']})
  self.assertEqual({x['symbol'] for x in result['rows']},{'TTWO','AAPL'});self.assertEqual(result['history']['TTWO']['daily']['count'],0)
  self.assertNotIn('token',result);self.assertNotIn('points',str(result['imports']))
 def test_quote_zero_change_is_preserved_in_snapshot(self):
  with s.contextlib.closing(s.db_connection()) as con,con:
   s.screening.remember(con,'TTWO','quote',{'c':100,'pc':100,'t':NOW//1000-100},NOW,NOW)
  with patch.object(s.time,'time',return_value=NOW/1000):result=s.desk_snapshot(['TTWO'])
  self.assertEqual(result['rows'][0]['change'],0)
 def test_history_metadata_never_fills_missing_dates(self):
  with s.contextlib.closing(s.db_connection()) as con,con:
   con.executemany('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)',[('TTWO',NOW-20*desk.DAY,10,11,9,10,100,NOW//1000),('TTWO',NOW-desk.DAY,12,13,11,12,100,NOW//1000)])
  info=s.desk_snapshot(['TTWO'])['history']['TTWO']['daily']
  self.assertEqual(info,{'count':2,'first':NOW-20*desk.DAY,'last':NOW-desk.DAY})
 def test_import_library_has_metadata_not_prices_or_secrets(self):
  s.change_imported_history({'symbol':'TTWO','csv':'Date,Close\n2020-01-02,10\n2025-01-02,20','source':'Synthetic test fixture','confirmed':True,'split_adjusted':False})
  result=s.desk_snapshot(['TTWO'])['imports'];self.assertEqual(result['total'],1);self.assertFalse(result['items'][0]['splitAdjusted']);self.assertNotIn('points',result['items'][0])
 def test_refresh_quote_batch_is_bounded_and_stops_on_failure(self):
  with self.assertRaises(ValueError):s.desk_refresh({'mode':'briefing','symbols':['AAPL']*9})
  with self.assertRaises(ValueError):s.desk_refresh({'mode':'company','symbols':['AAPL','TTWO']})
  failure={'items':[{'symbol':'AAPL','status':'error','code':429,'error':'Synthetic cooldown'}]}
  with patch.object(s,'handle_api',return_value=failure) as api:
   result=s.desk_refresh({'mode':'briefing','symbols':['AAPL']})
  api.assert_called_once_with('/api/quotes',{'symbols':['AAPL']});self.assertFalse(result['ok']);self.assertEqual(result['warnings'],['Synthetic cooldown'])
 def test_company_refresh_uses_one_profile_not_financial_metrics(self):
  def api(path,qs):
   return {'items':[{'symbol':'TTWO','status':'ok','quote':{'c':10,'pc':9,'t':NOW//1000}}]} if path=='/api/quotes' else {'items':[]}
  with patch.object(s,'handle_api',side_effect=api) as call,patch.object(s,'provider_get',return_value=({'name':'Test','ticker':'TTWO'},False)) as provider:
   result=s.desk_refresh({'mode':'company','symbols':['TTWO']})
  self.assertTrue(result['ok']);provider.assert_called_once_with('stock/profile2',{'symbol':'TTWO'},ttl=86400)
  self.assertEqual(call.call_args_list[-1].args,('/api/news',{'symbol':['TTWO']}))
  self.assertEqual(result['quotes'][0]['symbol'],'TTWO')
 def test_refresh_lock_and_local_post_enforcement(self):
  import threading,urllib.request,urllib.error
  s.DESK_REFRESH_LOCK.acquire()
  try:
   with self.assertRaises(ValueError):s.desk_refresh({'mode':'briefing','symbols':['TTWO']})
  finally:s.DESK_REFRESH_LOCK.release()
  http=s.ThreadingHTTPServer(('127.0.0.1',0),s.AppHandler);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  url='http://127.0.0.1:'+str(http.server_address[1])+'/api/desk/refresh'
  try:
   for headers in [{},{'X-MD-Request':'1','Origin':'https://example.com'}]:
    with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(urllib.request.Request(url,data=json.dumps({'mode':'briefing','symbols':['TTWO']}).encode(),headers=headers))
    self.assertEqual(error.exception.code,403)
  finally:http.shutdown();http.server_close();thread.join(2)
 def test_saved_daily_offline_read_needs_no_keys_or_external_calls(self):
  with s.contextlib.closing(s.db_connection()) as con,con:
   con.executemany('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)',[('TTWO',NOW-20*desk.DAY,10,11,9,10,100,NOW//1000),('TTWO',NOW-desk.DAY,12,13,11,12,100,NOW//1000)])
  with patch.object(s,'provider_get',side_effect=AssertionError('network')),patch.object(s,'massive_request',side_effect=AssertionError('network')):
   result=s.handle_api('/api/saved-daily',{'symbol':['TTWO'],'from':[str((NOW-30*desk.DAY)//1000)],'to':[str(NOW//1000)]})
  self.assertEqual(result['status'],'ok');self.assertTrue(result['cached']);self.assertEqual(result['candles']['c'],[10,12]);self.assertEqual(result['provider'],'massive')
 def test_saved_daily_invalid_range_and_missing_data(self):
  with self.assertRaises(ValueError):s.handle_api('/api/saved-daily',{'symbol':['TTWO'],'from':['0'],'to':['1']})
  result=s.handle_api('/api/saved-daily',{'symbol':['TTWO'],'from':['1700000000'],'to':['1793700000']})
  self.assertEqual(result['status'],'no_data');self.assertIsNone(result['candles'])
 def test_older_import_metadata_migrates_and_clear_keeps_library_consistent(self):
  payload={'source':'Old imported fixture','split_adjusted':True,'price_column':'Close','imported_at':NOW,'points':[{'t':NOW-10000,'p':10},{'t':NOW-1000,'p':20}]}
  with s.contextlib.closing(s.db_connection()) as con,con:
   con.execute('INSERT INTO imported_daily_history VALUES(?,?)',('TTWO',json.dumps(payload)))
   desk.init(con)
   self.assertEqual(desk.imports(con)['items'][0]['count'],2)
  s.change_imported_history({'symbol':'TTWO','clear':True})
  self.assertEqual(s.desk_snapshot(['TTWO'])['imports']['total'],0)
if __name__=='__main__':unittest.main()
