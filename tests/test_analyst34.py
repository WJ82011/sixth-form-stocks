"""Original analyst calculations: synthetic arithmetic, source controls and no future leakage."""
import copy,datetime as dt,math,unittest
from unittest.mock import patch
import analyst34 as a,market34 as m,workspace3 as w

def config():
 return {'baseline':{'symbol':'AAA','currency':'USD','taxonomy':'us-gaap','start':'2025-01-01','end':'2025-12-31','filed':'2026-02-01','url':'https://www.sec.gov/Archives/example','accession':'test-source','revenueM':100,'operatingProfitM':20,'costSalesM':40},'shared':{'affectedPct':100,'variableCostPct':40,'rationale':'Synthetic cost classification','noDoubleCount':True},'evidence':[],'scenarios':[{'name':name,'pricePct':0,'volumePct':0,'unitCostPct':0,'fixedCostPct':0,'rationale':'Synthetic conditional reference','product':{'enabled':False},'valuation':{'method':'none'}} for name in a.CASES],'capital':{'enabled':False}}
class AnalystTests(unittest.TestCase):
 def test_unchanged_business_conserves_baseline(self):
  x=a.calculate(config());self.assertEqual([c['revenueM'] for c in x['cases']],[100]*3);self.assertEqual(x['cases'][1]['operatingProfitM'],20)
 def test_price_and_volume_interact_and_cost_follows_volume(self):
  c=config();c['scenarios'][1].update(pricePct=10,volumePct=20);r=a.calculate(c)['cases'][1];self.assertEqual(r['revenueM'],132);self.assertEqual(r['coreVariableCostM'],48);self.assertEqual(r['operatingProfitM'],44)
 def test_affected_share_applies_only_to_price_volume(self):
  c=config();c['shared']['affectedPct']=50;c['scenarios'][1].update(pricePct=10,volumePct=20);r=a.calculate(c)['cases'][1];self.assertEqual(r['revenueM'],116);self.assertEqual(r['coreVariableCostM'],44)
 def test_unit_cost_and_fixed_cost_change_separately(self):
  c=config();c['scenarios'][1].update(unitCostPct=10,fixedCostPct=20);r=a.calculate(c)['cases'][1];self.assertEqual(r['operatingProfitM'],8)
 def test_launch_timing_recognition_and_cannibalisation(self):
  c=config();c['evidence']=[{'id':'e1','kind':'assumption','channel':'launch','title':'Synthetic','date':'2026-02-01','source':'Synthetic arithmetic assumption','text':'Not actual company data'}];c['scenarios'][1].update(evidenceIds=['e1'],product={'enabled':True,'name':'Synthetic product','unitsM':2,'netPerUnit':40,'launchMonth':7,'recognitionPct':50,'cannibalPct':25,'costPct':20});r=a.calculate(c)['cases'][1];self.assertEqual(r['launchRevenueM'],15);self.assertEqual(r['launchVariableCostM'],3);self.assertEqual(r['operatingProfitM'],32)
 def test_require_double_count_confirmation(self):
  c=config();c['shared']['noDoubleCount']=False
  with self.assertRaises(ValueError):a.calculate(c)
 def test_impossible_cost_classification_withheld(self):
  c=config();c['shared']['variableCostPct']=90
  with self.assertRaises(ValueError):a.calculate(c)
 def test_missing_and_nonfinite_inputs_rejected(self):
  for value in (None,float('nan'),float('inf'),True):
   c=config();c['scenarios'][1]['volumePct']=value
   with self.subTest(value=value),self.assertRaises(ValueError):a.calculate(c)
 def test_valuation_has_no_inferred_shares_or_currency(self):
  c=config();c['scenarios'][1]['valuation']={'method':'EV/Sales','multiple':3,'rationale':'Synthetic multiple'};r=a.calculate(c)['cases'][1];self.assertEqual(r['enterpriseValueM'],300);self.assertIsNone(r['valuePerListingUnit'])
 def test_explicit_capital_and_adr_ratio(self):
  c=config();c['scenarios'][1]['valuation']={'method':'EV/Sales','multiple':3,'rationale':'Synthetic multiple'};c['capital']={'enabled':True,'sharesM':10,'listingRatio':2,'netDebtM':50,'otherClaimsM':10,'source':'Synthetic capital fixture','unitsConfirmed':True};self.assertEqual(a.calculate(c)['cases'][1]['valuePerListingUnit'],48)
 def test_negative_operating_profit_multiple_withheld(self):
  c=config();c['scenarios'][1].update(volumePct=-50,valuation={'method':'EV/Operating profit','multiple':10,'rationale':'Synthetic'});self.assertIsNone(a.calculate(c)['cases'][1]['enterpriseValueM'])
 def test_unique_three_cases_required(self):
  c=config();c['scenarios'][2]['name']='Base'
  with self.assertRaises(ValueError):a.calculate(c)
 def test_public_source_credentials_and_future_dates_rejected(self):
  for url in ('https://example.com/x?key=secret','http://example.com/x','https://user:secret@example.com/x'):
   c=config();c['baseline']['url']=url
   with self.assertRaises(ValueError):a.calculate(c)
 def test_snapshots_immutable_in_workspace_and_old_backups_upgrade(self):
  s=w.normalise({});self.assertEqual(s['analyst']['snapshots'],[]);s=w.mutate(s,'analyst.save',{'id':'s1','title':'Synthetic','config':config()});self.assertEqual(len(s['analyst']['snapshots']),1)
  with self.assertRaises(ValueError):w.mutate(s,'analyst.save',{'id':'s1','title':'Overwrite','config':config()})
  with self.assertRaises(ValueError):w.mutate(s,'analyst.remove',{'id':'s1'})
  s=w.mutate(s,'analyst.archive',{'id':'s1','archived':True});self.assertEqual(w.mutate(s,'analyst.remove',{'id':'s1'})['analyst']['snapshots'],[])
 def test_snapshot_cannot_include_later_filing(self):
  x={'snapshots':[{'id':'s1','title':'Synthetic','createdAt':'2026-01-01T12:00:00+00:00','config':config()}]}
  with self.assertRaises(ValueError):a.normalise(x)
 def test_ai_source_labels_conditional_not_reported_guidance(self):
  s=a.mutate({},'save',{'id':'s1','title':'Synthetic','config':config()});p=a.evidence_packet(s,'AAA');self.assertEqual(p[0]['id'],'A1');self.assertIn('not reported guidance',p[0]['body']);self.assertEqual(a.evidence_packet(s,'BBB'),[])
 def test_sensitivity_does_not_mutate_input(self):
  c=config();before=copy.deepcopy(c);r=a.calculate(c);self.assertEqual(c,before);self.assertEqual(len(r['sensitivity']),4)

 def test_launch_requires_evidence_reference(self):
  c=config();c['scenarios'][1]['product']={'enabled':True,'name':'Synthetic','unitsM':1,'netPerUnit':10,'launchMonth':1,'recognitionPct':100,'cannibalPct':0,'costPct':40}
  with self.assertRaises(ValueError):a.calculate(c)
 def test_source_book_currency_and_filing_alignment(self):
  b=config()['baseline'];f={'value':100000000,'unit':'USD','start':b['start'],'end':b['end'],'filed':b['filed'],'accession':b['accession'],'url':b['url']};op={**f,'value':20000000};book={'currency':'USD','taxonomy':'us-gaap','annual':[{'metrics':{'revenue':f,'operatingProfit':op}}]};report={'statementBooks':[book]}
  self.assertEqual(a.source_pack(report,'AAA')[0]['baseline']['revenueM'],100)
  book['currency']='TWD';self.assertEqual(a.source_pack(report,'AAA'),[])
  book['currency']='USD';op['accession']='different-filing';self.assertEqual(a.source_pack(report,'AAA'),[])
 def test_cost_proxy_does_not_mix_currencies_or_periods(self):
  b=config()['baseline'];f={'value':100000000,'unit':'USD','start':b['start'],'end':b['end'],'filed':b['filed'],'accession':b['accession'],'url':b['url']};report={'statementBooks':[{'currency':'USD','taxonomy':'us-gaap','annual':[{'metrics':{'revenue':f,'operatingProfit':{**f,'value':20000000},'costSales':{**f,'unit':'TWD','value':40000000}}}]}]}
  self.assertIsNone(a.source_pack(report,'AAA')[0]['baseline']['costSalesM'])

 def test_news_questions_keep_news_ahead_of_saved_cases_in_bounded_packet(self):
  sources=[{'id':x} for x in ['C0','A1','A2','A3','A4','T1','N1','N2','M1']];order=[x['id'] for x in a.prioritise_sources(sources,'Explain the latest company news')];self.assertEqual(order[:2],['N1','N2']);self.assertGreater(order.index('A1'),order.index('M1'))
 def test_saved_case_questions_retain_all_scenarios_and_chart_scope_stays_separate(self):
  sources=[{'id':x} for x in ['N1','T1','A1','A2','A3','A4','P1','M1']];self.assertEqual([x['id'] for x in a.prioritise_sources(sources,'Explain my saved analyst worksheet')][:4],['A1','A2','A3','A4']);self.assertEqual(a.prioritise_sources(sources,'Explain this price chart')[0]['id'],'P1')

def prices(count=400):
 end=dt.datetime(2026,10,30,tzinfo=dt.timezone.utc);days=[];d=end
 while len(days)<count:
  if d.weekday()<5:days.append(d)
  d-=dt.timedelta(days=1)
 days.reverse();return [{'t':int(d.timestamp()*1000),'p':100*math.exp(.0003*i+.025*math.sin(i/11)+.008*math.cos(i/3))} for i,d in enumerate(days)]
NOW=int(dt.datetime(2026,11,1,tzinfo=dt.timezone.utc).timestamp()*1000)
class MarketTests(unittest.TestCase):
 def test_insufficient_does_not_invent_history(self):self.assertEqual(m.run(prices(100),now=NOW)['status'],'insufficient')
 def test_walkforward_only_trains_on_known_targets(self):
  r=m.run(prices(),now=NOW);self.assertEqual(r['status'],'ok');self.assertTrue(all(x['lastTrainingTarget']<=x['anchor']<x['target'] for x in r['tests']));self.assertGreater(r['backtest']['cases'],20)
 def test_prefix_results_identical_without_future_data(self):
  p=prices();a=m.run(p[:300],now=NOW);b=m.run(p,now=NOW);self.assertEqual(a['tests'],b['tests'][:len(a['tests'])])
 def test_baseline_errors_recomputed_from_holdouts(self):
  r=m.run(prices(),now=NOW);expected=sum(abs(math.expm1(x['actualLogReturn'])*100) for x in r['tests'])/len(r['tests']);self.assertAlmostEqual(r['backtest']['unchangedPriceErrorPP'],expected)
 def test_interval_coverage_uses_only_prior_errors(self):
  r=m.run(prices(),now=NOW);self.assertEqual(r['backtest']['sequentialRangeCases'],r['backtest']['cases']-20)
 def test_stale_series_has_tests_but_no_current_prediction(self):
  r=m.run(prices(),now=NOW+20*m.DAY);self.assertTrue(r['stale']);self.assertIsNone(r['forecastPrice']);self.assertIsNone(r['range']);self.assertGreater(r['backtest']['cases'],0)
 def test_aligned_benchmark_and_missing_fallback(self):
  p=prices();r=m.run(p,p,now=NOW);self.assertTrue(r['benchmarkUsed']);self.assertEqual(len(r['features']),7);self.assertFalse(m.run(p,p[-100:],now=NOW)['benchmarkUsed'])
 def test_duplicates_and_large_gaps(self):
  p=prices()
  with self.assertRaises(ValueError):m.run(p+[p[-1]],now=NOW)
  self.assertEqual(m.run(p[:100]+p[110:],now=NOW)['status'],'withheld')
 def test_flat_series_remains_finite_and_has_zero_error(self):
  p=prices();p=[{**x,'p':100} for x in p];r=m.run(p,now=NOW);self.assertEqual(r['forecastPrice'],100);self.assertEqual(r['backtest']['absoluteReturnErrorPP'],0);self.assertIsNone(r['backtest']['skillVsUnchangedPct'])
 def test_extreme_move_withheld(self):
  p=prices();p[-1]['p']*=10;self.assertEqual(m.run(p,now=NOW)['status'],'withheld')

import test_v3_api as fixture
s=fixture.s
import lab3
class AnalystAPITests(unittest.TestCase):
 setUp=fixture.V3APITests.setUp
 # Reuse temporary database setup, without duplicating inherited test methods.
 def test_analyst_reads_and_price_training_never_fetch(self):
  with patch.object(s,'provider_get',side_effect=AssertionError('No provider request')),patch.object(s,'sec_saved',return_value={}):
   r=s.handle_api('/api/v3/analyst-source',{'symbol':['AAA']});self.assertEqual(r['books'],[])
   r=lab3.post('/api/v3/market-model',{'symbol':'AAA'},vars(s));self.assertEqual(r['status'],'insufficient')
   with self.assertRaises(ValueError):lab3.post('/api/v3/analyst-calculate',{'symbol':'AAA','bookIndex':0,'config':config()},vars(s))
 def test_calculation_uses_server_baseline_not_client_claims(self):
  c=config();b=a.baseline(c['baseline']);c['baseline']['revenueM']=99999
  with patch.object(a,'source_pack',return_value=[{'bookIndex':0,'baseline':b}]),patch.object(s,'sec_saved',return_value={}):
   with self.assertRaises(ValueError):lab3.post('/api/v3/analyst-calculate',{'symbol':'AAA','bookIndex':0,'config':c},vars(s))
   c['baseline']=b;r=lab3.post('/api/v3/analyst-calculate',{'symbol':'AAA','bookIndex':0,'config':c},vars(s));self.assertEqual(r['cases'][1]['revenueM'],100)
 def test_full_backup_includes_saved_assumptions_and_rejects_corruption_atomically(self):
  state=w.mutate({},'analyst.save',{'id':'s1','title':'Synthetic fixture','config':config()});s.write_workspace({'v3':state});before=s.WORKSPACE_FILE.read_bytes();self.assertEqual(s.read_workspace()['snapshot']['v3']['analyst'],state['analyst'])
  state['analyst']['snapshots'][0]['config']['shared']['variableCostPct']=190
  with self.assertRaises(ValueError):s.write_workspace({'v3':state})
  self.assertEqual(s.WORKSPACE_FILE.read_bytes(),before)

 def test_frozen_review_preserves_original_horizon_and_case_inputs(self):
  x={'id':'s1','title':'Synthetic','createdAt':'2026-06-01T12:00:00+00:00','config':config()};r=lab3.post('/api/v3/analyst-review',{'snapshot':x},vars(s));self.assertEqual(r['horizonEnd'],'2027-06-01');self.assertEqual(r['cases'][1]['revenueM'],100)
 def test_current_new_york_session_is_not_used_as_a_completed_close(self):
  now=int(dt.datetime.now(dt.timezone.utc).timestamp());bar={'bars':{'t':[now],'c':[100]},'fetched_at':now*1000}
  with patch.object(s,'read_massive_daily_bars',return_value=bar):r=lab3.post('/api/v3/market-model',{'symbol':'AAA'},vars(s));self.assertEqual(r['count'],0)

 def test_saved_cases_enter_local_ai_packet_as_conditional_sources(self):
  state=w.mutate({},'analyst.save',{'id':'s1','title':'Synthetic','config':config()});s.write_workspace({'v3':state})
  with patch.object(s,'provider_get',side_effect=AssertionError('No network')):r=s.ai_evidence('AAA','Explain the saved business cases')
  sources={x['id']:x for x in r['sources']};self.assertTrue({'A1','A2','A3','A4'}<=set(sources));self.assertIn('User assumptions, not reported guidance',sources['A2']['body']);self.assertEqual(sources['A2']['url'],'')
