"""Offline tests of Finnhub tape persistence, classifications and no synthetic data."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import time

SPEC=importlib.util.spec_from_file_location('marketdesk_tape_server',Path(__file__).parents[1]/'server.py')
s=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(s)

class TapeDataTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.ps=[patch.object(s,'USER_DIR',Path(tmp.name)),patch.object(s,'DB_FILE',Path(tmp.name)/'obs.sqlite3'),patch.object(s,'KEY_FILE',Path(tmp.name)/'key')]
        for p in self.ps:p.start();self.addCleanup(p.stop)
        s.init_storage()
        self.current=int(time.time()*1000)

    def test_trade_and_zero_volume_price_update_separated(self):
        t=self.current
        frames=[{'s':'AAPL','t':t,'p':275.12,'v':12},{'s':'AAPL','t':t+1,'p':275.15,'v':0}]
        self.assertEqual(s.store_points_batch(frames),2)
        events=s.get_tape_events('AAPL')
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['p'],275.12)
        self.assertEqual(events[0]['v'],12.0)
        hist=s.get_history('AAPL')
        self.assertEqual({x['source'] for x in hist},{'finnhub_websocket_trade','finnhub_websocket_update'})

    def test_rejects_invalid_negative_unreported_and_stale_volume(self):
        t=self.current
        frames=[{'s':'AAPL','t':t,'p':120,'v':-1},
                {'s':'AAPL','t':t,'p':120},
                {'s':'AAPL','t':t-600000,'p':120,'v':45},
                {'s':'AAPL','t':t+120000,'p':120,'v':45},
                {'s':'AAPL','t':t,'p':0,'v':45},
                {'s':'../etc','t':t,'p':120,'v':45},
                {'s':'AAPL','t':t,'p':120,'v':float('nan')},
                {'s':'AAPL','t':t,'p':120,'v':4}]
        self.assertEqual(s.store_points_batch(frames),1)
        self.assertEqual(len(s.get_tape_events('AAPL')),1)

    def test_multiple_same_timestamp_trades_preserve_observed_volume(self):
        t=self.current
        self.assertEqual(s.store_points_batch([{'s':'AAPL','t':t,'p':98.25,'v':10},
                         {'s':'AAPL','t':t,'p':98.25,'v':20}]),2)
        self.assertEqual(sum(e['v'] for e in s.get_tape_events('AAPL')),30.0)

    def test_tape_response_has_provenance_and_filters_by_symbol(self):
        t=self.current
        s.store_points_batch([{'s':'AAPL','t':t,'p':130,'v':11},
                              {'s':'MSFT','t':t,'p':420,'v':9}])
        data=s.handle_api('/api/tape',{'symbol':['AAPL'],'since':[str(t-100)]})
        self.assertEqual(data['symbol'],'AAPL')
        self.assertFalse(data['complete_market_tape'])
        self.assertEqual(len(data['events']),1)
        self.assertEqual(data['events'][0]['v'],11)
        self.assertIn('Finnhub',data['source'])

    def test_local_tape_excludes_rest_quote(self):
        t=self.current
        s.store_point('AAPL',t,100,'finnhub_quote')
        self.assertEqual(s.get_tape_events('AAPL'),[])

    def test_restart_preserves_recorded_events(self):
        t=self.current
        s.store_points_batch([{'s':'AAPL','t':t,'p':250,'v':7}])
        s.init_storage()
        self.assertEqual(len(s.get_tape_events('AAPL')),1)

    def test_untrusted_tape_symbol_validation(self):
        with self.assertRaises(ValueError):
            s.handle_api('/api/tape',{'symbol':['../../etc/passwd']})

if __name__=='__main__':unittest.main()
