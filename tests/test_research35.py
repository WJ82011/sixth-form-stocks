"""Synthetic V3.5 fixtures. No assertions about actual company performance."""
import copy,contextlib,datetime as dt,json,math,tempfile,unittest
from unittest.mock import patch
import draft35 as d,forecast35 as f,research35 as r,lab3
from test_analyst34 import config,prices,NOW
import test_v3_api as fixture
s=fixture.s

def draft():
 c=config();c['scenarios'][1]['pricePct']=None;c['scenarios'][1]['rationale']=''
 return {'symbol':'AAA','revision':'rev-1','updatedAt':'2026-11-01T12:00:00+00:00','book':{'bookIndex':0,'baseline':c['baseline']},'config':c,'caseIndex':1,'forms':{'shared':{'affectedPct':'','variableCostPct':'40','rationale':'unfinished reasoning','noDoubleCount':False},'evidence':{'title':'Unfinished','text':'Still typing','source':''},'assistant':{'question':'How would pricing affect revenue?','driver':'pricePct','change':'','case':'1'}}}
class DraftTests(unittest.TestCase):
 def test_partial_fields_are_recoverable_without_becoming_a_saved_analysis(self):
  x=d.normalise({'records':[draft()]})['records'][0];self.assertIsNone(x['config']['scenarios'][1]['pricePct']);self.assertEqual(x['forms']['evidence']['source'],'');self.assertEqual(x['config']['scenarios'][1]['rationale'],'')
 def test_old_backups_have_empty_drafts(self):self.assertEqual(d.normalise({})['records'],[])
 def test_unknown_fields_and_credentials_keys_are_not_restored(self):
  x=draft();x['token']='secret';x['config']['token']='secret';x['forms']['shared']['token']='secret';self.assertNotIn('secret',json.dumps(d.normalise({'records':[x]})))
 def test_different_company_cannot_use_another_baseline(self):
  x=draft();x['symbol']='BBB'
  with self.assertRaises(ValueError):d.normalise({'records':[x]})
 def test_duplicate_companies_and_oversized_input_rejected(self):
  with self.assertRaises(ValueError):d.normalise({'records':[draft(),draft()]})
  x=draft();x['forms']['shared']['rationale']='x'*2001
  with self.assertRaises(ValueError):d.normalise({'records':[x]})
 def test_future_recovery_metadata_rejected(self):
  x=draft();x['updatedAt']='2099-01-01T00:00:00Z'
  with self.assertRaises(ValueError):d.normalise({'records':[x]})
 def test_infinite_incomplete_input_rejected(self):
  x=draft();x['config']['scenarios'][0]['pricePct']=float('inf')
  with self.assertRaises(ValueError):d.normalise({'records':[x]})
class BridgeTests(unittest.TestCase):
 def test_all_effects_reconcile_and_price_volume_interaction_is_explicit(self):
  c=config();c['scenarios'][1].update(pricePct=10,volumePct=20,unitCostPct=5,fixedCostPct=10);out=r.bridge(c);b=out['cases'][1]['steps'];self.assertAlmostEqual(b[0]['value']+sum(x['value'] for x in b[1:-1]),b[-1]['value']);self.assertEqual(b[1]['value'],10);self.assertEqual(b[2]['value'],14);self.assertIn('interaction',out['notice'])
 def test_negative_profit_and_no_changes_remain_exact(self):
  c=config();c['baseline']['operatingProfitM']=-20;out=r.bridge(c);self.assertEqual(out['cases'][0]['steps'][-1]['value'],-20)
 def test_visuals_do_not_modify_the_input(self):
  c=config();before=copy.deepcopy(c);r.bridge(c);self.assertEqual(c,before)
class GuideTests(unittest.TestCase):
 def test_headline_matches_do_not_include_other_companies(self):
  context={'news':[{'headline':'Apple launches a device'},{'headline':'PENN reports earnings'},{'headline':'AAPL report'}],'prices':[],'upcoming':[],'filings':[],'asOf':NOW};x=r.guide('AAPL',context,[],{'name':'Apple Inc.'});self.assertEqual(len(x['headlines']),2);self.assertGreater(len(x['gaps']),1)
 def test_no_news_is_not_invented(self):
  x=r.guide('AAA',{'news':[],'prices':[],'upcoming':[],'filings':[],'asOf':NOW},[],None);self.assertEqual(x['headlines'],[])

def ms(day,hour=12,minute=0):return int(dt.datetime.fromisoformat(day+'T'+f'{hour:02}:{minute:02}:00').replace(tzinfo=f.NY).timestamp()*1000)
def receipt():
 anchor='2026-11-02';p={'t':ms(anchor,0),'p':100};raw={'version':1,'id':'synthetic','symbol':'AAA','currency':'USD','issuedAt':ms('2026-11-03',8),'anchorDay':anchor,'targetDays':f.future_sessions(dt.date.fromisoformat(anchor)),'method':'price-factors-ridge-v1','model':{'anchor':p,'forecastReturnPct':5,'forecastPrice':105,'range':{'lowPrice':95,'highPrice':110}},'trainingPrices':[p],'benchmarkPrices':[]};raw['hash']=f.digest(raw);return raw
class ForecastTests(unittest.TestCase):
 def test_calendar_handles_holidays_early_close_and_dst(self):
  self.assertIsNone(f.close_at(dt.date(2026,11,26)));self.assertEqual(f.close_at(dt.date(2026,11,27)),ms('2026-11-27',13));self.assertEqual(f.last_session(ms('2026-11-27',13,10)).isoformat(),'2026-11-25');self.assertEqual(f.last_session(ms('2026-11-27',13,20)).isoformat(),'2026-11-27')
 def test_calendar_does_not_claim_unknown_years(self):
  with self.assertRaises(ValueError):f.last_session(ms('2029-01-04'))
 def test_cannot_score_before_final_session_closes(self):
  x=receipt();r0=f.evaluate(x,x['trainingPrices'],ms(x['targetDays'][0],17));self.assertEqual(r0['status'],'waiting')
 def test_required_missing_date_is_not_replaced_by_a_later_bar(self):
  x=receipt();points=x['trainingPrices']+[{'t':ms(day,0),'p':105} for day in x['targetDays'][1:]]+[{'t':ms('2026-11-10',0),'p':106}];self.assertEqual(f.evaluate(x,points,ms('2026-11-10',18))['status'],'missing')
 def test_actual_error_and_unchanged_baseline_use_same_target(self):
  x=receipt();points=x['trainingPrices']+[{'t':ms(day,0),'p':103} for day in x['targetDays']];e=f.evaluate(x,points,ms('2026-11-10',18));self.assertEqual(e['status'],'resolved');self.assertAlmostEqual(e['outcome']['absoluteErrorPP'],2);self.assertAlmostEqual(e['outcome']['unchangedErrorPP'],3)
 def test_revised_training_anchor_withholds_score(self):
  x=receipt();p=[{**x['trainingPrices'][0],'p':50}];self.assertEqual(f.evaluate(x,p,ms('2026-11-10',18))['status'],'revised')
 def test_changed_outcome_withdraws_score_but_retains_original(self):
  x=receipt();points=x['trainingPrices']+[{'t':ms(day,0),'p':103} for day in x['targetDays']];e=f.evaluate(x,points,ms('2026-11-10',18));old=copy.deepcopy(e['outcome']);points[-1]['p']=104;r0=f.evaluate(x,points,ms('2026-11-11',18),old);self.assertEqual(r0['status'],'revised');self.assertEqual(old['actualPrice'],103)
 def test_frozen_outcome_survives_cache_pruning_and_detects_tampering(self):
  x=receipt();points=x['trainingPrices']+[{'t':ms(day,0),'p':103} for day in x['targetDays']];e=f.evaluate(x,points,ms('2026-11-10',18));self.assertFalse(f.evaluate(x,[],ms('2026-11-11',18),e['outcome'])['rechecked']);e['outcome']['absoluteErrorPP']=0
  with self.assertRaises(ValueError):f.evaluate(x,[],ms('2026-11-11',18),e['outcome'])
 def test_forecast_receipt_tampering_rejected(self):
  x=receipt();x['model']['forecastPrice']=10000
  with self.assertRaises(ValueError):f.evaluate(x,[],ms('2026-11-10',18))
 def test_archived_forecasts_stay_in_aggregate_and_overlaps_are_separate(self):
  x=receipt();points=x['trainingPrices']+[{'t':ms(day,0),'p':103} for day in x['targetDays']];e=f.evaluate(x,points,ms('2026-11-10',18));rows=[{**x,'archived':True,'evaluation':e},{**x,'id':'second','issuedAt':x['issuedAt']+1,'anchorDay':'2026-11-03','evaluation':e}];summary=f.totals(rows);self.assertEqual(summary['all']['count'],2);self.assertEqual(summary['nonOverlapping']['count'],1)
class APITests(unittest.TestCase):
 setUp=fixture.V3APITests.setUp
 def test_draft_backup_roundtrip_and_invalid_drafts_do_not_replace_private_backup(self):
  x={'analystDrafts':{'records':[draft()]}};s.write_workspace(x);self.assertEqual(len(s.read_workspace()['snapshot']['analystDrafts']['records']),1);before=s.WORKSPACE_FILE.read_bytes();x['analystDrafts']['records'][0]['symbol']='BBB'
  with self.assertRaises(ValueError):s.write_workspace(x)
  self.assertEqual(s.WORKSPACE_FILE.read_bytes(),before)
 def test_empty_journal_and_validation_never_fetch(self):
  with patch.object(s,'provider_get',side_effect=AssertionError('No network')):
   self.assertEqual(s.handle_api('/api/v3/forecast-journal',{})['rows'],[]);self.assertEqual(lab3.post('/api/v3/drafts-validate',{'drafts':{}},vars(s))['records'],[])
 def test_unverified_listing_and_insufficient_history_reject_recording(self):
  with self.assertRaises(ValueError):f.create(vars(s),'AAA',ms('2026-11-03',8))
  with self.assertRaises(ValueError):f.create(vars(s),'AAPL',ms('2026-11-03',8))
 def test_assistant_uses_user_hypothesis_and_retains_grounding_checks(self):
  with patch.object(s,'ai_evidence',return_value={'sources':[],'asOf':NOW}),patch.object(r.research_ai,'start',return_value={'id':'synthetic-job'}) as start:
   result=lab3.post('/api/v3/scenario-assist',{'symbol':'AAA','question':'What could pricing change?','driver':'pricePct','change':7,'model':'local-test'},vars(s));self.assertEqual(result['id'],'synthetic-job');args=start.call_args.args;self.assertEqual(args[1],'answer');self.assertIn('7.0 percent',args[3]['sources'][0]['body']);self.assertIn('unapproved hypothesis',args[3]['sources'][0]['body'])
   long_question='x'*1400;lab3.post('/api/v3/scenario-assist',{'symbol':'AAA','question':long_question,'driver':'fixedCostPct','change':None,'model':'local-test'},vars(s));self.assertTrue(start.call_args.args[2].endswith(long_question));self.assertLessEqual(len(start.call_args.args[2]),1600)
 def test_assistant_rejects_unsupported_numbers_and_driver(self):
  for driver,value in [('pricePct',float('nan')),('pricePct',301),('fake',7)]:
   with self.subTest(driver=driver,value=value),self.assertRaises(ValueError):lab3.post('/api/v3/scenario-assist',{'symbol':'AAA','question':'What could change?','driver':driver,'change':value},vars(s))

 def seed_prices(self):
  issued=ms('2026-10-20',8);end=dt.date(2026,10,19);dates=[]
  while len(dates)<500:
   if end.weekday()<5:dates.append(end)
   end-=dt.timedelta(days=1)
  dates.reverse()
  with contextlib.closing(s.db_connection()) as c,c:
   for i,date in enumerate(dates):
    p=100*math.exp(.0002*i+.02*math.sin(i/9));c.execute('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)',('AAPL',ms(date.isoformat(),0),p,p,p,p,0,issued//1000))
  return issued
 def test_record_is_created_before_future_sessions_and_cannot_be_replaced(self):
  issued=self.seed_prices();x=f.create(vars(s),'AAPL',issued);self.assertEqual(x['anchorDay'],'2026-10-19');self.assertGreater(f.close_at(dt.date.fromisoformat(x['targetDays'][0])),x['issuedAt'])
  with self.assertRaises(ValueError):f.create(vars(s),'AAPL',issued)
  with contextlib.closing(s.db_connection()) as c:self.assertEqual(c.execute('SELECT count(*) FROM forecast35').fetchone()[0],1)
 def test_stale_data_and_preclose_fetches_cannot_be_recorded(self):
  issued=self.seed_prices()
  with self.assertRaises(ValueError):f.create(vars(s),'AAPL',ms('2026-10-21',8))
  with contextlib.closing(s.db_connection()) as c,c:c.execute('UPDATE massive_daily_bars SET fetched_at=? WHERE ts_ms=?',(ms('2026-10-19',15)//1000,ms('2026-10-19',0)))
  with self.assertRaises(ValueError):f.create(vars(s),'AAPL',issued)
 def test_future_outcomes_are_added_without_changing_forecast_receipt(self):
  issued=self.seed_prices();x=f.create(vars(s),'AAPL',issued)
  self.assertEqual(f.read(vars(s),issued)['rows'][0]['evaluation']['status'],'waiting')
  with contextlib.closing(s.db_connection()) as c,c:
   before=c.execute('SELECT body FROM forecast35').fetchone()[0]
   for date in x['targetDays']:
    p=x['model']['anchor']['p']*1.03;c.execute('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)',('AAPL',ms(date,0),p,p,p,p,0,ms(date,17)//1000))
  result=f.read(vars(s),ms('2026-10-27',18));self.assertEqual(result['summary']['all']['count'],1);self.assertAlmostEqual(result['rows'][0]['evaluation']['outcome']['actualReturnPct'],3)
  with contextlib.closing(s.db_connection()) as c:self.assertEqual(before,c.execute('SELECT body FROM forecast35').fetchone()[0])
  f.archive(vars(s),x['id'],True);self.assertEqual(f.read(vars(s),ms('2026-10-27',18))['summary']['all']['count'],1)
 def test_creation_endpoint_cannot_accept_a_client_prediction_or_backdate(self):
  with patch.object(f,'create',return_value={'issuedAt':999,'model':{'forecastPrice':123}}) as create:
   result=lab3.post('/api/v3/forecast-record',{'symbol':'AAPL','issuedAt':1,'forecastPrice':10000},vars(s));self.assertEqual(result['receipt']['issuedAt'],999);self.assertEqual(create.call_args.args[1],'AAPL')
  self.assertEqual(len(create.call_args.args),2)

 def test_archive_rejects_malformed_identifiers_without_touching_records(self):
  for ident in (None,{},123,'not-a-receipt'):
   with self.subTest(ident=ident),self.assertRaises(ValueError):f.archive(vars(s),ident,True)
