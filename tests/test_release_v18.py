"""Release 1.8 regression tests: no internet/no keys. Test data is fictional."""
import json
import unittest
import sys
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server as s

class Release18Tests(unittest.TestCase):
 def test_version_and_navigation(self):
  doc=(s.SITE/'index.html').read_text()
  self.assertEqual(s.VERSION,'6.8.0')
  for target in ('macro','accuracy'):
   self.assertIn('data-view="'+target+'"',doc)
   self.assertIn('id="view-'+target+'"',doc)
  loader=(s.SITE/'view-loader.js').read_text()
  self.assertIn('/macro.js',doc+loader)
  self.assertNotIn('fake prices',doc.lower())
 def test_tombstone_persisted_in_private_workspace(self):
  sample={'id':'report-1','symbol':'AAPL','title':'An earlier example','updated':'2026-11-02T20:00:00.000Z','deleted':True}
  result=s.normalise_workspace({'reports':[sample]})
  self.assertTrue(result['reports'][0]['deleted'])
  self.assertEqual(result['reports'][0]['updated'],sample['updated'])
  self.assertNotIn('api-key',json.dumps(result))
 def test_active_limit_forty_tombstones_eighty(self):
  data=[{'id':'a'+str(i),'symbol':'AAPL'} for i in range(60)] + [{'id':'b'+str(i),'symbol':'AAPL','deleted':True} for i in range(90)]
  reports=s.normalise_workspace({'reports':data})['reports']
  self.assertEqual(sum(not r['deleted'] for r in reports),40)
  self.assertEqual(sum(r['deleted'] for r in reports),60) # bounded input to first 120
 def test_world_bank_valid_annual_rows_and_null(self):
  payload=[{'page':1},[
   {'countryiso3code':'GBR','indicator':{'id':'NY.GDP.MKTP.KD.ZG'},'date':'2024','value':1.321478},
   {'countryiso3code':'USA','indicator':{'id':'FP.CPI.TOTL.ZG'},'date':'2024','value':2.42},
   {'countryiso3code':'USA','indicator':{'id':'FR.INR.LEND'},'date':'2023','value':7.62},
   {'countryiso3code':'USA','indicator':{'id':'FR.INR.LEND'},'date':'2025','value':None},
   {'countryiso3code':'GBR','indicator':{'id':'NY.GDP.MKTP.KD.ZG'},'date':'2025','value':float('nan')},
  ]]
  result=s.normalise_world_bank(payload)
  self.assertEqual(result['GB']['NY.GDP.MKTP.KD.ZG'],[{'year':2024,'value':1.321478}])
  self.assertEqual(result['US']['FR.INR.LEND'],[{'year':2023,'value':7.62}])
 def test_world_bank_invalid_payload_never_fabricates(self):
  for payload in ({},[{}],[{},[]],[{},[{'value':8}]]):
   with self.assertRaises(s.ProviderError):s.normalise_world_bank(payload)
 def test_world_bank_failure_returns_unavailable_no_fake(self):
  with mock.patch.object(s.urllib.request,'urlopen',side_effect=OSError('connection unavailable')):
   with s.WORLD_BANK_LOCK:
    s.WORLD_BANK_CACHE.update(when=0.0,result=None,failure_when=0.0,failure='')
   result=s.world_bank_macro()
   self.assertEqual(result['status'],'unavailable')
   self.assertNotIn('series',result)
  with s.WORLD_BANK_LOCK:
   s.WORLD_BANK_CACHE.update(when=0.0,result=None,failure_when=0.0,failure='')
 def test_world_bank_cached_data_labeled(self):
  result={'status':'ok','series':{'GB':{},'US':{}},'source':'World Bank WDI','fetched_at':12345}
  with s.WORLD_BANK_LOCK:
   s.WORLD_BANK_CACHE.update(when=__import__('time').time(),result=result,failure_when=0.0,failure='')
  returned=s.world_bank_macro()
  self.assertTrue(returned['cached'])
  self.assertEqual(returned['fetched_at'],12345)
  with s.WORLD_BANK_LOCK:
   s.WORLD_BANK_CACHE.update(when=0.0,result=None,failure_when=0.0,failure='')
 def test_macro_api_route_never_requests_provider_when_cached(self):
  with mock.patch.object(s,'world_bank_macro',return_value={'status':'unavailable','source':'World Bank'}) as request:
   self.assertEqual(s.handle_api('/api/macro',{})['status'],'unavailable')
   request.assert_called_once_with(refresh=False)
 def test_css_js_are_whitelisted_and_correct_type(self):
  servertext=(s.ROOT/'server.py').read_text()
  self.assertIn("'/macro.js':'macro.js'",servertext)
  self.assertIn("'macro.js':'text/javascript",servertext)
  self.assertIn("'research-v18.css':'text/css",servertext)

if __name__=='__main__':unittest.main()

class Release18NetworkMocks(unittest.TestCase):
 def test_world_bank_success_uses_verified_tls_and_preserves_years(self):
  class StubResponse:
   status=200
   def __enter__(self):return self
   def __exit__(self,*args):return False
   def read(self,n):
    out=[]
    for code in s.WORLD_BANK_INDICATORS:
     for country in ('GBR','USA'):
      out.append({'countryiso3code':country,'indicator':{'id':code},'date':'2024','value':1.2345})
    return json.dumps([{'page':1},out]).encode()
  with s.WORLD_BANK_LOCK:s.WORLD_BANK_CACHE.update(when=0.0,result=None,failure_when=0.0,failure='')
  with mock.patch.object(s,'verified_tls_context',return_value=(object(),'verified')) as tls:
   with mock.patch.object(s.urllib.request,'urlopen',return_value=StubResponse()) as fn:
    got=s.world_bank_macro()
    self.assertEqual(got['status'],'ok')
    self.assertFalse(got['cached'])
    self.assertEqual(got['series']['GB']['NY.GDP.MKTP.KD.ZG'][0]['year'],2024)
    self.assertEqual(len(got['series']['US']),5)
    tls.assert_called_once()
    self.assertIn('context',fn.call_args.kwargs)
    self.assertIn('api.worldbank.org',fn.call_args.args[0].full_url)
  with s.WORLD_BANK_LOCK:s.WORLD_BANK_CACHE.update(when=0.0,result=None,failure_when=0.0,failure='')
 def test_company_cache_uses_actual_provider_fetch_time(self):
  import time
  with s.LOCK:s.CACHE_FETCHED_AT.clear()
  def fake_get(endpoint,params,ttl=0):
   with s.LOCK:
    key=(endpoint,tuple(sorted((k,str(v)) for k,v in params.items())))
    if key not in s.CACHE_FETCHED_AT:s.CACHE_FETCHED_AT[key]=1234567890000
   return ({'name':'Test company','currency':'USD'} if endpoint=='stock/profile2' else {'metric':{'peTTM':14.25}}),True
  with mock.patch.object(s,'provider_get',side_effect=fake_get):
   data=s.handle_api('/api/company',{'symbol':['AAPL']})
   self.assertEqual(data['retrieved_at'],1234567890000)
   self.assertTrue(data['metrics_cached'])
   self.assertTrue(data['profile_cached'])
  with s.LOCK:s.CACHE_FETCHED_AT.clear()
