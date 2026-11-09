"""Synthetic grouped-market fixtures, never bundled demonstration prices."""
import contextlib,datetime as dt,json,unittest
from unittest.mock import patch
import market37 as m
import test_v3_api as fixture
s=fixture.s
class Heat37Tests(unittest.TestCase):
 setUp=fixture.V3APITests.setUp
 def payload(self,day,close=100):
  stamp=int(dt.datetime.combine(dt.date.fromisoformat(day),dt.time(),m.NY).timestamp()*1000)
  return {'status':'OK','adjusted':True,'results':[{'T':'AAPL','t':stamp,'o':close,'h':close,'l':close,'c':close,'v':1}]}
 def store(self,generation,day,close):
  value=m.normalise(self.payload(day,close),day,{'AAPL'})
  with contextlib.closing(s.db_connection()) as c,c:c.execute('INSERT OR REPLACE INTO heat37_days VALUES(?,?,?,?)',(generation,day,json.dumps(value),1))
 def test_calendar_excludes_weekends_holidays_and_current_day(self):
  self.assertEqual(m.sessions(dt.date(2026,11,6)),['2026-11-05','2026-11-04','2026-11-03','2026-11-02','2026-10-30','2026-10-29'])
  self.assertEqual(m.sessions(dt.date(2026,9,8),2),['2026-09-04','2026-09-03'])
  self.assertEqual(m.sessions(dt.date(2026,4,6),1),['2026-04-02'])
  self.assertEqual(m.sessions(dt.date(2028,1,1),1),['2027-12-31'])
  with self.assertRaises(ValueError):m.sessions(dt.date(2030,1,1))
 def test_periods_use_matching_closes_not_quote_age(self):
  gen=m.today(vars(s)).isoformat();days=m.sessions(m.today(vars(s)))
  for i,day in enumerate(days):self.store(gen,day,100-i*10)
  for period,index in [('1D',1),('3D',3),('1W',5)]:
   d=m.packet(vars(s),period);a=next(x for x in d['rows'] if x['symbol']=='AAPL');self.assertEqual(d['start'],days[index]);self.assertAlmostEqual(a['change'],(100/(100-index*10)-1)*100);self.assertEqual(len(a['points']),index+1)
 def test_missing_middle_bar_is_not_shortened_to_wrong_period(self):
  gen=m.today(vars(s)).isoformat();days=m.sessions(m.today(vars(s)))
  for i,day in enumerate(days):
   if i!=2:self.store(gen,day,100+i)
  row=next(x for x in m.packet(vars(s),'1W')['rows'] if x['symbol']=='AAPL');self.assertIsNone(row['change']);self.assertEqual(row['points'],[])
 def test_invalid_and_unadjusted_bars_withheld(self):
  day='2026-11-05'
  for field,value in [('c',float('nan')),('v',-1),('o',False),('t',0)]:
   p=self.payload(day);p['results'][0][field]=value;self.assertEqual(m.normalise(p,day,{'AAPL'})['rows'],{})
  p=self.payload(day);p['adjusted']=False
  with self.assertRaises(ValueError):m.normalise(p,day,{'AAPL'})
  p=self.payload(day);p['results']*=2
  with self.assertRaises(ValueError):m.normalise(p,day,{'AAPL'})
 def test_step_one_call_atomic_saved_chart_and_resume(self):
  day=m.sessions(m.today(vars(s)))[0]
  with patch.object(s,'get_massive_key',return_value='synthetic'),patch.object(s,'massive_request',return_value=(self.payload(day),False)) as fetch:
   result=m.step(vars(s),{});self.assertEqual(result['completed'],1);self.assertEqual(fetch.call_count,1);self.assertTrue(fetch.call_args.args[0].endswith(day));self.assertEqual(fetch.call_args.kwargs['max_bytes'],8000000)
  with contextlib.closing(s.db_connection()) as c:self.assertEqual(c.execute('SELECT count(*) FROM massive_daily_bars WHERE symbol="AAPL"').fetchone()[0],1)
  self.assertNotEqual(m.packet(vars(s))['nextDay'],day)
 def test_provider_denial_and_throttle_keep_previous_data(self):
  for status in (403,429):
   with patch.object(s,'get_massive_key',return_value='synthetic'),patch.object(s,'massive_request',side_effect=s.ProviderError(status,'Synthetic denied',retry_after=65)):
    d=m.step(vars(s),{});self.assertEqual(d['status'],'waiting' if status==429 else 'error');self.assertEqual(m.packet(vars(s))['completed'],0)
 def test_reads_and_completed_jobs_never_request_providers(self):
  gen=m.today(vars(s)).isoformat()
  for day in m.sessions(m.today(vars(s))):self.store(gen,day,100)
  with patch.object(s,'massive_request',side_effect=AssertionError('No network')):
   self.assertEqual(m.step(vars(s),{})['status'],'complete');self.assertEqual(m.packet(vars(s))['completed'],6)
 def test_previous_map_remains_explicitly_dated_during_new_load(self):
  current=dt.date(2026,11,6);older=current-dt.timedelta(days=1)
  for day in m.sessions(older):self.store(older.isoformat(),day,100)
  with patch.object(m,'today',return_value=current):
   d=m.packet(vars(s),'1W')
  self.assertEqual(d['generation'],older.isoformat());self.assertTrue(d['stale']);self.assertEqual(d['completed'],0)
 def test_corrupt_saved_data_is_not_displayed(self):
  gen=m.today(vars(s)).isoformat();day=m.sessions(m.today(vars(s)))[0]
  with contextlib.closing(s.db_connection()) as c,c:c.execute('INSERT INTO heat37_days VALUES(?,?,?,?)',(gen,day,'{"rows":{"AAPL":{"c":0}}}',1))
  self.assertEqual(m.packet(vars(s))['completed'],0);self.assertTrue(all(x['change'] is None for x in m.packet(vars(s))['rows']))

 def test_new_york_midnight_boundary_controls_available_day(self):
  from types import SimpleNamespace
  for instant,expected in [('2026-11-06T00:30:00+00:00','2026-11-04'),('2026-11-06T05:01:00+00:00','2026-11-05')]:
   clock=SimpleNamespace(time=lambda:dt.datetime.fromisoformat(instant).timestamp());self.assertEqual(m.sessions(m.today({'time':clock}))[0],expected)
 def test_bad_payload_cannot_record_completed_checkpoint(self):
  day=m.sessions(m.today(vars(s)))[0];payload=self.payload(day);payload['results']*=2
  with patch.object(s,'get_massive_key',return_value='synthetic'),patch.object(s,'massive_request',return_value=(payload,False)),self.assertRaises(ValueError):m.step(vars(s),{})
  self.assertEqual(m.packet(vars(s))['completed'],0)
 def test_concurrent_sync_is_not_duplicated(self):
  m.SYNC.acquire()
  try:
   with patch.object(s,'massive_request',side_effect=AssertionError('No concurrent request')):self.assertEqual(m.step(vars(s),{})['status'],'waiting')
  finally:m.SYNC.release()
