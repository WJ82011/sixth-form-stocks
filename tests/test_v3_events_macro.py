"""Synthetic calendar and official-series parser fixtures; no live network."""
import datetime as dt,unittest
from unittest.mock import patch
import events3,macro3,workspace3
class EventTests(unittest.TestCase):
 def event(self,**kw):return {'id':'event1','title':'Synthetic company event','date':'2026-11-05','zone':'Europe/London','status':'estimated','source':'Synthetic public company source',**kw}
 def test_date_only_stays_date_only(self):
  r=events3.normalise([self.event()])[0];self.assertTrue(r['allDay']);self.assertNotIn('utc',r)
 def test_london_summer_time_is_converted_correctly(self):
  r=events3.normalise([self.event(date='2026-07-01',time='10:00')])[0];self.assertIn('09:00:00+00:00',r['utc'])
 def test_ambiguous_and_nonexistent_clock_change_times_rejected(self):
  for day,time in [('2026-03-29','01:30'),('2026-10-25','01:30')]:
   with self.assertRaisesRegex(ValueError,'ambiguous|does not exist'):events3.normalise([self.event(date=day,time=time)])
 def test_invalid_zone_time_status_rejected(self):
  for changes in ({'zone':'Not/AZone'},{'time':'25:00'},{'status':'AI confirmed'}):
   with self.assertRaises(ValueError):events3.normalise([self.event(**changes)])
 def test_revision_preserves_prior_source_and_date(self):
  a=workspace3.mutate({},'event.add',{'event':self.event()});b=workspace3.mutate(a,'event.add',{'event':self.event(date='2026-11-06',status='confirmed')});self.assertEqual(b['events'][0]['history'][0]['date'],'2026-11-05');self.assertEqual(b['events'][0]['status'],'confirmed')
 def test_ics_escaping_and_no_alarm(self):
  e=events3.normalise([self.event(title='Title, with; punctuation\nnot a command')])[0];ics=events3.ics([e]);self.assertIn('DTSTART;VALUE=DATE:20261105',ics);self.assertIn('STATUS:TENTATIVE',ics);self.assertNotIn('BEGIN:VALARM',ics);self.assertIn('\\,',ics);self.assertIn('\\;',ics)
 def test_timed_calendar_export_uses_utc(self):
  e=events3.normalise([self.event(date='2026-07-01',time='10:00')])[0];self.assertIn('DTSTART:20260701T090000Z',events3.ics([e]))
 def test_calendar_utf8_folded_lines_fit(self):
  e=events3.normalise([self.event(title='Résumé é'*15)])[0]
  self.assertTrue(all(len(line.encode())<=75 for line in events3.ics([e]).split('\r\n')))
 def test_earnings_no_exact_time_or_confirmation_is_invented(self):
  raw={'earningsCalendar':[{'symbol':'AAA','date':'2026-11-06','hour':'amc'},{'symbol':'OTHER','date':'2026-11-06'}]};r=events3.earnings(raw,'AAA',123);self.assertEqual(len(r),1);self.assertTrue(r[0]['allDay']);self.assertEqual(r[0]['status'],'estimated');self.assertNotIn('utc',r[0]);self.assertIn('After US',r[0]['window'])
 def test_sec_filings_are_completed_not_earnings_schedule(self):
  r=events3.filings({'filings':{'recent':{'accessionNumber':['0000000001-26-000001'],'form':['8-K'],'filingDate':['2026-11-05']}}},1)
  self.assertEqual(r[0]['status'],'completed');self.assertIn('not a confirmed earnings',r[0]['note'])
class MacroTests(unittest.TestCase):
 def test_exact_period_yoy_and_missing_is_not_zero(self):
  r=macro3.parse('CPIAUCSL','observation_date,CPIAUCSL\n2025-09-01,100\n2026-09-01,104\n2026-10-01,.',dt.date(2026,11,5));self.assertAlmostEqual(r['yearAgoChangePct'],4);self.assertEqual(r['latest']['date'],'2026-09-01')
 def test_wrong_period_future_and_nonfinite_filtered(self):
  csv='DATE,UNRATE\n2026-09-01,4.2\n2026-09-02,99\n2027-01-01,10\n2026-10-01,NaN';r=macro3.parse('UNRATE',csv,dt.date(2026,11,5));self.assertEqual(len(r['observations']),1);self.assertIsNone(r['yearAgoChangePct'])
 def test_gdp_only_actual_quarter_start_dates(self):
  r=macro3.parse('GDPC1','DATE,GDPC1\n2026-07-01,200\n2026-08-01,999',dt.date(2026,11,5));self.assertEqual(len(r['observations']),1);self.assertIn('annual rate',r['unit'])
 def test_missing_year_ago_withholds_change(self):
  r=macro3.parse('CPIAUCSL','DATE,CPIAUCSL\n2025-08-01,100\n2026-09-01,104',dt.date(2026,11,5));self.assertIsNone(r['yearAgoChangePct'])
 def test_unknown_series_and_wrong_headers_rejected(self):
  for code,body in [('BAD','DATE,BAD\n2026-09-01,1'),('UNRATE','DATE,WRONG\n2026-09-01,1')]:
   with self.assertRaises(ValueError):macro3.parse(code,body)
