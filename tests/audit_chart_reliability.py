#!/usr/bin/env python3
"""Standalone chart reliability regression with offline-shaped Massive data."""
from pathlib import Path
from playwright.sync_api import sync_playwright
from audit_browser import HTML, FAKE_JS, JS_FILES, SITE

ROOT=Path(__file__).resolve().parents[1]

def main():
    fake=FAKE_JS.replace('api_budget:48}', 'api_budget:48,massive_configured:true}')
    fake=fake.replace("source:'Finnhub historical OHLC',candles", "source:'Massive EOD split adjusted',provider:'massive',adjusted:true,candles")
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        page=browser.new_page(viewport={'width':1512,'height':982},device_scale_factor=1)
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(HTML,wait_until='domcontentloaded')
        page.evaluate(fake)
        for js in JS_FILES:page.add_script_tag(content=(SITE/js).read_text())
        page.wait_for_function("E.range==='1Y' && Boolean(E.chartForecast) && E.chartPoints.length>45",timeout=10000)
        state=page.evaluate('''() => ({range:E.range,forecast:E.chartForecast?.rows.length,points:E.chartPoints.length,
          provider:E.candles.get('AAPL')?.provider,labels:document.getElementById('chart-forecast-legend').textContent,
          sources:[...new Set(E.chartPoints.map(x=>x.source))]})''')
        assert state['range']=='1Y' and state['forecast']==61,state
        assert state['sources']==['massive_daily'],state
        assert 'VIOLET' in state['labels'],state
        curvature=page.evaluate('''() => {const r=E.chartForecast.rows;return Math.abs((r[1].price-r[0].price)-(r[60].price-r[59].price));}''')
        assert curvature>0.00001,('Scenario should be a data-driven curve rather than constant linear daily change',curvature)
        page.locator('#main-chart-panel').screenshot(path='/mnt/data/MarketDesk-v1.6.4-Forecast-Preview.png')
        print('PASS default on verified Massive = 1Y, 60-session genuinely curved purple scenario, no mixed intraday prices')
        page.locator('#overview-ranges button[data-range="1D"]').click()
        page.wait_for_function("E.range==='1D'",timeout=5000)
        page.locator('#chart-show-forecast').uncheck()
        page.locator('#chart-show-forecast').check()
        page.wait_for_function("E.range==='1Y' && Boolean(E.chartForecast)",timeout=5000)
        print('PASS turning forecast on while at 1D switches to 1Y and renders scenario')
        # Test Mac-sleep observation gap without calling providers or inventing prices.
        page.evaluate('''() => {
          const now=Date.now();E.range='1D';E.forecastEnabled=true;E.chartForecast=null;
          E.chartDomain={from:now-86400000,to:now,range:'1D'};
          E.chartPoints=[{t:now-9*3600000,p:100},{t:now-8*3600000,p:101},
                         {t:now-1*3600000,p:102},{t:now-1800000,p:101}];drawChart();
        }''')
        assert page.evaluate('ChartResearch.chartSegments(E.chartPoints,"1D").length')==2
        print('PASS 7-hour Mac-sleep gap remains two disjoint observed segments, no invented bridge')
        assert not errors,errors
        print('PASS no browser JavaScript errors')
        browser.close()

if __name__=='__main__':main()
