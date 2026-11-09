"""Synthetic saved-price fixtures; no external requests or personal data."""
import contextlib,datetime as dt,importlib.util,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('offline_restart_server',Path(__file__).parents[1]/'server.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class OfflineRestartTests(unittest.TestCase):
 def test_saved_prices_survive_storage_reinitialisation_and_need_no_provider(self):
  with tempfile.TemporaryDirectory() as tmp:
   home=Path(tmp)
   with patch.object(s,'USER_DIR',home),patch.object(s,'DB_FILE',home/'prices.sqlite3'):
    s.init_storage()
    t=int(dt.datetime(2025,1,2,15,tzinfo=dt.timezone.utc).timestamp())
    with contextlib.closing(s.db_connection()) as c,c:
     c.executemany('INSERT INTO observations VALUES(?,?,?,?,?)',[('AAA',t*1000,10,'finnhub_quote',t*1000),('AAA',(t+60)*1000,11,'finnhub_quote',(t+60)*1000)])
    s.store_massive_daily_bars('AAA',{'t':[t,t+86400],'o':[10,11],'h':[11,12],'l':[9,10],'c':[10,11],'v':[100,100]})
    # Startup recreates tables/indexes without deleting existing rows.
    s.init_storage()
    with patch.object(s,'provider_get',side_effect=AssertionError('Offline path requested network')),patch.object(s,'massive_request',side_effect=AssertionError('Offline path requested network')):
     observed=s.handle_api('/api/history',{'symbol':['AAA'],'since':['0']})
     daily=s.handle_api('/api/saved-daily',{'symbol':['AAA'],'from':[str(t-86400)],'to':[str(t+2*86400)]})
    self.assertEqual([p['p'] for p in observed['points']],[10,11]);self.assertEqual(observed['points'][-1]['t'],(t+60)*1000)
    self.assertEqual(daily['status'],'ok');self.assertEqual(daily['candles']['c'],[10,11]);self.assertTrue(daily['cached'])
