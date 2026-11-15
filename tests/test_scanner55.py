import datetime as dt
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

import market37
import scanner55
import test_v3_api as fixture

s = fixture.s
NY = ZoneInfo('America/New_York')


def sessions(count, start=dt.date(2026, 6, 1)):
    found = []
    day = start
    while len(found) < count:
        if day.weekday() < 5 and day not in market37.holidays(day.year):
            found.append(day.isoformat())
        day += dt.timedelta(days=1)
    return found


def closes(values, days=None, volume=None):
    days = days or sessions(len(values))
    return [{'date': day, 'close': price, 'volume': volume, 'ts': index} for index, (day, price) in enumerate(zip(days, values))]


class ScannerTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_fixed_move_percentile_average_and_high_match_the_hand_examples(self):
        days = sessions(2)
        matched = scanner55.scan_books({'AAA': closes([100, 105], days)}, {'conditions': [{'kind': 'session_move', 'threshold': 5}]}, days[-1])
        self.assertEqual(matched['matches'][0]['symbol'], 'AAA')
        self.assertAlmostEqual(matched['matches'][0]['measured'], 5)
        quiet = scanner55.scan_books({'AAA': closes([100, 104], days)}, {'conditions': [{'kind': 'session_move', 'threshold': 5}]}, days[-1])
        self.assertEqual(quiet['counts']['matched'], 0)
        price = 100.0
        history = [price]
        for move in range(1, 21):
            price *= 1 + move / 100
            history.append(price)
        threshold = scanner55._percentile(list(range(1, 21)), 90)
        self.assertEqual(threshold, 18)
        hit = history + [history[-1] * 1.18]
        miss = history + [history[-1] * 1.179]
        days = sessions(len(hit))
        found = scanner55.scan_books({'AAA': closes(hit, days)}, {'conditions': [{'kind': 'session_move', 'threshold': 'history', 'percentile': 90}]}, days[-1])
        self.assertEqual(found['counts']['matched'], 1)
        self.assertAlmostEqual(found['matches'][0]['comparison'], 18)
        missed = scanner55.scan_books({'AAA': closes(miss, days)}, {'conditions': [{'kind': 'session_move', 'threshold': 'history', 'percentile': 90}]}, days[-1])
        self.assertEqual(missed['counts']['matched'], 0)
        days = sessions(3)
        above = scanner55.scan_books({'AAA': closes([1, 2, 3], days)}, {'conditions': [{'kind': 'above_average', 'sessions': 3}]}, days[-1])
        self.assertAlmostEqual(above['matches'][0]['comparison'], 2)
        flat = scanner55.scan_books({'AAA': closes([2, 2, 2], days)}, {'conditions': [{'kind': 'above_average', 'sessions': 3}]}, days[-1])
        self.assertEqual(flat['counts']['matched'], 0)
        days = sessions(3)
        high = scanner55.scan_books({'AAA': closes([5, 6, 7], days)}, {'conditions': [{'kind': 'closing_high', 'sessions': 2}]}, days[-1])
        self.assertAlmostEqual(high['matches'][0]['comparison'], 6)
        tied = scanner55.scan_books({'AAA': closes([5, 6, 6], days)}, {'conditions': [{'kind': 'closing_high', 'sessions': 2}]}, days[-1])
        self.assertEqual(tied['counts']['matched'], 0)

    def test_gaps_splits_missing_volume_and_stale_prices_are_omissions(self):
        days = sessions(3)
        gap = scanner55.scan_books({'AAA': closes([10, 11], [days[0], days[2]])}, {'conditions': [{'kind': 'session_move', 'threshold': 1}]}, days[2])
        self.assertEqual(gap['omissions'][0]['reason'], 'gap')
        self.assertIn(days[1], gap['omissions'][0]['detail'])
        split = scanner55.scan_books({'AAA': closes([10, 40], days[:2])}, {'conditions': [{'kind': 'session_move', 'threshold': 1}]}, days[1])
        self.assertEqual(split['omissions'][0]['reason'], 'split')
        stale_days = sessions(2, dt.date(2026, 6, 1))
        stale = scanner55.scan_books({'AAA': closes([10, 11], stale_days)}, {'conditions': [{'kind': 'session_move', 'threshold': 1}]}, '2026-06-15')
        self.assertEqual(stale['omissions'][0]['reason'], 'stale')
        volume_days = sessions(21)
        volumes = closes([10] * 21, volume_days, volume=10)
        volumes[-1]['volume'] = None
        missing = scanner55.scan_books({'AAA': volumes}, {'conditions': [{'kind': 'unusual_volume', 'percentile': 90}]}, volume_days[-1])
        self.assertEqual(missing['omissions'][0]['reason'], 'incomplete-volume')
        loud = closes([10] * 21, volume_days, volume=10)
        loud[-1]['volume'] = 50
        found = scanner55.scan_books({'AAA': loud}, {'conditions': [{'kind': 'unusual_volume', 'percentile': 90}]}, volume_days[-1])
        self.assertEqual(found['counts']['matched'], 1)
        self.assertIn('Large daily move', scanner55.presets()[0]['plainEnglish'])

    def test_repeated_runs_keep_one_alert_and_a_dropout_is_recorded(self):
        days = sessions(2)
        stamps = [int(dt.datetime.fromisoformat(day + 'T16:00:00').replace(tzinfo=NY).timestamp() * 1000) for day in days]
        with s.db_connection() as con, con:
            con.executemany('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)', [
                ('TTWO', stamps[0], 100, 100, 100, 100, 1, 1),
                ('TTWO', stamps[1], 105, 105, 105, 105, 1, 1)])
        body = {'title': 'Five percent', 'alert': True, 'schedule': True, 'asOf': days[-1],
                'conditions': [{'kind': 'session_move', 'threshold': 5}]}
        first = scanner55.save(vars(s), body, 10)
        again = scanner55.save(vars(s), {**body, 'id': first['id']}, 20)
        self.assertEqual(first['result']['alertsCreated'], 1)
        self.assertEqual(again['result']['alertsCreated'], 0)
        self.assertEqual(again['result']['changes'][0]['change'], 'continued')
        moment = int(dt.datetime.fromisoformat(days[-1] + 'T18:00:00').replace(tzinfo=NY).timestamp() * 1000)
        self.assertTrue(scanner55.scheduled(vars(s), moment)['ran'])
        self.assertFalse(scanner55.scheduled(vars(s), moment)['ran'])
        with s.db_connection() as con, con:
            con.execute('UPDATE massive_daily_bars SET c=101 WHERE symbol=? AND ts_ms=?', ('TTWO', stamps[1]))
        dropped = scanner55.run(vars(s), {**body, 'id': first['id']}, 30, record=True)
        self.assertEqual(dropped['counts']['matched'], 0)
        self.assertEqual(dropped['changes'][0]['change'], 'dropped')
        opened = scanner55.read(vars(s), first['id'], 40)
        self.assertIn('not recalculated', opened['notice'])
        text, _evidence = scanner55.answer(vars(s), first['id'], 'TTWO')
        self.assertIn('TTWO', text)
        source = Path('site/scanner55.js').read_text()
        self.assertIn('id!==seq', source)
        self.assertIn('data-journal="scan"', source)
        self.assertIn('last.matches.filter', source)
        room = scanner55.refresh({'valid_symbol': lambda symbol: symbol, 'massive_daily_candles': lambda *_args: None, 'time': s.time}, ['TTWO', 'AMD'], 0)
        self.assertEqual(room['requested'], 0)

    def test_company_results_do_not_cross(self):
        days = sessions(2)
        result = scanner55.scan_books({
            'AAA': closes([100, 110], days),
            'BBB': closes([100, 101], days),
        }, {'conditions': [{'kind': 'session_move', 'threshold': 5}]}, days[-1])
        self.assertEqual([row['symbol'] for row in result['matches']], ['AAA'])
        other = scanner55.scan_books({'BBB': closes([100, 110], days)}, {'conditions': [{'kind': 'session_move', 'threshold': 5}]}, days[-1])
        self.assertEqual(other['matches'][0]['symbol'], 'BBB')
        self.assertNotIn('AAA', [row['symbol'] for row in other['matches']])
