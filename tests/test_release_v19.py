"""Release 1.9: offline data integrity and Mac packaging contracts."""
import sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server as s
ROOT=Path(__file__).resolve().parents[1]
class Release19(unittest.TestCase):
 def test_app_navigation_and_version(self):
  html=(s.SITE/'index.html').read_text()
  self.assertEqual(s.VERSION,'6.8.0')
  for name in ('indicators','valuation','portfolio'):
   self.assertIn('data-view="'+name+'"',html)
   self.assertIn('id="view-'+name+'"',html)
  for asset in ('v19.js','v19.css','v19-models.js'):
   self.assertTrue((s.SITE/asset).is_file())
   self.assertIn("'/"+asset+"':'"+asset+"'",(ROOT/'server.py').read_text())
 def test_portfolio_backup_only_clean_bounded_fields(self):
  portfolio={'capital':10000,'trades':[{'symbol':'AAPL','side':'BUY','qty':2,'price':100,'date':'2026-11-02','apikey':'PRIVATE-DO-NOT-SAVE'}, {'symbol':'../../','side':'BUY','qty':1,'price':20},{'symbol':'NVDA','side':'SELL','qty':1,'price':float('inf')}], 'token':'NOT STORED'}
  clean=s.normalise_workspace({'portfolio':portfolio})
  self.assertEqual(clean['portfolio'],{'capital':10000,'trades':[{'symbol':'AAPL','side':'BUY','qty':2,'price':100,'date':'2026-11-02'}]})
  self.assertNotIn('PRIVATE',str(clean))
  self.assertNotIn('token',str(clean))
 def test_older_backup_compatible(self):
  self.assertEqual(s.normalise_workspace({'watch':['AAPL']})['portfolio'],{'capital':10000,'trades':[]})
 def test_paper_trades_persist_atomically(self):
  with tempfile.TemporaryDirectory() as tmp:
   with patch.object(s,'USER_DIR',Path(tmp)),patch.object(s,'WORKSPACE_FILE',Path(tmp)/'workspace.json'):
    clean={'portfolio':{'capital':12000,'trades':[{'symbol':'MSFT','side':'BUY','qty':1,'price':250,'date':'2026-11-02'}]}}
    s.write_workspace(clean)
    result=s.read_workspace()['snapshot']
    self.assertEqual(result['portfolio']['capital'],12000)
    self.assertEqual(result['portfolio']['trades'][0]['symbol'],'MSFT')
    self.assertEqual((Path(tmp)/'workspace.json').stat().st_mode&0o777,0o600)
if __name__=='__main__':unittest.main()
