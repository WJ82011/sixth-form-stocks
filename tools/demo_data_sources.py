#!/usr/bin/env python3
"""Free-provider helpers for building the public demo snapshot.

Preferred equity path (when keys exist):
  - Finnhub free-tier REST quotes (`c` / `pc`)
  - Massive Basic daily aggregates for chart bars

Always-free public paths already in the product:
  - Coinbase Exchange REST (crypto candles / ticker)
  - FRED fredgraph.csv (macro series)

Offline fallback:
  - tools/demo_fixtures/equity_bars.json (bundled historical closes)

No new paid APIs. Keys are read from the environment or ~/.marketdesk-reborn/.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import math
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER_DIR = Path.home() / '.marketdesk-reborn'
FIXTURE = Path(__file__).resolve().parent / 'demo_fixtures' / 'equity_bars.json'
FINNHUB_BASE = 'https://finnhub.io/api/v1/'
MASSIVE_BASE = 'https://api.massive.com/'
COINBASE_BASE = 'https://api.exchange.coinbase.com/products/'
TLS = ssl.create_default_context()
UA = 'MarketDesk-Reborn/demo-export (+https://github.com/wj82011/sixth-form-stocks)'


def _read_key(env_names: tuple[str, ...], file_name: str) -> str | None:
    for name in env_names:
        value = (os.environ.get(name) or '').strip()
        if value:
            return value
    path = USER_DIR / file_name
    if path.is_file():
        value = path.read_text(encoding='utf-8').strip()
        if value:
            return value
    return None


def finnhub_key() -> str | None:
    return _read_key(('FINNHUB_API_KEY', 'FINNHUB_TOKEN', 'FINNHUB_KEY'), 'finnhub_key')


def massive_key() -> str | None:
    return _read_key(('MASSIVE_API_KEY', 'POLYGON_API_KEY', 'MASSIVE_KEY'), 'massive_key')


def http_json(url: str, headers: dict | None = None, timeout: float = 20) -> object:
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json', **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout, context=TLS) as response:
        body = response.read(2_000_001)
    if len(body) > 2_000_000:
        raise ValueError('response too large')
    return json.loads(body.decode('utf-8'))


def http_text(url: str, timeout: float = 20) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/csv,*/*'})
    with urllib.request.urlopen(req, timeout=timeout, context=TLS) as response:
        body = response.read(500_001)
    if len(body) > 500_000:
        raise ValueError('response too large')
    return body.decode('utf-8-sig')


def load_equity_fixture() -> dict:
    if not FIXTURE.is_file():
        raise FileNotFoundError(f'Missing equity fixture at {FIXTURE}')
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def session_change_pct(close: float, prev_close: float) -> float | None:
    if not (math.isfinite(close) and math.isfinite(prev_close) and prev_close > 0 and close > 0):
        return None
    return round((close / prev_close - 1) * 100, 4)


def fetch_finnhub_quotes(symbols: list[str]) -> dict[str, dict]:
    token = finnhub_key()
    if not token:
        return {}
    out: dict[str, dict] = {}
    for sym in symbols:
        try:
            url = FINNHUB_BASE + 'quote?' + urllib.parse.urlencode({'symbol': sym, 'token': token})
            raw = http_json(url)
            if not isinstance(raw, dict):
                continue
            c, pc = float(raw.get('c') or 0), float(raw.get('pc') or 0)
            t = int(raw.get('t') or 0)
            if c <= 0 or pc <= 0 or t <= 0:
                continue
            out[sym] = {
                'c': round(c, 4),
                'pc': round(pc, 4),
                't': t,
                'prevT': t - 86400,
                'o': round(float(raw.get('o') or c), 4),
                'h': round(float(raw.get('h') or c), 4),
                'l': round(float(raw.get('l') or c), 4),
                'source': 'Finnhub free-tier quote',
            }
            time.sleep(0.35)  # free-tier polite pacing
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError, TypeError):
            continue
    return out


def fetch_massive_daily(symbol: str, days: int = 260) -> dict | None:
    token = massive_key()
    if not token:
        return None
    end = dt.datetime.now(dt.timezone.utc).date() - dt.timedelta(days=1)
    start = end - dt.timedelta(days=int(days * 1.7))
    endpoint = f'v2/aggs/ticker/{urllib.parse.quote(symbol, safe="")}/range/1/day/{start.isoformat()}/{end.isoformat()}'
    url = MASSIVE_BASE + endpoint + '?' + urllib.parse.urlencode({'adjusted': 'true', 'sort': 'asc', 'limit': 50000})
    try:
        raw = http_json(url, headers={'Authorization': f'Bearer {token}'})
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError, TypeError):
        return None
    results = raw.get('results') if isinstance(raw, dict) else None
    if not isinstance(results, list) or len(results) < 2:
        return None
    t, o, h, l, c, v = [], [], [], [], [], []
    for row in results:
        try:
            close = float(row['c'])
            stamp = int(row['t'] // 1000)
        except (KeyError, TypeError, ValueError):
            continue
        if close <= 0:
            continue
        t.append(stamp)
        c.append(round(close, 4))
        o.append(round(float(row.get('o') or close), 4))
        h.append(round(float(row.get('h') or close), 4))
        l.append(round(float(row.get('l') or close), 4))
        v.append(int(float(row.get('v') or 0)))
    if len(c) < 2:
        return None
    return {'s': 'ok', 't': t, 'c': c, 'o': o, 'h': h, 'l': l, 'v': v, 'source': 'Massive Basic daily'}


def fetch_coinbase_products(products: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    now = int(time.time())
    for product in products:
        try:
            ticker = http_json(COINBASE_BASE + product + '/ticker')
            price = float(ticker['price'])
            # last two completed UTC days via 86400 candles
            end = now - (now % 86400)
            start = end - 3 * 86400
            candles = http_json(
                COINBASE_BASE
                + product
                + '/candles?'
                + urllib.parse.urlencode({'start': dt.datetime.fromtimestamp(start, dt.timezone.utc).isoformat(),
                                          'end': dt.datetime.fromtimestamp(end, dt.timezone.utc).isoformat(),
                                          'granularity': 86400})
            )
            closes = []
            if isinstance(candles, list):
                for row in sorted(candles, key=lambda r: r[0]):
                    if isinstance(row, list) and len(row) >= 5:
                        closes.append((int(row[0]), float(row[4])))
            pc = closes[-2][1] if len(closes) >= 2 else price * 0.995
            # Prefer distinct session closes when present; never force a flat book %.
            if len(closes) >= 2:
                price = closes[-1][1]
                pc = closes[-2][1]
            out[product] = {
                'price': round(price, 6 if price < 10 else 4),
                'previous': round(pc, 6 if pc < 10 else 4),
                'time': int(dt.datetime.fromisoformat(str(ticker['time']).replace('Z', '+00:00')).timestamp() * 1000)
                if ticker.get('time') else now * 1000,
                'source': 'Coinbase Exchange public REST',
            }
            # 1D / 1W chart points
            for rng, (step, count) in {'1H': (60, 60), '1D': (300, 288), '1W': (3600, 168)}.items():
                end_s = (now // step) * step
                start_s = end_s - count * step
                rows = http_json(
                    COINBASE_BASE
                    + product
                    + '/candles?'
                    + urllib.parse.urlencode({
                        'start': dt.datetime.fromtimestamp(start_s, dt.timezone.utc).isoformat(),
                        'end': dt.datetime.fromtimestamp(end_s, dt.timezone.utc).isoformat(),
                        'granularity': step,
                    })
                )
                points = []
                if isinstance(rows, list):
                    for row in sorted(rows, key=lambda r: r[0]):
                        if isinstance(row, list) and len(row) >= 5 and row[4]:
                            points.append({'t': (int(row[0]) + step) * 1000, 'p': float(row[4])})
                out[product].setdefault('charts', {})[rng] = points
            time.sleep(0.2)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError, TypeError, KeyError):
            continue
    return out


def fetch_fred_latest(codes: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    start = f'{dt.datetime.now(dt.timezone.utc).year - 3}-01-01'
    for code in codes:
        try:
            text = http_text(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={code}&cosd={start}')
            reader = csv.DictReader(io.StringIO(text))
            rows = []
            for row in reader:
                stamp = row.get('observation_date') or row.get('DATE')
                try:
                    value = float(row.get(code, ''))
                    day = dt.date.fromisoformat(stamp)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(value):
                    rows.append({'date': day.isoformat(), 'value': value})
            if not rows:
                continue
            latest = rows[-1]
            prior = next((r for r in reversed(rows) if r['date'][:4] == str(int(latest['date'][:4]) - 1)
                          and r['date'][5:] == latest['date'][5:]), None)
            yoy = None
            if prior and prior['value'] and code in ('CPIAUCSL', 'GDPC1'):
                yoy = round((latest['value'] / prior['value'] - 1) * 100, 4)
            out[code] = {'latest': latest, 'yearAgoChangePct': yoy, 'source': 'FRED public CSV'}
            time.sleep(0.3)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ValueError):
            continue
    return out


def merge_equity_quotes(fixture: dict, live: dict[str, dict]) -> dict[str, dict]:
    merged = dict(fixture.get('quotes') or {})
    for sym, quote in live.items():
        merged[sym] = {**merged.get(sym, {}), **quote}
    return merged


def equity_from_fixture_or_live(symbols: list[str], watchlist: list[str], allow_network: bool = True) -> dict:
    """Return quotes, sessions, dailyBars, and a provenance label."""
    fixture = load_equity_fixture()
    quotes = dict(fixture.get('quotes') or {})
    sessions = dict(fixture.get('sessions') or {})
    daily = dict(fixture.get('dailyBars') or {})
    sources = ['bundled historical equity closes (tools/demo_fixtures/equity_bars.json)']

    if allow_network:
        live_quotes = fetch_finnhub_quotes(symbols)
        if live_quotes:
            quotes = merge_equity_quotes(fixture, live_quotes)
            sources.insert(0, f'Finnhub free-tier quotes ({len(live_quotes)} symbols)')
            # Refresh session tips from live quote pairs
            for sym, q in live_quotes.items():
                tip = sessions.get(sym) or []
                tip = list(tip)
                tip.append({'t': q['prevT'], 'c': q['pc']})
                tip.append({'t': q['t'], 'c': q['c']})
                sessions[sym] = tip[-8:]
        for sym in watchlist:
            bars = fetch_massive_daily(sym)
            if bars:
                daily[sym] = bars
                if 'Massive Basic daily bars' not in sources:
                    sources.insert(0, 'Massive Basic daily bars')
                time.sleep(0.3)

    return {
        'quotes': quotes,
        'sessions': sessions,
        'dailyBars': daily,
        'sources': sources,
        'fixtureNote': fixture.get('sourceNote') or '',
        'asOf': fixture.get('asOf'),
    }
