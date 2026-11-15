"""Evidence, chart board, investigations, model ledger and repairs. Figures are test records."""
import datetime as dt
import time
import unittest

import desk50
import desk61
import events42
import test_v3_api as fixture

s = fixture.s
NOW = int(dt.datetime(2026, 1, 12, 18, tzinfo=events42.NY).timestamp() * 1000)


def stamp(day, hour=16):
    return int(dt.datetime.combine(day, dt.time(hour), events42.NY).timestamp() * 1000)


def bars(symbol, days, prices, fetched=10):
    with s.LOCK, s.db_connection() as con, con:
        for day, price in zip(days, prices):
            con.execute('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)',
                        (symbol, stamp(day), price, price, price, price, 1, fetched))


class Desk61Tests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_weekly_investigation_can_pause_and_keeps_its_source(self):
        start, end = desk61._week(NOW)
        days = desk61._sessions(start, end)
        bars('TTWO', [dt.date.fromisoformat(day) for day in days], [100, 101, 102, 103, 110])
        bars('SPY', [dt.date.fromisoformat(day) for day in days], [400, 400, 400, 400, 404])
        plan = desk61.propose(vars(s), "Investigate TTWO's latest completed weekly move.", NOW)
        self.assertFalse(plan['calculated'])
        self.assertEqual(len(plan['steps']), 5)
        job = desk61.start(vars(s), plan['question'], NOW)
        job = desk61.step(vars(s), job['id'], NOW)
        self.assertEqual(job['steps'][0]['status'], 'done')
        desk61.cancel(vars(s), job['id'], NOW)
        with self.assertRaises(ValueError):
            desk61.step(vars(s), job['id'], NOW)
        desk61.resume(vars(s), job['id'], NOW)
        finished = desk61.run_all(vars(s), job['id'], NOW)
        self.assertEqual(finished['status'], 'done')
        self.assertIn('10.00%', finished['steps'][1]['detail'])
        self.assertIn('SPY 1.00%', finished['steps'][2]['detail'])
        traced = desk61.trace(finished)
        prices = [ref for step in traced['steps'] for ref in step['references'] if ref['kind'] == 'price']
        self.assertTrue(prices)
        self.assertIsNotNone(prices[0]['publishedAt'])
        self.assertEqual(prices[0]['retrievedAt'], 10000)
        self.assertNotEqual(prices[0]['publishedAt'], prices[0]['retrievedAt'])
        reopened = desk61.read(vars(s), finished['id'])
        self.assertIn('not recalculated', reopened['notice'])
        self.assertEqual(reopened['fingerprint'], finished['fingerprint'])

    def test_missing_prices_do_not_become_a_number(self):
        job = desk61.start(vars(s), 'Investigate TTWO latest completed weekly move.', NOW)
        finished = desk61.run_all(vars(s), job['id'], NOW)
        self.assertEqual(finished['steps'][1]['status'], 'gap')
        self.assertNotIn('%', finished['steps'][-1]['detail'])

    def test_a_changed_close_creates_a_new_version(self):
        start, end = desk61._week(NOW)
        days = [dt.date.fromisoformat(day) for day in desk61._sessions(start, end)]
        bars('TTWO', days, [100, 100, 100, 100, 110])
        bars('SPY', days, [100, 100, 100, 100, 100])
        job = desk61.run_all(vars(s), desk61.start(vars(s), 'Investigate TTWO latest completed weekly move.', NOW)['id'], NOW)
        same = desk61.refresh(vars(s), job['id'], NOW + 1)
        self.assertEqual(same['id'], job['id'])
        with s.LOCK, s.db_connection() as con, con:
            con.execute('UPDATE massive_daily_bars SET o=?,h=?,l=?,c=? WHERE symbol=? AND ts_ms=?',
                        (120, 120, 120, 120, 'TTWO', stamp(days[-1])))
        newer = desk61.refresh(vars(s), job['id'], NOW + 2)
        self.assertNotEqual(newer['id'], job['id'])
        self.assertEqual(newer['previousId'], job['id'])
        self.assertIn('20.00%', newer['steps'][1]['detail'])
        original = desk61.read(vars(s), job['id'])
        self.assertIn('10.00%', original['steps'][1]['detail'])

    def test_shared_board_shows_a_gap_and_reopens(self):
        days = [dt.date(2026, 1, 5), dt.date(2026, 1, 6), dt.date(2026, 1, 7)]
        bars('TTWO', days, [100, 110, 120])
        bars('AAPL', days[:2], [50, 55])
        events42.store(vars(s), 'TTWO', {'events': [{'title': 'Test item', 'publishedAt': stamp(days[1])}]}, NOW)
        built = desk61.build(vars(s), {'symbols': ['TTWO', 'AAPL'], 'start': '2026-01-05', 'end': '2026-01-07',
                                        'shared': True, 'mode': 'percent'}, NOW)
        take_two = next(panel for panel in built['panels'] if panel['symbol'] == 'TTWO')
        self.assertTrue(any(row['date'] == '2026-01-06' for row in take_two['events']))
        apple = next(panel for panel in built['panels'] if panel['symbol'] == 'AAPL')
        self.assertIn('2026-01-07', apple['missing'])
        self.assertIsNone(apple['points'][-1]['plot'])
        self.assertEqual(apple['points'][0]['plot'], 100)
        saved = desk61.save_board(vars(s), {'symbols': ['TTWO', 'AAPL'], 'start': '2026-01-05', 'end': '2026-01-07',
                                             'shared': True, 'mode': 'percent'}, NOW)
        opened = desk61.read_board(vars(s), saved['id'])
        self.assertIn('not rebuilt', opened['notice'])
        self.assertEqual(opened['panels'][0]['points'][0]['price'], 100)

    def test_large_board_stays_quick(self):
        books = {}
        for symbol in ('TTWO', 'AAPL', 'MSFT', 'NVDA'):
            books[symbol] = [{'date': f'2020-01-{(index % 27) + 1:02d}', 'price': 100 + index % 17,
                              'retrievedAt': 1, 'publishedAt': 2} for index in range(800)]
        started = time.perf_counter()
        built = desk61.assemble(list(books), books, '', '', False, 'price')
        elapsed = time.perf_counter() - started
        self.assertLess(elapsed, 1)
        self.assertEqual(len(built['panels'][0]['points']), 800)
        self.assertEqual(built['panels'][0]['points'][0]['price'], books['TTWO'][0]['price'])

    def test_failed_candidates_stay_and_baseline_can_remain(self):
        prices = [{'t': index * 86400000, 'p': 100 * (1.0003 ** index)} for index in range(420)]
        first = desk61.evaluate_candidate(vars(s), 'steady', {'horizon': 5}, prices, NOW)
        second = desk61.evaluate_candidate(vars(s), 'steady', {'horizon': 5}, prices, NOW + 1)
        saved = desk61.experiments(vars(s))
        self.assertEqual(len(saved), 2)
        self.assertGreaterEqual(second['trials'], 2)
        self.assertIn(first['activeMethod'], ('baseline', 'steady'))
        if first['full'].get('status') != 'learned':
            self.assertEqual(first['activeMethod'], 'baseline')
        self.assertIn('unchanged-price baseline', ' '.join(first['criteria']))
        with s.db_connection() as con:
            self.assertEqual(con.execute('SELECT count(*) FROM learning40').fetchone()[0], 0)

    def test_duplicate_repair_is_inspected_recoverable_and_leaves_imports(self):
        day = dt.date(2026, 1, 5)
        bars('TTWO', [day, dt.date(2026, 1, 6)], [100, 110])
        with s.LOCK, s.db_connection() as con, con:
            con.execute('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)',
                        ('TTWO', stamp(day, 20), 90, 90, 90, 90, 1, 1))
            con.execute('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)',
                        ('TTWO', stamp(dt.date(2026, 1, 7)), 400, 400, 400, 400, 1, 1))
            con.execute('INSERT INTO imported_daily_history VALUES(?,?)', ('TTWO', 'USER-IMPORT'))
        report = desk61.inspect(vars(s), 'TTWO', NOW)
        kinds = {item['kind'] for item in report['problems']}
        self.assertIn('duplicate', kinds)
        self.assertIn('adjustment', kinds)
        self.assertIn('imported', kinds)
        with self.assertRaises(ValueError):
            desk61.repair(vars(s), 'TTWO', 'not-inspected', NOW)
        g = vars(s).copy()
        g['desk61_fail'] = True
        with self.assertRaises(ValueError):
            desk61.repair(g, 'TTWO', report['id'], NOW)
        with s.db_connection() as con:
            self.assertEqual(con.execute('SELECT count(*) FROM massive_daily_bars WHERE symbol=?', ('TTWO',)).fetchone()[0], 4)
            self.assertEqual(con.execute('SELECT payload FROM imported_daily_history WHERE symbol=?', ('TTWO',)).fetchone()[0], 'USER-IMPORT')
        done = desk61.repair(vars(s), 'TTWO', report['id'], NOW)
        self.assertEqual(done['removed'], 1)
        with s.db_connection() as con:
            self.assertEqual(con.execute('SELECT count(*) FROM massive_daily_bars WHERE symbol=?', ('TTWO',)).fetchone()[0], 3)
            self.assertEqual(con.execute('SELECT payload FROM imported_daily_history WHERE symbol=?', ('TTWO',)).fetchone()[0], 'USER-IMPORT')
        desk61.undo_repair(vars(s), 'TTWO')
        with s.db_connection() as con:
            self.assertEqual(con.execute('SELECT count(*) FROM massive_daily_bars WHERE symbol=?', ('TTWO',)).fetchone()[0], 4)

    def test_backup_restores_an_investigation(self):
        job = desk61.start(vars(s), 'Investigate TTWO latest completed weekly move.', NOW)
        name = desk50.create_backup(vars(s))['file']
        with s.LOCK, s.db_connection() as con, con:
            con.execute('DELETE FROM desk61_jobs')
        desk50.restore_backup(vars(s), name, 'restore-this-backup')
        self.assertEqual(desk61.read(vars(s), job['id'])['symbol'], 'TTWO')

    def test_provider_failure_is_a_gap(self):
        g = vars(s).copy()

        def fail(*_args, **_kwargs):
            raise OSError('provider unavailable')

        g['read_massive_daily_bars'] = fail
        start, end = desk61._week(NOW)
        days = [dt.date.fromisoformat(day) for day in desk61._sessions(start, end)]
        bars('TTWO', days, [100, 100, 100, 100, 100])
        job = desk61.start(g, 'Investigate TTWO latest completed weekly move.', NOW)
        # The week step does not read prices. The return step does.
        desk61.step(g, job['id'], NOW)
        finished = desk61.run_all(g, job['id'], NOW)
        self.assertEqual(finished['steps'][1]['status'], 'gap')
        self.assertIn('provider unavailable', finished['steps'][1]['detail'])
