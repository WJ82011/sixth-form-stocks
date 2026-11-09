"""Historical equity minutes cannot become live observations."""
import datetime as dt
import unittest
from unittest.mock import patch

import market37
import session38
import test_v3_api as fixture

s = fixture.s


class SessionTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_past_ny_date_cached_without_writing_to_tape(self):
        date = dt.date(2026, 11, 6)
        midnight = int(dt.datetime.combine(date, dt.time(), market37.NY).timestamp())
        response = {'status':'OK','ticker':'AMD','adjusted':True,
                    'results':[{'t':(midnight+i*60)*1000,'o':100,'h':102,'l':99,'c':101,'v':1}
                               for i in (-1, 570, 572, 1440)]}
        with patch.object(market37,'today',return_value=dt.date(2026,11,9)), patch.object(
                s,'get_massive_key',return_value='fixture'),patch.object(
                s,'massive_request',return_value=(response,False)) as provider:
            packet = session38.packet(vars(s),'AMD')
            saved = session38.packet(vars(s),'AMD')
        self.assertEqual(packet['day'],'2026-11-06')
        self.assertEqual([p['t'] for p in packet['points']],[(midnight+i*60)*1000 for i in (571,573)])
        self.assertEqual(saved['points'],packet['points'])
        self.assertEqual(provider.call_count,1)
        self.assertEqual(s.get_history('AMD'),[])
        self.assertEqual(s.get_tape_events('AMD'),[])

    def test_crypto_symbol_cannot_use_equity_history(self):
        with self.assertRaises(ValueError):
            session38.packet(vars(s),'BTC-USD')
