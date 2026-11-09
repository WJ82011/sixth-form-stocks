"""Offline contract tests for Massive historical integration; no real keys or network."""
import importlib.util
import json
import math
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

spec=importlib.util.spec_from_file_location('md_massive',Path(__file__).parents[1]/'server.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)

class MassiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        for attr,name in [('USER_DIR',''),('DB_FILE','observations.sqlite3'),('KEY_FILE','finnhub_key'),('MASSIVE_KEY_FILE','massive_key'),('WORKSPACE_FILE','workspace.json')]:
            p=patch.object(s,attr,Path(self.tmp.name)/name if name else Path(self.tmp.name));p.start();self.addCleanup(p.stop)
        self.fixes=[patch.object(s,'MASSIVE_CACHE',{}),patch.object(s,'MASSIVE_REQUEST_LOG',s.collections.deque()),patch.object(s,'MASSIVE_BACKOFF',0.0)]
        for fix in self.fixes:fix.start();self.addCleanup(fix.stop)
        s.init_storage()

    def bars(self,symbol='AAPL',days=80):
        day=86400_000;now=int(time.time()*1000);anchor=now-now%day
        data=[]
        for i in range(days):
            v=150+i*.2
            data.append({'t':anchor-(days-i)*day,'o':v,'h':v+2,'l':v-2,'c':v+.5,'v':3_000_000})
        return {'status':'OK','ticker':symbol,'adjusted':True,'results':data}

    def test_key_permissions_separation_and_privacy(self):
        s.save_massive_key('massive123456abc')
        self.assertEqual(s.get_massive_key(),'massive123456abc')
        self.assertEqual(s.MASSIVE_KEY_FILE.stat().st_mode&0o777,0o600)
        self.assertFalse(s.get_key())
        self.assertNotIn('massive123456abc',str(s.handle_api('/api/status',{})))
        self.assertNotIn('massive123456abc',str(s.handle_api('/api/session',{})))
        self.assertNotIn('massive123456abc',str(s.handle_api('/api/workspace',{})))
        self.assertTrue(s.handle_api('/api/status',{})['massive_configured'])

    def test_missing_massive_key_preserves_finnhub_fallback(self):
        qs={'symbol':['AAPL'],'resolution':['D'],'from':['1730000000'],'to':[str(int(time.time()))]}
        with patch.object(s,'provider_get',return_value=({'s':'no_data'},False)) as call:
            output=s.handle_api('/api/candles',qs)
        self.assertEqual(output['status'],'no_data')
        call.assert_called_once()

    def test_massive_selected_when_configured_no_finnhub_historical_request(self):
        s.save_massive_key('massive123456abc')
        start=int(time.time())-400*86400;end=int(time.time())
        with patch.object(s,'massive_request',return_value=(self.bars(),False)) as request,patch.object(s,'provider_get') as finn:
            output=s.handle_api('/api/candles',{'symbol':['AAPL'],'resolution':['D'],'from':[str(start)],'to':[str(end)]})
        self.assertEqual(output['status'],'ok')
        self.assertEqual(output['provider'],'massive')
        self.assertEqual(len(output['candles']['t']),80)
        self.assertTrue(output['adjusted'])
        self.assertIn('daily closes',output['source'])
        self.assertEqual(output['candles']['c'][0],150.5)
        self.assertEqual(output['candles']['t'][0],self.bars()['results'][0]['t']//1000)
        finn.assert_not_called()
        self.assertIn('adjusted',request.call_args.kwargs['__class__'] if '__class__' in request.call_args.kwargs else str(request.call_args))

    def test_rejects_incorrect_symbol_and_unadjusted(self):
        start=int(time.time())-400*86400;end=int(time.time())
        for payload in (self.bars('MSFT'),{**self.bars(),'adjusted':False}):
            with self.assertRaises(s.ProviderError):s.normalized_massive_candles(payload,'AAPL',start,end)

    def test_rejects_corrupt_prices_time_order_and_nan(self):
        start=int(time.time())-400*86400;end=int(time.time())
        cases=[]
        d=self.bars();d['results'][0]['h']=d['results'][0]['l']-1;cases.append(d)
        d=self.bars();d['results'][0]['c']=float('nan');cases.append(d)
        d=self.bars();d['results'][1]['t']=d['results'][0]['t'];cases.append(d)
        for payload in cases:
            with self.assertRaises(s.ProviderError):s.normalized_massive_candles(payload,'AAPL',start,end)

    def test_empty_response_no_fake_price(self):
        s.save_massive_key('massive123456abc');now=int(time.time())
        with patch.object(s,'massive_request',return_value=({'status':'OK','ticker':'AAPL','adjusted':True,'results':[]},False)):
            result=s.massive_daily_candles('AAPL',now-86400*30,now)
        self.assertEqual(result['status'],'no_data');self.assertIsNone(result['candles'])

    def test_http_401_never_leaks_secret_and_keeps_tls_verification(self):
        s.save_massive_key('superPrivateMassiveKeyabc')
        exc=urllib.error.HTTPError('https://api.massive.com/v2/aggs',401,'Unauthorized',{},None)
        with patch.object(s.urllib.request,'urlopen',side_effect=exc) as call:
            with self.assertRaises(s.ProviderError) as err:
                s.massive_request('v2/aggs/ticker/AAPL/range/1/day/2026-09-01/2026-09-02',ttl=0)
        self.assertEqual(err.exception.kind,'massive_authentication')
        self.assertNotIn('superPrivateMassiveKeyabc',err.exception.message)
        request=call.call_args.args[0]
        self.assertNotIn('superPrivateMassiveKeyabc',request.full_url)
        self.assertEqual(request.get_header('Authorization'),'Bearer superPrivateMassiveKeyabc')
        ctx=call.call_args.kwargs['context']
        self.assertEqual(ctx.verify_mode,s.ssl.CERT_REQUIRED)
        self.assertTrue(ctx.check_hostname)

    def test_cache_and_budget(self):
        s.save_massive_key('massive123456abc')
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self,n):return json.dumps(self.selfPayload).encode()
        payload=self.bars();Response.selfPayload=payload
        with patch.object(s.urllib.request,'urlopen',return_value=Response()) as request:
            for i in range(2):
                r,_=s.massive_request('v2/aggs/ticker/AAPL/range/1/day/2026-10-01/2026-11-01')
            self.assertEqual(request.call_count,1)
            for i in range(3):s.massive_request('ticker'+str(i),ttl=1)
            with self.assertRaises(s.ProviderError) as err:s.massive_request('fifth')
            self.assertEqual(err.exception.kind,'massive_local_budget')
            self.assertEqual(request.call_count,4)

    def test_clear_key_does_not_touch_finnhub(self):
        s.save_key('finnhub123456abc');s.save_massive_key('massive123456abc')
        s.clear_massive_key()
        self.assertEqual(s.get_massive_key(),'')
        self.assertEqual(s.get_key(),'finnhub123456abc')

    def test_massive_diagnose_shows_true_eod_not_live(self):
        s.save_massive_key('massive123456abc')
        now=int(time.time());bar=self.bars(days=6)
        with patch.object(s,'massive_request',return_value=(bar,False)) as request:
            result=s.diagnose_massive()
        self.assertTrue(result['ok']);self.assertEqual(result['count'],6)
        self.assertIn('end-of-day',result['message'].lower())
        self.assertTrue(request.call_args.kwargs['bypass_cache'])

    def test_persisted_bars_survive_cache_reset_and_avoid_repeat_call(self):
        s.save_massive_key('massive123456abc');start=int(time.time())-80*86400;end=int(time.time())
        with patch.object(s,'massive_request',return_value=(self.bars(days=80),False)) as call:
            first=s.massive_daily_candles('AAPL',start,end)
            self.assertEqual(first['status'],'ok')
            self.assertEqual(call.call_count,1)
        cached=s.read_massive_daily_bars('AAPL',start,end)
        self.assertTrue(s.cached_massive_adequate(cached,start,end))
        with patch.object(s,'massive_request') as provider:
            second=s.massive_daily_candles('AAPL',start,end)
        provider.assert_not_called()
        self.assertTrue(second['cached'])
        self.assertEqual(second['candles']['c'],first['candles']['c'])
        self.assertIn('local verified',second['source'])

    def test_outage_uses_real_locally_cached_bars_and_reports_refresh_failure(self):
        s.save_massive_key('massive123456abc');start=int(time.time())-80*86400;end=int(time.time())
        with patch.object(s,'massive_request',return_value=(self.bars(days=80),False)):
            s.massive_daily_candles('AAPL',start,end)
        with s.contextlib.closing(s.db_connection()) as con, con:
            con.execute('UPDATE massive_daily_bars SET fetched_at=fetched_at-86400')
        with patch.object(s,'massive_request',side_effect=s.ProviderError(429,'provider cooldown',kind='massive_rate_limit')):
            result=s.massive_daily_candles('AAPL',start,end)
        self.assertEqual(result['status'],'ok')
        self.assertTrue(result['cached'])
        self.assertEqual(result['refresh_error'],'provider cooldown')
        self.assertIn('refresh unavailable',result['source'])

    def test_diagnostic_bypasses_cached_history(self):
        s.save_massive_key('massive123456abc')
        with patch.object(s,'massive_request',return_value=(self.bars(days=80),False)):
            s.massive_daily_candles('AAPL',int(time.time())-80*86400,int(time.time()))
        with patch.object(s,'massive_request',return_value=(self.bars(days=18),False)) as provider:
            result=s.diagnose_massive()
        provider.assert_called_once()
        self.assertTrue(provider.call_args.kwargs['bypass_cache'])
        self.assertTrue(result['ok'])

    def test_delayed_status_is_valid_genuine_historical_data(self):
        """Regression: v1.6.1 allowed DELAYED on fetch but rejected it in normalizer."""
        now=int(time.time());data=self.bars(days=70);data['status']='DELAYED'
        clean=s.normalized_massive_candles(data,'AAPL',now-90*86400,now)
        self.assertEqual(len(clean['t']),70)
        self.assertEqual(clean['c'][0],150.5)
        s.save_massive_key('massive123456abc')
        with patch.object(s,'massive_request',return_value=(data,False)):
            r=s.massive_daily_candles('AAPL',now-90*86400,now)
        self.assertEqual(r['status'],'ok')
        self.assertTrue(r['adjusted'])
        self.assertIn('end-of-day',r['notice'].lower())

    def test_free_basic_date_window_uses_new_york_not_utc(self):
        # 00:30 UTC on 3 Nov = still 2 Nov in NY. 2 Nov must be excluded.
        when=s.dt.datetime(2026,11,3,0,30,tzinfo=s.dt.timezone.utc)
        earliest, latest=s.massive_free_date_window(when)
        self.assertEqual(str(latest),'2026-11-01')
        self.assertGreaterEqual(earliest,s.dt.date(2024,11,2))
        # Next NY midnight: 05:30 UTC now allows the November 2 bar.
        when=s.dt.datetime(2026,11,3,5,30,tzinfo=s.dt.timezone.utc)
        _, latest=s.massive_free_date_window(when)
        self.assertEqual(str(latest),'2026-11-02')

    def test_basic_request_excludes_current_day_and_old_two_year_history(self):
        s.save_massive_key('massive123456abc')
        now=int(time.time());earliest=s.dt.date(2025,1,2);latest=s.dt.date(2026,11,1)
        with patch.object(s,'massive_free_date_window',return_value=(earliest,latest)):
            with patch.object(s,'massive_request',return_value=(self.bars(days=60),False)) as request:
                s.massive_daily_candles('AAPL',now-800*86400,now)
            endpoint=request.call_args.args[0]
            self.assertIn('/2025-01-02/2026-11-01',endpoint)
            self.assertNotIn('/2026-11-02',endpoint)

    def test_bad_date_range_returns_no_data_without_network(self):
        s.save_massive_key('massive123456abc');now=int(time.time())
        start=now-100*86400;end=now-99*86400
        with patch.object(s,'massive_free_date_window',return_value=(s.dt.date(2026,10,1),s.dt.date(2026,11,1))):
            with patch.object(s,'massive_request') as request:
                r=s.massive_daily_candles('AAPL',start,end)
        request.assert_not_called()
        self.assertEqual(r['status'],'no_data')
        self.assertIn('window',r['message'])

    def test_http_403_reports_safe_provider_message_and_code(self):
        import io
        secret='mySuperSecretMassiveKey123'
        s.save_massive_key(secret)
        body=json.dumps({'status':'NOT_AUTHORIZED','message':"Your plan doesn't include this data timeframe; apiKey="+secret}).encode()
        exc=urllib.error.HTTPError('https://api.massive.com/v2/aggs',403,'Forbidden',{},io.BytesIO(body))
        with patch.object(s.urllib.request,'urlopen',side_effect=exc):
            with self.assertRaises(s.ProviderError) as error:
                s.massive_request('v2/aggs/ticker/AAPL/range/1/day/2026-10-01/2026-10-31')
        self.assertEqual(error.exception.status,403)
        self.assertEqual(error.exception.kind,'massive_recency')
        self.assertIn('NOT_AUTHORIZED',error.exception.message)
        self.assertNotIn(secret,error.exception.message)

    def test_provider_status_error_in_http_200_body_is_actionable(self):
        s.save_massive_key('massive123456abc')
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):
                return json.dumps({"status":"NOT_AUTHORIZED","message":"Your plan does not include this data timeframe"}).encode()
        with patch.object(s.urllib.request,'urlopen',return_value=Response()):
            with self.assertRaises(s.ProviderError) as error:
                s.massive_request('v2/aggs/ticker/AAPL/range/1/day/2026-10-01/2026-10-31')
        self.assertEqual(error.exception.status,403)
        self.assertEqual(error.exception.kind,'massive_recency')

if __name__=='__main__':unittest.main()
