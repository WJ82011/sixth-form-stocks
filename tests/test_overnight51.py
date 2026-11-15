import contextlib
import unittest
from pathlib import Path
from unittest.mock import patch

import learning40
import overnight51
import test_v3_api as fixture

s = fixture.s
NOW = 1794500000000  # 2026-11-12 07:13 New York, inside the default window and after 06:00


class OvernightTests(unittest.TestCase):
    setUp = fixture.V3APITests.setUp

    def test_schedule_uses_followed_companies_and_resumes_one_job(self):
        s.write_workspace({'watch': ['AAPL', 'AMD', 'TTWO']})
        saved = overnight51.save_schedule(vars(s), {'symbols': ['TTWO'], 'startHour': 0, 'endHour': 24, 'researchHour': 6}, NOW)
        self.assertEqual(saved['symbols'], ['TTWO'])
        calls = []
        with patch.object(s, 'get_massive_key', return_value='fixture'), patch.object(
                s, 'massive_daily_candles', lambda sym, start, end: calls.append(sym) or {'status': 'error', 'message': 'Provider unavailable'}):
            failed = overnight51.step(vars(s), NOW)
        self.assertEqual(failed['state'], 'attention')
        self.assertEqual(calls, ['TTWO'])
        with contextlib.closing(s.db_connection()) as con, con:
            con.execute("UPDATE overnight51_jobs SET status='running' WHERE kind='history'")
        overnight51.recover(vars(s), NOW + 1000)
        rows = overnight51.jobs(vars(s), '2026-11-12')
        history = [row for row in rows if row['kind'] == 'history']
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['status'], 'waiting')
        self.assertIn('same job resumes', history[0]['detail'])
        with patch.object(s, 'get_massive_key', return_value='fixture'), patch.object(
                s, 'massive_daily_candles', lambda sym, start, end: {'status': 'ok', 'source': 'Massive test'}):
            done = overnight51.step(vars(s), NOW + 2000)
        self.assertEqual(done['state'], 'completed')
        self.assertEqual(len([row for row in overnight51.jobs(vars(s), '2026-11-12') if row['kind'] == 'history']), 1)

    def test_pause_provider_failure_and_quiet_training_stay_single(self):
        s.write_workspace({'watch': ['AMD', 'TTWO']})
        overnight51.save_schedule(vars(s), {'symbols': ['AMD', 'TTWO'], 'startHour': 22, 'endHour': 7, 'researchHour': 6, 'quiet': 1}, NOW)
        self.assertEqual(overnight51.step(vars(s), NOW)['reason'], 'outside')
        overnight51.set_paused(vars(s), True, NOW)
        overnight51.save_schedule(vars(s), {'symbols': ['AMD'], 'startHour': 0, 'endHour': 24, 'researchHour': 6, 'paused': 1, 'quiet': 1}, NOW)
        self.assertEqual(overnight51.step(vars(s), NOW)['reason'], 'paused')
        overnight51.set_paused(vars(s), False, NOW)
        trained = []
        with patch.object(s, 'get_massive_key', return_value='fixture'), patch.object(
                s, 'massive_daily_candles', lambda sym, start, end: {'status': 'ok', 'source': 'Massive test'}), patch.object(
                learning40, 'report', lambda g, symbol: trained.append(symbol) or {'closes': 3, 'scorecard': {'pending': []}}):
            overnight51.step(vars(s), NOW)
            graded = overnight51.step(vars(s), NOW + 1)
            skipped = overnight51.step(vars(s), NOW + 2)
        self.assertEqual(trained, ['AMD'])
        self.assertIn('report used', graded['detail'])
        self.assertIn('left for another day', skipped['detail'])
        issued = s.db_connection().execute('SELECT COUNT(*) FROM learning41_issued').fetchone()[0]
        self.assertEqual(issued, 0)

    def test_morning_report_matches_the_job_and_names_a_gap(self):
        overnight51.save_schedule(vars(s), {'symbols': ['AAPL'], 'startHour': 0, 'endHour': 24, 'researchHour': 6}, NOW)
        with patch.object(s, 'get_massive_key', return_value='fixture'), patch.object(
                s, 'massive_daily_candles', lambda sym, start, end: {'status': 'ok', 'source': 'Massive test'}):
            overnight51.step(vars(s), NOW)
        with contextlib.closing(s.db_connection()) as con, con:
            con.execute('INSERT INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)', ('AAPL', NOW, 1, 1, 1, 10, 1, NOW // 1000))
            con.execute('INSERT INTO overnight51_beats VALUES(?)', (NOW - 30 * 60 * 1000,))
        report = overnight51.morning(vars(s), NOW - 3600000, NOW + 1000)
        self.assertEqual(report['savedBars'][0]['symbol'], 'AAPL')
        self.assertIn('Closes', report['jobs'][0]['detail'])
        self.assertTrue(report['gaps'])
        self.assertIn('asleep', report['gaps'][0]['note'])

    def test_busy_step_does_not_overlap(self):
        self.assertTrue(overnight51.BUSY.acquire(blocking=False))
        try:
            self.assertEqual(overnight51.step(vars(s), NOW)['state'], 'busy')
        finally:
            overnight51.BUSY.release()

    def test_watchlist_keeps_sixteen_companies(self):
        symbols = ['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AMD', 'PLTR', 'JPM', 'KO', 'DIS', 'NFLX', 'BA', 'TSM', 'TTWO', 'INTC']
        s.write_workspace({'watch': symbols})
        overnight51.save_schedule(vars(s), {'symbols': [], 'startHour': 0, 'endHour': 24, 'researchHour': 6}, NOW)
        overnight51.enqueue(vars(s), NOW)
        active = {row['symbol'] for row in overnight51.jobs(vars(s), '2026-11-12') if row['status'] == 'waiting'}
        self.assertEqual(len(active), 16)
        self.assertNotIn('INTC', active)

    def test_page_explains_the_awake_requirement(self):
        source = Path('site/overnight51.js').read_text()
        self.assertIn('Quiet mode', source)
        self.assertIn("pausing?'pause':'resume'", source)
        self.assertIn('window.changeView', source)
