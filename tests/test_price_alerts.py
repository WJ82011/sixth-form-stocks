import concurrent.futures
import contextlib
import importlib
import json
import sqlite3
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server as s
import price_alerts as a
NOW=1793700000000

class PriceAlertsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.now=NOW
  for key,value in [('USER_DIR',Path(self.tmp.name)),('DB_FILE',Path(self.tmp.name)/'db.sqlite3'),('KEY_FILE',Path(self.tmp.name)/'key'),('MASSIVE_KEY_FILE',Path(self.tmp.name)/'massive-key'),('WORKSPACE_FILE',Path(self.tmp.name)/'workspace.json')]:
   p=patch.object(s,key,value);p.start();self.addCleanup(p.stop)
  p=patch.object(s.time,'time',side_effect=lambda:self.now/1000);p.start();self.addCleanup(p.stop);s.init_storage()
 def create(self,direction='above',target=100,symbol='AAPL'):
  return s.change_alerts(dict(action='create',symbol=symbol,direction=direction,target=target,unit='USD'))['id']
 def state(self):return s.read_alerts()
 def observe(self,price=110,offset=1000,source='finnhub_quote'):
  self.now=NOW+offset;return s.store_point('AAPL',self.now,price,source)
 def test_above_equal_and_below_equal(self):
  self.create();self.create('below');self.observe(100);self.assertEqual(len(self.state()['events']),2)
 def test_first_qualifying_observation_no_cross_required(self):
  self.create();self.observe(110);d=self.state();self.assertEqual(d['alerts'][0]['status'],'triggered');self.assertEqual(d['events'][0]['price'],110)
 def test_non_matching_price_updates_last_seen(self):
  self.create();self.observe(90);d=self.state();self.assertEqual(d['alerts'][0]['last_price'],90);self.assertEqual(d['events'],[])
 def test_duplicate_and_repeated_matches_trigger_once(self):
  self.create();self.observe();self.observe();self.observe(130,2000);self.assertEqual(len(self.state()['events']),1)
 def test_new_arm_requires_new_price(self):
  ident=self.create();self.observe();self.now=NOW+2000;s.change_alerts({'action':'rearm','id':ident});s.store_point('AAPL',NOW+1000,120,'finnhub_quote');self.assertEqual(len(self.state()['events']),1);self.observe(120,3000);self.assertEqual(len(self.state()['events']),2);self.assertEqual(self.state()['events'][0]['arm'],2)
 def test_pause_prevents_trigger(self):
  ident=self.create();s.change_alerts({'action':'pause','id':ident});self.observe();self.assertEqual(self.state()['events'],[])
 def test_pause_after_trigger_does_not_erase_triggered_state(self):
  ident=self.create();self.observe();s.change_alerts({'action':'pause','id':ident});self.assertEqual(self.state()['alerts'][0]['status'],'triggered')
 def test_rearm_armed_is_idempotent(self):
  ident=self.create();self.now+=1000;s.change_alerts({'action':'rearm','id':ident});self.assertEqual(self.state()['alerts'][0]['arm'],1);self.assertEqual(self.state()['alerts'][0]['armed_at'],NOW)
 def test_edit_rearms_and_keeps_history(self):
  ident=self.create();self.observe();self.now=NOW+2000;s.change_alerts(dict(action='update',id=ident,symbol='AAPL',direction='below',target=80,unit='USD'));self.observe(70,3000);d=self.state();self.assertEqual(len(d['events']),2);self.assertEqual(d['events'][1]['target'],100);self.assertEqual(d['events'][0]['target'],80)
 def test_delete_keeps_trigger_snapshot(self):
  ident=self.create();self.observe();s.change_alerts({'action':'delete','id':ident});d=self.state();self.assertEqual(d['alerts'],[]);self.assertEqual(d['events'][0]['symbol'],'AAPL');self.assertEqual(d['events'][0]['target'],100)
 def test_stale_data_is_skipped(self):
  self.create();self.now=NOW+600000;s.store_point('AAPL',NOW+1000,110,'finnhub_quote');self.assertEqual(self.state()['events'],[])
 def test_before_arming_is_skipped_even_if_recent(self):
  self.create();self.now+=1000;s.store_point('AAPL',NOW-1000,110,'finnhub_quote');self.assertEqual(self.state()['events'],[])
 def test_future_provider_time_is_skipped(self):
  self.create();s.store_point('AAPL',NOW+1000,110,'finnhub_quote');self.assertEqual(self.state()['events'],[])
 def test_out_of_order_price_is_skipped(self):
  self.create();self.observe(90,2000);s.store_point('AAPL',NOW+1000,120,'finnhub_quote');self.assertEqual(self.state()['events'],[]);self.assertEqual(self.state()['alerts'][0]['last_price'],90)
 def test_daily_and_zero_size_stream_sources_do_not_trigger(self):
  self.create();self.observe(110,1000,'massive_daily');self.observe(110,2000,'finnhub_websocket_update');self.assertEqual(self.state()['events'],[])
 def test_positive_size_websocket_trade_triggers(self):
  self.create();self.now+=1000;s.store_points_batch([{'s':'AAPL','t':self.now,'p':110,'v':2}]);self.assertEqual(self.state()['events'][0]['source'],'finnhub_websocket_trade')
 def test_zero_size_websocket_update_does_not_trigger(self):
  self.create();self.now+=1000;s.store_points_batch([{'s':'AAPL','t':self.now,'p':110,'v':0}]);self.assertEqual(self.state()['events'],[])
 def test_other_symbol_does_not_trigger(self):
  self.create();self.now+=1000;s.store_point('MSFT',self.now,110,'finnhub_quote');self.assertEqual(self.state()['events'],[])
 def test_restart_keeps_settings_history_and_revision(self):
  self.create();self.observe();before=self.state();s.init_storage();self.assertEqual(before,self.state())
 def test_gap_checks_only_new_observation(self):
  self.create();self.now=NOW+8*3600000;s.store_point('AAPL',self.now-1000,120,'finnhub_quote');event=self.state()['events'][0];self.assertEqual(event['price_ts'],self.now-1000);self.assertEqual(event['received_at'],self.now);self.assertEqual(len(self.state()['events']),1)
 def test_bad_targets_and_fields(self):
  for value in [0,-1,float('nan'),float('inf'),True,1e10,'bad',None]:
   with self.subTest(value=value):
    with self.assertRaises(ValueError):self.create(target=value)
  for symbol in ['../../bad','AAPL?token=x','']:
   with self.assertRaises(ValueError):self.create(symbol=symbol)
  with self.assertRaises(ValueError):self.create(direction='cross')
 def test_invalid_mutation_does_not_change_state(self):
  ident=self.create();old=self.state()
  with self.assertRaises(ValueError):s.change_alerts({'action':'update','id':ident,'symbol':'AAPL','direction':'above','target':0})
  self.assertEqual(old,self.state())
 def test_limit_and_duplicate_create_retry(self):
  ident=self.create();self.assertEqual(ident,self.create());self.assertEqual(len(self.state()['alerts']),1)
  with patch.object(a,'MAX_ALERTS',1):
   with self.assertRaises(ValueError):self.create(target=101)
 def test_concurrent_create_and_observation_are_single_shot(self):
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:ids=list(pool.map(lambda _:self.create(),range(20)))
  self.assertEqual(len(set(ids)),1);self.now+=1000
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(lambda _:s.store_point('AAPL',self.now,110,'finnhub_quote'),range(20)))
  self.assertEqual(len(self.state()['events']),1)
 def test_history_retention(self):
  ident=self.create()
  with patch.object(a,'MAX_HISTORY',3):
   for j in range(6):
    self.observe(110,(j+1)*1000);self.now+=1;s.change_alerts({'action':'rearm','id':ident})
  self.assertEqual(len(self.state()['events']),3);self.assertEqual(self.state()['events'][0]['arm'],6)
 def test_revision_increases_only_for_accepted_state_changes(self):
  self.create();r=self.state()['revision'];self.observe(90);self.assertGreater(self.state()['revision'],r);r=self.state()['revision'];self.observe(90);self.assertEqual(self.state()['revision'],r)
 def test_quote_endpoint_feeds_alert_engine(self):
  self.create();self.now+=1000
  with patch.object(s,'provider_get',return_value=({'c':110,'t':self.now//1000},False)):
   result=s.handle_api('/api/quote',{'symbol':['AAPL']})
  self.assertEqual(result['items'][0]['status'],'ok');self.assertEqual(self.state()['events'][0]['price'],110)
 def test_boolean_is_not_a_real_price(self):
  self.create(target=1);self.now+=1000;self.assertFalse(s.store_point('AAPL',self.now,True,'finnhub_quote'));self.assertEqual(self.state()['events'],[])
 def test_boolean_stream_fields_are_not_real_trade_values(self):
  self.create(target=1);self.now+=1000;self.assertEqual(s.store_points_batch([{'s':'AAPL','t':self.now,'p':True,'v':1}]),0);self.assertEqual(self.state()['events'],[])
 def test_local_health_checks_alert_storage(self):
  self.create();self.observe();result=s.local_health();db=next(x for x in result['checks'] if x['name']=='Market data database');self.assertTrue(db['ok']);self.assertIn('1 saved alerts, 1 trigger records',db['detail'])
 def test_http_mutations_require_local_request_header(self):
  http=s.ThreadingHTTPServer(('127.0.0.1',0),s.AppHandler);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  try:
   url='http://127.0.0.1:'+str(http.server_port)+'/api/alerts';body=json.dumps(dict(action='create',symbol='AAPL',direction='above',target=100,unit='USD')).encode()
   with self.assertRaises(urllib.error.HTTPError) as exc:urllib.request.urlopen(urllib.request.Request(url,data=body,headers={'Content-Type':'application/json'}))
   self.assertEqual(exc.exception.code,403)
   with urllib.request.urlopen(urllib.request.Request(url,data=body,headers={'Content-Type':'application/json','X-MD-Request':'1'})) as response:result=json.load(response)
   self.assertEqual(result['alerts'][0]['target'],100);self.assertNotIn('token',result)
  finally:http.shutdown();http.server_close();thread.join()

if __name__=='__main__':unittest.main()
