#!/usr/bin/env python3
"""Offline end-to-end v1.8 audit with entirely simulated data. Never ships test values as market data."""
import json,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_browser import HTML,FAKE_JS,JS_FILES
ROOT=Path(__file__).resolve().parents[1]
assert 'macro.js' in JS_FILES,JS_FILES
checks=[]
def check(label,condition):
 if not condition:raise AssertionError(label)
 checks.append(label);print('PASS',label,flush=True)
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':1440,'height':960},accept_downloads=True)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content(HTML,wait_until='domcontentloaded')
 page.evaluate(FAKE_JS.replace('getWorkspace:()=>workspace','getWorkspace:()=>workspace,setWorkspace:v=>{workspace=v}'))
 for name in JS_FILES:page.add_script_tag(content=(ROOT/'site'/name).read_text())
 page.wait_for_timeout(800)
 page.locator('[data-view="reports"]').click()
 page.locator('#report-title').fill('Temporary reliability regression report')
 page.locator('#report-summary').fill('This should be deleted, including across a restart.')
 page.locator('#report-save').click()
 check('Report saved before deletion',page.locator('.report-library-item').count()==1)
 older=page.evaluate('JSON.parse(localStorage.getItem("md-reborn-reports"))')
 check('Original saved report is not a deletion',len(older)==1 and older[0].get('deleted') is False)
 page.once('dialog',lambda dlg:dlg.accept())
 page.locator('[data-report-delete]').click()
 check('Deletion immediately removes visible report',page.locator('.report-library-item').count()==0)
 state=page.evaluate('JSON.parse(localStorage.getItem("md-reborn-reports"))')
 check('Deletion tombstone saved synchronously in browser',len(state)==1 and state[0]['deleted'] is True)
 # Recreate the exact bug: older server data exists, but browser already remembers deletion.
 page.evaluate('window.__audit.setWorkspace({watch:["AAPL"],names:{},notes:[],reports:window.__staleReports,preferences:{},tapeSymbol:"AAPL"})') if False else None
 page.evaluate('(older)=>window.__audit.setWorkspace({watch:["AAPL"],names:{},notes:[],reports:older,preferences:{},tapeSymbol:"AAPL"})',older)
 page.evaluate('localStorage.setItem("md-workspace-server-synced",String(Date.now()))')
 page.evaluate('restoreWorkspace()')
 page.wait_for_timeout(180)
 restored=page.evaluate('JSON.parse(localStorage.getItem("md-reborn-reports"))')
 check('Stale server copy does not resurrect deleted report',page.locator('.report-library-item').count()==0 and len(restored)==1 and restored[0].get('deleted') is True)
 # Comparison provenance: same source time reused, with explicit CACHED label.
 page.locator('[data-view="comparison"]').click()
 page.evaluate('''() => { E.fundamentals.set('AAPL',{symbol:'AAPL',retrievedAt:Date.now()-62000,profile:{currency:'USD',name:'Apple Inc'},metrics:{metric:{peTTM:23.17}}}); }''')
 previous=page.evaluate('E.fundamentals.get("AAPL").retrievedAt')
 page.locator('#compare-a').select_option('AAPL');page.locator('#compare-b').select_option('MSFT');page.locator('#compare-c').select_option('')
 page.locator('#compare-run').click()
 page.wait_for_timeout(350)
 foot=page.locator('.compare-foot').inner_text()
 check('Comparison displays original per-company retrieval time',('AAPL' in foot and 'BROWSER CACHE' in foot and 'Per-company source retrieval' in foot))
 check('Cache timestamp not overwritten by comparison click',page.evaluate('E.fundamentals.get("AAPL").retrievedAt')==previous)
 # New macro workspace using a clearly synthetic UI fixture (network not contacted).
 fixture={'status':'ok','cached':False,'fetched_at':1730000000000,'source':'World Bank · TEST-ONLY data',
          'series':{c:{code:[{'year':year,'value':round((1 if c=='GB' else 1.5)+i*.09,4)} for i,year in enumerate(range(2018,2026))] for code in ['NY.GDP.MKTP.KD.ZG','FP.CPI.TOTL.ZG','SL.UEM.TOTL.ZS','NE.EXP.GNFS.ZS','FR.INR.LEND']} for c in ('GB','US')}}
 page.evaluate('''(payload) => {const original=window.fetch;window.fetch=async(url,options)=>String(url).startsWith('/api/macro')?({ok:true,status:200,json:async()=>payload}):original(url,options); }''',fixture)
 page.locator('[data-view="macro"]').click()
 page.wait_for_timeout(280)
 check('Macro view displays five source-labelled metrics',page.locator('.macro-metric').count()==5)
 check('Macro chart displays two country observation series',page.locator('#macro-chart polyline').count()==2)
 check('Macro series displays observation years not fake live times','2025' in page.locator('#macro-cards').inner_text())
 page.locator('#macro-indicator').select_option('FR.INR.LEND')
 check('Lending rate explicitly distinguished from policy rate','NOT the Bank' in page.locator('#macro-context').inner_text())
 page.screenshot(path='/mnt/data/MarketDesk-v1.8.0-Macro-Preview.png',full_page=False)
 # Accuracy test: synthetic weekday price closes, just used to exercise the algorithm.
 page.locator('[data-view="accuracy"]').click()
 page.evaluate('''() => {
  const rows=[];let time=Date.now()-420*86400000,i=0;
  while(time<Date.now()-86400000){const day=new Date(time).getUTCDay();if(day!==0&&day!==6){rows.push({t:time,p:120*Math.exp(i*.0007+.018*Math.sin(i/13))});i++;}time+=86400000}
  E.candles.set('AAPL',{savedAt:Date.now(),status:'ok',provider:'massive',points:rows,cached:true});
 }''')
 page.locator('#accuracy-symbol').select_option('AAPL')
 page.locator('#accuracy-run').click()
 page.wait_for_timeout(280)
 check('Accuracy Centre displays 5- and 20-session audits',page.locator('.accuracy-score').count()==2)
 check('Accuracy audit displays real benchmark comparison terms','UNCHANGED PRICE' in page.locator('#accuracy-results').inner_text())
 check('Accuracy audit explicitly warns historical performance is not guaranteed','not guaranteed' in page.locator('#accuracy-results').inner_text().lower())
 page.screenshot(path='/mnt/data/MarketDesk-v1.8.0-Accuracy-Preview.png',full_page=False)
 page.set_viewport_size({'width':390,'height':844})
 page.locator('#menu-toggle').click();page.locator('[data-view="macro"]').click()
 check('Macro workspace usable on mobile',page.locator('#view-macro').is_visible())
 check('No browser JavaScript exceptions',not errors)
 print('V1.8 BROWSER AUDIT:',len(checks),'checks, exceptions:',errors)
 browser.close()
