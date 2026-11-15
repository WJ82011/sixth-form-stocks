"""Offline checks for the original Market Desk Crest's application integration."""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site'

class IdentityTests(unittest.TestCase):
    def test_scalable_local_vector_mark(self):
        root=ET.parse(SITE/'brand-mark.svg').getroot()
        self.assertEqual(root.attrib['viewBox'],'0 0 56 56')
        self.assertEqual(root.tag,'{http://www.w3.org/2000/svg}svg')
        self.assertEqual(len(list(root)),1)
        self.assertNotIn('http',list(root)[0].attrib.get('d',''))
    def test_favicon_and_touch_assets_exist(self):
        self.assertEqual(ET.parse(SITE/'favicon.svg').getroot().tag,'{http://www.w3.org/2000/svg}svg')
        self.assertEqual((SITE/'apple-touch-icon.png').read_bytes()[:8],b'\x89PNG\r\n\x1a\n')
    def test_both_edition_header_marks_look_up_local_asset(self):
        html=(SITE/'index.html').read_text()
        self.assertEqual(html.count('src="/brand-mark.svg"'),3)
        self.assertIn('<link rel="icon" type="image/svg+xml" href="/favicon.svg">',html)
        self.assertIn('href="/apple-touch-icon.png"',html)
        self.assertNotIn('class="brand-slash"',html)
        self.assertIn('SIGNAL / PRO <span class="brand-version">6.8.0',html)
        self.assertIn('data-md-version',html)
        self.assertNotIn('Market Desk<span>4.3</span>',html)
        self.assertTrue((SITE/'release.js').exists())
    def test_local_server_serves_icons_safely(self):
        server=(ROOT/'server.py').read_text()
        for file,ctype in [('brand-mark.svg','image/svg+xml'),('favicon.svg','image/svg+xml'),('apple-touch-icon.png','image/png')]:
            self.assertIn("'/"+file+"':'"+file+"'",server)
            self.assertIn("'"+file+"':'"+ctype+"'",server)
    def test_style_removes_old_tile_and_scales_with_edition(self):
        css=(SITE/'terminal.css').read_text()
        self.assertIn('background:none!important',css)
        self.assertIn('body[data-edition="professional"] .brand-mark',css)
        self.assertIn('.pro-mark img',css)

if __name__=='__main__': unittest.main()
