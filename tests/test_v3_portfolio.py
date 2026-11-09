"""Synthetic hypothetical ledger fixtures; never real trade data."""
import copy,datetime as dt,unittest
import portfolio3 as p,workspace3 as w

def e(kind,id='x',date='2025-01-02',**fields):return {'id':id,'kind':kind,'date':date,'source':'Synthetic test record',**fields}
def buy(id='b',**kw):return e('BUY',id,quantity=10,price=10,symbol='AAA',currency='USD',fx=1,fee=0,**kw)
def mark(sym='AAA',date='2025-01-03',price=20,**kw):return {'symbol':sym,'date':date,'price':price,'currency':'USD','fx':1,'source':'Synthetic dated test quote',**kw}
class PortfolioTests(unittest.TestCase):
 def ledger(self):return [e('DEPOSIT','d',amount=1000),buy()]
 def test_cash_fifo_and_fees(self):
  ledger=[e('DEPOSIT','d',amount=1000),e('BUY','b1',symbol='AAA',quantity=10,price=10,fee=2),e('BUY','b2',symbol='AAA',quantity=10,price=20,fee=2),e('SELL','s',symbol='AAA',quantity=15,price=30,fee=3)]
  r=p.calculate(ledger,[mark()],as_of='2025-01-03');self.assertEqual(r['cashUSD'],1143);self.assertEqual(r['realisedUSD'],244);self.assertEqual(r['holdings'][0]['costBasisUSD'],101);self.assertEqual(r['feesUSD'],7);self.assertEqual(r['totalValueUSD'],1243)
 def test_deposits_withdrawals_are_not_profit(self):
  ledger=[e('DEPOSIT','d',amount=1000),e('WITHDRAW','w',amount=200)]
  r=p.calculate(ledger,as_of='2025-01-03');self.assertEqual(r['gainAfterCashFlowsUSD'],0);self.assertEqual(r['cashUSD'],800)
 def test_dividend_deductions_are_income_not_external_flows(self):
  ledger=self.ledger()+[e('DIVIDEND','div',symbol='AAA',amount=20,fee=3)]
  r=p.calculate(ledger,[mark(price=10)],as_of='2025-01-03');self.assertEqual(r['netDividendsUSD'],17);self.assertEqual(r['gainAfterCashFlowsUSD'],17);self.assertEqual(r['depositsUSD'],1000)
 def test_explicit_fx_cost_and_mark(self):
  ledger=[e('DEPOSIT','d',amount=1000),e('BUY','b',symbol='UK.L',quantity=10,price=10,currency='GBP',fx=1.2,fee=1,fxSource='Synthetic dated FX record')]
  m={'symbol':'UK.L','date':'2025-01-03','currency':'GBP','price':12,'fx':1.3,'source':'Synthetic mark','fxSource':'Synthetic dated FX'}
  r=p.calculate(ledger,[m],as_of='2025-01-03');self.assertAlmostEqual(r['holdings'][0]['costBasisUSD'],121.2);self.assertAlmostEqual(r['holdings'][0]['valueUSD'],156)
 def test_fx_source_and_usd_identity_are_required(self):
  for fields in ({'currency':'GBP','fx':1.2},{'currency':'USD','fx':1.2}):
   with self.assertRaises(ValueError):p.events([e('BUY',symbol='AAA',quantity=1,price=10,**fields)])
 def test_split_changes_quantity_not_cost(self):
  ledger=self.ledger()+[e('SPLIT','split',symbol='AAA',ratio=2),e('SELL','s',symbol='AAA',quantity=5,price=12)]
  r=p.calculate(ledger,[mark(price=12)],as_of='2025-01-03');self.assertEqual(r['holdings'][0]['quantity'],15);self.assertEqual(r['holdings'][0]['costBasisUSD'],75);self.assertEqual(r['realisedUSD'],35)
 def test_missing_and_stale_marks_withhold_total_and_weights(self):
  for marks in ([],[mark(date='2024-01-02')]):
   r=p.calculate(self.ledger(),marks,as_of='2025-01-03');self.assertFalse(r['complete']);self.assertIsNone(r['totalValueUSD']);self.assertIsNone(r['holdings'][0]['weightPct'])
 def test_wrong_currency_mark_does_not_value_holding(self):
  m=mark();m.update(currency='EUR',fx=1.1,fxSource='Synthetic FX')
  self.assertFalse(p.calculate(self.ledger(),[m],as_of='2025-01-03')['complete'])
 def test_same_day_entry_order_is_explicit(self):
  with self.assertRaises(ValueError):p.calculate([buy(),e('DEPOSIT','d',amount=1000)],as_of='2025-01-03')
 def test_oversell_negative_cash_and_duplicate_ids_rejected(self):
  for ledger in (self.ledger()+[e('SELL','s',symbol='AAA',quantity=11,price=20)], [e('WITHDRAW','w',amount=1)],[e('DEPOSIT','d',amount=10),e('DEPOSIT','d',amount=10)]):
   with self.assertRaises(ValueError):p.calculate(ledger,as_of='2025-01-03')
 def test_bool_nonfinite_future_records_rejected(self):
  for amount in (True,float('inf'),float('nan'),-1):
   with self.assertRaises(ValueError):p.events([e('DEPOSIT',amount=amount)])
  future=(dt.datetime.now(dt.timezone.utc).date()+dt.timedelta(days=1)).isoformat()
  with self.assertRaises(ValueError):p.events([e('DEPOSIT',date=future,amount=10)])
 def test_split_precision_and_quantity_limits(self):
  with self.assertRaises(ValueError):p.calculate([e('DEPOSIT','d',amount=1),e('BUY','b',quantity=.00000001,price=1,symbol='AAA'),e('SPLIT','sp',symbol='AAA',ratio=.000001)],as_of='2025-01-03')
 def test_checkpoint_requires_same_date_all_marks(self):
  with self.assertRaises(ValueError):p.checkpoint(self.ledger(),[mark(date='2025-01-02')],'2025-01-03')
  cp=p.checkpoint(self.ledger(),[mark()],'2025-01-03');self.assertEqual(cp['equityUSD'],1100)
 def test_edit_invalidates_affected_checkpoint(self):
  ledger=self.ledger();a=p.checkpoint(ledger,[mark(date='2025-01-02',price=10)],'2025-01-02');b=p.checkpoint(ledger,[mark(date='2025-01-03',price=20)],'2025-01-03')
  changed=copy.deepcopy(ledger);changed[1]['price']=11
  self.assertEqual(p.performance(changed,[a,b],[])['status'],'insufficient')
 def test_modified_dietz_and_exact_benchmark_dates(self):
  ledger=[e('DEPOSIT','d',amount=1000),e('BUY','b',symbol='AAA',quantity=100,price=10)]
  a=p.checkpoint(ledger,[mark(date='2025-01-02',price=10)],'2025-01-02');b=p.checkpoint(ledger,[mark(date='2025-01-12',price=11)],'2025-01-12')
  r=p.performance(ledger,[a,b],[{'date':'2025-01-02','price':100},{'date':'2025-01-12','price':105}]);self.assertEqual(r['modifiedDietzPct'],10);self.assertAlmostEqual(r['benchmarkPriceChangePct'],5)
  r=p.performance(ledger,[a,b],[{'date':'2025-01-03','price':100},{'date':'2025-01-12','price':105}]);self.assertIsNone(r['benchmarkPriceChangePct'])
 def test_dietz_deposit_mid_period_is_not_market_gain(self):
  ledger=[e('DEPOSIT','d',amount=1000),e('DEPOSIT','d2',date='2025-01-07',amount=500)]
  a=p.checkpoint(ledger,[],'2025-01-02');b=p.checkpoint(ledger,[],'2025-01-12');r=p.performance(ledger,[a,b],[]);self.assertEqual(r['modifiedDietzPct'],0)
 def test_checkpoint_tampering_and_atomic_removal(self):
  state=w.normalise({'ledger':self.ledger(),'marks':[mark()]});state=w.mutate(state,'checkpoint.add',{'date':'2025-01-03'});state['checkpoints'][0]['equityUSD']+=1
  with self.assertRaises(ValueError):w.normalise(state)
  state=w.normalise({'ledger':self.ledger()})
  with self.assertRaises(ValueError):w.mutate(state,'ledger.remove',{'id':'d'})
  self.assertEqual(len(state['ledger']),2)
 def test_legacy_import_explicit_date_and_fee_assumption(self):
  legacy={'capital':1000,'trades':[{'date':'2025-01-03T12:00:00Z','symbol':'AAA','side':'BUY','qty':10,'price':10}]}
  state=w.mutate({},'legacy.import',{'portfolio':legacy,'date':'2025-01-02'});self.assertEqual(state['ledger'][1]['fee'],0);self.assertIn('assumed zero',state['ledger'][0]['note'])
  with self.assertRaises(ValueError):w.mutate(state,'legacy.import',{'portfolio':legacy,'date':'2025-01-02'})
 def test_source_credential_links_not_saved(self):
  for source in ('https://user:secret@example.com/data','https://example.com/?token=secret'):
   with self.assertRaises(ValueError):p.events([e('DEPOSIT',amount=1,source=source)])

 def test_standalone_fee_reduces_cash_and_return(self):
  r=p.calculate([e('DEPOSIT','d',amount=1000),e('FEE','f',amount=5)],as_of='2025-01-03')
  self.assertEqual(r['cashUSD'],995);self.assertEqual(r['feesUSD'],5);self.assertEqual(r['gainAfterCashFlowsUSD'],-5)
 def test_explicit_zero_mark_allows_total_loss_checkpoint(self):
  ledger=[e('DEPOSIT','d',amount=100),buy()]
  a=p.checkpoint(ledger,[mark(date='2025-01-02',price=10)],'2025-01-02')
  b=p.checkpoint(ledger,[mark(date='2025-01-03',price=0)],'2025-01-03')
  self.assertEqual(b['equityUSD'],0)
  state=w.normalise({'ledger':ledger,'marks':[mark(price=0)],'checkpoints':[a,b]})
  self.assertEqual(p.performance(state['ledger'],state['checkpoints'],[])['modifiedDietzPct'],-100)
