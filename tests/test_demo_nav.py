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
            for view in ('home', 'overview', 'heatmap', 'markets', 'settings'):
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
            browser.close()
        print('PASS demo navigation', {'tiles': tiles, 'price': price, 'console': len(errors)})
        if errors:
            print('WARN page errors:', errors[:3], file=sys.stderr)
    finally:
        server.terminate()
        server.wait(timeout=5)


if __name__ == '__main__':
    main()