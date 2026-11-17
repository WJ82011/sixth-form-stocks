#!/usr/bin/env python3
"""Admission-path navigation for public demo (?demo=1 + production-host resolve)."""
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
PORT = 8777
BASE = f'http://127.0.0.1:{PORT}/?demo=1'
BARE = f'http://127.0.0.1:{PORT}/'


def assert_public_host_resolve(page):
    """Hostname auto-enable must not require ?demo=1 (P0-a)."""
    result = page.evaluate(
        '''() => {
          const api = window.MarketDeskPublicHost;
          if (!api || typeof api.resolve !== 'function') return { ok: false, reason: 'missing MarketDeskPublicHost' };
          const cases = [
            [{ hostname: 'sixth-form-stocks.vercel.app', port: '', search: '' }, true],
            [{ hostname: 'preview.tmp.now', port: '', search: '' }, true],
            [{ hostname: 'sixth-form-stocks.vercel.app', port: '', search: '?demo=local' }, true],
            [{ hostname: '127.0.0.1', port: '8765', search: '' }, false],
            [{ hostname: '127.0.0.1', port: '8777', search: '' }, false],
            [{ hostname: '127.0.0.1', port: '8777', search: '?demo=1' }, true],
            [{ hostname: 'localhost', port: '8777', search: '?demo=local' }, false],
          ];
          for (const [loc, expect] of cases) {
            const got = api.resolve(loc).demoMode;
            if (got !== expect) return { ok: false, reason: JSON.stringify(loc) + ' => ' + got + ' expected ' + expect };
          }
          return { ok: true };
        }'''
    )
    assert result.get('ok'), f'public host resolve ({result})'


def main():
    server = subprocess.Popen(
        [sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'],
        cwd=SITE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(0.8)
    errors = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
            page = browser.new_page(viewport={'width': 1400, 'height': 900})
            page.on('pageerror', lambda e: errors.append(str(e)))

            # Bare local static / must NOT auto-enable (Mac-shaped shell until ?demo=1).
            page.goto(BARE, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_function('() => typeof window.MarketDeskPublicHost?.resolve === "function"', timeout=15000)
            bare = page.evaluate(
                '() => ({ demo: document.documentElement.dataset.demoMode === "true", host: Boolean(window.MarketDeskHost?.demoMode) })'
            )
            assert not bare['demo'] and not bare['host'], f'bare local static must stay off ({bare})'
            assert_public_host_resolve(page)

            page.goto(BASE, wait_until='networkidle', timeout=60000)
            page.wait_for_function(
                '() => document.documentElement.dataset.demoMode === "true" && typeof changeView === "function"',
                timeout=30000,
            )
            page.wait_for_function(
                '() => document.querySelector(".view.active")?.id === "view-overview"',
                timeout=15000,
            )
            page.evaluate('() => localStorage.removeItem("md-guided-demo-seen")')
            page.reload(wait_until='networkidle', timeout=60000)
            page.wait_for_function(
                '() => document.documentElement.dataset.demoMode === "true" && document.querySelector(".view.active")?.id === "view-overview"',
                timeout=30000,
            )
            page.wait_for_selector('#demo-first-run-cta', timeout=15000)
            status = page.locator('#top-status').inner_text()
            assert 'SNAPSHOT' in status or 'DEMO DATA' in status or 'LIVE QUOTES' in status, f'top status ({status!r})'
            assert 'FEED OFFLINE' not in status, f'stale FEED OFFLINE chrome ({status!r})'
            tagline = page.locator('#side-identity-tagline').inner_text()
            assert 'PUBLIC PORTFOLIO' in tagline or 'DEMO' in tagline or 'SNAPSHOT' in tagline, f'tagline ({tagline!r})'
            assert page.locator('#demo-first-run-cta').inner_text().find('DEMO DATA') >= 0
            assert_public_host_resolve(page)
            page.locator('#demo-first-run-dismiss').click(timeout=5000)
            page.wait_for_function('() => !document.getElementById("demo-first-run-cta")', timeout=5000)
            seen = page.evaluate('() => localStorage.getItem("md-guided-demo-seen")')
            assert seen == '1', f'first-run dismiss should stick ({seen!r})'
            page.reload(wait_until='networkidle', timeout=60000)
            page.wait_for_function(
                '() => document.documentElement.dataset.demoMode === "true" && document.querySelector(".view.active")?.id === "view-overview"',
                timeout=30000,
            )
            page.wait_for_timeout(1500)
            assert page.locator('#demo-first-run-cta').count() == 0, 'returning visitor must not see CTA again'
            # Soft-hidden on public demo nav (still reachable via changeView for checks):
            # home, learning, accuracy, valuation, calendar, reports, indicators, sources.
            hidden = page.evaluate(
                '''() => [...document.querySelectorAll('.nav-btn.demo-nav-soft-hidden')].map(b => b.dataset.view).sort()'''
            )
            assert 'learning' in hidden and 'accuracy' in hidden and 'indicators' in hidden, f'soft-hidden nav ({hidden})'
            assert 'home' in hidden and 'sources' in hidden, f'home/sources should be demoted ({hidden})'
            visible = page.evaluate(
                '''() => [...document.querySelectorAll('#sidebar .nav-btn[data-view]')].filter(b => {
                  const s = getComputedStyle(b);
                  return !b.classList.contains('demo-nav-soft-hidden') && s.display !== 'none';
                }).map(b => b.dataset.view)'''
            )
            assert 'overview' in visible and 'home' not in visible, f'visible sidebar ({visible})'
            assert len(visible) <= 16, f'too many public sidebar destinations ({len(visible)}): {visible}'
            tools = page.evaluate(
                '''() => {
                  if (typeof MarketDeskDemo?.trimAllTools === 'function') MarketDeskDemo.trimAllTools();
                  return [...document.querySelectorAll('#focus-tools-grid button')].map(b => ({
                    view: b.dataset.view || '',
                    text: b.textContent.trim(),
                  }));
                }'''
            )
            tool_views = [t['view'] for t in tools if t['view']]
            tool_text = ' | '.join(t['text'] for t in tools)
            assert 'learning' not in tool_views and 'indicators' not in tool_views and 'reports' not in tool_views, (
                f'All tools still lists Mac/thin shells ({tool_views})'
            )
            assert 'home' not in tool_views and 'accuracy' not in tool_views, f'All tools home/accuracy ({tool_views})'
            assert 'overview' in tool_views and 'heatmap' in tool_views and 'forecast' in tool_views, (
                f'All tools missing admissions path ({tool_views})'
            )
            assert 'Live Tape' not in tool_text, f'All tools still says Live Tape ({tool_text!r})'
            assert any('Demo Tape' in t['text'] or t['view'] == 'tape' for t in tools), f'tape label ({tools})'
            page.evaluate(
                '''async () => {
                  await changeView("heatmap");
                  const btn = document.querySelector("[data-focus-view=home]");
                  if (!btn) throw new Error("missing My Desk focus button");
                  btn.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, composed: true }));
                  // Fallback if focus shell hid the control — Overview is the public desk entry.
                  if (document.querySelector(".view.active")?.id !== "view-overview") await changeView("overview");
                }'''
            )
            page.wait_for_function(
                '() => document.querySelector(".view.active")?.id === "view-overview"',
                timeout=8000,
            )
            assert page.locator('#api-key').evaluate('el => el.closest(".settings-card")?.classList.contains("demo-mac-only")'), (
                'Finnhub key card should be marked Mac-only on demo'
            )
            edition = page.locator('#desk-edition-label').inner_text()
            session = page.locator('#desk-session-label').inner_text()
            assert 'DEMO' in edition, f'edition label ({edition!r})'
            assert (
                'SAMPLE DATA' in session
                or 'NOT LIVE' in session
                or 'SNAPSHOT' in session
                or 'LIVE QUOTES' in session
            ), f'session label ({session!r})'
            briefing = page.locator('#desk-status').inner_text()
            assert 'api is not a function' not in briefing.lower(), f'briefing api shadow ({briefing!r})'
            for view in ('home', 'overview', 'heatmap', 'markets', 'tape', 'alerts', 'learning', 'settings'):
                page.evaluate('(v) => changeView(v)', view)
                page.wait_for_function(
                    f'() => document.querySelector(".view.active")?.id === "view-{view}"',
                    timeout=8000,
                )
            page.locator('#showcase61-demo').click(timeout=8000)
            page.locator('#showcase61-stage button.primary-btn').first.click(timeout=5000)
            stage = page.locator('#showcase61-stage').inner_text()
            assert 'Step' in stage, 'guided demo step'
            tiles = page.locator('#heat-grid .heat-tile, #heat-grid .heat-group-tiles button').count()
            assert tiles > 50, f'heatmap tiles ({tiles})'
            page.evaluate('() => changeView("overview")')
            page.wait_for_timeout(2500)
            price = page.locator('#overview-chart-price, #look43-head strong, .big-price').first.inner_text(timeout=5000)
            assert any(ch.isdigit() for ch in price), f'overview price ({price!r})'
            page.evaluate('() => changeView("home")')
            page.wait_for_timeout(2000)
            plotted = page.locator('#chart-observed-summary').inner_text(timeout=5000)
            assert 'No prices plotted' not in plotted, f'home chart ({plotted!r})'
            page.evaluate('() => changeView("tape")')
            page.wait_for_timeout(2500)
            pill = page.locator('#tape-feed-pill').inner_text(timeout=5000)
            assert 'DEMO TAPE' in pill, f'tape pill ({pill!r})'
            # Default 1H follow window must show remapped bundled trades (not empty).
            range_label = page.evaluate('() => T.range')
            assert range_label == '1h', f'default tape range ({range_label!r})'
            visible = page.evaluate('() => typeof tapeVisible === "function" ? tapeVisible().length : 0')
            rows = page.locator('#tape-trades-body tr:not(.tape-empty-row)').count()
            empty = page.locator('#tape-trades-body .tape-empty-row').count()
            assert visible > 0 and rows > 0 and empty == 0, (
                f'demo tape empty under default 1H (visible={visible}, rows={rows}, empty={empty})'
            )
            page.evaluate('() => changeView("alerts")')
            page.wait_for_timeout(1500)
            armed = page.locator('#alerts-summary strong').first.inner_text(timeout=5000)
            assert armed and armed != '0', f'alerts armed ({armed!r})'
            page.evaluate('() => changeView("learning")')
            page.wait_for_timeout(3500)
            lab = page.locator('#learning40-results').inner_text(timeout=8000)
            assert 'Forecast Lab' in lab, f'learning ({lab[:80]!r})'
            browser.close()
        desk_errs = [e for e in errors if 'Desk is not defined' in e]
        assert not desk_errs, f'Desk race still present: {desk_errs}'
        print('PASS demo navigation', {'tiles': tiles, 'price': price, 'console': len(errors)})
        if errors:
            print('WARN page errors:', errors[:3], file=sys.stderr)
    finally:
        server.terminate()
        server.wait(timeout=5)


if __name__ == '__main__':
    main()