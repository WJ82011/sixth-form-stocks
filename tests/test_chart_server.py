"""v1.6 local HTTP integration and asset integrity; no Finnhub account used."""
import importlib.util
import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).parents[1]
spec=importlib.util.spec_from_file_location('marketdesk_chart_server',ROOT/'server.py')
s=importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)

class ChartAssetTests(unittest.TestCase):
    def test_server_exposes_new_library_only_on_localhost(self):
        with tempfile.TemporaryDirectory() as home:
            with patch.object(s,'USER_DIR',Path(home)),patch.object(s,'DB_FILE',Path(home)/'data.sqlite3'),patch.object(s,'KEY_FILE',Path(home)/'no_key'):
                s.init_storage()
                server=s.ThreadingHTTPServer(('127.0.0.1',0),s.AppHandler)
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                try:
                    url='http://127.0.0.1:'+str(server.server_address[1])
                    pages={
                        'index.html':(s.SITE/'index.html').read_text(),
                        'view-loader.js':(s.SITE/'view-loader.js').read_text(),
                        'app.js':(s.SITE/'app.js').read_text(),
                        'styles.css':(s.SITE/'styles.css').read_text(),
                    }
                    for name,needle in [('chart-research.js','headlineSignal'),('app.js','forecastHeadlines'),('styles.css','forecast-overlay-switch')]:
                        with urllib.request.urlopen(url+'/'+name,timeout=3) as response:
                            self.assertEqual(response.status,200)
                            self.assertIn(needle,response.read().decode())
                    self.assertIn('/chart-research.js',pages['index.html']+pages['view-loader.js'])
                    with urllib.request.urlopen(url+'/index.html',timeout=3) as response:
                        self.assertIn('Content-Security-Policy',response.headers)
                    with urllib.request.urlopen(url+'/api/selftest',timeout=3) as response:
                        audit=json.load(response)
                    self.assertTrue(audit['ok'])
                    self.assertIn('essential assets present',str(audit['checks']))
                finally:
                    server.shutdown();server.server_close();thread.join(timeout=2)

if __name__=='__main__':unittest.main()
