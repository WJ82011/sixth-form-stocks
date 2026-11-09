#!/usr/bin/env python3
"""Offline full UI regression: real application JS with deterministic Finnhub-shaped fixture.
No external network, fake numbers ONLY inside test context (never shipped to UI)."""
import json,re,sys,time
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site'
STYLE_FILES=['styles.css','tape.css','signal.css','pro.css','terminal.css','research-v17.css','research-v18.css','v19.css']
JS_FILES=['market-hours.js','chart-research.js','tape.js','compare.js','reports.js','macro.js','v19-models.js','v19.js','app.js','signal.js','pro.js','terminal.js']
HTML=re.sub(r'<script[^>]+src="/[^"]+"[^>]*></script>','',(SITE/'index.html').read_text())
HTML=re.sub(r'<link rel="stylesheet" href="/[^"]+">','',HTML)
HTML=HTML.replace('</head>','<style>'+'\n'.join((SITE/f).read_text() for f in STYLE_FILES)+'</style></head>')
FAKE_JS=r'''
(() => {
 const storage = new Map();
 Object.defineProperty(window,'localStorage',{value:{getItem:k=>storage.has(k)?storage.get(k):null,setItem:(k,v)=>storage.set(k,String(v)),removeItem:k=>storage.delete(k)}});
 const start=Date.now(), sec=Math.floor(start/1000);
 const symbols=['AAPL','NVDA','MSFT','GOOGL','AMZN','META','TSLA','AMD','PLTR','JPM','KO','DIS','NFLX','BA','TSM'];
 const prices={AAPL:125.35,NVDA:175.1,MSFT:352.71,GOOGL:204.27,AMZN:176.22,META:627.56,TSLA:244.81,AMD:155.2,PLTR:50.28,JPM:203.12,KO:62.49,DIS:114.25,NFLX:901.02,BA:196.01,TSM:173.19};
 let workspace=null;
 window.__audit={storage,prices,getWorkspace:()=>workspace};
 function fixture(url,options){
  const parsed=new URL(String(url),'http://127.0.0.1:8765');const path=parsed.pathname;let payload={};
  if(path==='/api/status')payload={configured:true,api_used_last_60s:4,api_budget:48};
  else if(path==='/api/session')payload={token:'TEST_ONLY_NOT_REAL_KEY',local_only:true};
  else if(path==='/api/diagnose')payload={ok:true,kind:'quote_received',latency_ms:16,tls_trust:'TEST FIXTURE NO NETWORK',checked_at:Date.now(),quote_time_ms:Date.now(),message:'Mock quote received; not live'};
  else if(path==='/api/workspace'){
    if(options?.method==='POST'){workspace=JSON.parse(options.body).snapshot;payload={ok:true,updated_at:Date.now()}}
    else payload={snapshot:workspace,updated_at:workspace?Date.now()-1500:0};
  }
  else if(path==='/api/selftest')payload={ok:true,checks:[{name:'Saved data folder',ok:true,detail:'Fixture'},{name:'Market data database',ok:true,detail:'Fixture only'},{name:'Website files',ok:true,detail:'All test files present'},{name:'Finnhub key permissions',ok:true,detail:'Mock token only'},{name:'Workspace backup permissions',ok:true,detail:'Mock backup'}],notice:'Offline fixture only. Not Finnhub.'};
  else if(path==='/api/quotes'||path==='/api/quote'){
    const syms=path==='/api/quote'?[parsed.searchParams.get('symbol')]:String(parsed.searchParams.get('symbols')||'').split(',');
    payload={items:syms.map(sym=>{const v=prices[sym]||95.8;return {symbol:sym,quote:{c:v,t:sec,pc:v-1.2,o:v-.7,h:v+2,l:v-2,dp:1.5},source:'Finnhub REST quote',status:'ok'}})};
  }
  else if(path==='/api/history'){
    const sym=parsed.searchParams.get('symbol'),v=prices[sym]||100;
    payload={symbol:sym,points:[{t:start-60000,p:v-.5,source:'finnhub_quote'},{t:start-20000,p:v+.02,source:'finnhub_quote'}]};
  }
  else if(path==='/api/candles'){
    const sym=parsed.searchParams.get('symbol'),v=prices[sym]||100;
    payload={status:'ok',source:'Finnhub historical OHLC',candles:{s:'ok',t:Array.from({length:90},(_,i)=>sec-(90-i)*86400),c:Array.from({length:90},(_,i)=>v*(.96+i*.00045))}};
  }
  else if(path==='/api/tape'){
    const sym=parsed.searchParams.get('symbol'),v=prices[sym]||100;
    payload={symbol:sym,events:[{t:start-3000,p:v-.03,v:10,receivedAt:start-3000,id:1},{t:start-1500,p:v+.01,v:15,receivedAt:start-1500,id:2}]};
  }
  else if(path==='/api/search')payload={result:[{symbol:'TSLA',description:'Tesla Inc.',type:'Common Stock'},{symbol:'TEST',description:'Test Industries PLC',type:'Common Stock'},{symbol:'AAPL',description:'Apple Inc',type:'Common Stock'}]};
  else if(path==='/api/company'){
    const sym=parsed.searchParams.get('symbol');payload={symbol:sym,profile:{name:sym==='AAPL'?'Apple Inc':'Tesla Inc',ticker:sym,exchange:'NASDAQ',currency:'USD',country:'US',marketCapitalization:300000,weburl:'https://example.com',finnhubIndustry:'Technology',ipo:'2000-01-02'},metrics:{metric:{peTTM:21.4,'52WeekHigh':185,'52WeekLow':90}}};
  }
  else if(path==='/api/news')payload={items:[{headline:'Offline fixture headline',source:'Test-only source',url:'https://example.com/article',datetime:sec,summary:'Test-only text'}]};
  else if(path==='/api/token'||path==='/api/ticks')payload={configured:true,accepted:2};
  else payload={};
  return payload;
 }
 window.fetch=async(url,options)=>({ok:true,status:200,json:async()=>fixture(url,options)});
 class WS extends EventTarget {
   static OPEN=1;
   constructor(url){super();this.readyState=0;this.subscribed=[];setTimeout(()=>{this.readyState=1;this.dispatchEvent(new Event('open'))},120)}
   send(str){try{const o=JSON.parse(str);if(o.type==='subscribe'){this.subscribed.push(o.symbol);if(['AAPL','TSLA'].includes(o.symbol))setTimeout(()=>{
     if(this.readyState!==1)return;
     const frame={type:'trade',data:[{s:o.symbol,p:(prices[o.symbol]||100)+.09,v:15,t:Date.now()}]};
     this.dispatchEvent(new MessageEvent('message',{data:JSON.stringify(frame)}));},1000)}
   }catch{}}
   close(){this.readyState=3;this.dispatchEvent(new Event('close'))}
 }
 window.WebSocket=WS;
})();
'''

def assert_true(p,msg):
  if not p:raise AssertionError(msg)

def main():
  error_messages=[];ok=[]
  def passed(text):ok.append(text);print('PASS',text,flush=True)
  with sync_playwright() as playwright:
    b=playwright.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
    page=b.new_page(viewport={'width':1512,'height':982},accept_downloads=True)
    page.on('pageerror',lambda e:error_messages.append(str(e)))
    page.set_content(HTML,wait_until='domcontentloaded')
    page.evaluate(FAKE_JS)
    for js in JS_FILES:page.add_script_tag(content=(SITE/js).read_text())
    page.wait_for_timeout(2800)
    assert_true('125.' in page.locator('#overview-chart-price').inner_text(),'Overview quote failed')
    assert_true(page.locator('#overview-chart').count()==1,'Chart missing')
    passed('Overview quote/chart/ticker')
    page.locator('button[data-view="settings"]').click()
    page.locator('#edition-pro').click()
    page.locator('button[data-view="overview"]').click()
    page.wait_for_timeout(250)
    assert_true(page.locator('#pro-console').is_visible(),'Pro terminal hidden')
    page.locator('[data-pro-select="TSLA"]').first.click()
    assert_true('TSLA' in page.locator('#pro-focus-name').inner_text(),'Pro stock switching failed')
    passed('Professional edition controls and data inspector')
    page.locator('button[data-view="markets"]').click()
    assert_true(page.locator('#markets-table [data-select]').count()>=12,'Watchlist table missing')
    page.locator('#symbol-search').fill('test')
    page.wait_for_timeout(650)
    assert_true(page.locator('#search-results [data-add="TEST"]').count()==1,'Search result failed')
    page.locator('[data-add="TEST"]').click()
    assert_true('TEST' in page.locator('#markets-table').inner_text(),'Adding searched company failed')
    passed('Stock Browser search/add/watchlist')
    page.locator('button[data-view="company"]').click()
    page.locator('#company-select').select_option('AAPL')
    page.wait_for_timeout(400)
    assert_true('Apple Inc' in page.locator('#company-content').inner_text(),'Company data failed')
    passed('Company Overview / metrics')
    page.locator('button[data-view="forecast"]').click()
    page.locator('#forecast-select').select_option('AAPL')
    page.locator('#forecast-calculate').click()
    page.wait_for_timeout(400)
    assert_true('Possible price ranges based on past data' in page.locator('#forecast-content').inner_text(),'Forecast calculation failed')
    passed('Forecast historical scenario and backtest')
    page.locator('button[data-view="news"]').click()
    page.wait_for_timeout(160)
    assert_true(page.locator('#news-content a[href="https://example.com/article"]').count()==1,'Sourced news failed')
    passed('News links and provider citation')
    page.locator('button[data-view="research"]').click()
    page.locator('#note-title').fill('My test research note')
    page.locator('#note-thesis').fill('An independent thesis')
    page.locator('#note-risk').fill('Risks and competing evidence')
    page.locator('#note-evidence').fill('Verified reference here')
    page.locator('#save-note').click()
    assert_true('My test research note' in page.locator('#saved-notes').inner_text(),'Note save failed')
    with page.expect_download() as download:page.locator('#export-notes').click()
    assert_true(download.value.suggested_filename.endswith('.txt'),'Research export failed')
    passed('Research note write/export')
    page.locator('button[data-view="tape"]').click()
    page.wait_for_timeout(300)
    assert_true(page.locator('#tape-canvas').count()==1,'Tape chart missing')
    page.locator('#tape-quick-search').fill('Tes')
    page.wait_for_timeout(650)
    assert_true(page.locator('#tape-quick-results [data-tape-suggest="TSLA"]').count()==1,'Tape autocomplete missing')
    page.locator('#tape-quick-results [data-tape-suggest="TSLA"]').click()
    assert_true(page.evaluate('T.symbol')=='TSLA','Tape stock switching failed')
    page.wait_for_timeout(1000)
    page.locator('#tape-pause').click()
    page.locator('#tape-pause').click()
    page.locator('#tape-zoom-in').click()
    passed('Live Tape autocomplete, controls and trade stream fixture')
    page.locator('button[data-view="settings"]').click()
    page.locator('#local-audit-run').click()
    page.wait_for_timeout(250)
    assert_true('Market data database' in page.locator('#local-audit-output').inner_text(),'Local health audit failed')
    page.wait_for_timeout(600)
    assert_true('backed up' in page.locator('#workspace-backup-status').inner_text().lower(),'Workspace backup failed')
    passed('Settings local audit, saved workspace backup')
    with page.expect_download() as dl:page.locator('#export-workspace').click()
    exported=json.loads(Path(dl.value.path()).read_text())
    assert_true('token' not in json.dumps(exported).lower(),'Research export contains token')
    assert_true(exported['format']=='MarketDesk-Research-Backup','Full backup exported wrong format')
    assert_true(any(n['title']=='My test research note' for n in exported['snapshot']['notes']),'Export missing research notes')
    page.evaluate('E.notes=[];saveJSON("md-reborn-notes",[]);renderNotes()')
    assert_true('My test research note' not in page.locator('#saved-notes').inner_text(),'Could not clear fixture notes')
    page.locator('#import-workspace').set_input_files({'name':'research-backup.json','mimeType':'application/json','buffer':json.dumps(exported).encode()})
    page.wait_for_timeout(450)
    assert_true('My test research note' in page.locator('#saved-notes').inner_text(),'Full workspace restore failed')
    passed('Full research backup export/import; excludes Finnhub token')
    # Distinguish old snapshots from recent verified streaming prices.
    page.evaluate('''() => {E.wsOpen=false; E.trades.clear(); const q=E.quotes.get('AAPL');q.quote.t=Math.floor((Date.now()-7200000)/1000);window.MarketDeskBrowser.refresh()}''')
    assert_true(page.evaluate('quoteFor("AAPL").type')=='stale','Old quote falsely labelled current')
    page.locator('button[data-view="markets"]').click()
    assert_true('STALE QUOTE' in page.locator('#markets-table').inner_text(),'Market table does not warn on stale quote')
    passed('Stale quote provenance and market table warning')
    page.locator('button[data-view="settings"]').click()
    page.screenshot(path=str(ROOT.parent/'MarketDesk-v1.5.0-Pro-Offline-Test.png'),full_page=True)
    # Mobile use same document/scripts with new fixture and no external assets.
    m=b.new_page(viewport={'width':390,'height':844})
    m.on('pageerror',lambda e:error_messages.append('mobile: '+str(e)))
    m.set_content(HTML,wait_until='domcontentloaded');m.evaluate(FAKE_JS)
    for js in JS_FILES:m.add_script_tag(content=(SITE/js).read_text())
    m.wait_for_timeout(500)
    assert_true(m.locator('#menu-toggle').is_visible(),'Mobile menu not visible')
    m.locator('#menu-toggle').click()
    assert_true(m.locator('#sidebar').evaluate('(x)=>x.classList.contains("open")'),'Mobile menu did not open')
    m.screenshot(path=str(ROOT.parent/'MarketDesk-v1.5.0-Mobile-Offline-Test.png'),full_page=True)
    passed('Small-screen navigation and responsive layout')
    print('SUMMARY:',len(ok),'workflow groups, JavaScript errors:',len(error_messages),flush=True)
    for e in error_messages:print('ERROR:',e,flush=True)
    assert_true(not error_messages,'Browser JavaScript failures: '+str(error_messages))
    b.close()
if __name__=='__main__':main()
