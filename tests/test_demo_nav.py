#!/usr/bin/env python3
"""Admission-path navigation for public demo (?demo=1)."""
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
PORT = 8777
BASE = f'http://127.0.0.1:{PORT}/?demo=1'


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
            assert 'DEMO DATA' in status, f'top status ({status!r})'
            assert page.locator('#demo-first-run-cta').inner_text().find('DEMO DATA') >= 0
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
            # learning, accuracy, valuation, calendar, reports.
            hidden = page.evaluate(
                '''() => [...document.querySelectorAll('.nav-btn.demo-nav-soft-hidden')].map(b => b.dataset.view).sort()'''
            )
            assert 'learning' in hidden and 'accuracy' in hidden and 'indicators' in hidden, f'soft-hidden nav ({hidden})'
            assert page.locator('#api-key').evaluate('el => el.closest(".settings-card")?.classList.contains("demo-mac-only")'), (
                'Finnhub key card should be marked Mac-only on demo'
            )
            edition = page.locator('#desk-edition-label').inner_text()
            session = page.locator('#desk-session-label').inner_text()
            assert 'DEMO' in edition, f'edition label ({edition!r})'
            assert 'SAMPLE DATA' in session or 'NOT LIVE' in session, f'session label ({session!r})'
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
            page.wait_for_timeout(2000)
            pill = page.locator('#tape-feed-pill').inner_text(timeout=5000)
            assert 'DEMO TAPE' in pill, f'tape pill ({pill!r})'
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