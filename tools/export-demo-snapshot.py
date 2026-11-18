#!/usr/bin/env python3
"""Build site/demo/snapshot.json for the public Vercel demo.

Equity closes come from distinct historical session pairs (never a flat % on all names).
Preferred refresh when keys exist: Finnhub free-tier quotes + Massive Basic daily bars.
Always-free public paths: Coinbase Exchange REST (crypto), FRED CSV (macro).
Offline: tools/demo_fixtures/equity_bars.json.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import demo_data_sources as providers  # noqa: E402

CATALOG = ROOT / 'ai_catalog.json'
OUT = ROOT / 'site' / 'demo' / 'snapshot.json'

WATCHLIST = [
    'AAPL', 'NVDA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AMD',
    'PLTR', 'JPM', 'KO', 'DIS', 'NFLX', 'BA', 'TSM', 'TTWO',
]
CRYPTO_PRODUCTS = [
    'BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD', 'DOGE-USD', 'ADA-USD', 'LINK-USD', 'AVAX-USD',
]
# Fallback crypto marks only if Coinbase is unreachable during export.
CRYPTO_USD_FALLBACK = {
    'BTC-USD': 97240.0, 'ETH-USD': 3425.0, 'SOL-USD': 198.5, 'XRP-USD': 1.12,
    'DOGE-USD': 0.38, 'ADA-USD': 0.72, 'LINK-USD': 17.2, 'AVAX-USD': 38.5,
}
QUOTE_TS = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
BASE_TS_SEC = QUOTE_TS // 1000
TAPE_SYMBOLS = ['AAPL', 'NVDA', 'TSLA', 'AMD', 'TTWO', 'MSFT']

# Filled in main() from fixtures / live providers.
EQUITY: dict = {}
CRYPTO_LIVE: dict = {}
FRED_LIVE: dict = {}
PROVENANCE: list[str] = []


def seed(sym: str, salt: str = '') -> int:
    return int(hashlib.md5(f'{sym}{salt}'.encode(), usedforsecurity=False).hexdigest()[:8], 16)


def _quote_row(sym: str) -> dict | None:
    return (EQUITY.get('quotes') or {}).get(sym)


def price(sym: str) -> float:
    row = _quote_row(sym)
    if row and row.get('c'):
        return float(row['c'])
    return round(25 + (seed(sym) % 5000) / 20, 2)


def prev_close(sym: str) -> float:
    """Distinct previous close from the session pair — never close * 0.99 for every name."""
    row = _quote_row(sym)
    if row and row.get('pc'):
        return float(row['pc'])
    sessions = (EQUITY.get('sessions') or {}).get(sym) or []
    if len(sessions) >= 2 and sessions[-2].get('c'):
        return float(sessions[-2]['c'])
    # Last-resort: tiny symbol-specific offset so the book never shows one flat %.
    return round(price(sym) / (1 + ((seed(sym, 'pc') % 900) - 450) / 10000), 4)


def change_for(sym: str) -> float | None:
    row = _quote_row(sym)
    if row:
        pct = providers.session_change_pct(float(row['c']), float(row['pc']))
        if pct is not None:
            return round(pct, 2)
    sessions = (EQUITY.get('sessions') or {}).get(sym) or []
    if len(sessions) >= 2:
        pct = providers.session_change_pct(float(sessions[-1]['c']), float(sessions[-2]['c']))
        if pct is not None:
            return round(pct, 2)
    return None


def spark(sym: str, n: int = 5) -> list[dict]:
    sessions = (EQUITY.get('sessions') or {}).get(sym) or []
    if len(sessions) >= 2:
        use = sessions[-n:]
        return [
            {
                'date': dt.datetime.fromtimestamp(int(pt['t']), dt.timezone.utc).date().isoformat(),
                'price': round(float(pt['c']), 4),
            }
            for pt in use
        ]
    # Insufficient history — two honest points from close/prevClose rather than a synthetic ramp.
    c, pc = price(sym), prev_close(sym)
    day = dt.datetime.fromtimestamp(BASE_TS_SEC, dt.timezone.utc).date()
    return [
        {'date': (day - dt.timedelta(days=1)).isoformat(), 'price': round(pc, 4)},
        {'date': day.isoformat(), 'price': round(c, 4)},
    ]


def daily_bars(sym: str, days: int = 260) -> dict:
    bars = (EQUITY.get('dailyBars') or {}).get(sym)
    if bars and bars.get('c') and len(bars['c']) >= 2:
        return {k: bars[k] for k in ('s', 't', 'c', 'o', 'h', 'l', 'v') if k in bars} | {'s': 'ok'}
    # No invented multi-month sine path: emit the real session pair only.
    row = _quote_row(sym)
    if row:
        t0 = int(row.get('prevT') or (int(row['t']) - 86400))
        t1 = int(row['t'])
        c0, c1 = float(row['pc']), float(row['c'])
        return {
            's': 'ok',
            't': [t0, t1],
            'c': [c0, c1],
            'o': [c0, float(row.get('o') or c1)],
            'h': [max(c0, c1), float(row.get('h') or c1)],
            'l': [min(c0, c1), float(row.get('l') or c1)],
            'v': [0, 0],
        }
    raise ValueError(f'No historical closes available for {sym}')


def metric(sym: str, field: str) -> float | None:
    s = seed(sym, field)
    if field == 'pe':
        return round(8 + (s % 450) / 10, 2)
    if field == 'growth':
        return round((s % 800) / 10 - 20, 2)
    if field == 'margin':
        return round((s % 600) / 10, 2)
    return None


def screener_row(entry: dict, stamp: int) -> dict:
    sym = entry['symbol']
    p = price(sym)
    prev = prev_close(sym)
    ch = change_for(sym)
    row = _quote_row(sym) or {}
    raw_t = int(row.get('t') or BASE_TS_SEC)
    quote_ms = raw_t if raw_t >= 10_000_000_000 else raw_t * 1000
    return {
        'symbol': sym,
        'name': entry['name'],
        'category': entry.get('category', 'Sector not recorded'),
        'exchange': entry.get('exchange', ''),
        'listingCurrency': entry.get('currency', 'USD'),
        'filingCurrency': 'USD',
        'inDirectory': True,
        'price': p,
        'previousClose': prev,
        'change': ch,
        'quoteTime': quote_ms,
        'quoteFetchedAt': stamp,
        'pe': metric(sym, 'pe'),
        'peField': 'peTTM',
        'growth': metric(sym, 'growth'),
        'margin': metric(sym, 'margin'),
        'marketCapMillions': round(p * (seed(sym, 'cap') % 9000 + 1000), 2),
        'marketCapCurrency': 'USD',
        'marketCapFetchedAt': stamp,
        'financialsFetchedAt': stamp,
        'profileFetchedAt': stamp,
        'financialPeriod': 'Not supplied by this snapshot',
        'source': 'Portfolio demo · historical session closes (not live Finnhub on this host)',
        'profileUrl': 'https://finnhub.io/docs/api/company-profile2',
        'metricsUrl': 'https://finnhub.io/docs/api/company-basic-financials',
        'quoteUrl': 'https://finnhub.io/docs/api/quote',
    }


def heatmap_rows(catalog: list[dict], stamp: int) -> list[dict]:
    rows = []
    for entry in catalog:
        sym = entry['symbol']
        points = spark(sym)
        start = points[0]['date'] if points else None
        end = points[-1]['date'] if points else None
        rows.append({
            'symbol': sym,
            'name': entry['name'],
            'category': entry['category'],
            'inDirectory': True,
            'listingCurrency': entry.get('currency', 'USD'),
            'change': change_for(sym),
            'price': points[-1]['price'] if points else price(sym),
            'start': start,
            'end': end,
            'period': '1D',
            'points': points,
            'reason': None if change_for(sym) is not None else 'missing-close',
            'fetchedAt': stamp,
            'quoteTime': stamp,
            'quoteFetchedAt': stamp,
        })
    return rows


def overview60_packet(heatmap_rows: list[dict]) -> dict:
    sectors: dict[str, list[float]] = defaultdict(list)
    companies, excluded, unusual = [], [], []
    for row in heatmap_rows:
        ch = row.get('change')
        if ch is None:
            excluded.append({'symbol': row['symbol'], 'reason': 'missing-close'})
            continue
        companies.append({
            'symbol': row['symbol'],
            'changePct': ch,
            'sector': row.get('category') or 'Sector not recorded',
        })
        sectors[row.get('category') or 'Sector not recorded'].append(ch)
        if abs(ch) >= 3:
            unusual.append({'symbol': row['symbol'], 'changePct': ch})
    sector_rows = [
        {'name': name, 'count': len(vals), 'changePct': round(sum(vals) / len(vals), 4)}
        for name, vals in sectors.items() if len(vals) >= 2
    ]
    ends = [r.get('end') for r in heatmap_rows if r.get('end')]
    starts = [r.get('start') for r in heatmap_rows if r.get('start')]
    equity = {
        'calendar': 'New York sessions',
        'start': min(starts) if starts else None,
        'end': max(ends) if ends else None,
        'evaluated': len(heatmap_rows),
        'included': len(companies),
        'advancing': sum(1 for r in companies if r['changePct'] > 0),
        'declining': sum(1 for r in companies if r['changePct'] < 0),
        'unchanged': sum(1 for r in companies if r['changePct'] == 0),
        'excluded': excluded[:12],
        'companies': companies[:80],
        'sectors': sorted(sector_rows, key=lambda x: -abs(x['changePct']))[:12],
        'unusual': unusual[:15],
        'thresholdPct': 3.0,
        'notice': 'Demo overview from bundled historical directory closes. Not a live session recap.',
    }
    crypto_companies = []
    for product in CRYPTO_PRODUCTS:
        live = CRYPTO_LIVE.get(product) or {}
        end_px = float(live.get('price') or CRYPTO_USD_FALLBACK.get(product) or 0)
        start_px = float(live.get('previous') or end_px)
        ch = providers.session_change_pct(end_px, start_px) if start_px else None
        if ch is None:
            continue
        crypto_companies.append({'symbol': product, 'changePct': round(ch, 2), 'start': start_px, 'end': end_px})
    crypto = {
        'calendar': 'UTC days',
        'start': None,
        'end': None,
        'evaluated': len(CRYPTO_PRODUCTS),
        'included': len(crypto_companies),
        'advancing': sum(1 for r in crypto_companies if r['changePct'] > 0),
        'declining': sum(1 for r in crypto_companies if r['changePct'] < 0),
        'excluded': [],
        'companies': crypto_companies,
        'notice': 'Demo crypto UTC-day changes from Coinbase public candles when reachable, else bundled marks.',
    }
    return {
        'method': 'market-overview-v6.0-demo',
        'equity': equity,
        'crypto': crypto,
        'notice': 'Portfolio demo · equities and crypto counts stay separate.',
    }


def crypto_points(product: str, count: int, step_ms: int) -> list[dict]:
    live = CRYPTO_LIVE.get(product) or {}
    charts = live.get('charts') or {}
    # Prefer real Coinbase points when the export refreshed them.
    for key in ('1D', '1W', '1H'):
        pts = charts.get(key)
        if pts and len(pts) >= 2:
            # Resample / trim to requested count when possible.
            if key == '1D' and step_ms == 300_000:
                return pts[-count:] if len(pts) >= 2 else pts
            if key == '1W' and step_ms == 3_600_000:
                return pts[-count:] if len(pts) >= 2 else pts
            if key == '1H' and step_ms == 60_000:
                return pts[-count:] if len(pts) >= 2 else pts
    base = float(live.get('price') or CRYPTO_USD_FALLBACK.get(product) or 100.0)
    prev = float(live.get('previous') or base)
    end = QUOTE_TS
    # Honest two-anchor path between previous and latest — not a flat book % across products.
    return [
        {
            't': end - (count - i) * step_ms,
            'p': round(prev + (base - prev) * (i / max(1, count - 1)), 6 if base < 10 else 4),
        }
        for i in range(count)
    ]


def crypto_bundle() -> dict:
    followed = ['BTC-USD', 'ETH-USD', 'SOL-USD']
    products = {p: float((CRYPTO_LIVE.get(p) or {}).get('price') or CRYPTO_USD_FALLBACK[p]) for p in CRYPTO_PRODUCTS}
    quotes = {}
    for product, px in products.items():
        live = CRYPTO_LIVE.get(product) or {}
        quotes[product] = {
            'price': px,
            'time': int(live.get('time') or QUOTE_TS),
            'status': 'cached',
            'product': product,
            'previous': live.get('previous'),
            'source': live.get('source') or 'Bundled demo crypto mark',
        }
    charts = {}
    for product in products:
        for rng, (step, count) in {'1H': (60_000, 60), '1D': (300_000, 288), '1W': (3_600_000, 168)}.items():
            pts = crypto_points(product, count, step)
            live_src = (CRYPTO_LIVE.get(product) or {}).get('source')
            charts[f'{product}|{rng}'] = {
                'product': product,
                'points': pts,
                'start': pts[0]['t'],
                'end': pts[-1]['t'],
                'interval': step,
                'expected': count,
                'fetchedAt': QUOTE_TS,
                'status': 'cached',
                'coverage': {
                    'label': live_src or 'Bundled Coinbase-style demo candles',
                    'gaps': 0,
                },
            }
    board_rows = []
    for product, name_px in products.items():
        day = charts.get(f'{product}|1D', {})
        pts = day.get('points') or []
        live = CRYPTO_LIVE.get(product) or {}
        if live.get('previous') and live.get('price'):
            ch24 = providers.session_change_pct(float(live['price']), float(live['previous']))
            ch24 = round(ch24, 2) if ch24 is not None else None
        else:
            ch24 = round((pts[-1]['p'] / pts[0]['p'] - 1) * 100, 2) if len(pts) >= 2 else None
        board_rows.append({
            'product': product,
            'name': product.split('-')[0],
            'id': product,
            'base': product.split('-')[0],
            'quote': 'USD',
            'price': name_px,
            'time': int(live.get('time') or QUOTE_TS),
            'quoteStatus': 'cached',
            'change24h': ch24,
            'change7d': None,
            'coverage': day.get('coverage'),
        })
    used_live = bool(CRYPTO_LIVE)
    return {
        'followed': followed,
        'quotes': quotes,
        'charts': charts,
        'board': {
            'exchange': 'Coinbase Exchange (public demo bundle)',
            'quote': 'USD',
            'timezone': 'UTC',
            'trading': (
                'Coinbase public REST candles bundled at export · not a live socket on this host.'
                if used_live else
                'Bundled crypto marks · refresh export with network for Coinbase public candles.'
            ),
            'unavailable': [],
            'rows': board_rows,
            'followed': followed,
        },
    }


def tape_events(sym: str, n: int = 120) -> list[dict]:
    base = price(sym)
    start = QUOTE_TS - 6 * 3600000
    events = []
    for i in range(n):
        t = start + i * (6 * 3600000 // n)
        p = round(base * (1 + 0.002 * math.sin(i / 5) + (seed(sym, str(i)) % 20 - 10) / 5000), 4)
        events.append({'t': t, 'p': p, 'v': 5 + seed(sym, f'v{i}') % 80, 'receivedAt': t + 12, 'id': i + 1, 's': sym})
    return events


def intelligence_packet(sym: str) -> dict:
    base = price(sym)
    now = QUOTE_TS
    hour_pts = [
        {'t': now - 3600000 + i * 120000, 'p': base * (0.998 + i * 0.00015), 'source': 'demo_fixture'}
        for i in range(12)
    ]
    day_pts = [
        {'t': now - 86400000 + i * 3600000, 'p': base * (0.99 + i * 0.001), 'source': 'demo_fixture'}
        for i in range(8)
    ]
    return {
        'symbol': sym,
        'asOf': now,
        'hour': {
            'hours': 1, 'start': now - 3600000, 'end': now, 'count': len(hour_pts),
            'occupiedMinutes': 12, 'requestedMinutes': 60, 'gaps': [], 'first': hour_pts[0],
            'last': hour_pts[-1], 'sources': ['demo_fixture'], 'stale': False, 'complete': False,
            'points': hour_pts, 'changePct': (hour_pts[-1]['p'] / hour_pts[0]['p'] - 1) * 100,
        },
        'day': {
            'hours': 24, 'start': now - 86400000, 'end': now, 'count': len(day_pts),
            'occupiedMinutes': 8, 'requestedMinutes': 1440, 'gaps': [], 'first': day_pts[0],
            'last': day_pts[-1], 'sources': ['demo_fixture'], 'stale': False, 'complete': False,
            'points': day_pts, 'changePct': (day_pts[-1]['p'] / day_pts[0]['p'] - 1) * 100,
        },
        'model': {
            'status': 'ok', 'count': 90, 'required': 90, 'source': 'Bundled daily closes',
            'method': 'Demo ridge AR(1) summary only.',
            'notice': 'Illustrative model metadata on the public demo.',
            'nextChangePct': 0.42,
            'lastClose': base,
            'lower': base * 0.97,
            'upper': base * 1.03,
            'predictedClose': base * 1.004,
        },
        'financial': {
            'summary': f'{sym} · bundled demo accounts excerpt. Run server.py on your Mac for SEC-linked books.',
            'sources': [{
                'title': f'Demo SEC excerpt · {sym}',
                'url': 'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany',
                'published': '2025-09-30',
            }],
        },
        'retention': 'Demo snapshot only.',
    }


def forecast_packet(sym: str) -> dict:
    base = price(sym)
    anchor = {'day': 0, 'price': base, 'low': base, 'high': base, 'kind': 'recorded', 'evaluated': True}
    common = {
        'symbol': sym,
        'method': 'Demo chronological model',
        'observations': 240,
        'inputs': 'Daily closing prices only (bundled).',
        'trainingNote': 'Not fitted on the public host.',
        'anchorDate': '2025-11-12',
        'first': '2024-11-12',
        'newsUsed': False,
        'demoMode': True,
        'issuedCount': 0,
    }
    if sym == 'TTWO':
        h5 = round(base * 1.06, 2)
        h20 = round(base * 1.11, 2)
        rows = [
            anchor,
            {'day': 5, 'price': h5, 'low': h5 - 2, 'high': h5 + 2, 'kind': 'evaluated', 'evaluated': True, 'returnPct': 6.0},
            {'day': 20, 'price': h20, 'low': h20 - 3, 'high': h20 + 3, 'kind': 'evaluated', 'evaluated': True, 'returnPct': 11.0},
        ]
        return {
            **common,
            'status': 'learned',
            'notice': 'Sample shown path: model beat unchanged price on later tests in this demo bundle.',
            'rows': rows,
            'horizons': [
                {'horizon': 1, 'status': 'baseline', 'testCases': 10},
                {'horizon': 5, 'status': 'learned', 'testCases': 12},
                {'horizon': 20, 'status': 'learned', 'testCases': 12},
            ],
            'interpolation': [
                'Sessions 1 to 4 are a straight join, not a separate forecast.',
                'Sessions 6 to 19 are a straight join, not a separate forecast.',
            ],
            'issuedForecasts': 'left unchanged',
        }
    if sym == 'AMD':
        return {
            **common,
            'status': 'withheld',
            'notice': 'Sample withholding: unchanged price beat the model on later dates — no purple path drawn.',
            'rows': [],
            'horizons': [{'horizon': 5, 'status': 'baseline', 'testCases': 10}],
            'interpolation': [],
        }
    return {
        **common,
        'status': 'insufficient' if sym == 'AAPL' else 'withheld',
        'notice': 'Try TTWO for a shown demo path or AMD for a withheld example.',
        'rows': [],
        'horizons': [],
        'interpolation': [],
    }


def macro_bundle() -> dict:
    series_defs = {
        'UNRATE': {'title': 'US unemployment', 'unit': '% of labour force', 'frequency': 'monthly',
                   'source': 'U.S. Bureau of Labor Statistics via FRED', 'adjustment': 'Seasonally adjusted'},
        'CPIAUCSL': {'title': 'US consumer prices', 'unit': 'Index, 1982–1984 = 100', 'frequency': 'monthly',
                    'source': 'U.S. Bureau of Labor Statistics via FRED', 'adjustment': 'Seasonally adjusted'},
        'FEDFUNDS': {'title': 'US effective federal funds rate', 'unit': '% · monthly average', 'frequency': 'monthly',
                     'source': 'Federal Reserve Board via FRED', 'adjustment': 'Not seasonally adjusted'},
        'GDPC1': {'title': 'US real GDP', 'unit': 'Billions of chained 2017 USD, annual rate', 'frequency': 'quarterly',
                 'source': 'U.S. Bureau of Economic Analysis via FRED', 'adjustment': 'Seasonally adjusted annual rate'},
    }
    fallback_latest = {
        'UNRATE': {'date': '2025-10-01', 'value': 4.1},
        'CPIAUCSL': {'date': '2025-10-01', 'value': 314.2},
        'FEDFUNDS': {'date': '2025-10-01', 'value': 4.58},
        'GDPC1': {'date': '2025-07-01', 'value': 23245.0},
    }
    series = []
    for code, definition in series_defs.items():
        live = FRED_LIVE.get(code) or {}
        latest = live.get('latest') or fallback_latest[code]
        series.append({
            **definition,
            'id': code,
            'url': f'https://fred.stlouisfed.org/series/{code}',
            'fetchedAt': QUOTE_TS,
            'latest': latest,
            'yearAgoChangePct': live.get('yearAgoChangePct'),
            'frequency': definition['frequency'],
            'notice': (
                'FRED public CSV observation bundled at export · not a live macro socket on this host.'
                if live else
                'Bundled observation for the admissions demo. Re-run export with network for FRED CSV.'
            ),
        })
    return {'series': series, 'available': series_defs}


def calendar_bundle() -> dict:
    """Labelled sample company dates for the public Company Calendar (no live IR)."""
    return {
        'notice': 'DEMO DATA · labelled sample company dates from the portfolio demo bundle.',
        'events': [
            {
                'id': 'demo-cal-ttwo-earn',
                'title': 'Take-Two earnings window (demo estimate)',
                'date': '2026-11-06',
                'status': 'estimated',
                'symbol': 'TTWO',
                'source': 'Portfolio demo calendar · labelled synthetic · not a live IR feed',
                'note': 'DEMO DATA sample for admissions. Replace with a sourced date on your Mac.',
                'origin': 'portfolio demo',
                'zone': 'America/New_York',
                'window': 'Date only · demo estimate',
            },
            {
                'id': 'demo-cal-aapl-event',
                'title': 'Apple product event window (demo sample)',
                'date': '2026-09-09',
                'status': 'confirmed',
                'symbol': 'AAPL',
                'source': 'Portfolio demo calendar · labelled synthetic',
                'note': 'Bundled sample only — not scraped from Apple.',
                'origin': 'portfolio demo',
                'zone': 'America/New_York',
                'window': 'Date only · demo sample',
            },
            {
                'id': 'demo-cal-nvda-report',
                'title': 'NVIDIA results window (demo estimate)',
                'date': '2026-11-25',
                'status': 'estimated',
                'symbol': 'NVDA',
                'source': 'Portfolio demo calendar · labelled synthetic',
                'note': 'Future-dated DEMO DATA row so Upcoming is not empty on first open.',
                'origin': 'portfolio demo',
                'zone': 'America/New_York',
                'window': 'Date only · demo estimate',
            },
        ],
    }


def workspace_bundle(catalog: list[dict]) -> dict:
    """Practice portfolio + research samples for admissions (?demo=1). Labelled synthetic only."""
    import portfolio3
    import research32
    import workspace3
    import insights46

    names = {e['symbol']: e['name'] for e in catalog}
    as_of = '2025-11-12'
    mark_source = 'Portfolio demo bundle · historical bundled close · not live Finnhub'

    # V2 paper portfolio (legacy details under Practice Portfolio)
    paper_trades = [
        {
            'symbol': 'AAPL',
            'side': 'BUY',
            'qty': 12,
            'price': 214.5,
            'date': '2025-09-15T15:30:00.000Z',
            'note': 'Demo sample BUY · practice ledger price',
        },
        {
            'symbol': 'TTWO',
            'side': 'BUY',
            'qty': 18,
            'price': 152.0,
            'date': '2025-10-02T14:05:00.000Z',
            'note': 'Demo sample BUY · practice ledger price',
        },
        {
            'symbol': 'NVDA',
            'side': 'BUY',
            'qty': 8,
            'price': 128.4,
            'date': '2025-10-20T16:00:00.000Z',
            'note': 'Demo sample BUY · practice ledger price',
        },
    ]
    paper = {'capital': 10000, 'trades': paper_trades}

    # V3 ledger: deposit + three labelled holdings with dated marks
    ledger = [
        {
            'id': 'demo-dep-1',
            'date': '2025-09-01',
            'kind': 'DEPOSIT',
            'amount': 10000,
            'source': 'Portfolio demo · synthetic starting cash (not a real deposit)',
            'note': 'Admissions sample ledger',
        },
        {
            'id': 'demo-buy-aapl',
            'date': '2025-09-15',
            'kind': 'BUY',
            'symbol': 'AAPL',
            'quantity': 12,
            'price': 214.5,
            'currency': 'USD',
            'fx': 1,
            'fee': 0,
            'fxSource': '',
            'assetType': 'stock',
            'source': mark_source,
            'note': 'Demo sample holding · labelled synthetic',
        },
        {
            'id': 'demo-buy-ttwo',
            'date': '2025-10-02',
            'kind': 'BUY',
            'symbol': 'TTWO',
            'quantity': 18,
            'price': 152.0,
            'currency': 'USD',
            'fx': 1,
            'fee': 0,
            'fxSource': '',
            'assetType': 'stock',
            'source': mark_source,
            'note': 'Demo sample holding · labelled synthetic',
        },
        {
            'id': 'demo-buy-nvda',
            'date': '2025-10-20',
            'kind': 'BUY',
            'symbol': 'NVDA',
            'quantity': 8,
            'price': 128.4,
            'currency': 'USD',
            'fx': 1,
            'fee': 0,
            'fxSource': '',
            'assetType': 'stock',
            'source': mark_source,
            'note': 'Demo sample holding · labelled synthetic',
        },
    ]
    marks = [
        {
            'symbol': 'AAPL',
            'date': as_of,
            'price': price('AAPL'),
            'currency': 'USD',
            'fx': 1,
            'fxSource': '',
            'source': mark_source,
        },
        {
            'symbol': 'TTWO',
            'date': as_of,
            'price': price('TTWO'),
            'currency': 'USD',
            'fx': 1,
            'fxSource': '',
            'source': mark_source,
        },
        {
            'symbol': 'NVDA',
            'date': as_of,
            'price': price('NVDA'),
            'currency': 'USD',
            'fx': 1,
            'fxSource': '',
            'source': mark_source,
        },
    ]

    research_raw = {
        'version': 1,
        'initialised': True,
        'watchlists': [
            {
                'id': 'wl-demo-core',
                'name': 'Demo core watchlist',
                'symbols': WATCHLIST[:6],
                'archived': False,
                'createdAt': '2025-09-01T12:00:00+00:00',
                'updatedAt': '2025-11-10T12:00:00+00:00',
            }
        ],
        'projects': [
            {
                'id': 'proj-demo-ttwo',
                'symbol': 'TTWO',
                'title': 'Take-Two · release cadence',
                'stage': 'Building a view',
                'question': 'How visible is the next franchise window in saved accounts and public filings?',
                'thesis': (
                    'Demo sample thesis only — not investment advice. Practice workflow: link a clear '
                    'question to dated evidence before sizing a paper trade.'
                ),
                'risks': (
                    'Bundled demo figures only. Release timing, marketing spend and platform concentration '
                    'could invalidate this practice view.'
                ),
                'archived': False,
                'createdAt': '2025-10-05T10:00:00+00:00',
                'updatedAt': '2025-11-10T12:00:00+00:00',
                'items': [
                    {
                        'id': 'item-demo-note-1',
                        'kind': 'note',
                        'title': 'What would change my mind',
                        'body': (
                            'Sample research note for the public demo. Look for dated revenue mix, '
                            'booking guidance and a clear source link before treating any figure as evidence.'
                        ),
                        'archived': False,
                        'createdAt': '2025-10-08T15:30:00+00:00',
                        'updatedAt': '2025-10-08T15:30:00+00:00',
                    },
                    {
                        'id': 'item-demo-source-1',
                        'kind': 'source',
                        'title': 'Company investor relations (public HTTPS)',
                        'body': 'Placeholder source row for admissions — link is public; page is not fetched or verified by this demo.',
                        'url': 'https://www.take2games.com/',
                        'sourceDate': '2025-11',
                        'archived': False,
                        'createdAt': '2025-10-12T11:00:00+00:00',
                        'updatedAt': '2025-10-12T11:00:00+00:00',
                    },
                ],
            }
        ],
    }
    research = research32.normalise(research_raw)

    v3_raw = {
        'version': 3,
        'ledger': ledger,
        'marks': marks,
        'checkpoints': [],
        # Calendar samples ship in snapshot.calendar (API), not v3.events,
        # so Company Calendar does not double-render the same DEMO DATA rows.
        'events': [],
        'manualStatements': [],
        'home': {'order': ['watchlist', 'portfolio', 'events', 'economy', 'research'], 'hidden': []},
        'benchmark': 'SPY',
        'researchFocus': 'Demo sample: what evidence would change the Take-Two practice view?',
        'analyst': {'snapshots': []},
        'briefing': {'checkpoints': []},
        'research': research,
    }
    v3 = workspace3.normalise(v3_raw)
    account = portfolio3.calculate(v3['ledger'], v3['marks'], as_of=as_of)
    sectors = {e['symbol']: e.get('category') or 'Sector not recorded' for e in catalog}
    insights = insights46.build(v3['ledger'], v3['marks'], sectors=sectors, as_of=as_of)
    # Keep comparison light on the static host (no SPY series required for display).
    insights['comparison'] = {
        'status': 'unavailable',
        'notice': 'SPY comparison needs matching saved daily prices on your Mac. Demo shows holdings only.',
    }

    notes = [
        {
            'title': 'TTWO — franchise timing (demo sample)',
            'thesis': (
                'Practice note for admissions: a student can write a thesis, risks and sources in one place. '
                'Figures here are labelled synthetic demo content, not a live research call.'
            ),
            'risk': (
                'Release slips, weaker attach rates or higher marketing spend could break the practice case. '
                'This note is bundled demo data only.'
            ),
            'evidence': (
                'Sources: portfolio demo snapshot · public company IR link saved in the research project. '
                'No Finnhub or SEC pull on this host.'
            ),
            'date': '10/11/2025, 12:00:00',
        },
        {
            'title': 'AAPL — services mix (demo sample)',
            'thesis': 'Second sample note so the research archive is not a single empty card on first open.',
            'risk': 'Demo-only risks list — replace with your own contrary evidence on the Mac install.',
            'evidence': 'Bundled snapshot · not live filings.',
            'date': '05/11/2025, 09:30:00',
        },
    ]

    return {
        'watch': WATCHLIST,
        'names': names,
        'notes': notes,
        'reports': [{
            'id': 'demo-report-1',
            'symbol': 'AAPL',
            'title': 'Services mix — demo draft',
            'status': 'Draft',
            'summary': 'Illustrative report shell for admissions screenshots.',
        }],
        # Kept for older readers; live research UI reads V3.research.
        'research': research,
        'portfolio': paper,
        'v3': v3,
        'v3Calc': {
            'asOf': as_of,
            'portfolio': account,
            'insights': insights,
            'performance': {
                'status': 'insufficient',
                'notice': 'Demo sample ledger · capture two checkpoints on your Mac to measure performance.',
            },
            'notice': 'Portfolio demo · labelled practice holdings · not live brokerage data.',
        },
    }


def news_bundle() -> tuple[list[dict], dict]:
    global_news = [
        {
            'headline': 'Portfolio demo: Market Desk overview for sixth-form admissions',
            'source': 'Bundled demo headline',
            'url': 'https://example.com/market-desk-demo',
            'datetime': BASE_TS_SEC,
            'summary': 'Bundled headline for the public demo. Live Finnhub news needs the Mac app.',
        },
        {
            'headline': 'Heatmap directory uses distinct historical session closes',
            'source': 'Demo bundle',
            'url': 'https://example.com/market-desk-heatmap',
            'datetime': BASE_TS_SEC - 7200,
            'summary': 'Directory tile colours come from bundled historical close/prevClose pairs, not a live Massive sync.',
        },
    ]
    by_symbol = {}
    for sym in WATCHLIST:
        by_symbol[sym] = [{
            'headline': f'{sym} · bundled company headline',
            'source': 'Portfolio demo',
            'url': f'https://example.com/news/{sym.lower()}',
            'datetime': BASE_TS_SEC - seed(sym) % 50000,
            'summary': f'Sample headline for {sym} on the public demo host.',
        }]
    return global_news, by_symbol


def learning_bundle() -> dict:
    trained = QUOTE_TS
    common = {
        'method': 'ridge-sessions-v4.1',
        'trainedAt': trained,
        'stale': False,
        'quality': 'Bundled chronological evaluation for the admissions demo.',
        'coverage': {
            'savedCloses': 240,
            'usedCloses': 240,
            'droppedForGap': 0,
            'firstUsed': '2024-11-12',
            'lastUsed': '2025-11-12',
            'latestSavedDate': '2025-11-12',
            'latestSavedPrice': price('AAPL'),
            'source': 'Portfolio demo · historical daily closes',
        },
        'anchorDate': '2025-11-12',
        'latestEligibleDate': '2025-11-12',
    }

    def row(horizon: int, status: str, learned: bool) -> dict:
        return {
            'horizon': horizon,
            'status': status,
            'calibrationCases': 14,
            'testCases': 11,
            'calibrationErrorPP': 1.8 if learned else 2.4,
            'calibrationBaselinePP': 2.1,
            'calibrationPassed': learned,
            'modelErrorPP': 2.2 if learned else 2.9,
            'baselineErrorPP': 2.5,
            'rangeCoveragePct': 78.0,
            'expectedCoveragePct': 80,
            'returnPct': 1.4 * horizon if learned else None,
            'price': round(158.2 * (1.014 ** horizon), 2) if learned else None,
            'low': round(158.2 * (1.012 ** horizon), 2) if learned else None,
            'high': round(158.2 * (1.016 ** horizon), 2) if learned else None,
        }

    def lab_block(horizon: int, withheld: bool = False) -> dict:
        return {
            'horizon': horizon,
            'status': 'withheld' if withheld else 'learned',
            'path': [{'actualPrice': 158.2 + i * 0.6} for i in range(12)],
            'reason': 'No volatility forecast was released on later dates.' if withheld else 'Later test favoured the learned path over an unchanged price.',
            'shrinkage': 0.12 if not withheld else None,
            'calibration': {'count': 12},
            'durability': None if withheld else {'lateErrorPP': 2.1, 'lateBaselineErrorPP': 2.6, 'rangeCoveragePct': 76.0, 'expectedCoveragePct': 80},
            'models': [] if withheld else [{'name': 'Ridge sessions', 'start': '2024-11-12', 'end': '2025-06-01', 'count': 9, 'averageErrorPP': 2.1, 'rangeCoveragePct': 77.0}],
            'misses': [] if withheld else [{'anchorDate': '2025-08-01', 'targetDate': '2025-08-08', 'forecastPrice': 167.0, 'baselinePrice': 165.0, 'actualPrice': 168.5, 'errorPP': 1.1, 'baselineErrorPP': 1.8, 'inRange': True, 'low': 165.5, 'high': 169.0, 'currentPrice': 166.8, 'inputs': [{'date': '2025-07-28', 'price': 164.4}]}],
        }

    ttwo = {
        **common,
        'symbol': 'TTWO',
        'closes': 240,
        'rows': [row(1, 'baseline', False), row(5, 'learned', True), row(20, 'learned', True)],
        'lab': [lab_block(1), lab_block(5), lab_block(20)],
        'scorecard': {
            'message': 'Issued forecasts stay on your Mac · below is a bundled illustration.',
            'notice': 'The public demo does not train models or store issued forecasts.',
            'backtestNotice': 'Backtests above are illustrative only.',
            'summary': {'count': 2, 'averageErrorPP': 2.0, 'baselineAverageErrorPP': 2.4, 'rangeCoveragePct': 75.0, 'rangeCount': 2, 'beatBaseline': True},
            'pending': [{'id': 'demo-issued-ttwo', 'symbol': 'TTWO', 'anchorDay': '2025-10-01', 'horizon': 5, 'targetDay': '2025-10-08', 'anchorPrice': 155.0, 'low': 156.2, 'high': 162.8, 'method': 'Ridge sessions', 'issuedAt': trained - 86400000 * 30, 'outcome': {'status': 'pending'}, 'knownCloses': [{'date': '2025-09-28', 'price': 154.2}]}],
            'graded': [{'id': 'demo-graded-ttwo', 'symbol': 'TTWO', 'anchorDay': '2025-08-01', 'horizon': 5, 'targetDay': '2025-08-08', 'anchorPrice': 163.0, 'low': 164.5, 'high': 170.0, 'method': 'Ridge sessions', 'issuedAt': trained - 86400000 * 90, 'outcome': {'status': 'scored', 'actualPrice': 168.5, 'absoluteErrorPP': 1.2, 'unchangedErrorPP': 1.9, 'inRange': True, 'beatBaseline': True}, 'knownCloses': [{'date': '2025-07-31', 'price': 162.1}]}],
        },
    }
    amd = {
        **common,
        'symbol': 'AMD',
        'closes': 240,
        'rows': [row(1, 'baseline', False), row(5, 'baseline', False), row(20, 'baseline', False)],
        'lab': [lab_block(5, withheld=True), lab_block(20, withheld=True)],
        'quality': 'Sample withholding example · unchanged price beat the model on later tests.',
        'scorecard': {'message': 'No graded issued forecasts in this demo slice.', 'summary': {'count': 0}, 'pending': [], 'graded': []},
    }
    aapl = {
        **common,
        'symbol': 'AAPL',
        'closes': 240,
        'coverage': {**common['coverage'], 'latestSavedPrice': price('AAPL')},
        'rows': [row(1, 'insufficient', False), row(5, 'learned', True), row(20, 'learned', True)],
        'lab': [lab_block(5), lab_block(20)],
        'scorecard': {'message': 'Bundled AAPL lab rows for screenshots.', 'summary': {'count': 1, 'averageErrorPP': 1.9, 'baselineAverageErrorPP': 2.3, 'rangeCoveragePct': 80.0, 'rangeCount': 1, 'beatBaseline': True}, 'pending': [], 'graded': []},
    }
    return {'TTWO': ttwo, 'AMD': amd, 'AAPL': aapl}


def alerts_bundle() -> dict:
    armed_at = QUOTE_TS - 3_600_000
    return {
        'revision': 2,
        'alerts': [
            {
                'id': 'demo-alert-aapl',
                'symbol': 'AAPL',
                'direction': 'above',
                'target': 230.0,
                'unit': 'USD',
                'kind': 'level',
                'status': 'armed',
                'created_at': armed_at - 86_400_000,
                'armed_at': armed_at,
                'arm': 1,
                'last_ts': 0,
                'last_received': None,
                'last_price': None,
                'frequency': 'once',
                'rule_text': 'At or above 230 USD',
                'evaluation_note': 'Bundled demo alert · not evaluated on the static host.',
            },
            {
                'id': 'demo-alert-nvda',
                'symbol': 'NVDA',
                'direction': 'below',
                'target': 130.0,
                'unit': 'USD',
                'kind': 'cross',
                'status': 'paused',
                'created_at': armed_at - 172_800_000,
                'armed_at': armed_at - 86_400_000,
                'arm': 1,
                'last_ts': QUOTE_TS - 7_200_000,
                'last_received': QUOTE_TS - 7_100_000,
                'last_price': price('NVDA'),
                'frequency': 'once',
                'rule_text': 'Crosses below 130 USD',
                'evaluation_note': 'Paused for the demo · live evaluation needs your Mac.',
            },
        ],
        'events': [{
            'id': 1,
            'alert_id': 'demo-alert-ttwo',
            'arm': 1,
            'symbol': 'TTWO',
            'direction': 'above',
            'target': 155.0,
            'unit': 'USD',
            'price': 158.2,
            'price_ts': QUOTE_TS - 86_400_000 * 5,
            'received_at': QUOTE_TS - 86_400_000 * 5 + 120_000,
            'source': 'saved_daily_close',
            'match_type': 'level',
            'rule_text': 'At or above 155 USD',
            'chart_range': '1M',
            'start_date': '2025-10-01',
            'end_date': '2025-11-12',
            'comparison_price': 154.0,
        }],
        'serverTime': QUOTE_TS,
        'maxAlerts': 25,
        'historyLimit': 2000,
        'maxPriceAgeSeconds': 86400,
        'notice': 'Demo alert list · rules are not evaluated on the static host.',
    }


def build_quotes_map(watch_symbols: list[str], catalog_symbols: list[str]) -> dict:
    """Watchlist quotes plus any catalog symbols that have fixture/live rows."""
    wanted = list(dict.fromkeys([*watch_symbols, *catalog_symbols]))
    out = {}
    for sym in wanted:
        row = _quote_row(sym)
        if not row:
            continue
        out[sym] = {'c': float(row['c']), 'pc': float(row['pc'])}
    # Guarantee watchlist coverage
    for sym in watch_symbols:
        if sym not in out:
            out[sym] = {'c': price(sym), 'pc': prev_close(sym)}
    return out


def main() -> None:
    global EQUITY, CRYPTO_LIVE, FRED_LIVE, PROVENANCE, QUOTE_TS, BASE_TS_SEC
    allow_network = os.environ.get('MARKETDESK_DEMO_OFFLINE', '').strip() not in {'1', 'true', 'yes'}
    catalog = json.loads(CATALOG.read_text())
    catalog_symbols = [e['symbol'] for e in catalog]

    EQUITY = providers.equity_from_fixture_or_live(catalog_symbols, WATCHLIST, allow_network=allow_network)
    PROVENANCE = list(EQUITY.get('sources') or [])
    if allow_network:
        CRYPTO_LIVE = providers.fetch_coinbase_products(CRYPTO_PRODUCTS)
        if CRYPTO_LIVE:
            PROVENANCE.append(f'Coinbase Exchange public REST ({len(CRYPTO_LIVE)} products)')
        FRED_LIVE = providers.fetch_fred_latest(['UNRATE', 'CPIAUCSL', 'FEDFUNDS', 'GDPC1'])
        if FRED_LIVE:
            PROVENANCE.append(f'FRED public CSV ({len(FRED_LIVE)} series)')
    else:
        CRYPTO_LIVE = {}
        FRED_LIVE = {}
        PROVENANCE.append('offline export (MARKETDESK_DEMO_OFFLINE)')

    QUOTE_TS = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
    BASE_TS_SEC = QUOTE_TS // 1000
    stamp = QUOTE_TS
    rows = heatmap_rows(catalog, stamp)
    global_news, news_by_symbol = news_bundle()
    ends = sorted({r.get('end') for r in rows if r.get('end')})
    starts = sorted({r.get('start') for r in rows if r.get('start')})
    session_end = ends[-1] if ends else EQUITY.get('asOf')
    session_start = starts[0] if starts else session_end

    quotes = build_quotes_map(WATCHLIST, catalog_symbols)
    # Sanity: refuse to ship a flat book % across the watchlist.
    pcts = []
    for sym, q in quotes.items():
        pct = providers.session_change_pct(q['c'], q['pc'])
        if pct is not None:
            pcts.append(round(pct, 2))
    if len(pcts) >= 4 and len(set(pcts)) == 1:
        raise SystemExit(f'Refused to write snapshot: every quote move is {pcts[0]}% (flat synthetic book).')

    used_finnhub = any('Finnhub' in p for p in PROVENANCE)
    used_massive = any('Massive' in p for p in PROVENANCE)
    if used_finnhub or used_massive:
        # Still a static file on Vercel — honest DEMO DATA, not a browser live feed.
        label = 'PORTFOLIO DEMO · Finnhub/Massive snapshot refresh · DEMO DATA · not live market data'
    else:
        label = 'PORTFOLIO DEMO · historical bundled closes · DEMO DATA · not live market data'

    snapshot = {
        'version': 3,
        'label': label,
        'generated': dt.datetime.now(dt.timezone.utc).date().isoformat(),
        'provenance': PROVENANCE,
        'watchlist': WATCHLIST,
        'quotes': quotes,
        'heatmap': {
            'rows': rows,
            'period': '1D',
            'start': session_start,
            'end': session_end,
            'generation': session_end,
            'latestAvailableSession': session_end,
            'stale': False,
            'completed': 6,
            'required': 6,
            'nextDay': None,
            'configured': True,
            'asOf': stamp,
            'source': ' · '.join(PROVENANCE) or 'Portfolio demo historical closes',
            'notice': (
                'Close-to-close changes use distinct historical session pairs per symbol. '
                'Static host is not a live Finnhub/Massive feed.'
            ),
        },
        'dailyBars': {sym: daily_bars(sym) for sym in WATCHLIST},
        'news': global_news,
        'newsBySymbol': news_by_symbol,
        'screener': {
            'asOf': stamp,
            'directoryCount': len(catalog),
            'rows': [screener_row(e, stamp) for e in catalog],
            'notice': 'Bundled screener rows use the same historical close/prevClose pairs as quotes.',
        },
        'overview60': overview60_packet(rows),
        'crypto': crypto_bundle(),
        'tape': {
            sym: {
                'events': tape_events(sym),
                'recordingDays': [{'date': session_end or 'bundled', 'count': 120}],
            }
            for sym in TAPE_SYMBOLS
        },
        'intelligence': {sym: intelligence_packet(sym) for sym in WATCHLIST},
        'forecasts': {sym: forecast_packet(sym) for sym in ['TTWO', 'AMD', 'AAPL', 'NVDA', 'TSLA']},
        'macro': macro_bundle(),
        'alerts': alerts_bundle(),
        'learning': learning_bundle(),
        'workspace': workspace_bundle(catalog),
        'calendar': calendar_bundle(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, separators=(',', ':')))
    sample = {sym: quotes[sym] for sym in ('AAPL', 'NVDA') if sym in quotes}
    print(
        f'Wrote {OUT} ({len(rows)} heatmap rows, {len(snapshot["screener"]["rows"])} screener rows, '
        f'{OUT.stat().st_size} bytes)'
    )
    print('Provenance:', '; '.join(PROVENANCE))
    for sym, q in sample.items():
        pct = providers.session_change_pct(q['c'], q['pc'])
        print(f"  {sym}: c={q['c']} pc={q['pc']} pct={pct}")


if __name__ == '__main__':
    main()