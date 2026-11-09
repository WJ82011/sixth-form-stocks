"""Synthetic saved-source fixtures; no real market assertions or provider calls."""
import copy,contextlib,datetime as dt,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import brief33 as b,workspace3 as w,desk
from test_v3_api import s

def point(syms=None,t=None,price=10,currency='USD'):
 t=t or b.millis()-10000;syms=syms if syms is not None else ['AAA']
 return {'symbols':syms,'reviewedAt':t,'quotes':{'AAA':{'price':price,'time':t-1000,'currency':currency,'fetchedAt':t}} if 'AAA' in syms else {},'news':[],'filings':[],'events':{}}
class BriefingTests(unittest.TestCase):
 def test_old_backup_has_no_review_point(self):self.assertEqual(w.normalise({})['briefing']['reviews'],[])
 def test_scopes_are_order_independent_and_never_mix_lists(self):
  self.assertEqual(b.scope(['AAA','BBB']),b.scope(['BBB','AAA']));self.assertNotEqual(b.scope(['AAA']),b.scope(['BBB']))
 def test_recorded_delta_uses_only_two_comparable_endpoints(self):
  a=b.checkpoint(point(t=b.millis()-20000));c=b.checkpoint(point(price=12));r=b.compare(c,a)[0];self.assertEqual(r['state'],'changed');self.assertAlmostEqual(r['changePct'],20)
 def test_no_delta_for_missing_equal_older_or_currency_mismatch(self):
  a=b.checkpoint(point(t=b.millis()-20000));c=copy.deepcopy(a)
  for mode in ['same','missing','older','revised','currency']:
   x=copy.deepcopy(c)
   if mode=='missing':x['quotes']={}
   if mode=='older':x['quotes']['AAA']['time']-=100
   if mode=='revised':x['quotes']['AAA']['price']=20
   if mode=='currency':x['quotes']['AAA'].update(time=x['quotes']['AAA']['time']+100,currency='GBP')
   with self.subTest(mode=mode):r=b.compare(x,a)[0];self.assertEqual(r['state'],mode);self.assertIsNone(r['changePct'])
 def test_unverified_currency_does_not_become_usd(self):
  a=b.checkpoint(point(t=b.millis()-20000,currency=''));c=b.checkpoint(point());self.assertEqual(b.compare(c,a)[0]['state'],'currency')
 def test_extreme_finite_prices_cannot_generate_infinite_json(self):
  a=b.checkpoint(point(t=b.millis()-20000,price=1e-300));c=b.checkpoint(point(price=1e9));r=b.compare(c,a)[0];self.assertEqual(r['state'],'range');self.assertIsNone(r['changePct']);json.dumps(r,allow_nan=False)
 def test_first_quote_is_not_a_market_change(self):self.assertIsNone(b.compare(b.checkpoint(point()),None)[0]['changePct'])
 def test_zero_percent_is_a_valid_new_quote(self):
  a=b.checkpoint(point(t=b.millis()-20000));c=b.checkpoint(point());self.assertEqual(b.compare(c,a)[0]['changePct'],0)
 def test_review_keeps_eight_recent_groups_without_touching_projects(self):
  x={}
  for i in range(10):x=b.review(x,point(syms=['S'+str(i)],t=b.millis()-10000+i))
  self.assertEqual(len(x['reviews']),8);self.assertEqual(x['reviews'][0]['symbols'],['S9'])
  state=w.normalise({'research':{},'briefing':x});self.assertEqual(state['research']['projects'],[])
 def test_old_tab_cannot_reset_newer_review_backwards(self):
  x=b.review({},point())
  with self.assertRaises(ValueError):b.review(x,point(t=b.millis()-999999))
 def test_malformed_or_future_points_rejected(self):
  for change in [lambda p:p.update(reviewedAt=True),lambda p:p.update(reviewedAt=b.millis()+999999),lambda p:p['quotes']['AAA'].update(price=float('nan')),lambda p:p['quotes']['AAA'].update(time=b.millis()+999999),lambda p:p.update(news=['not-a-hash'])]:
   p=point();change(p)
   with self.subTest(p=p):
    with self.assertRaises(ValueError):b.checkpoint(p)
 def test_sensitive_links_not_exposed(self):
  for u in ['javascript:alert(1)','https://u:secret@example.com','https://example.com/?api_key=secret']:
   self.assertEqual(b.url(u),'')
 def test_unknown_fields_not_kept(self):
  p=point();p['token']='must-not-save';self.assertNotIn('must-not-save',json.dumps(b.review({},p)))
class BriefingStorageTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  for attr,name in [('USER_DIR',''),('DB_FILE','data.sqlite3'),('WORKSPACE_FILE','workspace.json'),('KEY_FILE','no-key'),('MASSIVE_KEY_FILE','no-massive')]:
   x=patch.object(s,attr,Path(self.tmp.name)/name);x.start();self.addCleanup(x.stop)
  s.init_storage();self.now=b.millis()
 def build(self,syms=None,state=None):return b.build(vars(s),syms or ['AAA'],w.normalise(state or {}))
 def news(self,scope='AAA',url='https://example.com/synthetic',headline='Synthetic earlier headline'):
  with contextlib.closing(s.db_connection()) as c,c:desk.remember_news(c,scope,[{'headline':headline,'source':'Synthetic provider','url':url,'datetime':(self.now-86400000)//1000}],self.now,self.now)
 def test_reading_briefing_does_not_fetch_sources_or_modify_review(self):
  with patch.object(s,'provider_get',side_effect=AssertionError('No provider request')):
   r=self.build();self.assertIsNone(r['previousReviewAt']);self.assertEqual(r['prices'][0]['state'],'missing')
  self.assertFalse(s.WORKSPACE_FILE.exists())
 def test_headline_dedup_and_older_loaded_item_remain_source_dated(self):
  self.news();self.news('BBB');state={'briefing':b.review({},point(syms=['AAA','BBB'],t=self.now-10000))};r=self.build(['AAA','BBB'],state);self.assertEqual(len(r['news']),1);self.assertTrue(r['news'][0]['newToBriefing']);self.assertLess(r['news'][0]['datetime']*1000,r['previousReviewAt']);self.assertEqual(r['news'][0]['symbols'],['AAA','BBB'])
 def test_review_removes_new_flag_without_erasing_sources(self):
  self.news();a=self.build();state={'briefing':b.review({},a['checkpoint'])};r=self.build(state=state);self.assertEqual(len(r['news']),1);self.assertFalse(r['news'][0]['newToBriefing'])
 def test_event_revision_and_cancellation_do_not_become_upcoming(self):
  date=(dt.datetime.now(dt.timezone.utc).date()+dt.timedelta(days=2)).isoformat();e={'id':'event','title':'Synthetic test date','date':date,'status':'estimated','source':'Synthetic test only','zone':'UTC'};state=w.normalise({'events':[e]});a=self.build(state=state);state['briefing']=b.review({},a['checkpoint']);state['events'][0]['status']='cancelled';r=self.build(state=state);self.assertEqual(len(r['eventChanges']),1);self.assertEqual(r['upcoming'],[])
 def test_malformed_individual_caches_are_reported_without_crashing(self):
  with contextlib.closing(s.db_connection()) as c,c:
   c.execute('INSERT INTO desk_news VALUES(?,?,?)',('AAA',self.now,'{broken'));c.execute('INSERT INTO sec_accounts VALUES(?,?,?)',('1','[]',self.now));c.execute('INSERT INTO sec_links VALUES(?,?)',('AAA','1'))
  r=self.build();self.assertEqual(len(r['coverage']['warnings']),2)
 def test_review_point_full_backup_roundtrip(self):
  state=w.mutate({},'briefing.review',{'checkpoint':point()});s.write_workspace({'notes':[{'title':'Preserve original'}],'v3':state});x=s.read_workspace()['snapshot'];self.assertEqual(len(x['v3']['briefing']['reviews']),1);self.assertEqual(x['notes'][0]['title'],'Preserve original')
 def test_invalid_review_does_not_replace_backup(self):
  s.write_workspace({'notes':[{'title':'Keep'}]});before=s.WORKSPACE_FILE.read_bytes()
  with self.assertRaises(ValueError):s.write_workspace({'v3':{'briefing':{'reviews':[{}]}}})
  self.assertEqual(s.WORKSPACE_FILE.read_bytes(),before)
