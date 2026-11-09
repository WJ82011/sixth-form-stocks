import contextlib
import copy
import hashlib
import json
import sqlite3
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import research_ai as a
import server as s
NOW=1793700000000
SOURCE={'id':'D1','title':'Fictional test source','kind':'test fixture','body':'Example Company reported revenue of 120 million USD and operating profit of 18 million USD. These are fictional test figures, not market prices.'}

def packet():return a.packet('TEST',[SOURCE],NOW,'What revenue was reported?')
def draft():return {'title':'Reported financial figures','sections':[{'heading':'Revenue','bullets':[{'text':'Revenue was 120 million USD.','kind':'fact','evidence':[{'id':'D1','excerpt':'revenue of 120 million USD'}]}]}],'missing':['No current share price is provided.']}

class ResearchAITests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  for key,value in [('USER_DIR',Path(self.tmp.name)),('DB_FILE',Path(self.tmp.name)/'test.sqlite3'),('KEY_FILE',Path(self.tmp.name)/'key'),('MASSIVE_KEY_FILE',Path(self.tmp.name)/'massive-key')]:
   p=patch.object(s,key,value);p.start();self.addCleanup(p.stop)
  s.init_storage()
 def connect(self):return contextlib.closing(s.db_connection())
 def add(self,symbol='TEST',text=None,**kwargs):
  with self.connect() as con,con:return a.add_document(con,dict(symbol=symbol,title='Test source',text=text or SOURCE['body'],**kwargs),NOW)
 def test_valid_source_claim_is_accepted_and_not_called_fact_verified(self):
  d=a.verify(draft(),packet());self.assertEqual(d['checks']['sourceLinksMatched'],1);self.assertFalse(d['checks']['semanticVerification'])
 def test_missing_only_answer_can_decline_without_inventing_facts(self):
  result=a.verify({'title':'Not enough evidence','sections':[],'missing':['No share price is provided.']},packet());self.assertEqual(result['checks']['sourceLinksMatched'],0)
 def test_invented_number_is_rejected(self):
  d=draft();d['sections'][0]['bullets'][0]['text']='Revenue was 999 million USD.'
  with self.assertRaises(a.AIError):a.verify(d,packet())
 def test_wrong_source_id_is_rejected(self):
  d=draft();d['sections'][0]['bullets'][0]['evidence'][0]['id']='X999'
  with self.assertRaises(a.AIError):a.verify(d,packet())
 def test_fabricated_quote_is_rejected(self):
  d=draft();d['sections'][0]['bullets'][0]['evidence'][0]['excerpt']='Revenue was guaranteed to grow.'
  with self.assertRaises(a.AIError):a.verify(d,packet())
 def test_fact_without_citation_is_rejected(self):
  d=draft();d['sections'][0]['bullets'][0]['evidence']=[]
  with self.assertRaises(a.AIError):a.verify(d,packet())
 def test_number_must_be_in_its_cited_source_not_some_other_source(self):
  p=a.packet('TEST',[SOURCE,{'id':'D2','body':'Unrelated source reports a price of 999 USD.'}],NOW,'Check figures')
  d=draft();d['sections'][0]['bullets'][0]['text']='Revenue was 999 million USD.'
  with self.assertRaises(a.AIError):a.verify(d,p)
 def test_missing_information_does_not_allow_unsourced_numbers(self):
  d=draft();d['missing']=['The target should be 999 USD.']
  with self.assertRaises(a.AIError):a.verify(d,packet())
 def test_trade_instruction_is_rejected(self):
  d=draft();d['sections'][0]['bullets'][0]['text']='You should buy because revenue was 120 million USD.'
  with self.assertRaises(a.AIError):a.verify(d,packet())
 def test_bad_structures_are_rejected(self):
  for value in [None,[],{},dict(title='x',sections=[],missing=[])]:
   with self.subTest(value=value):
    with self.assertRaises(a.AIError):a.verify(value,packet())
 def test_plain_html_is_not_executed_or_turned_into_a_tool(self):
  d=draft();d['title']='<script>bad()</script>';result=a.verify(d,packet());self.assertEqual(result['title'],'<script>bad()</script>')
 def test_numeric_formatting_matches_commas(self):
  self.assertEqual(a.numeric_tokens('1,200.00'),a.numeric_tokens('1200'))
 def test_packet_is_bounded_and_hash_is_reproducible(self):
  p=a.packet('TEST',[{'id':'D'+str(i),'body':'A'*10000} for i in range(14)],NOW,'question');self.assertLessEqual(sum(len(x['body']) for x in p['sources']),a.MAX_PACKET);self.assertTrue(p['sources'][0]['truncated']);digest=p.pop('hash');self.assertEqual(digest,hashlib.sha256(json.dumps(p,sort_keys=True,ensure_ascii=False).encode()).hexdigest())
 def test_duplicate_source_ids_are_rejected(self):
  with self.assertRaises(a.AIError):a.packet('TEST',[SOURCE,SOURCE],NOW,'question')
 def test_links_strip_credentials_and_unsafe_schemes(self):
  self.assertEqual(a.safe_url('javascript:alert(1)'),'');self.assertEqual(a.safe_url('https://user:password@example.com/a'),'');self.assertNotIn('secret',a.safe_url('https://example.com/a?token=secret&x=ok'));self.assertIn('x=ok',a.safe_url('https://example.com/a?token=secret&x=ok'))
 def test_source_document_metadata_and_retrieval_are_private_and_scoped(self):
  ident=self.add();self.add(symbol='OTHER',text='Other company source with a completely different business model and risk profile.')
  with self.connect() as con:
   rows=a.retrieve(con,'TEST','revenue');self.assertEqual(len(rows),1);self.assertEqual(rows[0]['documentId'],ident);self.assertNotIn('OTHER',rows[0]['body']);self.assertEqual(a.documents(con,'TEST')[0]['characters'],len(SOURCE['body']))
 def test_source_limits_and_invalid_dates(self):
  with self.assertRaises(a.AIError):self.add(text='short')
  with self.assertRaises(a.AIError):self.add(published='yesterday')
  with self.assertRaises(a.AIError):self.add(text='x'*(a.MAX_DOC+1))
  for i in range(20):self.add(text=SOURCE['body']+str(i))
  with self.assertRaises(a.AIError):self.add()
 def test_document_survives_restart(self):
  ident=self.add();s.init_storage()
  with self.connect() as con:self.assertEqual(a.documents(con,'TEST')[0]['id'],ident)
 def test_document_delete_cannot_remove_another_stock_source(self):
  ident=self.add();s.ai_action('/api/ai/documents',{'symbol':'OTHER','action':'delete','id':ident})
  with self.connect() as con:self.assertEqual(len(a.documents(con,'TEST')),1)
 def test_local_models_reject_cloud_and_accept_mlx_and_gguf(self):
  model=lambda n,fmt='gguf',**extra:dict(name=n,size=4000000000,details={'format':fmt},**extra)
  rows=[model('local:4b'),model('local-mlx:4b','safetensors'),model('bad:cloud'),model('alias',remote_host='https://example.com'),dict(name='tiny',size=10,details={'format':'gguf'}),None]
  with patch.object(a,'engine_call',return_value={'models':rows}):self.assertEqual([x['name'] for x in a.local_models()],['local:4b','local-mlx:4b'])
 def test_status_handles_unavailable_engine(self):
  with patch.object(a,'engine_call',side_effect=a.AIError('Ollama unavailable')):self.assertFalse(a.status()['ready'])
 def test_ai_http_mutations_require_local_header_and_origin(self):
  http=s.ThreadingHTTPServer(('127.0.0.1',0),s.AppHandler);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  try:
   with patch.object(a,'engine_call',side_effect=AssertionError('Untrusted request must not reach the model')):
    for endpoint in ('ask','sources','documents','runs'):
     for headers in ({'Content-Type':'application/json'},{'Content-Type':'application/json','X-MD-Request':'1','Origin':'https://example.com'}):
      request=urllib.request.Request('http://127.0.0.1:'+str(http.server_port)+'/api/ai/'+endpoint,data=b'{"symbol":"TEST"}',headers=headers)
      with self.assertRaises(urllib.error.HTTPError) as exc:urllib.request.urlopen(request)
      self.assertEqual(exc.exception.code,403)
  finally:http.shutdown();http.server_close();thread.join()
 def test_no_arbitrary_engine_endpoint(self):
  with self.assertRaises(a.AIError):a.engine_call('https://example.com')
 def test_redirect_is_rejected(self):
  with self.assertRaises(a.AIError):a.NoRedirect().redirect_request(None,None,None,None,None,None)
 def test_generation_uses_local_structured_output_no_tools(self):
  with patch.object(a,'engine_call',return_value={'done':True,'message':{'content':json.dumps(draft())}}) as call:
   result=a.generate('local:4b','answer','What revenue?',packet());args=call.call_args;self.assertEqual(args[0][0],'/api/chat');body=args[0][1];self.assertFalse(body['stream']);self.assertFalse(body['think']);self.assertNotIn('tools',body);self.assertEqual(body['format']['required'],a.SCHEMA['required']);self.assertIn('D1:1',body['format']['properties']['sections']['items']['properties']['bullets']['items']['properties']['evidence']['items']['properties']['quote']['enum']);self.assertIn('untrusted',body['messages'][0]['content']);self.assertEqual(result['checks']['sourceLinksMatched'],1)
 def test_model_selects_excerpt_key_and_server_copies_exact_text(self):
  d=draft();d['sections'][0]['bullets'][0]['evidence']=[{'quote':'D1:1'}]
  with patch.object(a,'engine_call',return_value={'done':True,'message':{'content':json.dumps(d)}}):
   result=a.generate('local','answer','What revenue?',packet());ref=result['sections'][0]['bullets'][0]['evidence'][0];self.assertEqual(ref['id'],'D1');self.assertIn(ref['excerpt'],SOURCE['body'])
  d['sections'][0]['bullets'][0]['evidence']=[{'quote':'unknown'}]
  with patch.object(a,'engine_call',return_value={'done':True,'message':{'content':json.dumps(d)}}):
   with self.assertRaises(a.AIError):a.generate('local','answer','What revenue?',packet())
 def test_generation_discards_empty_headings_without_creating_claims(self):
  raw={'title':'Evidence missing','sections':[{'heading':'Unfilled heading','bullets':[]}],'missing':['No price is provided.']}
  with patch.object(a,'engine_call',return_value={'done':True,'message':{'content':json.dumps(raw)}}):
   result=a.generate('local','answer','What price?',packet());self.assertEqual(result['sections'],[]);self.assertEqual(result['checks']['factualStatements'],0)
 def test_citation_choices_are_exact_short_source_spans(self):
  p=packet();choices=a.citation_options(p,'revenue')
  for option in choices:
   source=next(x for x in p['sources'] if x['id']==option['id'])
   for quote in option['excerpts']:
    self.assertIn(quote,source['body']);self.assertGreaterEqual(len(quote),8);self.assertLessEqual(len(quote.split()),35)
 def test_one_correction_pass_keeps_same_checks_and_evidence(self):
  bad=draft();bad['sections'][0]['bullets'][0]['evidence'][0]['excerpt']='invented quotation'
  response=lambda d:{'done':True,'message':{'content':json.dumps(d)}}
  with patch.object(a,'engine_call',side_effect=[response(bad),response(draft())]) as call:
   self.assertEqual(a.generate('local','answer','What revenue?',packet())['checks']['sourceLinksMatched'],1);self.assertEqual(call.call_count,2)
  with patch.object(a,'engine_call',return_value=response(bad)) as call:
   with self.assertRaises(a.AIError):a.generate('local','answer','What revenue?',packet())
   self.assertEqual(call.call_count,2)
 def test_truncated_and_invalid_model_outputs_fail_closed(self):
  for response in [{'done':False},{'done':True,'done_reason':'length','message':{'content':json.dumps(draft())}},{'done':True,'message':{'content':'not json'}}]:
   with self.subTest(response=response),patch.object(a,'engine_call',return_value=response):
    with self.assertRaises(a.AIError):a.generate('local','answer','Question',packet())
 def test_no_evidence_does_not_call_the_model(self):
  with patch.object(a,'engine_call') as call:
   with self.assertRaises(a.AIError):a.generate('local','answer','Question',{'sources':[]})
   call.assert_not_called()
 def test_ai_evidence_does_not_make_provider_requests_or_include_keys(self):
  with patch.object(s,'provider_get',side_effect=AssertionError('No market requests')):
   p=s.ai_evidence('AAPL','chart');self.assertTrue(any(x['id']=='P1' for x in p['sources']))
  key=('stock/profile2',(('symbol','AAPL'),))
  with patch.dict(s.CACHE,{key:(0,{'name':'Apple','ticker':'AAPL','api_key':'SECRET-NEVER-SEND','token':'SECRET'})}),patch.dict(s.CACHE_FETCHED_AT,{key:NOW}):
   p=s.ai_evidence('AAPL','company');text=json.dumps(p);self.assertNotIn('SECRET',text);self.assertEqual(next(x for x in p['sources'] if x['id']=='C1')['retrievedAt'],NOW)
 def test_comparison_has_distinct_stock_scoped_sources_and_valid_hash(self):
  p=s.ai_research_pack('AAPL','Compare companies','MSFT');self.assertEqual(p['compareSymbol'],'MSFT');self.assertTrue(all(x['id'][0] in 'AB' for x in p['sources']));self.assertTrue(any(x.get('symbol')=='MSFT' for x in p['sources']));digest=p.pop('hash');self.assertEqual(digest,hashlib.sha256(json.dumps(p,sort_keys=True,ensure_ascii=False).encode()).hexdigest())
 def test_sources_refresh_handles_plan_restrictions(self):
  with patch.object(s,'provider_get',side_effect=s.ProviderError(403,'Plan access unavailable')):
   result=s.ai_action('/api/ai/sources',{'symbol':'AAPL'});self.assertEqual(len(result['warnings']),2)
 def test_saved_draft_keeps_original_source_snapshot(self):
  ident='a'*32;result={'id':ident,'symbol':'TEST','mode':'answer','question':'What revenue?','model':'local','createdAt':NOW,'draft':a.verify(draft(),packet()),'evidence':packet()}
  with self.connect() as con,con:a.save_run(con,result)
  self.add(text='The changed source no longer contains the earlier reported revenue or profit.')
  with self.connect() as con:
   self.assertEqual(a.get_run(con,ident,'TEST')['evidence']['sources'][0]['body'],SOURCE['body'])
   with self.assertRaises(a.AIError):a.get_run(con,ident,'OTHER')
 def test_busy_engine_does_not_start_another_draft(self):
  a.MODEL_LOCK.acquire()
  try:
   with patch.object(a,'local_models',return_value=[{'name':'local'}]):
    with self.assertRaises(a.AIError):a.start('local','answer','What revenue?',packet(),lambda x:None)
  finally:a.MODEL_LOCK.release()
 def test_job_completes_only_after_persistence(self):
  saved=[]
  with patch.object(a,'local_models',return_value=[{'name':'local'}]),patch.object(a,'generate',return_value=a.verify(draft(),packet())):
   j=a.start('local','answer','What revenue?',packet(),saved.append)
   for _ in range(100):
    state=a.job(j['id'])
    if state['status']!='running':break
    time.sleep(.01)
   self.assertEqual(state['status'],'complete');self.assertEqual(saved[0]['id'],j['id'])
 def test_validation_failure_does_not_save_a_fake_success(self):
  saved=[]
  with patch.object(a,'local_models',return_value=[{'name':'local'}]),patch.object(a,'generate',side_effect=a.AIError('Citation failed')):
   j=a.start('local','answer','What revenue?',packet(),saved.append)
   for _ in range(100):
    state=a.job(j['id'])
    if state['status']!='running':break
    time.sleep(.01)
   self.assertEqual(state['status'],'error');self.assertEqual(saved,[])

if __name__=='__main__':unittest.main()
