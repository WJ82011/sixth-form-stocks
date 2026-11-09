"""Private project/watchlist cases. All records are labelled synthetic fixtures."""
import copy,json,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
import research32 as r,workspace3 as w
from test_v3_api import s

def create(state=None):return r.mutate(state or {},'project.save',{'project':{'id':'p','symbol':'AAA','title':'Synthetic project','question':'What does the source support?'}})
def event(kind='note',id='n',**kw):return {'id':id,'kind':kind,'title':'Synthetic '+kind,'body':'Synthetic research only',**kw}
def captured():return {'symbol':'AAA','range':'1D','source':'Synthetic fixture · not market data','displayedCount':2,'points':[{'t':1735819200000,'p':10,'source':'synthetic_test_only'},{'t':1735822800000,'p':11,'source':'synthetic_test_only'}]}
class Research32Tests(unittest.TestCase):
 def test_old_workspace_has_empty_library(self):
  x=w.normalise({});self.assertEqual(x['research']['projects'],[]);self.assertFalse(x['research']['initialised']);self.assertEqual(x['ledger'],[])
 def test_bootstrap_keeps_original_order_and_empty_list(self):
  for symbols in (['TTWO','AAPL'],[]):
   with self.subTest(symbols=symbols):
    x=r.mutate({},'watchlist.bootstrap',{'symbols':symbols});self.assertEqual(x['watchlists'][0]['symbols'],symbols);self.assertEqual(r.mutate(x,'watchlist.bootstrap',{'symbols':['MSFT']}),x)
 def test_watchlist_deduplicates_without_silently_dropping_invalid_symbols(self):
  x=r.mutate({},'watchlist.save',{'watchlist':{'id':'l','name':'Synthetic list','symbols':['aapl','AAPL','TTWO']}});self.assertEqual(x['watchlists'][0]['symbols'],['AAPL','TTWO'])
  with self.assertRaises(ValueError):r.mutate(x,'watchlist.save',{'watchlist':{'id':'bad','name':'Bad','symbols':['AAPL','bad/symbol']}})
  self.assertEqual(len(x['watchlists']),1)
 def test_project_edits_keep_items_and_creation_date(self):
  x=create();x=r.mutate(x,'item.add',{'projectId':'p','item':event()});old=x['projects'][0];new={**old,'title':'Updated synthetic project','baseUpdatedAt':old['updatedAt'],'items':[]};updated=r.mutate(x,'project.save',{'project':new})['projects'][0];self.assertEqual(len(updated['items']),1);self.assertEqual(updated['createdAt'],old['createdAt'])
 def test_project_symbol_cannot_move_evidence_to_another_company(self):
  x=create();p=x['projects'][0]
  with self.assertRaises(ValueError):r.mutate(x,'project.save',{'project':{**p,'symbol':'BBB','baseUpdatedAt':p['updatedAt']}})
 def test_stale_project_edit_rejected(self):
  x=create();p=copy.deepcopy(x['projects'][0]);x=r.mutate(x,'item.add',{'projectId':'p','item':event()})
  with self.assertRaises(ValueError):r.mutate(x,'project.save',{'project':{**p,'baseUpdatedAt':p['updatedAt']}})
 def test_stale_watchlist_edit_rejected(self):
  x=r.mutate({},'watchlist.bootstrap',{'symbols':['AAA']});old=x['watchlists'][0];a={**old,'name':'First update','baseUpdatedAt':old['updatedAt']};x=r.mutate(x,'watchlist.save',{'watchlist':a})
  with self.assertRaises(ValueError):r.mutate(x,'watchlist.save',{'watchlist':a})
 def test_archive_and_restore_preserve_all_research(self):
  x=r.mutate(create(),'item.add',{'projectId':'p','item':event()});old=copy.deepcopy(x['projects'][0]['items']);x=r.mutate(x,'project.archive',{'id':'p','archived':True});self.assertEqual(x['projects'][0]['items'],old);x=r.mutate(x,'project.archive',{'id':'p','archived':False});self.assertFalse(x['projects'][0]['archived'])
 def test_notes_edit_without_becoming_facts(self):
  x=r.mutate(create(),'item.add',{'projectId':'p','item':event()});item=x['projects'][0]['items'][0];updated=r.mutate(x,'item.update',{'projectId':'p','item':{**item,'body':'Changed author view','baseUpdatedAt':item['updatedAt']}});self.assertEqual(updated['projects'][0]['items'][0]['body'],'Changed author view');self.assertEqual(updated['projects'][0]['items'][0]['createdAt'],item['createdAt'])
 def test_sources_reject_credentials_script_links_and_query_keys(self):
  for url in ['javascript:alert(1)','http://example.com','https://user:secret@example.com','https://example.com/?key=secret','https://[invalid']:
   with self.subTest(url=url):
    with self.assertRaises(ValueError):r.mutate(create(),'item.add',{'projectId':'p','item':event('source',url=url)})
 def test_source_saves_link_without_network(self):
  with patch('urllib.request.urlopen',side_effect=AssertionError('No URL reading')):
   x=r.mutate(create(),'item.add',{'projectId':'p','item':event('source',url='https://example.com/filing')});self.assertEqual(x['projects'][0]['items'][0]['url'],'https://example.com/filing')
 def test_chart_snapshot_preserves_original_prices_and_dates(self):
  c=captured();x=r.mutate(create(),'item.add',{'projectId':'p','item':event('chart',chart=c)});self.assertEqual(x['projects'][0]['items'][0]['chart']['points'][1]['p'],11);c['points'][1]['p']=999;self.assertEqual(x['projects'][0]['items'][0]['chart']['points'][1]['p'],11)
 def test_chart_cannot_be_relabelled_or_overwritten_by_note_edit(self):
  c=captured();c['symbol']='BBB'
  with self.assertRaises(ValueError):r.mutate(create(),'item.add',{'projectId':'p','item':event('chart',chart=c)})
  x=r.mutate(create(),'item.add',{'projectId':'p','item':event('chart',chart=captured())});item=x['projects'][0]['items'][0]
  with self.assertRaises(ValueError):r.mutate(x,'item.update',{'projectId':'p','item':{**item,'baseUpdatedAt':item['updatedAt']}})
 def test_chart_rejects_duplicates_future_nonfinite_and_boolean_prices(self):
  for change in [lambda c:c['points'].reverse(),lambda c:c['points'].append(c['points'][-1]),lambda c:c['points'][0].update(p=True),lambda c:c['points'][0].update(p=float('nan')),lambda c:c['points'][1].update(t=9999999999999999)]:
   c=captured();change(c)
   with self.subTest(c=c):
    with self.assertRaises(ValueError):r.chart(c,'AAA')
 def test_report_links_remain_ids_not_embedded_untrusted_html(self):
  x=r.mutate(create(),'item.add',{'projectId':'p','item':event('report',reportId='report-123')});self.assertEqual(x['projects'][0]['items'][0]['reportId'],'report-123')
 def test_limits_fail_atomically_and_ids_are_unique(self):
  x=create()
  for i in range(40):x=r.mutate(x,'item.add',{'projectId':'p','item':event(id='n'+str(i))})
  with self.assertRaises(ValueError):r.mutate(x,'item.add',{'projectId':'p','item':event(id='overflow')})
  self.assertEqual(len(x['projects'][0]['items']),40)
  with self.assertRaises(ValueError):r.mutate(create(),'item.add',{'projectId':'p','item':event(id='bad/id')})
 def test_oversized_library_is_not_silently_truncated(self):
  x=create()
  with self.assertRaises(ValueError):r.normalise({'projects':[dict(x['projects'][0],question='x'*2001)]})
 def test_unknown_secret_fields_are_not_backed_up(self):
  x=create();x['token']='must-not-save';x['projects'][0]['apiKey']='must-not-save';self.assertNotIn('must-not-save',json.dumps(r.normalise(x)))
 def test_invalid_action_does_not_modify_original(self):
  x=create();before=copy.deepcopy(x)
  with self.assertRaises(ValueError):r.mutate(x,'item.add',{'projectId':'p','item':None})
  self.assertEqual(x,before)
 def test_all_wrong_collection_shapes_rejected(self):
  for key in ['projects','watchlists']:
   for value in [True,{},'bad',1]:
    with self.subTest(key=key,value=value):
     with self.assertRaises(ValueError):r.normalise({key:value})
class ProjectBackupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  for attr,name in [('USER_DIR',''),('DB_FILE','data.sqlite3'),('WORKSPACE_FILE','workspace.json'),('KEY_FILE','no-key'),('MASSIVE_KEY_FILE','no-massive')]:
   p=patch.object(s,attr,Path(self.tmp.name)/name);p.start();self.addCleanup(p.stop)
  s.init_storage()
 def test_project_and_watchlist_roundtrip_in_full_backup(self):
  state=w.mutate({},'research.project.save',{'project':{'id':'p','symbol':'AAA','title':'Synthetic backup project'}});state=w.mutate(state,'research.watchlist.bootstrap',{'symbols':['AAA','TTWO']});s.write_workspace({'watch':['AAPL'],'notes':[{'title':'Keep old note'}],'v3':state});d=s.read_workspace()['snapshot'];self.assertEqual(d['v3']['research']['projects'][0]['title'],'Synthetic backup project');self.assertEqual(d['notes'][0]['title'],'Keep old note');self.assertEqual(d['watch'],['AAPL'])
 def test_invalid_project_import_does_not_replace_existing_backup(self):
  s.write_workspace({'notes':[{'title':'Keep'}]});before=s.WORKSPACE_FILE.read_bytes()
  with self.assertRaises(ValueError):s.write_workspace({'v3':{'research':{'projects':[{}]}}})
  self.assertEqual(s.WORKSPACE_FILE.read_bytes(),before)
class ResearchLifecycleTests(unittest.TestCase):
 def test_removal_requires_archive_and_keeps_original_list(self):
  x=create()
  with self.assertRaises(ValueError):r.mutate(x,'project.remove',{'id':'p'})
  x=r.mutate(x,'project.archive',{'id':'p','archived':True});self.assertEqual(r.mutate(x,'project.remove',{'id':'p'})['projects'],[])
  x=r.mutate({},'watchlist.bootstrap',{'symbols':['AAA']});x=r.mutate(x,'watchlist.archive',{'id':'original-watchlist','archived':True})
  with self.assertRaises(ValueError):r.mutate(x,'watchlist.remove',{'id':'original-watchlist'})
 def test_removed_project_cannot_be_resurrected_by_an_old_edit(self):
  x=create();old=x['projects'][0];x=r.mutate(x,'project.archive',{'id':'p','archived':True});x=r.mutate(x,'project.remove',{'id':'p'})
  with self.assertRaises(ValueError):r.mutate(x,'project.save',{'project':{**old,'baseUpdatedAt':old['updatedAt']}})
 def test_archived_chart_can_be_removed_to_release_capacity(self):
  x=r.mutate(create(),'item.add',{'projectId':'p','item':event('chart',chart=captured())});x=r.mutate(x,'item.archive',{'projectId':'p','id':'n','archived':True});x=r.mutate(x,'item.remove',{'projectId':'p','id':'n'});self.assertEqual(x['projects'][0]['items'],[])
 def test_project_and_watchlist_count_limits_include_archives(self):
  x=create();p=x['projects'][0]
  with self.assertRaises(ValueError):r.normalise({'projects':[dict(p,id='p'+str(i),archived=True) for i in range(25)]})
  x=r.mutate({},'watchlist.bootstrap',{'symbols':[]});l=x['watchlists'][0]
  with self.assertRaises(ValueError):r.normalise({'watchlists':[dict(l,id='l'+str(i)) for i in range(17)]})
 def test_global_library_byte_limit_rejects_complete_oversized_candidate(self):
  x=create();p=x['projects'][0];time=r.now();item=event(body='x'*26000,createdAt=time)
  p['items']=[dict(item,id='n'+str(i)) for i in range(30)]
  with self.assertRaises(ValueError):r.normalise(x)
