"""Sources, periods and capitalization arithmetic. Imported fixtures are synthetic."""
import unittest,copy,csv,io,contextlib,json
from unittest.mock import patch
import market36 as m
import test_v3_api as fixture
s=fixture.s
class MarketValueTests(unittest.TestCase):
 setUp=fixture.V3APITests.setUp
 def rows(self):return [{'market':'UK equities','currency':'GBP','date':d,'capitalization':v,'unit':'trillions','scope':'Synthetic matching coverage','source':'https://example.com/source'} for d,v in [('2025-12-31','3'),('2026-03-31','2.7')]]
 def data(self,rows):
  f=io.StringIO();w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);return {'csv':f.getvalue(),'coverageConfirmed':True}
 def test_published_us_comparison_is_quarterly_and_attributed(self):
  row=m.cards(vars(s))[0];self.assertEqual(row['start'],'2026-06-30');self.assertEqual(row['end'],'2026-09-30');self.assertAlmostEqual(row['change'],3455868.4);self.assertIn('siblisresearch',row['sources'][0]);self.assertTrue(all(x['change'] is None for x in m.cards(vars(s))[1:]))
 def test_import_normalizes_units_and_keeps_us_fallback(self):
  m.import_csv(vars(s),self.data(self.rows()));rows=m.cards(vars(s));self.assertAlmostEqual(rows[1]['change'],-300000);self.assertIsNotNone(rows[0]['change']);self.assertIn('User-supplied',rows[1]['status']);self.assertIn('Siblis',rows[0]['status'])
 def test_invalid_import_cannot_replace_last_good_values(self):
  m.import_csv(vars(s),self.data(self.rows()));before=m.cards(vars(s));rows=self.rows();rows[1]['scope']='Different coverage'
  with self.assertRaises(ValueError):m.import_csv(vars(s),self.data(rows))
  self.assertEqual(m.cards(vars(s)),before)
 def test_currency_future_dates_nan_and_duplicate_dates_rejected(self):
  for key,value in [('currency','USD'),('date','2099-01-01'),('capitalization','NaN'),('source','https://example.com/?token=secret')]:
   rows=self.rows();rows[1][key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):m.clean(rows)
  rows=self.rows();rows[1]['date']=rows[0]['date']
  with self.assertRaises(ValueError):m.clean(rows)
 def test_attestation_required(self):
  payload=self.data(self.rows());payload['coverageConfirmed']=False
  with self.assertRaises(ValueError):m.import_csv(vars(s),payload)

 def test_csv_export_roundtrip_and_attribution(self):
  m.import_csv(vars(s),self.data(self.rows()));before=m.cards(vars(s));export=m.export(vars(s))['csv']
  m.import_csv(vars(s),{'csv':export,'coverageConfirmed':True});after=m.cards(vars(s))
  self.assertEqual(after[1],before[1]);self.assertEqual(after[0]['change'],before[0]['change']);self.assertEqual(after[0]['sources'],before[0]['sources'])
