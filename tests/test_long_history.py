"""Isolated imported daily-price contracts. Synthetic prices are test fixtures only."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('md_long_history',Path(__file__).parents[1]/'server.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class LongHistoryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  for attr,name in [('USER_DIR',''),('DB_FILE','prices.sqlite3')]:
   fix=patch.object(s,attr,Path(self.tmp.name)/name);fix.start();self.addCleanup(fix.stop)
  s.init_storage()
 def data(self,**changes):
  value={'symbol':'TTWO','csv':'Date,Close,Symbol\n2020-01-02,100,TTWO\n2025-01-02,150,TTWO\n','source':'Offline test fixture','confirmed':True,'split_adjusted':True};value.update(changes);return value
 def test_round_trip_sorted_and_source_separate(self):
  out=s.change_imported_history(self.data(csv='Date,Close\n2025-01-02,150\n2020-01-02,100\n'))
  self.assertEqual(out['count'],2)
  data=s.handle_api('/api/imported-history',{'symbol':['TTWO']})
  self.assertEqual([x['p'] for x in data['points']],[100,150]);self.assertEqual(data['provider'],'imported')
  with s.contextlib.closing(s.db_connection()) as con:
   self.assertEqual(con.execute('SELECT COUNT(*) FROM massive_daily_bars').fetchone()[0],0)
   self.assertEqual(con.execute('SELECT COUNT(*) FROM observations').fetchone()[0],0)
 def test_invalid_atomic_import_keeps_old_file(self):
  s.change_imported_history(self.data())
  for csv in ['Date,Close\n2020-01-02,0\n2025-01-02,4','Date,Close\n2020-01-02,nan\n2025-01-02,4','Date,Close\n2020-01-02,inf\n2025-01-02,4','Date,Close\n2020-01-02,10\n2020-01-02,20','Date,Close\n2999-01-02,10\n2025-01-02,20','Date,Close\n20200102,10\n2025-01-02,20','Date,Close\n1999-01-02,10\n2025-01-02,20','Date,Price\n2020-01-02,10','Date,Close\n2020-01-02,10']:
   with self.subTest(csv=csv),self.assertRaises(ValueError):s.change_imported_history(self.data(csv=csv))
  self.assertEqual(len(s.imported_history('TTWO')['points']),2)
 def test_symbol_confirmation_and_source_validation(self):
  for changes in [{'confirmed':False},{'split_adjusted':'yes'},{'source':'x'},{'source':'a\nb'},{'csv':'Date,Close,Symbol\n2020-01-02,10,AAPL\n2025-01-02,20,AAPL'}]:
   with self.subTest(changes=changes),self.assertRaises(ValueError):s.change_imported_history(self.data(**changes))
 def test_adjusted_close_preferred_and_unadjusted_label_preserved(self):
  text='Date,Close,Adj Close\n2020-01-02,200,100\n2025-01-02,150,150'
  s.change_imported_history(self.data(csv=text));self.assertEqual(s.imported_history('TTWO')['points'][0]['p'],100)
  with self.assertRaises(ValueError):s.change_imported_history(self.data(csv=text,split_adjusted=False))
  s.change_imported_history(self.data(split_adjusted=False));self.assertFalse(s.imported_history('TTWO')['split_adjusted'])
 def test_clear_only_selected_import_and_no_network(self):
  with patch.object(s,'provider_get',side_effect=AssertionError('network')),patch.object(s,'massive_request',side_effect=AssertionError('network')):
   s.change_imported_history(self.data());s.change_imported_history(self.data(symbol='AAPL',csv='Date,Close\n2020-01-02,10\n2025-01-02,20'))
   s.change_imported_history({'symbol':'TTWO','clear':True})
   self.assertEqual(s.imported_history('TTWO')['status'],'no_data');self.assertEqual(s.imported_history('AAPL')['status'],'ok')
 def test_bom_and_quoted_csv_supported(self):
  s.change_imported_history(self.data(csv='\ufeff"Date","Close"\n"2020-01-02","10.50"\n"2025-01-02","20.25"'))
  self.assertEqual(s.imported_history('TTWO')['points'][0]['p'],10.5)
 def test_http_import_enforces_origin_header_and_validates_data(self):
  import threading, json, urllib.request, urllib.error
  http=s.ThreadingHTTPServer(('127.0.0.1',0),s.AppHandler)
  thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  url='http://127.0.0.1:'+str(http.server_address[1])+'/api/imported-history'
  try:
   for headers in [{},{'X-MD-Request':'1','Origin':'https://example.com'}]:
    request=urllib.request.Request(url,data=json.dumps(self.data()).encode(),headers=headers)
    with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request)
    self.assertEqual(error.exception.code,403)
   request=urllib.request.Request(url,data=json.dumps(self.data()).encode(),headers={'X-MD-Request':'1','Content-Type':'application/json'})
   with urllib.request.urlopen(request) as response:self.assertEqual(json.load(response)['count'],2)
   with urllib.request.urlopen(url+'?symbol=TTWO') as response:self.assertEqual(json.load(response)['provider'],'imported')
  finally:http.shutdown();http.server_close();thread.join(2)
if __name__=='__main__':unittest.main()
