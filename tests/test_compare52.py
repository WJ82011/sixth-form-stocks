import contextlib
import datetime as dt
import unittest
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import ask48
import compare52
import test_v3_api as fixture

s = fixture.s
NY = ZoneInfo('America/New_York')


def stamp(day):
    moment = dt.datetime.fromisoformat(day + 'T16:00:00').replace(tzinfo=NY)
    return int(moment.timestamp() * 1000)


def bars(symbol, pairs):
    with contextlib.closing(s.db_connection()) as con, con:
        con.executemany('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)', [
            (symbol, stamp(day), price, price, price, price, 1, 1) for day, price in pairs])


class CompareTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_shared_sessions_gaps_and_a_split_stay_visible(self):
        bars('TTWO', [('2026-11-09', 100), ('2026-11-10', 110), ('2026-11-12', 30)])
        bars('RBLX', [('2026-11-09', 50), ('2026-11-12', 80)])
        built = compare52.build(vars(s), ['TTWO', 'RBLX', 'U', 'SONY'])
        self.assertEqual(built['status'], 'insufficient')
        bars('U', [('2026-11-09', 10), ('2026-11-10', 10), ('2026-11-12', 12)])
        bars('SONY', [('2026-11-09', 20), ('2026-11-10', 20), ('2026-11-12', 22)])
        built = compare52.build(vars(s), ['TTWO', 'RBLX', 'U', 'SONY'])
        self.assertEqual(built['dates'], ['2026-11-09', '2026-11-12'])
        ttwo = next(row for row in built['rows'] if row['symbol'] == 'TTWO')
        roblox = next(row for row in built['rows'] if row['symbol'] == 'RBLX')
        self.assertEqual(ttwo['points'][0]['index'], 100)
        self.assertAlmostEqual(ttwo['returnPct'], -70)
        self.assertIn('not rewritten', ttwo['splitNote'])
        self.assertAlmostEqual(roblox['indexEnd'], 160)
        self.assertGreater(roblox['missingCount'], 0)
        self.assertEqual({row['currency'] for row in built['rows']}, {'USD'})
        with self.assertRaises(ValueError):
            compare52.build(vars(s), ['TTWO', 'RBLX', 'U', 'SONY', 'AAPL'])

    def test_fiscal_periods_currencies_and_saved_reopen(self):
        bars('TTWO', [('2026-11-09', 100), ('2026-11-12', 120)])
        bars('RBLX', [('2026-11-09', 40), ('2026-11-12', 44)])

        def accounts(symbol):
            end = '2026-03-31' if symbol == 'TTWO' else '2025-12-31'
            start = '2025-04-01' if symbol == 'TTWO' else '2025-01-01'
            return {'symbol': symbol, 'name': symbol, 'unit': 'EUR' if symbol == 'RBLX' else 'USD', 'annual': [{
                'start': start, 'end': end, 'durationDays': 365, 'currency': 'EUR' if symbol == 'RBLX' else 'USD',
                'revenueGrowthPct': 10 if symbol == 'TTWO' else 4, 'netMarginPct': 12, 'longTermDebt': 5,
                'debtScope': 'Long-term debt portions only.',
                'metrics': {'revenue': {'value': 100, 'url': 'https://www.sec.gov/Archives/example', 'tag': 'Revenues'},
                            'cash': {'value': 20}}}]}

        with patch.object(s, 'sec_saved', side_effect=accounts):
            text, evidence = compare52.answer(vars(s), 'How do their operating margins compare?', ['TTWO', 'RBLX'])
        self.assertIn('Operating margin was not calculated', text)
        self.assertIn('do not cover the same months', text)
        self.assertIn('EUR', text)
        self.assertIsNone(evidence['financials']['rows'][0]['operatingMarginPct'])
        saved = compare52.save(vars(s), {'symbols': ['TTWO', 'RBLX'], 'title': 'Games'}, 1)
        bars('TTWO', [('2026-11-13', 999)])
        opened = compare52.read(vars(s), saved['id'], 2)
        self.assertEqual(opened['saved']['end'], '2026-11-12')
        self.assertAlmostEqual(opened['saved']['rows'][0]['endPrice'], 120)
        self.assertEqual(opened['fresh']['rows'][0]['latestDate'], '2026-11-13')

    def test_best_answer_matches_the_chart(self):
        bars('TTWO', [('2026-11-09', 200), ('2026-11-12', 220)])
        bars('RBLX', [('2026-11-09', 50), ('2026-11-12', 80)])
        result = ask48.answer(vars(s), 'Which company performed best over these dates?', {'symbol': 'TTWO', 'compareSymbols': 'TTWO,RBLX'})
        chart = compare52.build(vars(s), ['TTWO', 'RBLX'])
        leader = max(chart['rows'], key=lambda row: row['indexEnd'])
        self.assertIn(leader['symbol'], result['answer'])
        self.assertAlmostEqual(result['evidence']['endPrice'], leader['indexEnd'])
        self.assertEqual(result['context']['start'], chart['start'])
        self.assertEqual(result['context']['end'], chart['end'])
        source = Path('site/compare52.js').read_text()
        self.assertIn('id!==seq', source)
        self.assertIn('data-journal="compare"', source)
