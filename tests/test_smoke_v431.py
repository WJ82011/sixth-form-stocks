'''Homepage buttons, full-width modes and a late company reply. Disposable server only.'''
import importlib.util
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CHROME = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
spec = importlib.util.spec_from_file_location('smoke_server', ROOT / 'server.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class HomeSmokeTest(unittest.TestCase):
    def test_homepage_buttons_modes_and_late_company_reply(self):
        if not CHROME.is_file():
            self.skipTest('Google Chrome is not installed')
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            with patch.object(server, 'USER_DIR', home), patch.object(server, 'DB_FILE', home / 'observations.sqlite3'), patch.object(server, 'KEY_FILE', home / 'finnhub_key'), patch.object(server, 'MASSIVE_KEY_FILE', home / 'massive_key'), patch.object(server, 'WORKSPACE_FILE', home / 'workspace.json'):
                server.init_storage()
                httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.AppHandler)
                thread = threading.Thread(target=httpd.serve_forever, daemon=True)
                thread.start()
                profile = home / 'chrome'
                try:
                    port = httpd.server_address[1]
                    command = [
                        str(CHROME), '--headless=new', '--disable-gpu', '--no-first-run',
                        '--window-size=1920,1000', f'--user-data-dir={profile}',
                        '--virtual-time-budget=30000', '--timeout=30000', '--dump-dom',
                        f'http://127.0.0.1:{port}/?smoke=431',
                    ]
                    completed = subprocess.run(command, text=True, capture_output=True, timeout=45)
                finally:
                    httpd.shutdown()
                    httpd.server_close()
                    thread.join(timeout=2)
        page = completed.stdout
        self.assertIn('id="smoke431-result"', page, completed.stderr[-500:])
        start = page.index('id="smoke431-result"')
        block = page[start:start + 2500]
        self.assertNotIn('FAIL ', block, block)
        for label in ('homepage controls', 'My Desk opens home', 'Explore opens markets', 'Investigate opens company', 'My Research opens research', 'Settings opens settings', 'standard fills the window', 'professional fills the window', 'late Take-Two news does not replace AMD', 'company events follow AMD', 'research follows AMD'):
            self.assertIn('PASS ' + label, block)
