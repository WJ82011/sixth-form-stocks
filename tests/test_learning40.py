import contextlib
import datetime as dt
import math
import time
import unittest
from unittest.mock import patch

import collector40
import learning40
import login40
import market37
import test_v3_api as fixture

s=fixture.s


class LearningAndCollectorTests(unittest.TestCase):
    setUp=fixture.V3APITests.setUp

    def test_learning_withholds_when_unchanged_is_as_good(self):
        points=[{'p':100.0} for _ in range(250)]
        result=learning40.evaluate(points,5)
        self.assertEqual(result['status'],'baseline')
        self.assertNotIn('price',result)
        self.assertEqual(result['testCases'],9)

    def test_learning_uses_later_independent_checks(self):
        points=[{'p':100*math.exp(.001*i)} for i in range(320)]
        result=learning40.evaluate(points,5)
        self.assertEqual(result['status'],'learned')
        self.assertLess(result['modelErrorPP'],result['baselineErrorPP'])
        self.assertAlmostEqual(result['returnPct'],math.expm1(.005)*100,places=7)

    def test_capture_is_saved_without_a_browser_and_reopens(self):
        now=int(time.time()*1000)
        worker=collector40.Collector(vars(s))
        worker.capture({'type':'trade','data':[
            {'s':'AMD','p':101,'v':5,'t':now-50},
            {'s':'AMD','p':102,'v':0,'t':now-40},
            {'s':'AAPL','p':100,'v':1,'t':now-30}]},{'AMD'})
        # A new worker has a new cursor, but the SQLite tape still has the trade.
        restarted=collector40.Collector(vars(s))
        self.assertNotEqual(worker.epoch,restarted.epoch)
        self.assertEqual(len(s.get_tape_events('AMD')),1)
        self.assertEqual(s.get_history('AMD')[-1]['p'],102)
        self.assertEqual(s.get_tape_events('AAPL'),[])
        self.assertEqual(worker.pulse(None,0,worker.epoch)['events'][0]['p'],101)
        self.assertEqual(restarted.pulse(None,1,worker.epoch)['events'],[])

    def test_login_uses_local_python_and_app_path(self):
        from pathlib import Path
        job=login40.definition(Path('/Applications/Market Desk'),Path('/usr/local/bin/python3'),Path('/Users/demo/.marketdesk-reborn'))
        self.assertEqual(job['ProgramArguments'][-1],'--background')
        self.assertTrue(job['RunAtLoad'])
        self.assertEqual(job['ProgramArguments'][1],'/Applications/Market Desk/server.py')

    def test_api_session_contains_no_browser_key(self):
        with patch.object(s,'get_key',return_value='private-test-value'):
            self.assertEqual(s.handle_api('/api/session',{}),{'configured':True,'local_only':True})

    def test_frame_parser_preserves_partial_messages(self):
        feed=collector40.Feed.__new__(collector40.Feed)
        feed.buffer=bytearray(b'\x81\x04ab')
        self.assertIsNone(feed.next_frame())
        feed.buffer.extend(b'cd')
        self.assertEqual(feed.next_frame(),(129,b'abcd'))
        self.assertFalse(feed.buffer)

    def test_reconnect_resumes_capture_after_an_outage(self):
        worker=collector40.Collector(vars(s))
        calls=[]
        now=int(time.time()*1000)

        class FeedFixture:
            sock=type('SocketFixture',(),{'close':lambda self:None})()
            def __init__(self, token, tls):
                calls.append('connect')
                if len(calls)==1:raise OSError('network unavailable')
            def send(self, opcode, body):
                pass
            def messages(self):
                yield {'type':'trade','data':[{'s':'AMD','p':100,'v':10,'t':now}]}
                worker.stop.set()

        with patch.object(collector40,'Feed',FeedFixture), patch.object(s,'get_key',return_value='fixture'), patch.object(
                s,'verified_tls_context',return_value=(None,None)),patch.object(worker.stop,'wait'):
            worker.stream_loop()
        self.assertEqual(calls,['connect','connect'])
        self.assertEqual(len(s.get_tape_events('AMD')),1)

    def test_duplicate_provider_labels_are_one_session(self):
        zone=market37.NY
        start=int(dt.datetime(2026,10,30,tzinfo=zone).timestamp()*1000)
        with contextlib.closing(s.db_connection()) as con,con:
            con.executemany('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)',[
                ('AMD',start,100,101,99,100,10,start//1000+90000),
                ('AMD',start+16*3600000,100,102,99,101,20,start//1000+90001)])
        saved=s.read_massive_daily_bars('AMD',start//1000,start//1000+86400)
        self.assertEqual(saved['bars']['c'],[100])
        self.assertEqual(saved['bars']['t'],[start//1000])
