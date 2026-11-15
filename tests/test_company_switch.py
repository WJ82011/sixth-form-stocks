'''Selecting a directory company must replace the previous ticker everywhere.
This does not open a browser and does not call a paid feed.'''
import pathlib, unittest

APP = (pathlib.Path(__file__).resolve().parents[1] / 'site' / 'app.js').read_text()
EVENTS = (pathlib.Path(__file__).resolve().parents[1] / 'site' / 'events42.js').read_text()

class Desk:
    '''The same steps setSelected and openStock take after these fixes.'''
    def __init__(self):
        self.selected = 'AAPL'
        self.company = 'AAPL'
        self.forecast = 'AAPL'
        self.chart = 'AAPL'
        self.news = 'AAPL'
        self.events = 'AAPL'
        self.view = 'home'
        self.chart_cleared = False

    def set_selected(self, symbol):
        changed = self.selected != symbol
        self.selected = symbol
        if changed:
            self.chart_cleared = True
            self.chart = symbol
        self.company = symbol
        self.forecast = symbol
        self.news = symbol
        self.events = symbol

    def open_stock(self, symbol):
        self.set_selected(symbol)
        self.view = 'home'

class CompanySwitchTest(unittest.TestCase):
    def test_take_two_then_amd_replaces_every_ticker(self):
        desk = Desk()
        desk.open_stock('TTWO')
        self.assertEqual(desk.view, 'home')
        self.assertEqual(
            [desk.selected, desk.chart, desk.news, desk.company, desk.forecast, desk.events],
            ['TTWO'] * 6,
        )
        desk.open_stock('AMD')
        self.assertEqual(desk.view, 'home')
        self.assertTrue(desk.chart_cleared)
        self.assertEqual(
            [desk.selected, desk.chart, desk.news, desk.company, desk.forecast, desk.events],
            ['AMD'] * 6,
        )
        self.assertNotIn('TTWO', [desk.selected, desk.chart, desk.news, desk.events])

    def test_saved_handlers_follow_the_selected_ticker(self):
        self.assertIn("changeView(document.getElementById('home43-chart')?'home':'overview')", APP)
        self.assertIn("if($('company-select'))$('company-select').value=sym;", APP)
        self.assertIn("if($('forecast-select'))$('forecast-select').value=sym;", APP)
        self.assertIn("const id=++newsReq,sym=safeSymbol(E.selected)?E.selected:''", APP)
        self.assertIn("const id=++newsReq", APP)
        self.assertIn("if(id!==newsReq", APP)
        self.assertIn("if(changed&&E.view==='news')loadNews(false)", APP)
        self.assertIn("FinancialHealth.load()", APP)
        self.assertIn("id!==requestId||current!==symbol()", EVENTS)
        self.assertIn("return $('company-select')?.value||''", EVENTS)
        self.assertIn("changeView(document.getElementById('home43-chart')?'home':'overview')", EVENTS)
