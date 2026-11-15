#!/usr/bin/env python3
"""Build site/demo/snapshot.json for the public Vercel demo. No API keys or network."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'ai_catalog.json'
OUT = ROOT / 'site' / 'demo' / 'snapshot.json'

BASE_PRICES = {
    'AAPL': 228.4, 'NVDA': 139.2, 'MSFT': 416.8, 'GOOGL': 176.5, 'AMZN': 198.3,
    'META': 572.1, 'TSLA': 338.7, 'AMD': 122.6, 'PLTR': 51.9, 'JPM': 243.2,
    'KO': 63.4, 'DIS': 112.8, 'NFLX': 892.0, 'BA': 178.4, 'TSM': 172.3, 'TTWO': 158.2,
}
WATCHLIST = [
    'AAPL', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AMD', 'PLTR', 'JPM',
    'KO', 'DIS', 'NFLX', 'BA', 'TSM', 'TTWO',
]


def price(sym: str) -> float:
    if sym in BASE_PRICES:
        return BASE_PRICES[sym]
    seed = int(hashlib.md5(sym.encode(), usedforsecurity=False).hexdigest()[:8], 16)
    return round(25 + (seed % 5000) / 20, 2)


def change_for(sym: str) -> float:
    seed = int(hashlib.md5(f'{sym}1D'.encode(), usedforsecurity=False).hexdigest()[:8], 16)
    return round((seed % 2000) / 100 - 10, 2)


def spark(sym: str, n: int = 5) -> list[dict]:
    base = price(sym)
    return [
        {
            'date': f'2025-11-{(8 + i):02d}',
            'price': round(base * (0.97 + 0.01 * i + 0.003 * math.sin(i + ord(sym[0]))), 4),
        }
        for i in range(n)
    ]


def daily_bars(sym: str, days: int = 260) -> dict:
    base = price(sym)
    base_ts = 1_730_000_000
    t = [base_ts + i * 86400 for i in range(days)]
    c = [round(base * (0.88 + (i / days) * 0.2 + 0.02 * math.sin(i / 11)), 4) for i in range(days)]
    return {'s': 'ok', 't': t, 'c': c, 'h': [x * 1.01 for x in c], 'l': [x * 0.99 for x in c], 'o': c}


def main() -> None:
    catalog = json.loads(CATALOG.read_text())
    start, end = '2025-11-07', '2025-11-12'
    stamp = 1_763_164_800_000
    rows = []
    for entry in catalog:
        sym = entry['symbol']
        points = spark(sym)
        rows.append({
            'symbol': sym,
            'name': entry['name'],
            'category': entry['category'],
            'inDirectory': True,
            'listingCurrency': entry.get('currency', 'USD'),
            'change': change_for(sym),
            'price': points[-1]['price'],
            'start': start,
            'end': end,
            'period': '1D',
            'points': points,
            'reason': None,
            'fetchedAt': stamp,
            'quoteTime': stamp,
            'quoteFetchedAt': stamp,
        })
    snapshot = {
        'version': 1,
        'label': 'PORTFOLIO DEMO · labelled synthetic snapshot · not live market data',
        'generated': '2026-11-15',
        'watchlist': WATCHLIST,
        'quotes': {sym: {'c': price(sym), 'pc': round(price(sym) * 0.99, 2)} for sym in BASE_PRICES},
        'heatmap': {
            'rows': rows,
            'period': '1D',
            'start': start,
            'end': end,
            'generation': '2025-11-12',
            'latestAvailableSession': '2025-11-12',
            'stale': False,
            'completed': 6,
            'required': 6,
            'nextDay': None,
            'configured': True,
            'asOf': stamp,
            'source': 'Portfolio demo bundle · not Massive',
            'notice': 'Split-adjusted close-to-close demo changes for admissions screenshots only.',
        },
        'dailyBars': {sym: daily_bars(sym) for sym in ['AAPL', 'TTWO', 'AMD', 'NVDA', 'MSFT']},
        'news': [{
            'headline': 'Portfolio demo: Market Desk overview for sixth-form admissions',
            'source': 'Bundled demo headline',
            'url': 'https://example.com/market-desk-demo',
            'datetime': 1_763_100_000,
            'summary': 'Bundled headline for the public demo. Live Finnhub news needs the Mac app.',
        }],
        'workspace': {
            'watch': WATCHLIST,
            'names': {e['symbol']: e['name'] for e in catalog if e['symbol'] in WATCHLIST},
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, separators=(',', ':')))
    print(f'Wrote {OUT} ({len(rows)} heatmap rows, {OUT.stat().st_size} bytes)')


if __name__ == '__main__':
    main()