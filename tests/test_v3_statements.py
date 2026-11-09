"""Synthetic cumulative accounts and currency fixtures, never market data."""
import copy,datetime as dt,unittest
import financials,statements3 as s,workspace3
TODAY=dt.date(2026,11,5)
def row(value,start,end,filed='2026-03-01',acc='0000000001-26-000001',form='10-K'):
 r={'val':value,'end':end,'filed':filed,'accn':acc,'form':form}
 if start:r['start']=start
 return r
def raw():
 dates=[('2025-01-01','2025-03-31',100),('2025-01-01','2025-06-30',230),('2025-01-01','2025-09-30',390),('2025-01-01','2025-12-31',600)]
 tags={t:{'units':{'USD':[row(v,a,b) for a,b,v in dates]}} for t in ('RevenueFromContractWithCustomerExcludingAssessedTax','NetIncomeLoss','NetCashProvidedByUsedInOperatingActivities','PaymentsToAcquirePropertyPlantAndEquipment')}
 return {'cik':1,'facts':{'us-gaap':tags}}
def books(r=None):return s.build(r or raw(),1,{'cik':'1','name':'Synthetic'},TODAY)
class StatementTests(unittest.TestCase):
 def test_three_statement_groups_and_annual(self):
  b=books()[0];self.assertIn('income',b['groups'].values());self.assertIn('cashflow',b['groups'].values());self.assertIn('balance',b['groups'].values());self.assertEqual(b['annual'][0]['metrics']['revenue']['value'],600)
 def test_ytd_differences_are_explicit_derived_quarters(self):
  b=books()[0];values=[p['metrics']['revenue']['value'] for p in b['derivedQuarters']];self.assertEqual(values,[130,160,210]);self.assertTrue(b['derivedQuarters'][0]['metrics']['revenue']['derived']);self.assertEqual(len(b['derivedQuarters'][0]['metrics']['revenue']['inputs']),2)
 def test_direct_ttm_missing_until_derived_opt_in(self):
  b=books()[0];self.assertEqual(b['ttmDirect'],[]);self.assertEqual(b['ttmWithDerived'][-1]['metrics']['revenue']['value'],600)
 def test_missing_cumulative_period_withholds_affected_quarter(self):
  r=raw();r['facts']['us-gaap']['NetCashProvidedByUsedInOperatingActivities']['units']['USD'].pop(1);b=books(r)[0]
  self.assertNotIn('operatingCash',b['ttmWithDerived'][-1]['metrics'])
 def test_currencies_do_not_convert_or_mix(self):
  r=raw();r['facts']['us-gaap']['NetIncomeLoss']['units']={'EUR':[row(90,'2025-01-01','2025-12-31')]};bb=books(r);usd=next(x for x in bb if x['currency']=='USD');self.assertIsNone(usd['annual'][0]['metrics']['profit'])
 def test_ifrs_forms_and_source_concepts(self):
  r={'cik':1,'facts':{'ifrs-full':{'Revenue':{'units':{'TWD':[row(500,'2025-01-01','2025-12-31',form='20-F')]}},'ProfitLoss':{'units':{'TWD':[row(100,'2025-01-01','2025-12-31',form='20-F')]}}}}}
  b=books(r)[0];f=b['annual'][0]['metrics']['revenue'];self.assertEqual((b['currency'],f['taxonomy'],f['form']),('TWD','ifrs-full','20-F'));self.assertIsNone(b['annual'][0]['longTermDebt'])
 def test_cash_investing_outflow_and_negative_equity_retained(self):
  r=raw();r['facts']['us-gaap']['NetCashProvidedByUsedInInvestingActivities']={'units':{'USD':[row(-200,'2025-01-01','2025-12-31')]}};r['facts']['us-gaap']['StockholdersEquity']={'units':{'USD':[row(-50,None,'2025-12-31')]}}
  m=books(r)[0]['annual'][0]['metrics'];self.assertEqual(m['investingCash']['value'],-200);self.assertEqual(m['equity']['value'],-50)
 def test_no_mixed_tags_in_ttm(self):
  b=books()[0];q=s.merge_quarters(b['quarterly'],b['derivedQuarters']);q[1]['metrics']['revenue']['tag']='DifferentConcept';self.assertNotIn('revenue',s.ttm(q)[-1]['metrics'])
 def test_manual_extensions_separate_and_validated(self):
  row={'id':'a','symbol':'AAA','statement':'income','label':'Company adjusted custom line','value':100,'currency':'USD','start':'2025-01-01','end':'2025-12-31','source':'Synthetic filing source'}
  state=workspace3.mutate({},'statement.add',{'row':row});self.assertFalse(state['manualStatements'][0]['verified']);self.assertEqual(state['ledger'],[])
  row['start']='bad'
  with self.assertRaises(ValueError):s.manual_rows([row])
 def test_csv_import_atomic_and_nonfinite_rejected(self):
  csv='statement,label,value,currency,start,end,source\nincome,Custom,100,USD,2025-01-01,2025-12-31,Synthetic source'
  state=workspace3.mutate({},'statement.import',{'symbol':'AAA','csv':csv});self.assertEqual(len(state['manualStatements']),1)
  with self.assertRaises(ValueError):workspace3.mutate(state,'statement.import',{'symbol':'AAA','csv':csv.replace(',100,',',NaN,')})
  self.assertEqual(len(state['manualStatements']),1)
 def test_derived_values_cannot_be_reported_without_label(self):
  b=books()[0];self.assertEqual(b['derivedQuarters'][0]['type'],'derived quarter');self.assertIn('calculation',b['ttmWithDerived'][0]['metrics']['profit'])
 def test_ttm_has_no_overlapping_or_gapped_quarters(self):
  b=books()[0];q=s.merge_quarters(b['quarterly'],b['derivedQuarters']);q[1]['start']='2025-04-02';self.assertEqual(s.ttm(q),[])
 def test_statement_evidence_retains_currency_and_filing(self):
  r={'name':'Synthetic','statementBooks':books(),'fetchedAt':1};e=s.evidence(r);self.assertTrue(e);self.assertIn('Annual period',e[0]['body']);self.assertIn('USD',e[0]['body']);self.assertTrue(e[0]['url'].startswith('https://www.sec.gov/'))
