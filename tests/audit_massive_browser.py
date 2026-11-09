#!/usr/bin/env python3
"""End-to-end offline v1.6.2 interface test; provider responses are labelled fixtures."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from audit_browser import HTML, FAKE_JS, JS_FILES, SITE
ROOT=Path(__file__).parents[1]

def main():
    fake=FAKE_JS.replace('api_budget:48}', 'api_budget:48,massive_configured:true}')
    fake=fake.replace("source:'Finnhub historical OHLC',candles", "source:'Massive · split-adjusted US daily closes (EOD)',provider:'massive',adjusted:true,candles")
    # Mock provider-specific key POST and real test separately. No credentials leave browser.
    fake=fake.replace("else if(path==='/api/token'||path==='/api/ticks')", "else if(path==='/api/massive-diagnose')payload={ok:true,kind:'daily_bars_received',count:12,latency_ms:17,latest_bar_time_ms:start-86400000,message:'Offline Massive EOD test fixture'};\n  else if(path==='/api/massive-token')payload={configured:true,provider:'Massive'};\n  else if(path==='/api/token'||path==='/api/ticks')")
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
        page=b.new_page(viewport={'width':1440,'height':960})
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.set_content(HTML,wait_until='domcontentloaded')
        page.evaluate(fake)
        for js in JS_FILES: page.add_script_tag(content=(SITE/js).read_text())
        page.wait_for_timeout(1300)
        assert page.evaluate('E.massiveConfigured') is True,'Massive configuration did not load'
        for label in ['1W','1M','3M','1Y']:
            page.locator(f'#overview-ranges button[data-range="{label}"]').click()
            page.wait_for_timeout(120)
            assert page.evaluate('E.candles.get("AAPL")?.provider')=='massive'
            assert 'MASSIVE' in page.evaluate('E.chartSource')
            assert page.evaluate('E.chartDomain.range')==label
            assert page.evaluate('Boolean(E.chartForecast)'),label
            print('PASS historical',label,'provider Massive, forecast available')
        page.locator('button[data-view="settings"]').click()
        assert page.locator('#massive-key-state').inner_text()=='SAVED PRIVATELY'
        page.locator('#massive-api-key').fill('LOCAL_TEST_KEY_NOT_REAL')
        page.locator('#massive-save-key').click()
        page.wait_for_timeout(100)
        assert page.locator('#massive-api-key').input_value()==''
        page.locator('#massive-test').click()
        page.wait_for_timeout(120)
        assert '✓ ' in page.locator('#massive-test-result').inner_text()
        assert 'Massive' in page.locator('#massive-test-result').inner_text()
        page.screenshot(path=str(ROOT.parent/'MarketDesk-v1.6.2-Dual-Source-Preview.png'),full_page=True)
        page.locator('#massive-clear-key').click()
        page.wait_for_timeout(160)
        assert page.evaluate('E.massiveConfigured') is False
        assert 'NOT CONFIGURED' in page.locator('#massive-key-state').inner_text()
        assert not errors,errors
        b.close()
        print('PASS Settings save/test/remove key; no browser errors; no actual network requests')

if __name__=='__main__':main()
