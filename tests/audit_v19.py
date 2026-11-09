#!/usr/bin/env python3
"""Browser audit of v1.9 new features, strictly offline fixture-only data."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from audit_browser import HTML,FAKE_JS,JS_FILES
ROOT=Path(__file__).resolve().parents[1]
passes=[]
def check(name,condition):
 if not condition: raise AssertionError(name)
 passes.append(name);print('PASS',name,flush=True)
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':1512,'height':980},accept_downloads=True)
 errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
 page.set_content(HTML,wait_until='domcontentloaded');page.evaluate(FAKE_JS)
 for js in JS_FILES: page.add_script_tag(content=(ROOT/'site'/js).read_text())
 page.wait_for_timeout(800)
 page.locator('[data-view="indicators"]').click()
 check('Chart Indicators navigation',page.locator('#view-indicators').is_visible())
 page.locator('#ind-symbol').select_option('AAPL')
 page.locator('#ind-run').click();page.wait_for_timeout(240)
 check('Indicators use test-only verified-history fixture',page.locator('#ind-chart svg path').count()>=3)
 check('Source and genuine sample count reported','90 recorded daily closing prices' in page.locator('#ind-status').inner_text())
 page.locator('[data-indicator="bb"]').check()
 check('Bollinger Bands render only when requested',page.locator('#ind-chart svg polygon').count()==1)
 page.screenshot(path='/mnt/data/MarketDesk-v1.9-Indicators-Preview.png',full_page=False)
 page.locator('[data-view="valuation"]').click()
 check('Company Valuation navigation',page.locator('#view-valuation').is_visible())
 page.locator('#dcf-run').click()
 check('No DCF valuation without supplied financial inputs','Fill in every required' in page.locator('#dcf-state').inner_text())
 for key,val in [('dcf-symbol','AAPL'),('dcf-source','TEST-ONLY numbers · not actual Apple financials'),('dcf-fcf','100'),('dcf-netdebt','100'),('dcf-shares','50'),('dcf-growth','5'),('dcf-discount','10'),('dcf-terminal','2')]:
  page.locator('#'+key).fill(val)
 page.locator('#dcf-run').click()
 check('DCF output and 3x3 sensitivity visible',page.locator('#dcf-results .v19-metrics article').count()==4 and page.locator('#dcf-results table').count()==2)
 check('DCF known test result correct','26.92' in page.locator('#dcf-results').inner_text())
 page.locator('#dcf-discount').fill('2');page.locator('#dcf-terminal').fill('3');page.locator('#dcf-run').click()
 check('DCF rejects impossible discount/terminal assumption','Discount rate must exceed' in page.locator('#dcf-state').inner_text())
 page.locator('#dcf-discount').fill('10');page.locator('#dcf-terminal').fill('2');page.locator('#dcf-run').click()
 with page.expect_download() as info:page.locator('#dcf-export').click()
 check('DCF assumptions can be exported to Markdown',info.value.suggested_filename.endswith('.md'))
 page.screenshot(path='/mnt/data/MarketDesk-v1.9-Valuation-Preview.png',full_page=False)
 page.locator('[data-view="portfolio"]').click()
 check('Practice Portfolio navigation',page.locator('#view-portfolio').is_visible())
 page.locator('#port-symbol').fill('AAPL')
 page.locator('#port-qty').fill('2');page.locator('#port-price').fill('125');page.locator('#port-add').click()
 check('Hypothetical BUY stored',page.locator('#port-content').inner_text().count('AAPL')>=2)
 check('Practice trade saved in browser backup state',len(page.evaluate('JSON.parse(localStorage.getItem("md-reborn-portfolio")).trades'))==1)
 page.locator('#port-side').select_option('SELL');page.locator('#port-qty').fill('3');page.locator('#port-price').fill('130');page.locator('#port-add').click()
 check('Oversell rejected','Cannot sell more' in page.locator('#port-state').inner_text())
 check('Rejected paper trade not recorded',len(page.evaluate('JSON.parse(localStorage.getItem("md-reborn-portfolio")).trades'))==1)
 page.locator('#port-capital').fill('5000');page.locator('#port-capital-save').click()
 check('Virtual initial cash cannot change after trade','before recording trades' in page.locator('#port-state').inner_text())
 page.locator('#port-side').select_option('SELL');page.locator('#port-qty').fill('1');page.locator('#port-price').fill('130');page.locator('#port-add').click()
 check('Valid paper sell recorded',len(page.evaluate('JSON.parse(localStorage.getItem("md-reborn-portfolio")).trades'))==2)
 with page.expect_download() as info:page.locator('#port-export').click()
 check('Practice trades export CSV',info.value.suggested_filename.endswith('.csv'))
 page.wait_for_timeout(500)
 snapshot=page.evaluate('snapshotWorkspace()')
 check('Private workspace snapshot contains paper portfolio',len(snapshot['portfolio']['trades'])==2)
 check('Private workspace snapshot contains no provider keys',not any(k in snapshot for k in ('finnhub_key','massive_key','apikey')))
 page.screenshot(path='/mnt/data/MarketDesk-v1.9-Portfolio-Preview.png',full_page=False)
 # Verify the same Settings import path used for portable research backups.
 import json
 page.locator('[data-view="settings"]').click()
 portable={'format':'MarketDesk-Research-Backup','version':1,'snapshot':{
  'watch':['AAPL','MSFT'],'names':{},'notes':[],'reports':[],
  'portfolio':{'capital':13000,'trades':[{'symbol':'MSFT','side':'BUY','qty':4,'price':200,'date':'2026-11-02T16:00:00Z'}]},
  'preferences':{},'tapeSymbol':'AAPL'}}
 page.locator('#import-workspace').set_input_files({'name':'MarketDesk-test.json','mimeType':'application/json','buffer':json.dumps(portable).encode()})
 page.wait_for_timeout(220)
 restored=page.evaluate('JSON.parse(localStorage.getItem("md-reborn-portfolio"))')
 check('Research backup import restores saved paper capital and trades',restored['capital']==13000 and len(restored['trades'])==1 and restored['trades'][0]['symbol']=='MSFT')
 check('No browser errors after importing a paper portfolio',errors==[])
 # Responsive audit: narrow sidebar and all 3 screens available.
 page.set_viewport_size({'width':390,'height':844})
 page.locator('#menu-toggle').click();page.locator('[data-view="valuation"]').click()
 check('Company Valuation navigates on mobile',page.locator('#view-valuation').is_visible())
 check('No browser JavaScript exceptions',errors==[])
 browser.close()
print('SUMMARY',len(passes),'checks, errors',errors)
