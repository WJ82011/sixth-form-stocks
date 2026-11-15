#!/usr/bin/env python3
"""Build site/demo/snapshot.json for the public Vercel demo. No API keys or network."""
from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'ai_catalog.json'
OUT = ROOT / 'site' / 'demo' / 'snapshot.json'

BASE_PRICES = {
    'AAPL': 228.4, 'NVDA': 139.2, 'MSFT': 416.8, 'GOOGL': 176.5, 'AMZN': 198.3,
    'META': 572.1, 'TSLA': 338.7, 'AMD': 122.6, 'PLTR': 51.9, 'JPM': 243.2,
    'KO': 63.4, 'DIS': 112.8, 'NFLX': 892.0, 'BA': 178.4, 'TSM': 172.3, 'TTWO': 158.2,
}
CRYPTO_USD = {
    'BTC-USD': 97240.0, 'ETH-USD': 3425.0, 'SOL-USD': 198.5, 'XRP-USD': 1.12,
    'DOGE-USD': 0.38, 'ADA-USD': 0.72, 'LINK-USD': 17.2, 'AVAX-USD': 38.5,
}
WATCHLIST = list(BASE_PRICES)
QUOTE_TS = 1_763_164_800_000
BASE_TS_SEC = 1_763_100_000
TAPE_SYMBOLS = ['AAPL', 'NVDA', 'TSLA', 'AMD', 'TTWO', 'MSFT']


def seed(sym: str, salt: str = '') -> int:
    return int(hashlib.md5(f'{sym}{salt}'.encode(), usedforsecurity=False).hexdigest()[:8], 16)


def price(sym: str) -> float:
    if sym in BASE_PRICES:
        return BASE_PRICES[sym]
    return round(25 + (seed(sym) % 5000) / 20, 2)


def change_for(sym: str) -> float:
    return round((seed(sym, '1D') % 2000) / 100 - 10, 2)


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
    prev = round(p * (1 - change_for(sym) / 100), 4)
    quote_sec = BASE_TS_SEC
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
        'change': change_for(sym),
        'quoteTime': quote_sec * 1000,
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
        'source': 'Portfolio demo bundle',
        'profileUrl': 'https://finnhub.io/docs/api/company-profile2',
        'metricsUrl': 'https://finnhub.io/docs/api/company-basic-financials',
        'quoteUrl': 'https://finnhub.io/docs/api/quote',
    }


def heatmap_rows(catalog: list[dict], stamp: int) -> list[dict]:
    start, end = '2025-11-07', '2025-11-12'
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
    equity = {
        'calendar': 'New York sessions',
        'start': '2025-11-11',
        'end': '2025-11-12',
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
        'notice': 'Demo overview from bundled directory closes. Not a live session recap.',
    }
    crypto_companies = []
    for product, px in list(CRYPTO_USD.items())[:8]:
        ch = round((seed(product, '1D') % 400) / 10 - 15, 2)
        crypto_companies.append({'symbol': product, 'changePct': ch, 'start': px * 0.99, 'end': px})
    crypto = {
        'calendar': 'UTC days',
        'start': '2025-11-13',
        'end': '2025-11-14',
        'evaluated': len(CRYPTO_USD),
        'included': len(crypto_companies),
        'advancing': sum(1 for r in crypto_companies if r['changePct'] > 0),
        'declining': sum(1 for r in crypto_companies if r['changePct'] < 0),
        'excluded': [],
        'companies': crypto_companies,
        'notice': 'Demo crypto UTC-day changes from bundled candles.',
    }
    return {
        'method': 'market-overview-v6.0-demo',
        'equity': equity,
        'crypto': crypto,
        'notice': 'Portfolio demo · equities and crypto counts stay separate.',
    }


def crypto_points(product: str, count: int, step_ms: int) -> list[dict]:
    base = CRYPTO_USD.get(product, 100.0)
    end = QUOTE_TS
    return [
        {
            't': end - (count - i) * step_ms,
            'p': round(base * (0.96 + 0.04 * (i / max(1, count - 1)) + 0.01 * math.sin(i / 7)), 4),
        }
        for i in range(count)
    ]


def crypto_bundle() -> dict:
    followed = ['BTC-USD', 'ETH-USD', 'SOL-USD']
    quotes = {
        product: {'price': px, 'time': QUOTE_TS, 'status': 'cached', 'product': product}
        for product, px in CRYPTO_USD.items()
    }
    charts = {}
    for product in CRYPTO_USD:
        for rng, (step, count) in {'1H': (60_000, 60), '1D': (300_000, 288), '1W': (3_600_000, 168)}.items():
            pts = crypto_points(product, count, step)
            charts[f'{product}|{rng}'] = {
                'product': product,
                'points': pts,
                'start': pts[0]['t'],
                'end': pts[-1]['t'],
                'interval': step,
                'expected': count,
                'fetchedAt': QUOTE_TS,
                'status': 'cached',
                'coverage': {'label': 'Bundled Coinbase-style demo candles', 'gaps': 0},
            }
    board_rows = []
    for product, name_px in [(p, CRYPTO_USD[p]) for p in CRYPTO_USD]:
        day = charts.get(f'{product}|1D', {})
        pts = day.get('points') or []
        ch24 = round((pts[-1]['p'] / pts[0]['p'] - 1) * 100, 2) if len(pts) >= 2 else None
        board_rows.append({
            'product': product,
            'name': product.split('-')[0],
            'id': product,
            'base': product.split('-')[0],
            'quote': 'USD',
            'price': name_px,
            'time': QUOTE_TS,
            'quoteStatus': 'cached',
            'change24h': ch24,
            'change7d': round(ch24 * 1.8, 2) if ch24 is not None else None,
            'coverage': day.get('coverage'),
        })
    return {
        'followed': followed,
        'quotes': quotes,
        'charts': charts,
        'board': {
            'exchange': 'Coinbase Exchange (demo bundle)',
            'quote': 'USD',
            'timezone': 'UTC',
            'trading': '24/7 demo candles · not live Coinbase on this host.',
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
                   'source': 'Bundled FRED-style demo', 'adjustment': 'Seasonally adjusted'},
        'CPIAUCSL': {'title': 'US consumer prices', 'unit': 'Index, 1982–1984 = 100', 'frequency': 'monthly',
                    'source': 'Bundled FRED-style demo', 'adjustment': 'Seasonally adjusted'},
        'FEDFUNDS': {'title': 'US effective federal funds rate', 'unit': '% · monthly average', 'frequency': 'monthly',
                     'source': 'Bundled FRED-style demo', 'adjustment': 'Not seasonally adjusted'},
        'GDPC1': {'title': 'US real GDP', 'unit': 'Billions of chained 2017 USD, annual rate', 'frequency': 'quarterly',
                 'source': 'Bundled FRED-style demo', 'adjustment': 'Seasonally adjusted annual rate'},
    }
    latest = {'UNRATE': 4.1, 'CPIAUCSL': 314.2, 'FEDFUNDS': 4.58, 'GDPC1': 23245.0}
    series = []
    for code, definition in series_defs.items():
        val = latest[code]
        series.append({
            **definition,
            'id': code,
            'url': f'https://fred.stlouisfed.org/series/{code}',
            'fetchedAt': QUOTE_TS,
            'latest': {'date': '2025-10-01', 'value': val},
            'yearAgoChangePct': 2.1 if code in ('CPIAUCSL', 'GDPC1') else None,
            'frequency': definition['frequency'],
            'notice': 'Bundled observation for the admissions demo. Live macro refresh needs your Mac.',
        })
    return {'series': series, 'available': series_defs}


def workspace_bundle(catalog: list[dict]) -> dict:
    names = {e['symbol']: e['name'] for e in catalog}
    return {
        'watch': WATCHLIST,
        'names': names,
        'notes': [{
            'id': 'demo-note-1',
            'symbol': 'TTWO',
            'title': 'GTA VI timing watch',
            'body': 'Bundled research note for the public demo. Save your own notes on your Mac.',
            'createdAt': '2025-11-01T18:00:00Z',
        }],
        'reports': [{
            'id': 'demo-report-1',
            'symbol': 'AAPL',
            'title': 'Services mix — demo draft',
            'status': 'Draft',
            'summary': 'Illustrative report shell for admissions screenshots.',
        }],
        'research': {
            'initialised': True,
            'watchlists': [{'id': 'wl-demo', 'title': 'Demo watchlist', 'symbols': WATCHLIST[:6]}],
            'projects': [{
                'id': 'proj-demo-ttwo',
                'symbol': 'TTWO',
                'title': 'Take-Two · release cadence',
                'stage': 'Investigate',
                'question': 'How visible is the next franchise window in saved accounts?',
                'thesis': 'Demo project only — not investment advice.',
                'risks': 'Bundled figures only.',
                'updatedAt': '2025-11-10T12:00:00Z',
                'items': [],
                'archived': False,
            }],
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
            'headline': 'Heatmap directory uses labelled synthetic closes',
            'source': 'Demo bundle',
            'url': 'https://example.com/market-desk-heatmap',
            'datetime': BASE_TS_SEC - 7200,
            'summary': '221-name directory tile colours come from snapshot.json, not a live Massive sync.',
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
            'latestSavedPrice': 228.4,
            'source': 'Portfolio demo · synthetic daily closes',
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
        'coverage': {**common['coverage'], 'latestSavedPrice': 228.4},
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
                'last_price': 139.2,
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


def main() -> None:
    catalog = json.loads(CATALOG.read_text())
    stamp = QUOTE_TS
    rows = heatmap_rows(catalog, stamp)
    global_news, news_by_symbol = news_bundle()

    snapshot = {
        'version': 3,
        'label': 'PORTFOLIO DEMO · labelled synthetic snapshot · not live market data',
        'generated': '2026-11-15',
        'watchlist': WATCHLIST,
        'quotes': {sym: {'c': price(sym), 'pc': round(price(sym) * 0.99, 2)} for sym in BASE_PRICES},
        'heatmap': {
            'rows': rows,
            'period': '1D',
            'start': '2025-11-07',
            'end': '2025-11-12',
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
        'dailyBars': {sym: daily_bars(sym) for sym in WATCHLIST},
        'news': global_news,
        'newsBySymbol': news_by_symbol,
        'screener': {
            'asOf': stamp,
            'directoryCount': len(catalog),
            'rows': [screener_row(e, stamp) for e in catalog],
            'notice': 'Bundled screener snapshots for the full directory on the public demo.',
        },
        'overview60': overview60_packet(rows),
        'crypto': crypto_bundle(),
        'tape': {
            sym: {
                'events': tape_events(sym),
                'recordingDays': [{'date': '2025-11-12', 'count': 120}],
            }
            for sym in TAPE_SYMBOLS
        },
        'intelligence': {sym: intelligence_packet(sym) for sym in WATCHLIST},
        'forecasts': {sym: forecast_packet(sym) for sym in ['TTWO', 'AMD', 'AAPL', 'NVDA', 'TSLA']},
        'macro': macro_bundle(),
        'alerts': alerts_bundle(),
        'learning': learning_bundle(),
        'workspace': workspace_bundle(catalog),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(snapshot, separators=(',', ':')))
    print(
        f'Wrote {OUT} ({len(rows)} heatmap rows, {len(snapshot["screener"]["rows"])} screener rows, '
        f'{OUT.stat().st_size} bytes)'
    )


if __name__ == '__main__':
    main()