import sys, math, unittest, tempfile, time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import intelligence as i
import server as s
NOW=1793664000000
class IntelligenceTests(unittest.TestCase):
 def pt(self,t,p=100,source='finnhub_quote'):return dict(t=t,p=p,source=source)
 def daily(self,count=160):
  return [self.pt(NOW-(count-j)*86400000,100*math.exp(.0005*j+.02*math.sin(j*.8)),'massive_daily') for j in range(count)]
 def test_intraday_rejects_daily_future_bad_and_outside(self):
  raw=[self.pt(NOW-60000),self.pt(NOW-3600001),self.pt(NOW+1),self.pt(NOW-1000,float('nan')),self.pt(NOW-1000,120,'massive_daily')]
  self.assertEqual(i.overview(raw,NOW,1)['count'],1)
 def test_window_dedupe_and_gap(self):
  raw=[self.pt(NOW-3600000,100),self.pt(NOW-3600000,101),self.pt(NOW-60000,102)]
  d=i.overview(raw,NOW,1);self.assertEqual(d['count'],2);self.assertEqual(len(d['gaps']),1);self.assertAlmostEqual(d['changePct'],(102/101-1)*100);self.assertFalse(d['complete'])
 def test_24h_not_daily_substitute(self):
  d=i.overview(self.daily(),NOW,24);self.assertEqual(d['count'],0)
 def test_empty_and_stale(self):
  self.assertTrue(i.overview([],NOW,1)['stale']);self.assertTrue(i.overview([self.pt(NOW-600000)],NOW,1)['stale'])
 def test_model_requires_history_and_does_not_train_ticks(self):
  self.assertEqual(i.daily_model(self.daily(89),NOW)['status'],'insufficient');self.assertEqual(i.daily_model([self.pt(NOW-60000)],NOW)['count'],0)
 def test_model_backtest_matches_manual_first_prediction(self):
  pts=self.daily();m=i.daily_model(pts,NOW);self.assertEqual(m['status'],'ok');self.assertEqual(m['samples'],98)
  returns=[math.log(b['p']/a['p']) for a,b in zip(pts,pts[1:])];rows=list(zip(returns[:-1],returns[1:]));errs=[]
  for j in range(60,len(rows)):
   a,b=i.fit(rows[:j]);errs.append(abs(math.exp(a+b*rows[j][0]-rows[j][1])-1)*100)
  self.assertAlmostEqual(m['maePct'],sum(errs)/len(errs));self.assertGreaterEqual(m['upper'],m['lower']);self.assertGreaterEqual(m['bandCoverage'],0);self.assertLessEqual(m['bandCoverage'],1)
 def test_future_data_excluded_and_extreme_history_withheld(self):
  pts=self.daily();self.assertEqual(i.daily_model(pts+[self.pt(NOW+1,500,'massive_daily')],NOW),i.daily_model(pts,NOW))
  pts[-2]['p']=1e8;self.assertEqual(i.daily_model(pts,NOW)['status'],'extreme_returns')
 def test_spacing(self):
  pts=self.daily();pts[20]['t']+=1000;self.assertEqual(i.daily_model(pts,NOW)['status'],'ok');pts[20]['t']=pts[19]['t']+1000;self.assertEqual(i.daily_model(pts,NOW)['status'],'invalid_spacing')
 def test_api_reads_only_local_storage(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(s,'USER_DIR',Path(tmp)),patch.object(s,'DB_FILE',Path(tmp)/'db'),patch.object(s,'provider_get',side_effect=AssertionError('Network forbidden')):
   s.init_storage();s.store_point('AAPL',int(time.time()*1000)-1000,120,'finnhub_quote');d=s.handle_api('/api/intelligence',{'symbol':['AAPL']});self.assertEqual(d['hour']['count'],1);self.assertNotIn('token',str(d))
if __name__=='__main__':unittest.main()
