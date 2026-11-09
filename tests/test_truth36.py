"""Synthetic previous-close fixtures, not actual AMD returns."""
import unittest,time,truth36
from unittest.mock import patch
class TruthTests(unittest.TestCase):
 def packet(self,rows):
  with patch('market36.cards',return_value=[{'change':None}]):return truth36.packet({'time':time,'screen_data':lambda syms:{'rows':rows}})
 def test_unknown_full_market_values_are_never_fabricated(self):self.assertTrue(all(x['change'] is None for x in self.packet([])['markets']))
 def test_comparison_uses_previous_close_not_intraday_first_point(self):
  r=self.packet([{'symbol':'AAA','price':90,'previousClose':100,'quoteTime':1793912400000,'listingCurrency':'USD','quoteFetchedAt':1793912400000}])['rows'][0];self.assertAlmostEqual(r['changePct'],-10);self.assertEqual(r['session'],'2026-11-05')
 def test_overflow_is_withheld(self):self.assertEqual(self.packet([{'symbol':'AAA','price':1e9,'previousClose':1e-300,'quoteTime':1793912400000}])['rows'],[])

 def test_explicit_history_refresh_bypasses_provider_cache(self):
  import test_v3_api as fixture
  s=fixture.s;now=int(time.time());qs={'symbol':['AMD'],'resolution':['D'],'from':[str(now-86400*10)],'to':[str(now)],'refresh':['1']}
  with patch.object(s,'get_massive_key',return_value='synthetic'),patch.object(s,'massive_daily_candles',return_value={'status':'ok'}) as request:
   s.handle_api('/api/candles',qs);self.assertTrue(request.call_args.kwargs['bypass_cache'])
  with patch.object(s,'get_massive_key',return_value=''),patch.object(s,'provider_get',return_value=({'s':'no_data'},None)) as request:
   s.handle_api('/api/candles',qs);self.assertTrue(request.call_args.kwargs['bypass_cache'])
