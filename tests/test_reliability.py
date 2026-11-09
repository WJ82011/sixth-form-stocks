"""v1.5.0 regression checks: local workspace backup, provider validation and HTTP security."""
import http.client, importlib.util, json, math, os, tempfile, threading, time, unittest
from pathlib import Path
from unittest.mock import patch
SPEC=importlib.util.spec_from_file_location('reliability_server',Path(__file__).parents[1]/'server.py')
s=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(s)

class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.dir=Path(tmp.name)
        for attr, value in [('USER_DIR',self.dir),('DB_FILE',self.dir/'obs.sqlite3'),('KEY_FILE',self.dir/'finnhub_key'),('WORKSPACE_FILE',self.dir/'workspace.json')]:
            patcher=patch.object(s,attr,value);patcher.start();self.addCleanup(patcher.stop)
        s.init_storage()
    def test_storage_folder_and_database_are_private(self):
        self.assertEqual(s.USER_DIR.stat().st_mode & 0o777,0o700)
        self.assertEqual(s.DB_FILE.stat().st_mode & 0o777,0o600)
    def test_workspace_roundtrip_with_notes_and_preferences(self):
        data={'watch':['TSLA','AAPL'],'notes':[{'title':'Portfolio thesis','thesis':'Research','risk':'Concentration','evidence':'Annual report','date':'Today'}],
              'names':{'TSLA':'Tesla'},'preferences':{'edition':'professional','density':'terminal','ticker':False},'tapeSymbol':'TSLA'}
        stamp=s.write_workspace(data);result=s.read_workspace()
        self.assertGreater(stamp,0)
        self.assertEqual(result['snapshot']['notes'][0]['title'],'Portfolio thesis')
        self.assertEqual(result['snapshot']['preferences']['edition'],'professional')
        self.assertEqual(result['snapshot']['watch'],['TSLA','AAPL'])
        self.assertEqual(s.WORKSPACE_FILE.stat().st_mode & 0o777,0o600)
        self.assertNotIn('api',result['snapshot'])
    def test_workspace_normalises_malicious_or_oversized_fields(self):
        result=s.normalise_workspace({'watch':['../etc','AAPL','AAPL','BRK.B'],
            'names':{'../../': 'Bad','TSLA':'T'*1000},'notes':[{'title':'X'*10000,'thesis':'Y'*10000}],
            'preferences':{'edition':'fake','ticker':'yes','motion':False},'tapeSymbol':'../../etc'})
        self.assertEqual(result['watch'],['AAPL','BRK.B'])
        self.assertEqual(len(result['notes'][0]['title']),180)
        self.assertEqual(len(result['notes'][0]['thesis']),8000)
        self.assertNotIn('edition',result['preferences'])
        self.assertIs(result['preferences']['motion'],False)
        self.assertEqual(result['tapeSymbol'],'')
    def test_blue_theme_preferences_survive_workspace_backup(self):
        s.write_workspace({'watch':['TTWO'],'preferences':{'colour':'blue','edition':'professional','chartHeight':'xl','motion':False}})
        saved=s.read_workspace()['snapshot']['preferences']
        self.assertEqual(saved,{'colour':'blue','edition':'professional','chartHeight':'xl','motion':False})
    def test_workspace_wrong_shapes_are_safe(self):
        result=s.normalise_workspace({'watch':'AAPL','names':['AAPL'],'notes':{'bad':1}})
        self.assertEqual(result['watch'],[])
        self.assertEqual(result['names'],{})
        self.assertEqual(result['notes'],[])
        with self.assertRaises(ValueError):s.normalise_workspace(None)
    def test_workspace_interrupted_file_falls_back_without_deleting(self):
        s.WORKSPACE_FILE.write_text('{partial JSON')
        self.assertIsNone(s.read_workspace()['snapshot'])
        self.assertTrue(s.WORKSPACE_FILE.exists())
    def test_selftest_database_assets_and_permissions(self):
        data=s.local_health()
        self.assertTrue(data['ok'],data)
        self.assertEqual(len(data['checks']),7)
        self.assertNotIn('real-time',data['notice'])
    def test_selftest_detects_missing_assets(self):
        p=patch.object(s,'SITE',self.dir/'missing-site');p.start();self.addCleanup(p.stop)
        result=s.local_health()
        self.assertFalse(result['ok'])
        self.assertFalse(next(x for x in result['checks'] if x['name']=='Website files')['ok'])
    def test_valid_quote_rejects_nan_infinity_future_and_boolean(self):
        now=int(time.time());base={'t':now,'c':120.1}
        self.assertTrue(s.valid_provider_quote(base))
        for price in [float('nan'),float('inf'),-1,0,True]:
            self.assertFalse(s.valid_provider_quote({'t':now,'c':price}),price)
        for stamp in [float('nan'),float('inf'),now+900,True]:
            self.assertFalse(s.valid_provider_quote({'t':stamp,'c':120.1}),stamp)
    def test_quote_labeled_stale_without_claiming_live(self):
        now=int(time.time());with_quote={'c':99.2,'t':now-3600,'pc':100.1}
        with patch.object(s,'provider_get',return_value=(with_quote,False)):
            item=s.handle_api('/api/quote',{'symbol':['TSLA']})['items'][0]
        self.assertEqual(item['status'],'ok')
        self.assertTrue(item['stale'])
        self.assertIn('REST quote',item['source'])
    def test_invalid_quotes_never_enter_history(self):
        with patch.object(s,'provider_get',return_value=({'c':float('inf'),'t':int(time.time())},False)):
            item=s.handle_api('/api/quote',{'symbol':['AAPL']})['items'][0]
        self.assertEqual(item['status'],'unavailable')
        self.assertEqual(s.get_history('AAPL'),[])
    def test_candle_series_requires_consistent_fields(self):
        now=int(time.time());valid={'s':'ok','t':[now-86400,now],'c':[100,101],'o':[98,100],
                                     'h':[102,103],'l':[97,99],'v':[2000,2500]}
        self.assertTrue(s.valid_provider_candles(valid))
        for bad in [{**valid,'c':[100]},{**valid,'t':[now,now-86400]},
                    {**valid,'v':[2000,float('inf')]},{**valid,'l':[104,99]}]:
            self.assertFalse(s.valid_provider_candles(bad))
    def test_candle_bad_provider_data_not_exposed_to_browser(self):
        now=int(time.time())
        bad={'s':'ok','t':[now-86400,now],'c':[1.0]}
        with patch.object(s,'provider_get',return_value=(bad,False)):
            response=s.handle_api('/api/candles',{'symbol':['AAPL'],'resolution':['D'],'from':[str(now-2592000)],'to':[str(now)]})
        self.assertEqual(response['status'],'no_data')
        self.assertIsNone(response['candles'])
    def test_provider_batch_explains_skipped_symbols(self):
        with patch.object(s,'provider_get',side_effect=s.ProviderError(429,'Provider rate limited',kind='rate_limit')):
            result=s.handle_api('/api/quotes',{'symbols':['AAPL,NVDA,TSLA']})
        self.assertEqual([x['status'] for x in result['items']],['error','skipped','skipped'])
        self.assertEqual(result['items'][2]['symbol'],'TSLA')
    def test_http_localhost_security_and_saved_workspace(self):
        server=s.ThreadingHTTPServer(('127.0.0.1',0),s.AppHandler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        port=server.server_address[1]
        def req(method,path,body=None,host=None,origin=None,header=True):
            conn=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
            headers={'Host':host or '127.0.0.1:'+str(port)}
            if origin:headers['Origin']=origin
            if body is not None:
                headers['Content-Type']='application/json'
                if header:headers['X-MD-Request']='1'
            conn.request(method,path,body=json.dumps(body) if body is not None else None,headers=headers)
            r=conn.getresponse();content=r.read();result=(r.status,r.getheaders(),content)
            conn.close();return result
        code,headers,content=req('GET','/api/selftest')
        self.assertEqual(code,200)
        self.assertIn('checks',json.loads(content))
        code,headers,content=req('GET','/api/session',host='malicious.test')
        self.assertEqual(code,403)
        code,headers,content=req('POST','/api/workspace',{'snapshot':{'notes':[]}},origin='https://malicious.test')
        self.assertEqual(code,403)
        code,headers,content=req('POST','/api/workspace',{'snapshot':{'notes':[{'title':'Local only'}]}})
        self.assertEqual(code,200)
        code,headers,content=req('GET','/api/workspace')
        self.assertEqual(json.loads(content)['snapshot']['notes'][0]['title'],'Local only')
        code,headers,content=req('GET','/index.html')
        self.assertEqual(code,200)
        self.assertIn('Content-Security-Policy',dict(headers))
        self.assertIn('Market Desk',content.decode())

if __name__=='__main__':unittest.main()
