"""New design options remain bounded and survive the existing workspace boundary."""
import unittest
import server
class DesignSettingsTests(unittest.TestCase):
 def test_design_fields_are_whitelisted(self):
  clean=server.normalise_workspace({'design':{'theme':'light','shell':'sidebar','accent':'cyan','intensity':900,'enabled':False,'pointer':'yes','apiKey':'private','style':'invalid'}})['design']
  self.assertEqual(clean,{'theme':'light','shell':'sidebar','accent':'cyan','intensity':100,'enabled':False})
 def test_old_backups_and_bad_data(self):
  for value in (None,[],False,'anything'):
   self.assertEqual(server.normalise_workspace({'design':value})['design'],{})
  self.assertEqual(server.normalise_workspace({})['design'],{})
 def test_intensity_is_numeric_and_bounded(self):
  for value,expected in ((-20,0),(32,30),(float('inf'),None),(True,None)):
   d=server.normalise_workspace({'design':{'intensity':value}})['design']
   self.assertEqual(d.get('intensity'),expected)
