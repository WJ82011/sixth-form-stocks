"""The chart must be drawn from saved closes before the slower forecast check."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class Chart63Tests(unittest.TestCase):
    def test_saved_closes_are_drawn_before_the_forecast_request(self):
        source = (ROOT / 'site' / 'app.js').read_text()
        load = source.split('async function loadChart', 1)[1].split('function drawChart', 1)[0]
        self.assertLess(load.index('drawChart();window.Look43'), load.index('/api/v3/forecast61'))

    def test_trades_do_not_reload_a_daily_chart(self):
        source = (ROOT / 'site' / 'app.js').read_text()
        refresh = source.split('function scheduleTradeRefresh', 1)[1].split('function stopWS', 1)[0]
        self.assertIn("['1H','1D'].includes(E.range)", refresh)
        self.assertNotIn('loadChart(false)', refresh)
        self.assertIn('appendRecordedTrade()', refresh)

    def test_a_collector_gap_reloads_only_the_intraday_chart(self):
        source = (ROOT / 'site' / 'app.js').read_text()
        packet = source.split('function acceptCollectorPacket', 1)[1].split('function connectWS', 1)[0]
        self.assertIn('E.collectorDown', packet)
        self.assertIn("['1H','1D'].includes(E.range))loadChart(false)", packet)
        self.assertNotIn('forecast61', packet)


if __name__ == '__main__':
    unittest.main()
