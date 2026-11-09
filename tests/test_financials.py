"""Synthetic filing fixtures. No live data, credentials or investment conclusions."""
import copy,datetime as dt,json,sqlite3,tempfile,unittest,urllib.error
from pathlib import Path
from unittest.mock import patch,Mock
import financials as f
import sec_accounts as sec
NOW=1793880000000
TODAY=dt.date(2026,11,5)
ACC='0000320193-26-000001'
def row(value,start='2025-01-01',end='2025-12-31',filed='2026-02-01',acc=ACC,form='10-K',**other):
 r={'val':value,'end':end,'filed':filed,'accn':acc,'form':form,'fy':2026,'fp':'FY'}
 if start is not None:r['start']=start
 return {**r,**other}
def fixture():
 tags={'RevenueFromContractWithCustomerExcludingAssessedTax':[row(1200),row(1000,'2024-01-01','2024-12-31')], 'NetIncomeLoss':[row(120),row(-100,'2024-01-01','2024-12-31')], 'NetCashProvidedByUsedInOperatingActivities':[row(180)],'CashAndCashEquivalentsAtCarryingValue':[row(300,None)],'Assets':[row(2000,None)],'Liabilities':[row(1000,None)],'LongTermDebtCurrent':[row(0,None)],'LongTermDebtNoncurrent':[row(400,None)]}
 return {'cik':320193,'entityName':'Synthetic Company','facts':{'us-gaap':{tag:{'units':{'USD':rows}} for tag,rows in tags.items()}}}
def norm(raw=None):return f.normalise_facts(raw or fixture(),320193,{'cik':'0000320193','name':'Synthetic Company'},TODAY)
class FinancialTests(unittest.TestCase):
 def test_actual_periods_not_filing_fiscal_year(self):
  r=norm();self.assertEqual([x['end'] for x in r['annual']],['2024-12-31','2025-12-31']);self.assertEqual(r['annual'][-1]['start'],'2025-01-01')
 def test_computed_ratios_and_zero_debt_portion(self):
  p=norm()['annual'][-1];self.assertEqual(p['netMarginPct'],10);self.assertAlmostEqual(p['revenueGrowthPct'],20);self.assertEqual(p['longTermDebt'],400)
 def test_missing_debt_is_not_zero(self):
  raw=fixture();del raw['facts']['us-gaap']['LongTermDebtCurrent'];self.assertIsNone(norm(raw)['annual'][-1]['longTermDebt'])
 def test_cash_flow_year_to_date_is_not_quarter(self):
  raw=fixture();g=raw['facts']['us-gaap'];g['NetIncomeLoss']['units']['USD']+=[row(50,'2026-07-01','2026-09-30','2026-10-30',form='10-Q')];g['NetCashProvidedByUsedInOperatingActivities']['units']['USD']+=[row(200,'2026-01-01','2026-09-30','2026-10-30',form='10-Q')]
  p=norm(raw)['quarterly'][-1];self.assertEqual(p['metrics']['profit']['value'],50);self.assertIsNone(p['metrics']['operatingCash']);self.assertEqual(len(norm(raw)['quarterly']),1)
 def test_quarter_never_summed_or_q4_inferred(self):
  r=norm();self.assertEqual(r['quarterly'],[])
 def test_latest_amendment_disclosed_and_point_in_time_not_claimed(self):
  raw=fixture();raw['facts']['us-gaap']['NetIncomeLoss']['units']['USD'].append(row(80,filed='2026-03-01',acc='0000320193-26-000002',form='10-K/A'))
  r=norm(raw);p=r['annual'][-1];self.assertEqual(p['metrics']['profit']['value'],80);self.assertTrue(p['metrics']['profit']['amended']);self.assertTrue(p['warnings']);self.assertIsNone(p['netMarginPct'],'Do not mix filing versions in a ratio');self.assertIn('not what was known',r['notice'])
 def test_no_future_filings_non_finite_or_bool_values(self):
  for invalid in (row(999,filed='2027-01-01'),row(True),row(float('inf')),row(float('nan')),row(1,end='2027-01-01'),row(2,acc='bad')):
   raw=fixture();raw['facts']['us-gaap']['NetIncomeLoss']['units']['USD']=[invalid];self.assertIsNone(norm(raw)['annual'][-1]['metrics']['profit'])
 def test_conflicting_same_filing_values_withheld(self):
  raw=fixture();raw['facts']['us-gaap']['NetIncomeLoss']['units']['USD'].append(row(99));p=norm(raw)['annual'][-1];self.assertIn('missing',p['metrics']['profit']);self.assertIsNone(p['netMarginPct'])
 def test_units_never_convert_or_mix(self):
  raw=fixture();raw['facts']['us-gaap']['NetIncomeLoss']['units']={'EUR':[row(99)],'USD-per-shares':[row(3)]};r=norm(raw);self.assertIsNone(r['annual'][-1]['metrics']['profit']);self.assertEqual(r['otherCurrenciesNotUsed'],['EUR'])
 def test_currency_and_custom_ifrs_coverage_honest(self):
  raw=fixture();raw['facts']={'ifrs-full':raw['facts']['us-gaap']};r=norm(raw);self.assertEqual(r['status'],'unsupported');self.assertEqual(r['annual'],[])
 def test_issuer_mismatch_stops(self):
  with self.assertRaises(ValueError):f.normalise_facts(fixture(),123,{'cik':'123'},TODAY)
 def test_growth_withheld_after_tag_change_or_nonpositive_base(self):
  raw=fixture();g=raw['facts']['us-gaap'];g['RevenueFromContractWithCustomerExcludingAssessedTax']['units']['USD']=[row(1200)];g['Revenues']={'units':{'USD':[row(1000,'2024-01-01','2024-12-31')]}};self.assertIsNone(norm(raw)['annual'][-1]['revenueGrowthPct'])
  g['RevenueFromContractWithCustomerExcludingAssessedTax']['units']['USD'].append(row(0,'2024-01-01','2024-12-31'));self.assertIsNone(norm(raw)['annual'][-1]['revenueGrowthPct'])
 def test_comparison_requires_shared_window(self):
  a=norm();a['symbol']='AAA';b=copy.deepcopy(a);b['symbol']='BBB';r=f.compare([a,b]);self.assertTrue(r['aligned']);self.assertEqual(len(r['rows']),2)
  for p in b['annual']:p.update(start=p['start'].replace('-01-01','-04-01'),end=p['end'].replace('-12-31','-09-30'))
  r=f.compare([a,b]);self.assertFalse(r['aligned']);self.assertIn('without rankings',r['basis'])
 def test_evidence_sources_cite_the_filing_of_each_fact(self):
  raw=fixture();raw['facts']['us-gaap']['CashAndCashEquivalentsAtCarryingValue']['units']['USD'].append(row(320,None,filed='2026-03-01',acc='0000320193-26-000002',form='10-Q'))
  r=norm(raw);sources=f.evidence(r);self.assertTrue(any('Cash and cash equivalents = 320' in x['body'] and '0000320193-26-000002' in x['url'] for x in sources));self.assertIn('Reported net profit/loss is higher',f.overview(r))
 def test_cash_restricted_and_total_debt_not_silently_substituted(self):
  raw=fixture();g=raw['facts']['us-gaap'];del g['CashAndCashEquivalentsAtCarryingValue'];g['CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents']={'units':{'USD':[row(500,None)]}};r=norm(raw);self.assertIsNone(r['annual'][-1]['metrics']['cash']);self.assertIn('not total debt',r['annual'][-1]['debtScope'])
 def test_same_day_different_filings_cannot_imply_known_order(self):
  raw=fixture();raw['facts']['us-gaap']['NetIncomeLoss']['units']['USD'].append(row(80,acc='0000320193-26-000002'))
  self.assertIn('missing',norm(raw)['annual'][-1]['metrics']['profit'])
 def test_ambiguous_period_starts_are_disclosed(self):
  raw=fixture();raw['facts']['us-gaap']['NetIncomeLoss']['units']['USD'].append(row(90,start='2025-01-02'))
  r=norm(raw);self.assertTrue(r['excludedPeriods']);self.assertFalse(any(p['end']=='2025-12-31' for p in r['annual']))
 def test_readable_evidence_preserves_signed_loss_and_dates_without_relaxing_checks(self):
  import research_ai
  raw=fixture();raw['facts']['us-gaap']['NetIncomeLoss']['units']['USD']=[row(-298200000)]
  r=norm(raw);sources=f.evidence(r);source=next(x for x in sources if 'Net profit or loss = -298200000' in x['body'])
  self.assertIn('298.2 million USD',source['body']);self.assertIn('December 31, 2025',source['body'])
  draft={'title':'Loss in annual accounts','sections':[{'heading':'Reported loss','bullets':[{'text':'A net loss of 298.2 million USD was reported for the year ending December 31, 2025.','kind':'fact','evidence':[{'id':source['id'],'excerpt':'Net loss amount = 298200000 USD (298.2 million USD).'}]}]}],'missing':[]}
  result=research_ai.verify(draft,{'sources':sources});self.assertTrue(result['checks']['sourceLinksMatched'])
  draft['sections'][0]['bullets'][0]['text']='The loss was 999.9 million USD.'
  with self.assertRaises(research_ai.AIError):research_ai.verify(draft,{'sources':sources})
 def test_malformed_fact_container_is_rejected(self):
  raw=fixture();raw['facts']=[]
  with self.assertRaises(ValueError):norm(raw)
 def test_ai_rejects_false_missing_sec_metadata_claims(self):
  import research_ai
  sources=f.evidence(norm());source=next(x for x in sources if 'Annual period 2025-01-01' in x['body']);packet={'sources':sources}
  excerpt='Annual period 2025-01-01 to 2025-12-31.'
  def draft(text,missing=None):return {'title':'Accounts','sections':[{'heading':'Context','bullets':[{'text':text,'kind':'analysis','evidence':[{'id':source['id'],'excerpt':excerpt}]}]}],'missing':missing or []}
  for text in ('The evidence does not specify the exact filing date.','The provided sources do not contain any previous fiscal year data.'):
   with self.assertRaises(research_ai.AIError):research_ai.verify(draft(text),packet)
  with self.assertRaises(research_ai.AIError):research_ai.verify(draft('The accounts have a reported period.',['Exact filing date of the latest annual report']),packet)
  research_ai.verify(draft('A filing date is not a live stock price.'),packet)
  research_ai.verify(draft('The next filing date is unknown.'),packet)
class ServiceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'test.sqlite3'
  with self.connect() as con:sec.init(con)
 def connect(self):return sqlite3.connect(self.path)
 def fetch(self,url,*args):return {'cik':'0000320193','tickers':['AAPL'],'name':'Synthetic'} if '/submissions/' in url else fixture()
 def test_refresh_verifies_identity_and_cache_reads_are_offline(self):
  with patch.object(sec,'fetch_json',side_effect=self.fetch) as call:
   r=sec.update(self.connect,'AAPL',NOW);self.assertEqual(call.call_count,2);self.assertEqual(r['symbol'],'AAPL')
   cached=sec.update(self.connect,'AAPL',NOW+100);self.assertEqual(call.call_count,2);self.assertTrue(cached['cached']);self.assertEqual(cached['fetchedAt'],NOW)
   with self.connect() as con:self.assertEqual(sec.read(con,'AAPL',NOW+100)['fetchedAt'],NOW)
 def test_failure_does_not_replace_previous_source_date(self):
  with patch.object(sec,'fetch_json',side_effect=self.fetch):sec.update(self.connect,'AAPL',NOW)
  with patch.object(sec,'fetch_json',side_effect=sec.SECError('Blocked')):
   with self.assertRaises(sec.SECError):sec.update(self.connect,'AAPL',NOW+2*sec.TTL)
  with self.connect() as con:self.assertEqual(sec.read(con,'AAPL')['fetchedAt'],NOW)
 def test_issuer_ticker_mismatch_is_not_saved(self):
  with patch.object(sec,'fetch_json',return_value={'cik':'320193','tickers':['WRONG']}):
   with self.assertRaises(sec.SECError):sec.update(self.connect,'AAPL',NOW)
  with self.connect() as con:self.assertEqual(sec.read(con,'AAPL')['status'],'not_loaded')
 def test_dynamic_directory_requires_confirmation_in_submissions(self):
  def fetch(url,*args):
   if url==sec.DIRECTORY:return {'0':{'ticker':'TEST','cik_str':320193}}
   if '/submissions/' in url:return {'cik':'320193','tickers':['TEST'],'name':'Test'}
   return fixture()
  with patch.object(sec,'fetch_json',side_effect=fetch) as call:r=sec.update(self.connect,'TEST',NOW)
  self.assertEqual(call.call_count,3);self.assertEqual(r['cik'],'0000320193')
 def test_fixed_endpoint_and_redirect_guard(self):
  with self.assertRaises(sec.SECError):sec.fetch_json('https://example.com/file')
  with self.assertRaises(sec.SECError):sec.NoRedirect().redirect_request(None,None,None,None,None,None)
 def test_rate_limit_sets_cooldown_no_retry(self):
  opener=Mock();opener.open.side_effect=urllib.error.HTTPError(sec.DIRECTORY,429,'test',{},None)
  with patch.object(sec,'BACKOFF',0),patch.object(sec,'LAST_REQUEST',0),patch.object(sec.urllib.request,'build_opener',return_value=opener):
   with self.assertRaisesRegex(sec.SECError,'HTTP 429'):sec.fetch_json(sec.DIRECTORY)
   with self.assertRaisesRegex(sec.SECError,'cooling down'):sec.fetch_json(sec.DIRECTORY)
   self.assertEqual(opener.open.call_count,1)
 def test_serial_refresh_lock(self):
  sec.NETWORK.acquire()
  try:
   with self.assertRaisesRegex(sec.SECError,'Another'):sec.update(self.connect,'AAPL',NOW)
  finally:sec.NETWORK.release()
 def test_no_credentials_or_raw_big_facts_stored(self):
  raw=fixture();raw['privateDummy']='SHOULD-NOT-PERSIST'
  def fetch(url,*args):return self.fetch(url) if '/submissions/' in url else raw
  with patch.object(sec,'fetch_json',side_effect=fetch):sec.update(self.connect,'AAPL',NOW)
  with self.connect() as con:body=con.execute('SELECT body FROM sec_accounts').fetchone()[0]
  self.assertNotIn('SHOULD-NOT-PERSIST',body);self.assertNotIn('User-Agent',body)
