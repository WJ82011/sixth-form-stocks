import datetime as dt
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import events42
import price_alerts
import replay43
import server as s
from test_price_alerts import NOW, PriceAlertsTests

NY=ZoneInfo('America/New_York')

def sessions(count,end=dt.date(2026,6,12)):
    found=[];cursor=end
    while len(found)<count:
        if events42.is_session(cursor):found.append(cursor)
        cursor-=dt.timedelta(days=1)
    return list(reversed(found))

def bars(days,closes):
    return {'t':[int(dt.datetime.combine(day,dt.time(16),NY).timestamp()) for day in days],'o':closes,'h':closes,'l':closes,'c':closes,'v':[1]*len(days)}

class SmarterAlertTests(unittest.TestCase):
    def setUp(self):
        PriceAlertsTests.setUp(self)
    def state(self):
        return PriceAlertsTests.state(self)
    def cross(self,symbol='AAPL',frequency='once'):
        return s.change_alerts({'action':'create','symbol':symbol,'kind':'cross','direction':'above','target':100,'unit':'USD','frequency':frequency})['id']
    def quote(self,price,offset,symbol='AAPL',source='finnhub_quote'):
        self.now=NOW+offset
        return s.store_point(symbol,self.now,price,source)
    def test_exact_threshold_is_a_crossing_and_repeats_do_not_notify(self):
        self.cross();self.quote(99,1000);self.quote(100,2000)
        state=self.state();self.assertEqual(state['events'][0]['match_type'],'crossing');self.assertEqual(state['events'][0]['price'],100);self.assertEqual(state['events'][0]['comparison_price'],100)
        self.quote(100,2000);self.quote(130,3000)
        self.assertEqual(len(self.state()['events']),1);self.assertEqual(self.state()['alerts'][0]['status'],'triggered')
    def test_restart_keeps_one_crossing(self):
        self.cross();self.quote(99,1000);self.quote(100,2000);before=self.state()['events'][0]['price']
        s.init_storage();self.quote(140,4000)
        self.assertEqual(len(self.state()['events']),1);self.assertEqual(self.state()['events'][0]['price'],before)
    def test_first_price_and_gap_are_not_called_crossings(self):
        self.cross();self.quote(110,1000)
        self.assertEqual(self.state()['events'][0]['match_type'],'after_gap')
        self.quote(90,2000);self.now=NOW+2000+price_alerts.GAP_MS+1000;s.store_point('AAPL',self.now,120,'finnhub_quote')
        kinds=[row['match_type'] for row in self.state()['events']]
        self.assertIn('after_gap',kinds);self.assertNotIn('crossing',kinds)
    def test_stale_price_is_named_and_not_evaluated(self):
        self.cross();self.now=NOW+600000;s.store_point('AAPL',NOW+1000,130,'finnhub_quote')
        state=self.state();self.assertEqual(state['events'],[]);self.assertIn('stale',state['alerts'][0]['evaluation_note'])
    def test_replay_prices_do_not_reach_live_evaluation(self):
        self.cross();self.quote(99,1000);self.quote(150,2000,'AAPL','replay')
        self.assertEqual(self.state()['events'],[])
        self.assertNotIn('price_alerts',Path('replay43.py').read_text())
        self.assertEqual(replay43.frame([{'t':0,'p':100},{'t':60000,'p':180}],[],[],0)['prices'][-1]['p'],100)
    def test_rapid_symbol_switch_keeps_each_evidence_card(self):
        self.cross('AAPL');self.cross('MSFT')
        self.quote(99,1000,'AAPL');self.quote(99,1500,'MSFT');self.quote(120,2000,'MSFT');self.quote(80,2500,'AAPL')
        events=self.state()['events'];self.assertEqual(len(events),1);self.assertEqual(events[0]['symbol'],'MSFT')
        source=Path('site/alerts.js').read_text();self.assertIn('openSeq',source);self.assertIn('setSelected(symbol)',source);self.assertIn('Move44.open',source)
    def test_percent_uses_the_dated_close_and_keeps_it(self):
        day=sessions(1)[0]
        s.store_massive_daily_bars('AAPL',bars([day],[200]))
        s.change_alerts({'action':'create','symbol':'AAPL','kind':'percent','direction':'above','target':5,'unit':'percent','referenceDate':day.isoformat()})
        self.quote(200,1000);self.quote(210,2000)
        event=self.state()['events'][0]
        self.assertEqual(event['match_type'],'crossing');self.assertEqual(event['comparison_price'],200);self.assertEqual(event['price'],210)
        self.quote(250,3000);self.assertEqual(self.state()['events'][0]['price'],210)
        with self.assertRaises(ValueError):s.change_alerts({'action':'create','symbol':'AAPL','kind':'percent','direction':'above','target':5,'unit':'percent','referenceDate':'2026-01-01'})
    def test_unusual_session_needs_a_sample_skips_a_split_and_names_a_gap(self):
        s.change_alerts({'action':'create','symbol':'AMD','kind':'unusual','direction':'above','target':90,'unit':'percent'})
        s.store_massive_daily_bars('AMD',bars(sessions(5),[100]*5))
        self.assertIn('not enabled',self.state()['alerts'][0]['evaluation_note']);self.assertEqual(self.state()['alerts'][0]['sample_size'],3)
        s.change_alerts({'action':'create','symbol':'AAPL','kind':'unusual','direction':'above','target':90,'unit':'percent'})
        s.store_massive_daily_bars('AAPL',bars(sessions(24),[100]*23+[30]))
        self.assertIn('split',next(a['evaluation_note'] for a in self.state()['alerts'] if a['symbol']=='AAPL'))
        self.assertEqual(s.read_massive_daily_bars('AAPL',946684800,2000000000)['bars']['c'][-1],30)
        flat=sessions(24)
        s.change_alerts({'action':'create','symbol':'MSFT','kind':'unusual','direction':'above','target':90,'unit':'percent'})
        s.store_massive_daily_bars('MSFT',bars(flat,[100]*24))
        self.assertEqual(next(a['condition_met'] for a in self.state()['alerts'] if a['symbol']=='MSFT'),0)
        s.store_massive_daily_bars('MSFT',bars([events42.sessions_after(flat[-1],1)[0]],[130]))
        crossing=self.state()['events'][0]
        self.assertEqual(crossing['symbol'],'MSFT');self.assertEqual(crossing['match_type'],'crossing');self.assertGreaterEqual(next(a['sample_size'] for a in self.state()['alerts'] if a['symbol']=='MSFT'),20)
        days=sessions(24);later=events42.sessions_after(days[-1],2)[1]
        s.change_alerts({'action':'create','symbol':'NVDA','kind':'unusual','direction':'above','target':90,'unit':'percent'})
        s.store_massive_daily_bars('NVDA',bars(days,[100]*24))
        s.store_massive_daily_bars('NVDA',bars([later],[140]))
        self.assertEqual(self.state()['events'][0]['symbol'],'NVDA');self.assertEqual(self.state()['events'][0]['match_type'],'after_gap')
    def test_pause_and_frequency_are_saved(self):
        ident=self.cross(frequency='repeat');s.change_alerts({'action':'pause','id':ident});self.quote(90,1000);self.quote(120,2000)
        self.assertEqual(self.state()['events'],[])
        s.change_alerts({'action':'frequency','id':ident,'frequency':'once'});self.assertEqual(self.state()['alerts'][0]['frequency'],'once')

if __name__=='__main__':unittest.main()
