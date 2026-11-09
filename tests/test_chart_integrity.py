"""Chart provenance and laptop-sleep gap invariants."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class ChartIntegrityTests(unittest.TestCase):
    def test_daily_bars_never_blend_with_local_intraday_values(self):
        app=(ROOT/'site/app.js').read_text()
        self.assertIn("actual=historical.points.filter(valid).map",app)
        self.assertIn("if(haveDaily)",app)
        self.assertIn("if(['1H','1D'].includes(range)&&offlineGapCount)",app)
        self.assertIn("for(const seg of segments)",app)
        self.assertNotIn("ctx.moveTo(X(points[0].t),h-pad.bottom)",app)

    def test_forecast_charts_dont_default_to_unsupported_intraday(self):
        app=(ROOT/'site/app.js').read_text()
        self.assertIn("E.massiveConfigured&&E.forecastEnabled&&['1H','1D'].includes(E.range)",app)
        self.assertIn("if(E.forecastEnabled&&['1H','1D'].includes(E.range))setChartRange('1Y')",app)
        self.assertIn("'1Y'",app)

    def test_gaps_have_explicit_pure_series_helpers(self):
        research=(ROOT/'site/chart-research.js').read_text()
        self.assertIn('function chartSegments(points,range)',research)
        self.assertIn('function chartGaps(points,range)',research)
        self.assertIn('gap)segments.push([])',research)

if __name__=='__main__':unittest.main()
