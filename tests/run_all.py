"""Isolated regression runner: no personal configuration and no real network."""
import pathlib, tempfile, unittest, sys, urllib.request
original_urlopen=urllib.request.urlopen
def offline_urlopen(req,*args,**kwargs):
    url=req.full_url if hasattr(req,"full_url") else str(req)
    if url.startswith(("http://127.0.0.1:","http://localhost:")):
        return original_urlopen(req,*args,**kwargs)
    raise AssertionError("Unexpected live network call in offline regression")
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
with tempfile.TemporaryDirectory() as tmp, patch('pathlib.Path.home',return_value=pathlib.Path(tmp)):
    suite=unittest.defaultTestLoader.discover(str(pathlib.Path(__file__).parent),'test_*.py')
    with patch('urllib.request.urlopen',side_effect=offline_urlopen):
        result=unittest.TextTestRunner(verbosity=1).run(suite)
    sys.exit(not result.wasSuccessful())
