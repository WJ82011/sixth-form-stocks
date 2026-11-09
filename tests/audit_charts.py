#!/usr/bin/env python3
"""Full chart controls and future scenario tests in a real headless Chromium page.
All quotes/news are offline fixtures, never shipped as real market data."""
import sys,time
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).parent))
from audit_browser import HTML,FAKE_JS,SITE,JS_FILES

def main():
  with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':1512,'height':982})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(HTML,wait_until='domcontentloaded');page.evaluate(FAKE_JS)
    page.evaluate('''() => {const old=window.fetch;window.__chartApiCalls=[];
      window.fetch=async (url,options)=>{window.__chartApiCalls.push(String(url));return old(url,options)};}''')
    for js in JS_FILES:page.add_script_tag(content=(SITE/js).read_text())
    page.wait_for_timeout(2200)
    outcomes={}
    for label in ['1D','1W','1M','3M','1Y']:
      page.locator(f'#overview-ranges button[data-range="{label}"]').click()
      page.wait_for_function('''(r) => E.range===r && E.chartDomain?.range===r && !document.getElementById('chart-data-coverage').textContent.includes('Loading')''',arg=label,timeout=9000)
      page.wait_for_timeout(300)
      data=page.evaluate('''() => ({range:E.range,pointCount:E.chartPoints.length,first:E.chartPoints[0]?.t,
         last:E.chartPoints.at(-1)?.t,span:E.chartDomain.to-E.chartDomain.from,
         model:Boolean(E.chartForecast),legend:document.getElementById('chart-forecast-legend').textContent,
         status:document.getElementById('chart-data-coverage').textContent})''')
      assert data['range']==label,data
      expected={'1D':1,'1W':7,'1M':30,'3M':90,'1Y':365}[label]
      assert abs(data['span']/86400000-expected)<.01,data
      outcomes[label]=data
      print('RANGE',label,'points',data['pointCount'],'days',round(data['span']/86400000),'scenario',data['model'])
    assert outcomes['1W']['pointCount']<outcomes['1M']['pointCount']<outcomes['3M']['pointCount']<=outcomes['1Y']['pointCount'],outcomes
    assert not outcomes['1D']['model']
    assert all(outcomes[s]['model'] for s in ['1W','1M','3M','1Y'])
    assert page.evaluate("document.querySelector('#chart-forecast-legend').classList.contains('active')")
    requests=page.evaluate("window.__chartApiCalls.filter(x => x.includes('/api/candles?symbol=AAPL')).length")
    assert requests==1,f'Expected one shared historical request for AAPL, got {requests}'
    print('PASS all five ranges are different; one shared Finnhub historical request; forecast gating')
    page.screenshot(path='/mnt/data/MarketDesk-v1.6.0-Chart-Preview.png',full_page=False)
    # Disabling overlays cannot alter historical prices.
    before=page.evaluate('JSON.stringify(E.chartPoints)')
    page.locator('#chart-show-forecast').uncheck();page.wait_for_timeout(380)
    assert page.evaluate('E.chartForecast') is None
    assert page.evaluate('JSON.stringify(E.chartPoints)')==before
    page.locator('#chart-show-forecast').check();page.wait_for_timeout(450)
    assert page.evaluate('Boolean(E.chartForecast)')
    print('PASS forecast on/off changes scenario only, not observed points')
    # Finite scenario model data, real source bounded future interval.
    model=page.evaluate('''() => E.chartForecast && ({n:E.chartForecast.sampleSize,
      horizon:E.chartForecast.rows.at(-1).day,spot:E.chartForecast.anchor.p,
      width:E.chartForecast.rows.at(-1).high-E.chartForecast.rows.at(-1).low})''')
    assert model and model['n']>=45 and model['horizon']==60 and model['width']>0,model
    # Simulate a genuine entitlement denial and ensure no projected line exists.
    page.evaluate('''() => {E.candles.clear();const old=window.fetch;window.fetch=async(url,options)=>{
      if(String(url).includes('/api/candles'))return {ok:true,status:200,json:async()=>({status:'entitlement',candles:null,message:'Subscription required'})};
      return old(url,options)};}''')
    page.locator('#overview-ranges button[data-range="1M"]').click();page.wait_for_timeout(520)
    restricted=page.evaluate('''() => ({forecast:E.chartForecast,
      legend:document.getElementById('chart-forecast-legend').textContent,
      note:document.getElementById('overview-chart-note').textContent,
      points:E.chartPoints.length,span:E.chartDomain.to-E.chartDomain.from})''')
    assert restricted['forecast'] is None,restricted
    assert 'unavailable' in restricted['legend'].lower(),restricted
    assert 'SOME HISTORY IS MISSING' in restricted['note'],restricted
    assert restricted['points']>=1 and abs(restricted['span']/86400000-30)<.01,restricted
    print('PASS restricted historical entitlement: real observations only, transparent incomplete coverage')
    # Switching symbols must never retain a previous stock's forecast.
    page.evaluate("setSelected('TSLA')")
    page.wait_for_timeout(400)
    assert page.evaluate("E.selected")=='TSLA'
    assert page.evaluate("E.chartForecast") is None
    print('PASS stock switching does not retain prior prediction line')
    # The separate Live Tape graph has minute-to-day windows based only on
    # provider-confirmed trade fixtures; it must not fabricate price points.
    page.locator('button[data-view="tape"]').click()
    page.wait_for_timeout(380)
    page.evaluate('''() => {
      const now=Date.now(); T.symbol='AAPL'; T.pause=false; T.follow=true; T.loading=false;
      T.events=[20,120,600,1800,28800].map((seconds,i)=>({t:now-seconds*1000,p:100+i,v:10+i,receivedAt:now-seconds*1000,id:i+1}));
      tapeRender();
    }''')
    counts=[]
    for label in ['1m','5m','15m','1h','1d']:
      page.locator(f'[data-tape-range="{label}"]').click()
      counts.append(page.evaluate('tapeVisible().length'))
    assert counts==[1,2,3,4,5],counts
    print('PASS Live Tape 1m/5m/15m/1h/24h windows filter verified trade fixtures correctly:',counts)
    page.locator('#tape-zoom-in').click()
    assert page.evaluate('T.range')=='1h'
    page.locator('#tape-zoom-out').click()
    assert page.evaluate('T.range')=='1d'
    print('PASS Live Tape zoom controls keep data and window states consistent')
    assert not errors,errors
    print('PASS browser JavaScript errors: 0')
    browser.close()

if __name__=='__main__':main()
