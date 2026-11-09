"""Saved tape recovery retains real time boundaries and excludes quote updates."""
import contextlib
import datetime as dt
import unittest

import test_v3_api as fixture

s = fixture.s


class TapeReviewTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_latest_recording_can_be_older_than_live_window(self):
        day = 86400000
        last = (int(s.time.time()*1000)//day-5)*day+12*3600000
        events = [('AMD', last-day-1, 98, 1, last-day-1, 'trade'),
                  ('AMD', last-1000, 99, 2, last-900, 'trade'),
                  ('AMD', last, 100, 3, last+100, 'trade'),
                  ('AMD', last+1, 101, 0, last+101, 'price_update'),
                  ('AAPL', last+200, 200, 5, last+201, 'trade')]
        with contextlib.closing(s.db_connection()) as con, con:
            con.executemany('INSERT INTO tape_events(symbol,ts,price,volume,received_at,kind) VALUES(?,?,?,?,?,?)',events)
        self.assertEqual(s.handle_api('/api/tape',{'symbol':['AMD'],'since':[str(last+day)]})['events'],[])
        review = s.handle_api('/api/tape',{'symbol':['AMD'],'last':['1']})
        self.assertEqual([r['t'] for r in review['events']],[last-1000,last])
        self.assertEqual([r['v'] for r in review['events']],[2,3])
        date=dt.datetime.fromtimestamp(last/1000,dt.timezone.utc).date().isoformat()
        self.assertEqual(review['recordingDays'][0],{'date':date,'count':2})
        chosen=s.handle_api('/api/tape',{'symbol':['AMD'],'day':[date]})
        self.assertEqual([r['t'] for r in chosen['events']],[last-1000,last])
