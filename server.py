#!/usr/bin/env python3
"""Market Desk Reborn — local-only market research server; Python standard library."""
from __future__ import annotations
import statements3
import lab3
import workspace3,analyst34,draft35
import financials
import sec_accounts
import research_ai
import screening
import desk
import price_alerts
import journal49
import intelligence
import hashlib
import collections
import csv
import io
import contextlib
import functools
import datetime as dt
import json
import math
import os
import re
import socket
import ssl
import subprocess
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer as _ThreadingHTTPServer

class ThreadingHTTPServer(_ThreadingHTTPServer):
    request_queue_size=64
    daemon_threads=True

from pathlib import Path
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

ROOT = Path(__file__).resolve().parent
SITE = ROOT / 'site'
USER_DIR = Path.home() / '.marketdesk-reborn'
KEY_FILE = USER_DIR / 'finnhub_key'
MASSIVE_KEY_FILE = USER_DIR / 'massive_key'
DB_FILE = USER_DIR / 'observations.sqlite3'
WORKSPACE_FILE = USER_DIR / 'workspace.json'
BASE_URL = 'https://finnhub.io/api/v1/'
MASSIVE_BASE_URL = 'https://api.massive.com/'
MASSIVE_CACHE = {}
MASSIVE_REQUEST_LOG = collections.deque()
MASSIVE_BACKOFF = 0.0
SYMBOL_RE = re.compile(r'^[A-Z0-9][A-Z0-9.\-:_]{0,23}$')
LOCK = threading.RLock()
CACHE = {}
CACHE_FETCHED_AT = {}  # true Finnhub fetch timestamp for source provenance, keyed like CACHE
REQUEST_LOG = collections.deque()
GLOBAL_BACKOFF = 0.0
NETWORK_BACKOFF_UNTIL = 0.0
VERSION = '6.8.0'
import collector40
import coverage41
COLLECTOR = None


def valid_symbol(raw):
    if not isinstance(raw,str):raise ValueError('Use a ticker written as text.')
    s = str(raw).strip().upper()
    if not SYMBOL_RE.fullmatch(s):
        raise ValueError('Use a valid ticker (letters, digits, dots, dashes or colons).')
    return s


def init_storage():
    USER_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(USER_DIR,0o700)
    with contextlib.closing(db_connection()) as con, con:
        con.execute('''CREATE TABLE IF NOT EXISTS observations (
            symbol TEXT NOT NULL, ts INTEGER NOT NULL, price REAL NOT NULL,
            source TEXT NOT NULL, received_at INTEGER NOT NULL,
            PRIMARY KEY(symbol, ts, source))''')
        con.execute('CREATE INDEX IF NOT EXISTS obs_sym_ts ON observations(symbol,ts)')
        con.execute('''CREATE TABLE IF NOT EXISTS tape_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL, ts INTEGER NOT NULL, price REAL NOT NULL,
            volume REAL NOT NULL, received_at INTEGER NOT NULL, kind TEXT NOT NULL
        )''')
        con.execute('CREATE INDEX IF NOT EXISTS tape_sym_ts ON tape_events(symbol,ts DESC)')
        con.execute('''CREATE TABLE IF NOT EXISTS massive_daily_bars (
            symbol TEXT NOT NULL, ts_ms INTEGER NOT NULL, o REAL NOT NULL, h REAL NOT NULL,
            l REAL NOT NULL, c REAL NOT NULL, v REAL NOT NULL, fetched_at INTEGER NOT NULL,
            PRIMARY KEY (symbol, ts_ms))''')
        con.execute('CREATE INDEX IF NOT EXISTS massive_daily_sym ON massive_daily_bars(symbol,ts_ms)')
        con.execute('''CREATE TABLE IF NOT EXISTS imported_daily_history (
            symbol TEXT PRIMARY KEY, payload TEXT NOT NULL)''')
        price_alerts.init(con)
        research_ai.init(con)
        screening.init(con)
        desk.init(con)
        sec_accounts.init(con)
        lab3.init(con)
    os.chmod(DB_FILE,0o600)


def db_connection():
    return sqlite3.connect(DB_FILE, timeout=12)


def store_point(symbol, ts_ms, price, source):
    if not isinstance(ts_ms, int) or ts_ms < 946684800000 or ts_ms > int(time.time()*1000)+60000:
        return False
    if isinstance(price,bool): return False
    try:
        price = float(price)
    except (TypeError, ValueError):
        return False
    if price <= 0 or price > 1e9 or price != price:
        return False
    with LOCK, contextlib.closing(db_connection()) as con, con:
        con.execute('INSERT OR REPLACE INTO observations VALUES(?,?,?,?,?)',
                    (symbol, ts_ms, price, source, int(time.time()*1000)))
        price_alerts.observe(con,symbol,ts_ms,price,source,int(time.time()*1000))
        # Bounded to prevent unbounded growth; keep ~5k most recent observations per symbol.
        con.execute('''DELETE FROM observations WHERE symbol=? AND rowid NOT IN
                    (SELECT rowid FROM observations WHERE symbol=? ORDER BY ts DESC LIMIT 5000)''', (symbol, symbol))
    return True



def store_points_batch(ticks):
    '''Store browser-received Finnhub stream frames, with source and volume.

    No claim of independent exchange authentication: browser validates WebSocket
    source and frame shape. Observations are not a consolidated market tape.
    '''
    normalized = []
    latest = int(time.time() * 1000)
    for item in ticks:
        if not isinstance(item, dict):
            continue
        try:
            if any(isinstance(item.get(k),bool) for k in ('t','p','v')): continue
            sym = valid_symbol(item.get('s', ''))
            raw_ts=item.get('t',0)
            if not isinstance(raw_ts,(int,float)) or not math.isfinite(raw_ts) or raw_ts!=int(raw_ts):continue
            ts = int(raw_ts)
            price = float(item.get('p', 0))
            volume = float(item.get('v', -1))
            if not (latest-300000 <= ts <= latest + 60000):
                continue
            if not (0 < price <= 1e9 and price == price and 0 <= volume <= 1e12 and volume == volume):
                continue
            kind = 'trade' if volume > 0 else 'price_update'
            normalized.append((sym, ts, price, volume, latest, kind))
        except (ValueError, TypeError, OverflowError):
            continue
    if not normalized:
        return 0
    with LOCK, contextlib.closing(db_connection()) as con, con:
        con.executemany('''INSERT INTO tape_events
            (symbol,ts,price,volume,received_at,kind) VALUES (?,?,?,?,?,?)''', normalized)
        con.executemany('''INSERT OR REPLACE INTO observations VALUES(?,?,?,?,?)''',
            [(sym, ts, price, 'finnhub_websocket_trade' if kind == 'trade' else 'finnhub_websocket_update', received)
             for sym, ts, price, volume, received, kind in normalized])
        for sym,ts,price,volume,received,kind in sorted(normalized,key=lambda x:x[1]):
            if kind=='trade':price_alerts.observe(con,sym,ts,price,'finnhub_websocket_trade',received)
        for symbol in {row[0] for row in normalized}:
            # Retain a finite local sample per symbol; preserve other workspace data.
            con.execute('''DELETE FROM observations WHERE symbol=? AND rowid NOT IN
                        (SELECT rowid FROM observations WHERE symbol=? ORDER BY ts DESC LIMIT 5000)''',
                        (symbol, symbol))
            con.execute('''DELETE FROM tape_events WHERE symbol=? AND id NOT IN
                        (SELECT id FROM tape_events WHERE symbol=? ORDER BY ts DESC,id DESC LIMIT 18000)''',
                        (symbol, symbol))
    return len(normalized)


def get_tape_events(symbol, since_ms=0, limit=2000, last_recording=False, until_ms=None):
    '''Return real positive-volume trade events in ascending event-time order.'''
    with contextlib.closing(db_connection()) as con, con:
        if until_ms is None:
            until_ms = int(time.time()*1000) + 60000
        if last_recording:
            latest = con.execute("SELECT max(ts) FROM tape_events WHERE symbol=? AND kind='trade'", (symbol,)).fetchone()[0]
            if latest is None:
                return []
            until_ms = latest
            since_ms = latest - 86400000
        rows = con.execute("""SELECT ts,price,volume,received_at,id
            FROM tape_events WHERE symbol=? AND kind='trade' AND ts>=? AND ts<=?
            ORDER BY ts DESC,id DESC LIMIT ?""",
            (symbol, since_ms, until_ms, max(1, min(limit, 4000)))).fetchall()
    return [{'t': ts, 'p': price, 'v': vol, 'receivedAt': recv, 'id': ident}
            for ts, price, vol, recv, ident in reversed(rows)]


def tape_recording_days(symbol):
    """Return UTC dates represented in the retained positive-size print sample."""
    with contextlib.closing(db_connection()) as con:
        rows = con.execute("""SELECT strftime('%Y-%m-%d',ts/1000,'unixepoch') AS day,count(*)
            FROM tape_events WHERE symbol=? AND kind='trade'
            GROUP BY day ORDER BY day DESC LIMIT 31""", (symbol,)).fetchall()
    return [{'date': day, 'count': count} for day,count in rows if day]


def get_history(symbol, since_ms=0, limit=2000):
    with contextlib.closing(db_connection()) as con, con:
        rows = con.execute('''SELECT ts,price,source FROM observations
                 WHERE symbol=? AND ts>=? ORDER BY ts DESC LIMIT ?''',
                 (symbol, since_ms, min(limit, 5000))).fetchall()
    return [{'t': ts, 'p': price, 'source': src} for ts, price, src in reversed(rows)]


def get_key():
    try:
        return KEY_FILE.read_text(encoding='utf-8').strip()
    except FileNotFoundError:
        return ''


def get_massive_key():
    try:
        return MASSIVE_KEY_FILE.read_text(encoding='utf-8').strip()
    except FileNotFoundError:
        return ''


def save_massive_key(key):
    """Keep Massive API credentials server-side; never expose to the browser."""
    key = str(key).strip()
    if not re.fullmatch(r'[A-Za-z0-9_\-]{8,200}', key):
        raise ValueError('This does not look like a Massive API key.')
    USER_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(USER_DIR, 0o700)
    fd = os.open(MASSIVE_KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as file:
        file.write(key)
    os.chmod(MASSIVE_KEY_FILE, 0o600)
    global MASSIVE_BACKOFF
    with LOCK:
        MASSIVE_CACHE.clear()
        MASSIVE_REQUEST_LOG.clear()
        MASSIVE_BACKOFF = 0.0
    return True


def clear_massive_key():
    global MASSIVE_BACKOFF
    MASSIVE_KEY_FILE.unlink(missing_ok=True)
    with LOCK:
        MASSIVE_CACHE.clear()
        MASSIVE_REQUEST_LOG.clear()
        MASSIVE_BACKOFF = 0.0


def save_key(key):
    key = key.strip()
    if not re.fullmatch(r'[A-Za-z0-9_\-]{8,160}', key):
        raise ValueError('This does not look like a valid Finnhub API key.')
    USER_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(key)
    os.chmod(KEY_FILE, 0o600)
    global GLOBAL_BACKOFF, NETWORK_BACKOFF_UNTIL
    with LOCK:
        CACHE.clear()
        GLOBAL_BACKOFF = 0.0
        NETWORK_BACKOFF_UNTIL = 0.0
    return True


class ProviderError(Exception):
    def __init__(self, status, message, retry_after=None, kind='provider'):
        super().__init__(message)
        self.status = status
        self.message = message
        self.retry_after = retry_after
        self.kind = kind


@functools.lru_cache(maxsize=1)
def verified_tls_context():
    """Use Python CA roots and, on macOS, verified system root certificates.

    `security` exports public *root certificates*, never secrets or private keys.
    Certificate validation and host-name checking remain enabled in all cases.
    """
    context = ssl.create_default_context()
    source = 'Python/OpenSSL default trusted roots'
    if sys.platform == 'darwin':
        keychain = '/System/Library/Keychains/SystemRootCertificates.keychain'
        try:
            completed = subprocess.run(
                ['/usr/bin/security', 'find-certificate', '-a', '-p', keychain],
                capture_output=True, text=True, timeout=7, check=True)
            pem = completed.stdout
            if pem.count('-----BEGIN CERTIFICATE-----') >= 20:
                context.load_verify_locations(cadata=pem)
                source = 'Python/OpenSSL + macOS system root certificates'
        except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError,
                ssl.SSLError, ValueError):
            # Keep TLS verification enforced, even if keychain import fails.
            source = 'Python/OpenSSL defaults (macOS root import unavailable)'
    return context, source


def classify_network_error(error):
    """Translate urllib failures into safe, actionable messages; never include keys."""
    cause = error.reason if isinstance(error, urllib.error.URLError) else error
    if isinstance(cause, (ssl.SSLCertVerificationError, ssl.CertificateError)) or 'CERTIFICATE_VERIFY_FAILED' in str(cause):
        return ('tls_certificate',
                'Secure HTTPS certificate verification failed in Python. '
                'Market Desk cannot verify Finnhub’s certificate. Check the Mac date/time '
                'and VPN or filtering software; see the detailed connection check.')
    if isinstance(cause, (socket.gaierror,)):
        return ('dns', 'Python could not resolve Finnhub’s address (DNS). '
                'Check internet access and any VPN, DNS filter or proxy.')
    if isinstance(cause, (TimeoutError, socket.timeout)) or 'timed out' in str(cause).lower():
        return ('timeout', 'Connection to Finnhub timed out. Check your network, VPN or firewall.')
    if isinstance(cause, ConnectionRefusedError):
        return ('connection_refused', 'The Finnhub connection was refused by the network or remote host.')
    if isinstance(cause, ssl.SSLError):
        return ('tls_other', 'Python could not negotiate a secure TLS connection to Finnhub. '
                'Check VPN or HTTPS inspection; certificate checks remain enabled.')
    if isinstance(cause, urllib.error.URLError):
        return ('network', 'Python could not establish an HTTPS connection to Finnhub. '
                'Check VPN, firewall and proxy configuration.')
    return ('network', 'Python could not complete the Finnhub connection. '
            'Open the Connection Check for troubleshooting.')


def provider_get(endpoint, params=None, ttl=30, bypass_cache=False):
    global GLOBAL_BACKOFF, NETWORK_BACKOFF_UNTIL
    key = get_key()
    if not key:
        raise ProviderError(401, 'Add a Finnhub API key in Settings first.', kind='no_token')
    params = params or {}
    cache_id = (endpoint, tuple(sorted((k, str(v)) for k, v in params.items())))
    with LOCK:
        entry = CACHE.get(cache_id)
        if not bypass_cache and entry and time.monotonic() < entry[0]:
            return entry[1], True
        now = time.monotonic()
        if not bypass_cache and now < NETWORK_BACKOFF_UNTIL:
            raise ProviderError(503, 'Finnhub network connection is cooling down after a failed request. '
                                'Use Run real connection check to retry immediately.',
                                int(NETWORK_BACKOFF_UNTIL-now)+1, kind='network_cooldown')
        if now < GLOBAL_BACKOFF:
            raise ProviderError(429, 'Finnhub rate limit cooldown is active. Please retry later.',
                                int(GLOBAL_BACKOFF-now)+1, kind='rate_limit')
        while REQUEST_LOG and now-REQUEST_LOG[0] > 60:
            REQUEST_LOG.popleft()
        if len(REQUEST_LOG) >= 48:
            raise ProviderError(429, 'Local API budget reached (48 provider calls/min). Please retry shortly.',
                                20, kind='local_budget')
        REQUEST_LOG.append(now)
    url = BASE_URL + endpoint + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        'X-Finnhub-Token': key, 'User-Agent': 'MarketDeskResearch/1.9.0 (local personal research)',
        'Accept': 'application/json'
    })
    try:
        context, _ = verified_tls_context()
        with urllib.request.urlopen(req, timeout=12, context=context) as response:
            result = json.loads(response.read(2_000_000))
    except urllib.error.HTTPError as exc:
        status = exc.code
        if status == 429:
            with LOCK:
                GLOBAL_BACKOFF = time.monotonic() + 60
            raise ProviderError(429, 'Finnhub returned HTTP 429 (rate limited); paused for 60 seconds.',
                                60, kind='rate_limit') from exc
        if status in (401, 403):
            raise ProviderError(status, 'Finnhub denied the request (HTTP %s). '
                                'Check API key and endpoint permissions.' % status,
                                kind='authentication' if status == 401 else 'entitlement') from exc
        if status == 404:
            raise ProviderError(502, 'Finnhub endpoint was not found (HTTP 404).', kind='endpoint') from exc
        raise ProviderError(502, 'Finnhub returned HTTP %s.' % status, kind='provider_http') from exc
    except (urllib.error.URLError, ssl.SSLError, TimeoutError, OSError) as exc:
        kind, detail = classify_network_error(exc)
        with LOCK:
            NETWORK_BACKOFF_UNTIL = time.monotonic()+18
        raise ProviderError(502, detail, kind=kind) from exc
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProviderError(502, 'Finnhub returned invalid JSON data.', kind='invalid_json') from exc
    if isinstance(result, dict) and result.get('error'):
        msg = str(result['error'])[:240]
        raise ProviderError(403, 'Finnhub: ' + msg, kind='provider_error')
    with LOCK:
        if ttl > 0:
            CACHE[cache_id] = (time.monotonic()+ttl, result)
            CACHE_FETCHED_AT[cache_id] = int(time.time()*1000)
            # Keep search/company cache bounded over long-running research sessions.
            if len(CACHE)>500:
                expired=[k for k,(expiry,_) in CACHE.items() if expiry<=time.monotonic()]
                for k in expired: CACHE.pop(k,None); CACHE_FETCHED_AT.pop(k,None)
                while len(CACHE)>480:
                    oldest=next(iter(CACHE)); CACHE.pop(oldest,None); CACHE_FETCHED_AT.pop(oldest,None)
    return result, False



def imported_history(symbol, start=0, end=None):
    """User-supplied closes stay separate from provider bars and ML training."""
    with contextlib.closing(db_connection()) as con:
        row=con.execute('SELECT payload FROM imported_daily_history WHERE symbol=?',(symbol,)).fetchone()
    if not row:
        return {'status':'no_data','provider':'imported','points':[]}
    data=json.loads(row[0])
    end=end if end is not None else int(time.time()*1000)
    data['points']=[x for x in data['points'] if start<=x['t']<=end]
    return data


def change_imported_history(obj):
    if not isinstance(obj,dict): raise ValueError('Use an import object.')
    symbol=valid_symbol(obj.get('symbol',''))
    if obj.get('clear') is True:
        with LOCK, contextlib.closing(db_connection()) as con, con:
            con.execute('DELETE FROM imported_daily_history WHERE symbol=?',(symbol,))
            con.execute('DELETE FROM desk_import_metadata WHERE symbol=?',(symbol,))
        return {'ok':True,'symbol':symbol,'cleared':True}
    source=obj.get('source','')
    text=obj.get('csv','')
    if not isinstance(source,str) or not 3<=len(source.strip())<=160 or any(ord(c)<32 for c in source):
        raise ValueError('Add a source name, 3–160 characters, such as the site that exported your file.')
    if obj.get('confirmed') is not True or not isinstance(obj.get('split_adjusted'),bool):
        raise ValueError('Confirm this is historical daily price data for the selected ticker and choose its split adjustment.')
    if not isinstance(text,str) or not 1<=len(text)<=900000:
        raise ValueError('Choose a CSV file smaller than 900 KB.')
    reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    fields={str(k).strip().lower().replace(' ','').replace('_',''):k for k in (reader.fieldnames or [])}
    date_key=fields.get('date'); price_key=fields.get('adjclose') or fields.get('adjustedclose') or fields.get('close')
    if not date_key or not price_key:
        raise ValueError('The CSV needs Date (YYYY-MM-DD) and Close or Adj Close columns.')
    if price_key in (fields.get('adjclose'),fields.get('adjustedclose')) and obj['split_adjusted'] is not True:
        raise ValueError('An adjusted-close column was found. Confirm its adjustment in the file source, then select split-adjusted.')
    points={}; now=dt.datetime.now(dt.timezone.utc).date()
    try:
        for index,row in enumerate(reader,2):
            if index>10001: raise ValueError('Use at most 10,000 daily rows per stock.')
            date_text=str(row.get(date_key,'')).strip()
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date_text): raise ValueError('Use YYYY-MM-DD dates.')
            date=dt.date.fromisoformat(date_text)
            if date<dt.date(2000,1,1) or date>now: raise ValueError('Dates must be from 2000 through today.')
            value=float(row.get(price_key,''))
            if not math.isfinite(value) or value<=0 or value>=1e9: raise ValueError('Closing prices must be positive finite numbers.')
            # A daily file describes a session date, not an intraday trade timestamp.
            ts=int(dt.datetime.combine(date,dt.time(0),tzinfo=dt.timezone.utc).timestamp()*1000)
            if ts in points: raise ValueError('Duplicate dates are not allowed.')
            if 'symbol' in fields and valid_symbol(row.get(fields['symbol'],''))!=symbol:
                raise ValueError('The file contains another ticker. Import one stock at a time.')
            points[ts]={'t':ts,'p':value}
    except (ValueError,TypeError,csv.Error) as exc:
        raise ValueError('CSV row %s: %s' % (index if 'index' in locals() else 1,str(exc))) from None
    if len(points)<2: raise ValueError('At least two daily closing prices are needed.')
    data={'status':'ok','provider':'imported','symbol':symbol,'source':source.strip(),
          'split_adjusted':obj['split_adjusted'],'price_column':str(price_key).strip(),
          'imported_at':int(time.time()*1000),'points':sorted(points.values(),key=lambda x:x['t'])}
    with LOCK, contextlib.closing(db_connection()) as con, con:
        con.execute('INSERT OR REPLACE INTO imported_daily_history VALUES (?,?)',(symbol,json.dumps(data)))
        desk.remember_import(con,symbol,data)
    return {'ok':True,'symbol':symbol,'count':len(points),'first':data['points'][0]['t'],'last':data['points'][-1]['t']}


def massive_free_date_window(utc_now=None):
    """Conservative Stocks Basic entitlement window in New York calendar dates.

    Basic does not include its *current* New York date, even after the exchange
    close; the previous date is available after local midnight ET. Buffer the
    two-year boundary by two days to avoid a boundary-date HTTP 403.
    """
    instant = utc_now or dt.datetime.now(dt.timezone.utc)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=dt.timezone.utc)
    eastern = instant.astimezone(ZoneInfo('America/New_York') if ZoneInfo else dt.timezone(dt.timedelta(hours=-5)))
    today = eastern.date()
    latest = today - dt.timedelta(days=1)
    try:
        earliest = today.replace(year=today.year-2) + dt.timedelta(days=2)
    except ValueError:  # February 29 in a leap year
        earliest = today.replace(year=today.year-2, day=28) + dt.timedelta(days=2)
    return earliest, latest


def safe_massive_provider_error(body, secret):
    """Extract only bounded, non-secret provider status/message from error JSON."""
    try:
        if isinstance(body, bytes):
            body = body[:10000].decode('utf-8', 'replace')
        data = json.loads(body)
    except (ValueError, TypeError, UnicodeError):
        return '', ''
    if not isinstance(data, dict):
        return '', ''
    provider_status = str(data.get('status') or data.get('error') or '').strip()[:45]
    if not re.fullmatch(r'[a-zA-Z0-9_ -]{1,45}', provider_status):
        provider_status = ''
    message = str(data.get('message') or data.get('error') or '').strip()[:300]
    if secret:
        message = message.replace(secret, '[REDACTED]')
    # Do not pass through unexpected URLs, credentials or control characters.
    message = re.sub(r'https?://\S+|(?i:apikey|token|authorization|secret)\s*[:=]\s*\S+', '[redacted]', message)
    message = ''.join(c for c in message if c.isprintable())[:220]
    return provider_status, message


def explain_massive_error(http_code, provider_status, provider_message):
    """Give safe, actionable diagnostics without mislabelling plan failures as key failures."""
    provider_status = provider_status or ('HTTP '+str(http_code))
    detail = (provider_status + (': '+provider_message if provider_message else ''))[:250]
    lower = provider_message.lower()
    if http_code == 401:
        return 'massive_authentication', 'HTTP 401 · Massive authentication failed. Check your saved key. '+detail
    if http_code == 403:
        if 'timeframe' in lower or 'historical' in lower or 'past' in lower:
            return 'massive_recency', 'HTTP 403 · Requested dates may be outside this plan’s entitlement. '+detail
        return 'massive_entitlement', 'HTTP 403 · Massive plan does not permit this request. '+detail
    if http_code == 429:
        return 'massive_rate_limit', 'HTTP 429 · Massive provider rate limit. '+detail
    return 'massive_http', ('HTTP %d · Massive historical request failed. '%http_code)+detail


def massive_request(endpoint, params=None, ttl=21600, bypass_cache=False, max_bytes=2000000):
    """Stocks Basic end-of-day bars; private Bearer auth, conservative free-tier budget."""
    global MASSIVE_BACKOFF
    token = get_massive_key()
    if not token:
        raise ProviderError(401, 'Save a Massive API key in Settings first.', kind='massive_no_token')
    params = params or {}
    cache_id = (endpoint, tuple(sorted((k, str(v)) for k, v in params.items())))
    with LOCK:
        now = time.monotonic()
        entry = MASSIVE_CACHE.get(cache_id)
        if not bypass_cache and entry and now < entry[0]:
            return entry[1], True
        if now < MASSIVE_BACKOFF:
            raise ProviderError(429, 'Massive is cooling down after a rate-limit response.',
                                int(MASSIVE_BACKOFF-now)+1, kind='massive_rate_limit')
        while MASSIVE_REQUEST_LOG and now-MASSIVE_REQUEST_LOG[0] >= 60:
            MASSIVE_REQUEST_LOG.popleft()
        # Leave one request/minute of headroom on the free 5/minute plan.
        if len(MASSIVE_REQUEST_LOG) >= 4:
            raise ProviderError(429, 'Massive free-tier allowance reached (4 local requests / 60 s). Try again shortly.',
                                int(60-(now-MASSIVE_REQUEST_LOG[0]))+1, kind='massive_local_budget')
        MASSIVE_REQUEST_LOG.append(now)
    url = MASSIVE_BASE_URL + endpoint.lstrip('/')
    if params:
        url += '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        'Authorization': 'Bearer '+token,
        'Accept': 'application/json',
        'User-Agent': 'MarketDesk-Reborn/1.7.0 (personal local historical research)',
    })
    try:
        context, _ = verified_tls_context()
        with urllib.request.urlopen(req, timeout=12, context=context) as response:
            raw = response.read(max_bytes+1)
            if len(raw)>max_bytes:raise ValueError("Response exceeds the bounded data allowance")
            result = json.loads(raw)
    except urllib.error.HTTPError as exc:
        code = exc.code
        provider_status, provider_message = safe_massive_provider_error(exc.read(10000), token)
        kind, message = explain_massive_error(code, provider_status, provider_message)
        if code == 429:
            with LOCK: MASSIVE_BACKOFF = time.monotonic() + 65
        raise ProviderError(code if code in (401, 403, 429) else 502,
                            message, 65 if code == 429 else None, kind=kind) from exc
    except (urllib.error.URLError, ssl.SSLError, TimeoutError, OSError) as exc:
        kind, _ = classify_network_error(exc)
        raise ProviderError(502, 'Massive HTTPS connection failed (%s). Check network and certificate settings.' % kind,
                            kind='massive_'+kind) from exc
    except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProviderError(502, 'Massive returned invalid JSON.', kind='massive_json') from exc
    if not isinstance(result, dict):
        raise ProviderError(502, 'Massive returned a non-object historical response.', kind='massive_schema')
    status = str(result.get('status','')).upper()
    if status not in ('OK','DELAYED'):
        provider_status, provider_message = safe_massive_provider_error(json.dumps(result), token)
        code = 403 if provider_status.upper() in ('NOT_AUTHORIZED', 'FORBIDDEN') else 502
        kind, message = explain_massive_error(code, provider_status, provider_message)
        raise ProviderError(code, message, kind=kind)
    with LOCK:
        if ttl:
            MASSIVE_CACHE[cache_id] = (time.monotonic()+ttl, result)
            while len(MASSIVE_CACHE) > 150:
                MASSIVE_CACHE.pop(next(iter(MASSIVE_CACHE)))
    return result, False


def normalized_massive_candles(payload, symbol, start, end):
    """Normalise split-adjusted Massive bars to existing Finnhub OHLC schema.

    Strictly refuse malformed bars, duplicate timestamps, unadjusted responses,
    incorrect ticker labels, and future-dated bars. Empty intervals remain empty.
    """
    # Massive explicitly documents DELAYED as valid HTTP 200 data on delayed tiers.
    # The old v1.6.1 normalizer rejected DELAYED even though massive_request
    # accepted it; this caused the user's repeated vague red error.
    if not isinstance(payload,dict) or str(payload.get('status','')).upper() not in ('OK','DELAYED'):
        raise ProviderError(502, 'Massive returned no usable historical bars (unexpected provider status).', kind='massive_response')
    if payload.get('ticker','').upper() != symbol:
        raise ProviderError(502, 'Massive returned data for a different symbol.', kind='massive_symbol_mismatch')
    if payload.get('adjusted') is not True:
        raise ProviderError(502, 'Massive bars were not marked split-adjusted.', kind='massive_adjustment')
    rows = payload.get('results', [])
    if not isinstance(rows,list) or len(rows)>5000:
        raise ProviderError(502, 'Massive returned an invalid bar collection.', kind='massive_schema')
    out = {k:[] for k in ('t','o','h','l','c','v')}
    prev = 0
    now_ms = int(time.time()*1000)
    for row in rows:
        if not isinstance(row,dict):
            raise ProviderError(502, 'Massive returned malformed bar data.', kind='massive_schema')
        try:
            stamp = row['t']
            if isinstance(stamp,bool) or not isinstance(stamp,int): raise ValueError()
            t_sec = stamp // 1000
            if stamp < 946684800000 or stamp > now_ms+60000 or not start-86400<=t_sec<=end+86400 or stamp<=prev:
                raise ValueError()
            op,hi,lo,close,vol = (row[k] for k in ('o','h','l','c','v'))
            if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)
                   for v in (op,hi,lo,close,vol)):
                raise ValueError()
            if not (0<lo<=op<=hi<=1e9 and lo<=close<=hi and 0<=vol<=1e13):
                raise ValueError()
        except (KeyError,ValueError,TypeError,OverflowError):
            raise ProviderError(502, 'Massive supplied inconsistent OHLC/volume/timestamp data.',
                                kind='massive_invalid_bar')
        prev = stamp
        for k,value in [('t',t_sec),('o',op),('h',hi),('l',lo),('c',close),('v',vol)]:
            out[k].append(value)
    return out



def store_massive_daily_bars(symbol, candles):
    '''Persist only validated, genuine split-adjusted Massive bars in SQLite.'''
    if not candles.get('t'):
        return
    stamp = int(time.time())
    rows = [(symbol,int(candles['t'][i])*1000,float(candles['o'][i]),float(candles['h'][i]),
             float(candles['l'][i]),float(candles['c'][i]),float(candles['v'][i]),stamp)
            for i in range(len(candles['t']))]
    with LOCK, contextlib.closing(db_connection()) as con, con:
        con.executemany('''INSERT OR REPLACE INTO massive_daily_bars
            (symbol,ts_ms,o,h,l,c,v,fetched_at) VALUES (?,?,?,?,?,?,?,?)''', rows)
        con.execute('''DELETE FROM massive_daily_bars WHERE symbol=? AND ts_ms NOT IN
            (SELECT ts_ms FROM massive_daily_bars WHERE symbol=? ORDER BY ts_ms DESC LIMIT 550)''',
            (symbol,symbol))
        price_alerts.observe_sessions(con,symbol,int(time.time()*1000))


def read_massive_daily_bars(symbol, start, end):
    '''Return previously downloaded EOD bars with their download timestamp.'''
    try:
        with contextlib.closing(db_connection()) as con:
            rows=con.execute('''SELECT ts_ms,o,h,l,c,v,fetched_at FROM massive_daily_bars
                WHERE symbol=? AND ts_ms>=? AND ts_ms<=? ORDER BY ts_ms''',
                (symbol,(start-86400)*1000,(end+86400)*1000)).fetchall()
    except (sqlite3.Error,OSError):
        return None
    if not rows:
        return None
    # Grouped bars and ticker daily bars may label the same New York date
    # at different times. Prefer the ticker's midnight session label, then
    # the most recent fetch, and preserve the chosen provider timestamp.
    by_session={}
    for row in rows:
        t,*_,fetched=row
        if not isinstance(t,(int,float)) or not math.isfinite(t) or t!=int(t) or not 946684800000<=t<=int(time.time()*1000)+60000:return None
        if not isinstance(fetched,(int,float)) or not math.isfinite(fetched) or fetched<0:return None
        label=dt.datetime.fromtimestamp(t/1000,ZoneInfo("America/New_York"))
        key=label.date()
        rank=(label.time()==dt.time(),fetched,t)
        if key not in by_session or rank>by_session[key][0]:by_session[key]=(rank,row)
    rows=[by_session[key][1] for key in sorted(by_session)]
    bars={k:[] for k in ('t','o','h','l','c','v')}
    for t,o,h,l,c,v,fetched in rows:
        for key,value in (('t',t//1000),('o',o),('h',h),('l',l),('c',c),('v',v)):
            bars[key].append(value)
    if not valid_provider_candles({'s':'ok',**bars}):return None
    return {'bars':bars,'fetched_at':max(r[6] for r in rows),
            'first_ms':rows[0][0],'last_ms':rows[-1][0]}


def cached_massive_adequate(snapshot, start, end):
    '''Avoid treating a short diagnostic query as a complete annual history.'''
    if not snapshot:
        return False
    requested_days=(end-start)/86400
    covered_days=(snapshot['last_ms']-snapshot['first_ms'])/86400000
    return (covered_days>=max(4,requested_days*.72) and
            snapshot['last_ms']>=end*1000-10*86400000 and
            len(snapshot['bars']['t'])>=max(3,int(requested_days*.48)))

def massive_daily_candles(symbol, start, end, bypass_cache=False):
    # NY date boundaries matter: Stocks Basic cannot request today's US date,
    # even after the stock-market close; no first-trading-day data until midnight ET.
    oldest, newest = massive_free_date_window()
    from_day = max(dt.datetime.fromtimestamp(start, tz=dt.timezone.utc).date(), oldest)
    to_day = min(dt.datetime.fromtimestamp(end, tz=dt.timezone.utc).date(), newest)
    if from_day > to_day:
        return {'status':'no_data','candles':None,'provider':'massive',
                'source':'Massive Stocks Basic · end-of-day',
                'message':'This date range is outside the conservative Stocks Basic historical window (%s to %s New York dates). No current-day data is available on Basic.' % (oldest, newest)}
    # 'adjusted=true' normalises splits, preventing phantom price changes.
    endpoint = 'v2/aggs/ticker/%s/range/1/day/%s/%s' % (urllib.parse.quote(symbol, safe=''), from_day, to_day)
    local = read_massive_daily_bars(symbol,start,end)
    if not bypass_cache and cached_massive_adequate(local,start,end) and time.time()-local['fetched_at'] < 21600:
        return {'status':'ok','candles':local['bars'],'source':'Massive · local verified EOD cache',
                'provider':'massive','adjusted':True,'cached':True,
                'as_of_ms':local['last_ms'],
                'notice':'Locally cached genuine Massive split-adjusted daily bars; not a live feed. Free Basic excludes the current New York date.'}
    try:
        result, cached = massive_request(endpoint, {'adjusted':'true','sort':'asc','limit':5000},
                                          ttl=21600, bypass_cache=bypass_cache)
        candles = normalized_massive_candles(result, symbol, start, end)
    except ProviderError as error:
        if not bypass_cache and cached_massive_adequate(local,start,end):
            return {'status':'ok','candles':local['bars'],
                    'source':'Massive · stored verified daily bars (refresh unavailable)',
                    'provider':'massive','adjusted':True,'cached':True,
                    'refresh_error':error.message,'as_of_ms':local['last_ms'],
                    'notice':'Using previously downloaded historical bars. Refresh failed: '+error.message}
        raise
    if not candles['t']:
        return {'status':'no_data','candles':None,'source':'Massive Stocks Basic · end-of-day',
                'message':'Massive returned no daily bars for this US stock and range. No prices were invented.'}
    store_massive_daily_bars(symbol,candles)
    return {'status':'ok','candles':candles, 'source':'Massive · split-adjusted US daily closes (EOD)',
            'provider':'massive','adjusted':True,'cached':cached,
            'as_of_ms':int(candles['t'][-1])*1000,
            'notice':'End-of-day historical bars, through '+str(newest)+' New York date at latest; Finnhub supplies separate live quotes and trades.'}


def diagnose_massive():
    """Explicit, uncached single-provider validation on a small recent range."""
    if not get_massive_key():
        return {'ok':False,'kind':'massive_no_token','message':'Save your Massive API key first.'}
    today = dt.datetime.now(dt.timezone.utc)
    start = int((today - dt.timedelta(days=21)).timestamp())
    end = int(today.timestamp())  # massive_daily_candles safely clips to previous NY date
    began = time.monotonic()
    try:
        check = massive_daily_candles('AAPL', start, end, bypass_cache=True)
        if check['status']=='ok':
            return {'ok':True,'kind':'daily_bars_received','provider':'Massive','symbol':'AAPL',
                    'count':len(check['candles']['t']), 'latency_ms':int((time.monotonic()-began)*1000),
                    'latest_bar_time_ms':check['as_of_ms'], 'entitlement_through':str(massive_free_date_window()[1]),
                    'message':'Massive returned genuine split-adjusted daily bars. Free Stocks Basic excludes the current New York date; these are end-of-day historical prices, not real-time ticks.'}
        return {'ok':False,'kind':'massive_no_data','message':check['message']}
    except ProviderError as exc:
        return {'ok':False,'kind':exc.kind,'message':exc.message,'retry_after':exc.retry_after, 'http_code':exc.status}

def valid_provider_quote(result):
    if not isinstance(result, dict):
        return False
    c, stamp = result.get('c'), result.get('t')
    return (isinstance(c,(int,float)) and not isinstance(c,bool) and
            isinstance(stamp,(int,float)) and not isinstance(stamp,bool) and
            math.isfinite(c) and 0 < c <= 1e9 and math.isfinite(stamp) and
            stamp == int(stamp) and 946684800 < stamp <= int(time.time()) + 60)


def valid_provider_candles(candles):
    """Check Finnhub OHLC arrays before the UI can present them as history."""
    if not isinstance(candles,dict) or candles.get('s')!='ok': return False
    keys=('t','c','o','h','l','v')
    arrays=[candles.get(k) for k in keys]
    if any(not isinstance(a,list) for a in arrays):return False
    length=len(arrays[0]);now=int(time.time())
    if not (1<=length<=15000) or any(len(a)!=length for a in arrays):return False
    last=0
    for stamp,close,op,high,low,volume in zip(*arrays):
        if (not all(isinstance(x,(int,float)) and not isinstance(x,bool) and
                    math.isfinite(x) for x in (stamp,close,op,high,low,volume))):return False
        if not (946684800<stamp<=now+60 and stamp>last and stamp==int(stamp) and
                0<low<=op<=high<=1e9 and low<=close<=high and 0<=volume<=1e13):return False
        last=stamp
    return True


def normalise_workspace(raw):
    """Only bounded user preferences and research may enter persistent storage."""
    if not isinstance(raw,dict):
        raise ValueError('Invalid workspace data.')
    watch=[]
    watch_values=raw.get('watch',[])
    if not isinstance(watch_values,list): watch_values=[]
    for value in watch_values:
        if len(watch)>=60: break
        try:
            symbol=valid_symbol(value)
            if symbol not in watch: watch.append(symbol)
        except ValueError: continue
    names={}
    raw_names=raw.get('names')
    if not isinstance(raw_names,dict): raw_names={}
    for symbol, name in list(raw_names.items())[:100]:
        try: sym=valid_symbol(symbol)
        except ValueError: continue
        if isinstance(name,str): names[sym]=name[:110]
    notes=[]
    raw_notes=raw.get('notes')
    if not isinstance(raw_notes,list): raw_notes=[]
    for n in raw_notes[:250]:
        if not isinstance(n,dict): continue
        notes.append({k:str(n.get(k,''))[:lim] for k,lim in
                      (('title',180),('thesis',8000),('risk',8000),('evidence',8000),('date',90))})
    reports=[]
    active_reports=0
    deleted_reports=0
    raw_reports=raw.get('reports',[])
    if not isinstance(raw_reports,list): raw_reports=[]
    report_fields={'id':80,'symbol':24,'title':150,'status':30,'summary':5000,'business':6000,
                   'financial':6000,'valuation':6000,'catalysts':5000,'risks':6000,
                   'sources':6000,'created':50,'updated':50}
    for item in raw_reports[:120]:
        if not isinstance(item,dict): continue
        report={k:str(item.get(k,''))[:size] for k,size in report_fields.items()}
        try: report['symbol']=valid_symbol(report['symbol'])
        except ValueError: continue
        if report['status'] not in ('Draft','In review','Completed'): report['status']='Draft'
        raw_checks=item.get('checks') if isinstance(item.get('checks'),dict) else {}
        report['checks']={k:bool(raw_checks.get(k,False)) for k in ('primary','counter','periods')}
        report['deleted']=item.get('deleted') is True
        if report['deleted']:
            if deleted_reports>=80: continue
            deleted_reports+=1
        else:
            if active_reports>=40: continue
            active_reports+=1
        reports.append(report)
    # Paper trades are only user-recorded simulation inputs; never real executions.
    initial=raw.get('portfolio',{})
    if not isinstance(initial,dict): initial={}
    cap=initial.get('capital',10000)
    if not isinstance(cap,(int,float)) or isinstance(cap,bool) or not math.isfinite(cap) or not (1<=cap<=1e9): cap=10000
    paper=[]
    candidates=initial.get('trades',[])
    if not isinstance(candidates,list): candidates=[]
    for t in candidates[:250]:
        if not isinstance(t,dict): continue
        try:
            sym=valid_symbol(t.get('symbol',''))
            side=t.get('side')
            qty=t.get('qty');price=t.get('price')
            if side not in ('BUY','SELL') or not all(isinstance(n,(int,float)) and not isinstance(n,bool) and math.isfinite(n) for n in (qty,price)) or not (.000001<=qty<=1e8 and .000001<=price<=1e9): continue
            day=str(t.get('date',''))[:40]
            paper.append({'symbol':sym,'side':side,'qty':qty,'price':price,'date':day})
        except ValueError: continue
    portfolio={'capital':cap,'trades':paper}
    pref=raw.get('preferences')
    if not isinstance(pref,dict): pref={}
    preferences={}
    allowed={'edition':('signal','professional'),'density':('balanced','compact','terminal'),
             'colour':('blue','brass','cyan','mint','violet'),'chartHeight':('standard','large','xl'),
             'contrast':('normal','high')}
    for key,choices in allowed.items():
        if pref.get(key) in choices: preferences[key]=pref[key]
    for key in ('ticker','motion'):
        if isinstance(pref.get(key),bool): preferences[key]=pref[key]
    design_raw=raw.get('design',{})
    design={}
    if isinstance(design_raw,dict):
        choices={'theme':('dark','light','system'),'accent':('blue','cyan','violet','mint','brass'),'roundness':('soft','extra','compact'),'density':('airy','compact','terminal'),'style':('soft','glide','depth'),'speed':('relaxed','balanced','snappy'),'atmosphere':('glow','glass','none'),'shell':('focus','sidebar')}
        for key,values in choices.items():
            if design_raw.get(key) in values: design[key]=design_raw[key]
        for key in ('enabled','pointer','hover','reveal','chart'):
            if isinstance(design_raw.get(key),bool): design[key]=design_raw[key]
        strength=design_raw.get('intensity')
        if isinstance(strength,(int,float)) and not isinstance(strength,bool) and math.isfinite(strength): design['intensity']=max(0,min(100,round(strength/5)*5))
    tape=raw.get('tapeSymbol','')
    try: tape=valid_symbol(tape)
    except ValueError: tape=''
    return {'analystDrafts':draft35.normalise(raw.get('analystDrafts',{})),'watch':watch,'names':names,'notes':notes,'reports':reports,'portfolio':portfolio,'preferences':preferences,'design':design,'v3':workspace3.normalise(raw.get('v3',{})),'tapeSymbol':tape,'journal':journal49.normalise(raw.get('journal',[]))}


def _workspace_record(path):
    if path.stat().st_size>2500000:raise ValueError('Workspace exceeds the safe size limit.')
    raw=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(raw,dict) or not isinstance(raw.get('snapshot'),dict):raise ValueError('Invalid workspace record.')
    stamp=raw.get('updated_at',0)
    if isinstance(stamp,bool) or not isinstance(stamp,(int,float)) or not math.isfinite(stamp) or stamp<0:raise ValueError('Invalid backup timestamp.')
    return {'snapshot':normalise_workspace(raw['snapshot']),'updated_at':int(stamp)}


def read_workspace():
    # Keep one known-good generation; corrupt files are never deleted on read.
    with LOCK:
        for path,recovered in ((WORKSPACE_FILE,False),(WORKSPACE_FILE.with_suffix('.previous.json'),True)):
            try:
                result=_workspace_record(path)
                return {**result,'recovered':recovered,'warning':'The latest backup could not be read. A previous valid backup was recovered; review your recent changes and export a backup.' if recovered else ''}
            except (OSError,ValueError,TypeError,AttributeError,OverflowError):pass
        return {'snapshot':None,'updated_at':0,'recovered':False,'warning':'The local workspace backup could not be read. Existing browser records have not been removed.' if WORKSPACE_FILE.exists() else ''}


def _atomic_private_file(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp')
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path);os.chmod(path,0o600)
    finally:tmp.unlink(missing_ok=True)


def write_workspace(snapshot):
    clean=normalise_workspace(snapshot)
    USER_DIR.mkdir(parents=True,exist_ok=True,mode=0o700)
    stamp=int(time.time()*1000)
    data=json.dumps({'updated_at':stamp,'snapshot':clean},ensure_ascii=False,allow_nan=False).encode('utf-8')
    if len(data)>2500000:raise ValueError('Workspace is too large to back up safely.')
    with LOCK:
        if WORKSPACE_FILE.exists():
            if WORKSPACE_FILE.stat().st_size>2500000:raise ValueError('The existing backup is too large. Preserve it and review it before replacing it.')
            try:_workspace_record(WORKSPACE_FILE);valid=True
            except (ValueError,TypeError,AttributeError,OverflowError,UnicodeError):valid=False
            # Save the old generation before committing the new one. If a disk
            # write fails, the old primary remains readable. Keep damaged evidence.
            target=WORKSPACE_FILE.with_suffix('.previous.json' if valid else '.damaged.json')
            _atomic_private_file(target,WORKSPACE_FILE.read_bytes())
        _atomic_private_file(WORKSPACE_FILE,data)
    return stamp


def local_health():
    checks=[]
    def add(name,okay,detail): checks.append({'name':name,'ok':bool(okay),'detail':detail})
    add('Saved data folder',USER_DIR.is_dir(),'Saved data folder is available' if USER_DIR.is_dir() else 'Missing storage folder')
    try:
        with contextlib.closing(db_connection()) as con:
            status=con.execute('PRAGMA quick_check').fetchone()[0]
            count=con.execute('SELECT COUNT(*) FROM observations').fetchone()[0]
            trades=con.execute("SELECT COUNT(*) FROM tape_events WHERE kind='trade'").fetchone()[0]
            eod=con.execute('SELECT COUNT(*) FROM massive_daily_bars').fetchone()[0]
            alerts=con.execute('SELECT COUNT(*) FROM price_alerts').fetchone()[0]
            events=con.execute('SELECT COUNT(*) FROM price_alert_events').fetchone()[0]
        add('Market data database',status=='ok',f'SQLite check: {status}; {count} observations, {trades} stored trades, {eod} verified Massive EOD bars; {alerts} saved alerts, {events} trigger records')
    except (sqlite3.Error,OSError) as exc:
        add('Market data database',False,'SQLite could not be read: '+type(exc).__name__)
    assets=['workbench40.js','crypto38.js','crypto57.js','stress58.js','pack59.js','workspace60.js','annotate60.js','overview60.js','desk61.js','showcase61.js','earnings62.js','tracker65.js','practice67.js','desk68.js','desk61.css','crypto38.css','truth36.js','truth36.css','research35.js','research35.css','analyst34.js','analyst34.css','briefing33.js','briefing33.css','projects32.js','projects32.css','v3.js','v3.css','financial-health.js','financial-health.css','events42.js','v43.js','v43.css','chart43.js','replay43.js','shell43.js','shell43.css','look43.js','look43.css','smoke431.js','move44.js','design.js','design.css','desk.js','desk.css','heatmap.js','heatmap.css','motion.css','screener.js','screener.css','navigation.js','sidebar.css','ai-research.js','ai-research.css','modern.css','alerts.js','alerts.css','stock-directory.css','intelligence.js','ask48.js','journal49.js','desk50.js','overnight51.js','compare52.js','scenario53.js','strategy54.js','scanner55.js','intelligence.css','index.html','app.js','compare.js','reports.js','macro.js','research-v17.css','research-v18.css','v19.css','v19-models.js','v19.js','tape.js','terminal.js','pro.js','styles.css','signal.css','tape.css','terminal.css','pro.css','market-hours.js','chart-research.js','brand-mark.svg','favicon.svg','apple-touch-icon.png']
    missing=[name for name in assets if not (SITE/name).is_file()]
    add('Website files',not missing,('All %s essential assets present'%len(assets)) if not missing else 'Missing: '+', '.join(missing))
    add('Finnhub key permissions',not KEY_FILE.exists() or (KEY_FILE.stat().st_mode & 0o077)==0,
        'Saved in a private file' if KEY_FILE.exists() else 'No key saved')
    add('Massive key permissions',not MASSIVE_KEY_FILE.exists() or (MASSIVE_KEY_FILE.stat().st_mode & 0o077)==0,
        'Saved in a private file' if MASSIVE_KEY_FILE.exists() else 'Price history is not set up')
    workspace=read_workspace()
    add('Workspace backup integrity',not workspace['warning'],workspace['warning'] or ('Valid local backup; previous generation retained when available' if workspace['snapshot'] is not None else 'No workspace backup yet'))
    add('Workspace backup permissions',not WORKSPACE_FILE.exists() or (WORKSPACE_FILE.stat().st_mode & 0o077)==0,
        'Private backup available' if WORKSPACE_FILE.exists() else 'No workspace backup yet')
    return {'ok':all(c['ok'] for c in checks),'checks':checks,
            'notice':'Checks saved files and prices on this Mac only. It does not test your Finnhub plan or confirm that live trades are arriving.'}

def diagnose_finnhub():
    """Fresh request, not a cached success or a WebSocket connection check."""
    _, trust_source = verified_tls_context()
    common = {'provider': 'Finnhub', 'symbol': 'AAPL', 'tls_trust': trust_source,
              'checked_at': int(time.time()*1000), 'live_trade_verified': False}
    if not get_key():
        return dict(common, ok=False, kind='no_token',
                    message='Save your Finnhub API key first.')
    started = time.monotonic()
    try:
        data, _ = provider_get('quote', {'symbol':'AAPL'}, ttl=10, bypass_cache=True)
        latency = int((time.monotonic()-started)*1000)
        if valid_provider_quote(data):
            return dict(common, ok=True, kind='quote_received', latency_ms=latency,
                        quote_time_ms=int(data['t'])*1000,
                        message='Finnhub returned a valid AAPL quote. This is a snapshot, not a verified streaming tick.')
        return dict(common, ok=False, kind='quote_no_data', latency_ms=latency,
                    message='Finnhub responded, but did not provide a valid price and timestamp for AAPL.')
    except ProviderError as exc:
        return dict(common, ok=False, kind=exc.kind, message=exc.message,
                    retry_after=exc.retry_after,
                    latency_ms=int((time.monotonic()-started)*1000))

# v1.8 Economics & Intelligence — public World Bank annual data; no personal API key.
# Each series retains the observation YEAR because macro releases lag and may be revised.
WORLD_BANK_INDICATORS = {
    'NY.GDP.MKTP.KD.ZG': ('Real GDP growth', '% year on year'),
    'FP.CPI.TOTL.ZG': ('Consumer price inflation', '% year on year'),
    'SL.UEM.TOTL.ZS': ('Unemployment, ILO modelled', '% labour force'),
    'NE.EXP.GNFS.ZS': ('Exports, goods and services', '% of GDP'),
    'FR.INR.LEND': ('Lending interest rate', '% per year (NOT central-bank policy rate)'),
}
WORLD_BANK_CACHE = {'when': 0.0, 'result': None, 'failure_when': 0.0, 'failure': ''}
WORLD_BANK_LOCK = threading.RLock()

def normalise_world_bank(payload):
    if not isinstance(payload, list) or len(payload) != 2 or not isinstance(payload[1], list):
        raise ProviderError(502, 'World Bank returned an unexpected data format.')
    result = {country: {code: [] for code in WORLD_BANK_INDICATORS} for country in ('GB', 'US')}
    for item in payload[1][:2000]:
        if not isinstance(item, dict):
            continue
        code = (item.get('indicator') or {}).get('id') if isinstance(item.get('indicator'), dict) else None
        iso = item.get('countryiso3code')
        if not iso and isinstance(item.get('country'), dict):
            iso = item['country'].get('id')
        country = {'GBR': 'GB', 'USA': 'US', 'GB': 'GB', 'US': 'US'}.get(iso)
        try:
            year = int(item.get('date', ''))
            raw = item.get('value')
            number = float(raw) if raw is not None and not isinstance(raw, bool) else None
        except (TypeError, ValueError):
            continue
        if (country and code in WORLD_BANK_INDICATORS and 1960 <= year <= dt.datetime.now(dt.timezone.utc).year
                and number is not None and math.isfinite(number) and abs(number) < 1e10):
            result[country][code].append({'year': year, 'value': round(number, 6)})
    for series in result.values():
        for code in series:
            uniq = {item['year']: item for item in series[code]}
            series[code] = sorted(uniq.values(), key=lambda item: item['year'])[-13:]
    if sum(len(rows) for group in result.values() for rows in group.values()) < 3:
        raise ProviderError(502, 'World Bank did not return enough usable observations. No macro values were substituted.')
    return result

def world_bank_macro(refresh=False):
    now = time.time()
    with WORLD_BANK_LOCK:
        cached = WORLD_BANK_CACHE['result']
        if cached is not None and (not refresh or now-WORLD_BANK_CACHE['when'] < 300) and now-WORLD_BANK_CACHE['when'] < 12*3600:
            return {**cached, 'cached': True, 'cache_age_s': int(now-WORLD_BANK_CACHE['when'])}
        if WORLD_BANK_CACHE['failure_when'] and now-WORLD_BANK_CACHE['failure_when'] < 90:
            if cached is not None:
                return {**cached, 'cached': True, 'stale': True, 'warning': 'Provider refresh unavailable; showing previously retrieved annual figures.'}
            return {'status': 'unavailable', 'error': WORLD_BANK_CACHE['failure'], 'source': 'World Bank WDI annual indicators'}
    codes = ';'.join(WORLD_BANK_INDICATORS)
    path = 'https://api.worldbank.org/v2/country/GB;US/indicator/' + codes
    query = urllib.parse.urlencode({'source': 2, 'format': 'json', 'date': '2013:'+str(dt.datetime.now(dt.timezone.utc).year), 'per_page': 1000})
    try:
        request = urllib.request.Request(path + '?' + query, headers={'User-Agent': 'MarketDeskResearch/1.8', 'Accept': 'application/json'})
        tls_context, _ = verified_tls_context()
        with urllib.request.urlopen(request, timeout=9, context=tls_context) as response:
            if response.status != 200:
                raise ProviderError(502, 'World Bank data request returned HTTP '+str(response.status))
            data = response.read(1_000_001)
            if len(data) > 1_000_000:
                raise ProviderError(502, 'World Bank response was too large.')
        series = normalise_world_bank(json.loads(data.decode('utf-8')))
        result = {'status': 'ok', 'series': series, 'indicators': {k: {'label': v[0], 'unit': v[1]} for k,v in WORLD_BANK_INDICATORS.items()},
                  'source': 'World Bank · World Development Indicators (annual, often delayed/revised)',
                  'url': 'https://data.worldbank.org/', 'fetched_at': int(time.time()*1000), 'cached': False,
                  'notice': 'Years are observation years, not publication times. Lending rates are NOT central-bank policy rates. Do not infer immediate market causation.'}
        with WORLD_BANK_LOCK:
            WORLD_BANK_CACHE.update(when=time.time(), result=result, failure_when=0.0, failure='')
        return result
    except Exception as exc:
        message = 'World Bank macro data unavailable: '+(exc.message if isinstance(exc, ProviderError) else type(exc).__name__)
        with WORLD_BANK_LOCK:
            WORLD_BANK_CACHE['failure_when'] = time.time()
            WORLD_BANK_CACHE['failure'] = message
            cached = WORLD_BANK_CACHE['result']
        if cached is not None:
            return {**cached, 'cached': True, 'stale': True, 'warning': message + '; showing earlier verified values.'}
        return {'status': 'unavailable', 'source': 'World Bank · World Development Indicators', 'error': message}


def ai_cache(endpoint,sym):
    with LOCK:
        matches=[(CACHE_FETCHED_AT.get(key,0),value[1]) for key,value in CACHE.items() if key[0]==endpoint and ('symbol',sym) in key[1]]
    kind={'stock/profile2':'profile','stock/metric':'metrics'}.get(endpoint)
    if kind:
        try:
            with LOCK,contextlib.closing(db_connection()) as con:
                saved=screening.snapshot(con,sym,kind)
                if saved[0] is not None:matches.append(saved)
        except (sqlite3.Error,ValueError,TypeError):pass
    return max(matches,key=lambda row:row[0]) if matches else (None,None)


SCREEN_REFRESH_LOCK=threading.Lock()

def screen_source_time(endpoint,params,data,cached):
    key=(endpoint,tuple(sorted((k,str(v)) for k,v in params.items())))
    with LOCK:
        item=CACHE.get(key)
        if item and item[1] is data:return CACHE_FETCHED_AT.get(key)
    return None if cached else int(time.time()*1000)

def screen_capture(symbol,kind,data,stamp):
    try:
        with LOCK,contextlib.closing(db_connection()) as con,con:
            return screening.remember(con,symbol,kind,data,stamp,int(time.time()*1000))
    except (sqlite3.Error,ValueError,TypeError):return False

def screen_data(symbols):
    if not isinstance(symbols,list) or len(symbols)>60:raise ValueError('Use up to 60 watchlist symbols.')
    symbols=list(dict.fromkeys(valid_symbol(x) for x in symbols))
    catalog=json.loads((ROOT/'ai_catalog.json').read_text())
    with LOCK,contextlib.closing(db_connection()) as con:
        return screening.rows(con,catalog,symbols,int(time.time()*1000))

def screen_refresh(obj):
    if not isinstance(obj,dict):raise ValueError('Invalid refresh request.')
    symbol=valid_symbol(obj.get('symbol',''))
    if not SCREEN_REFRESH_LOCK.acquire(blocking=False):raise ValueError('A stock refresh is already running. Wait for it to finish.')
    notes=[];stop=False
    try:
        for path in ('/api/quote','/api/company'):
            try:
                data=handle_api(path,{'symbol':[symbol]})
                if path=='/api/quote':
                    item=data['items'][0]
                    if item['status']!='ok':
                        notes.append(item.get('error') or 'Quote unavailable.');stop=item.get('code') in (401,403,429) or item.get('kind') in ('no_token','network_cooldown','skipped_due_to_provider_failure','dns','timeout','tls_certificate','connection_refused','network','tls_other')
                        if stop:break
                elif data.get('metrics_error'):
                    notes.append(data['metrics_error']);stop=True;break
                elif not screening.sanitize(symbol,'metrics',data.get('metrics'),int(time.time()*1000)):
                    notes.append('No usable financial filter figures returned. Earlier saved snapshots, if any, keep their original dates.')
            except ProviderError as exc:
                notes.append(exc.message);stop=exc.status in (401,403,429) or exc.kind in ('no_token','network_cooldown','dns','timeout','tls_certificate','connection_refused','network','tls_other')
                if stop:break
        return {'symbol':symbol,'warnings':notes,'stop':stop,'notice':'Requests complete. Review source dates; cached data may be reused. No missing value was guessed.'}
    finally:SCREEN_REFRESH_LOCK.release()


DESK_REFRESH_LOCK=threading.Lock()

def desk_snapshot(symbols):
    if not isinstance(symbols,list) or len(symbols)>60:raise ValueError('Use up to 60 watchlist symbols.')
    symbols=list(dict.fromkeys(valid_symbol(x) for x in symbols))
    now=int(time.time()*1000)
    result=screen_data(symbols)
    wanted=set(symbols)
    result['rows']=[x for x in result['rows'] if x['symbol'] in wanted]
    with LOCK,contextlib.closing(db_connection()) as con:
        result.update(desk.snapshot(con,symbols,now))
        result['profiles']={sym:{'fetchedAt':stamp,'data':data} for sym in symbols for stamp,data in [screening.snapshot(con,sym,'profile')]}
    return result

def desk_refresh(obj):
    if not isinstance(obj,dict):raise ValueError('Use a refresh object.')
    mode=obj.get('mode')
    symbols=obj.get('symbols',[])
    if mode not in ('briefing','company') or not isinstance(symbols,list) or not 1<=len(symbols)<=8:
        raise ValueError('Choose briefing or company, with 1–8 stocks.')
    symbols=list(dict.fromkeys(valid_symbol(x) for x in symbols))
    if mode=='company' and len(symbols)!=1:raise ValueError('Choose one company.')
    if not DESK_REFRESH_LOCK.acquire(blocking=False):raise ValueError('A desk refresh is already running.')
    warnings=[];completed=[]
    try:
        # Existing quote handler validates timestamps/prices, persists snapshots,
        # and stops a batch on rate-limit/network failures.
        result=handle_api('/api/quotes',{'symbols':[','.join(symbols)]})
        failures=[x for x in result['items'] if x.get('status')!='ok']
        completed=[x['symbol'] for x in result['items'] if x.get('status')=='ok']
        warnings.extend(x.get('error') or 'A quote was unavailable.' for x in failures)
        stop=any(x.get('code') in (401,403,429) or x.get('status')=='skipped' or x.get('kind') in ('no_token','local_budget','rate_limit','network_cooldown','dns','timeout','tls_certificate','connection_refused','network','tls_other') for x in failures)
        if not stop and mode=='company':
            try:
                raw,cached=provider_get('stock/profile2',{'symbol':symbols[0]},ttl=86400)
                screen_capture(symbols[0],'profile',raw,screen_source_time('stock/profile2',{'symbol':symbols[0]},raw,cached))
            except ProviderError as exc:
                warnings.append(exc.message);stop=True
        if not stop:
            try:handle_api('/api/news',{'symbol':[symbols[0]]} if mode=='company' else {})
            except ProviderError as exc:warnings.append(exc.message)
        return {'ok':not warnings,'completed':completed,'quotes':result['items'],'warnings':warnings,
                'notice':'Quotes and news can have different source times. A refresh does not guarantee current or complete coverage.'}
    finally:DESK_REFRESH_LOCK.release()


def ai_catalog_entry(sym):
    try:
        rows=json.loads((ROOT/'ai_catalog.json').read_text())
        return next((x for x in rows if x.get('symbol')==sym),None)
    except (OSError,ValueError,TypeError):return None


def ai_evidence(sym,question):
    now=int(time.time()*1000);sources=[]
    def add(ident,title,kind,body,url='',stamp=None,notice=''):
        sources.append({'id':ident,'title':title,'kind':kind,'body':body,'url':url,'retrievedAt':stamp,'notice':notice})
    entry=ai_catalog_entry(sym)
    if entry:
        add('C0','Local listing reference','directory reference',f"Stock symbol {sym}. Listed name {entry['name']}. Exchange {entry['exchange']}. Listing price currency {entry['currency']}. Browsing group {entry['category']} is editorial, not an official industry classification. Listing reference checked on {entry.get('checkedAt','2026-11-03')}.", 'https://www.nasdaqtrader.com/Trader.aspx?id=symbollookup',notice='Dated directory metadata, not a fresh company filing.')
    if sym=='TTWO':
        add('C2','Take-Two company reference','directory reference','Take-Two Interactive is the publicly listed parent of Rockstar Games. Its Nasdaq symbol is TTWO. Rockstar Games is not a separate listed stock. This reference was checked on 3 November 2026.','https://www.take2games.com/ir',notice='Reference relationship, not a new web request.')
    sources.extend(analyst34.evidence_packet(((read_workspace().get('snapshot') or {}).get('v3') or {}).get('analyst',{}),sym))
    sources.extend(statements3.evidence(sec_saved(sym)))
    observed=get_history(sym,0,5000)
    cleaned=intelligence.clean(observed,now,intelligence.INTRADAY_SOURCES)
    if cleaned:
        last=cleaned[-1];add('Q1','Last locally recorded price','observed prices',json.dumps({'symbol':sym,'price':last['p'],'providerTimeUTC':dt.datetime.fromtimestamp(last['t']/1000,dt.timezone.utc).isoformat(),'source':last.get('source'),'ageSeconds':int((now-last['t'])/1000),'note':'Recorded observation, not a guarantee of a current price. Currency comes from listing data when available.'}),stamp=now)
    for hours,ident in ((1,'P1'),(24,'P2')):
        d=intelligence.overview(observed,now,hours)
        summary={k:v for k,v in d.items() if k not in ('points','gaps','sources')}
        summary['gapsLongerThanFiveMinutes']=len(d['gaps']);summary['note']='Partial record only. Endpoint change is between available prices, not a full-window market return. Prices alone cannot establish a cause.'
        add(ident,'Past '+str(hours)+' hours: observed coverage','computed chart summary',json.dumps(summary,separators=(',',':')),stamp=now)
    with LOCK,contextlib.closing(db_connection()) as con:
        doc_sources=research_ai.retrieve(con,sym,question)
        rows=con.execute('SELECT ts_ms,c FROM massive_daily_bars WHERE symbol=? ORDER BY ts_ms',(sym,)).fetchall()
    sources.extend(financials.evidence(sec_saved(sym)))
    sources.extend(doc_sources)
    profile_at,profile=ai_cache('stock/profile2',sym);metric_at,metrics=ai_cache('stock/metric',sym)
    if isinstance(profile,dict):
        allowed={k:profile[k] for k in ('name','ticker','exchange','country','currency','finnhubIndustry','ipo','marketCapitalization') if k in profile and (isinstance(profile[k],str) or isinstance(profile[k],(int,float)) and not isinstance(profile[k],bool) and math.isfinite(profile[k]))}
        add('C1','Finnhub company profile','provider profile',json.dumps(allowed,allow_nan=False)+'. Market capitalization is in millions of profile currency. Profile currency may differ from listing currency. Retrieved time is not the financial reporting period.','https://finnhub.io/docs/api/company-profile2',profile_at,'Cached provider response; financial reporting periods may be unknown.')
    if isinstance(metrics,dict) and isinstance(metrics.get('metric'),dict):
        allowed={k:v for k,v in metrics['metric'].items() if k in ('peTTM','peBasicExclExtraTTM','revenueGrowthTTMYoy','netProfitMarginTTM','operatingMarginTTM','roeTTM','52WeekHigh','52WeekLow','52WeekHighDate','52WeekLowDate','dividendYieldIndicatedAnnual') and (isinstance(v,str) or isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v))}
        add('F1','Finnhub financial figures','provider metrics',json.dumps(allowed)+'. TTM means trailing twelve months. Ratios and price ranges have different units. Reporting dates are not guaranteed to match.','https://finnhub.io/docs/api/company-basic-financials',metric_at,'These figures have not been independently audited.')
    model=intelligence.daily_model([{'t':t,'p':p,'source':'massive_daily'} for t,p in rows],now)
    add('M1','Earlier one-close statistical model results','experimental model',json.dumps(model,separators=(',',':')),stamp=now,notice='Earlier one-close price model, not V3.4 five-close factor regression and not the language model. Estimates are not observed prices.')
    news_at,news=ai_cache('company-news',sym)
    if isinstance(news,list):
        news=sorted([x for x in news if isinstance(x,dict)],key=lambda x:x.get('datetime',0) if isinstance(x.get('datetime'),(int,float)) else 0,reverse=True)
        for i,item in enumerate(news[:3]):
            headline=research_ai.clean_text(item.get('headline'),240)
            if not headline:continue
            published=item.get('datetime');date=dt.datetime.fromtimestamp(published,dt.timezone.utc).isoformat() if isinstance(published,(int,float)) and math.isfinite(published) and 0<published<now/1000+86400 else 'Unreported'
            add('N'+str(i+1),'News: '+headline,'publisher report',headline+'\nPublisher: '+research_ai.clean_text(item.get('source'),80)+'\nPublished UTC: '+date+'\nProvider summary: '+research_ai.clean_text(item.get('summary'),260),research_ai.safe_url(item.get('url')),news_at,'Publisher claims, not verified causes of stock-price moves.')
    return research_ai.packet(sym,analyst34.prioritise_sources(sources,question),now,question)


def ai_research_pack(sym,question,other=''):
    primary=ai_evidence(sym,question)
    if not other or other==sym:return primary
    secondary=ai_evidence(other,question)
    priorities={'T1':-7,'T2':-6,'T3':-5,'T4':-4,'S1':-3,'S2':-2,'S3':-1,'C0':0,'C2':1,'C1':2,'F1':3,'D1':4,'N1':5,'Q1':6,'P2':7,'D2':8,'M1':9,'P1':10}
    merged=[]
    for prefix,stock,pack in (('A',sym,primary),('B',other,secondary)):
        chosen=sorted(pack['sources'],key=lambda x:priorities.get(x['id'],12))[:7]
        for source in chosen:
            merged.append({**source,'id':prefix+source['id'],'symbol':stock,'title':stock+' · '+source['title'],'body':'Stock '+stock+'. '+source['body']})
    result=research_ai.packet(sym,merged,int(time.time()*1000),question)
    result.pop('hash',None)
    result['compareSymbol']=other
    result['hash']=hashlib.sha256(json.dumps(result,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return result


def ai_refresh_sources(sym):
    warnings=[]
    for path,label in (('/api/company','Company details'),('/api/news','Company news')):
        try:handle_api(path,{'symbol':[sym]})
        except ProviderError as exc:warnings.append(label+': '+exc.message)
    return {'ok':not warnings,'warnings':warnings,'evidence':ai_evidence(sym,'company financial news research')}


def ai_persist(result):
    with LOCK,contextlib.closing(db_connection()) as con,con:research_ai.save_run(con,result)


def ai_action(path,obj):
    if not isinstance(obj,dict):raise ValueError('Invalid AI request.')
    sym=valid_symbol(obj.get('symbol',''))
    other=valid_symbol(obj['compareSymbol']) if obj.get('compareSymbol') else ''
    if path=='/api/ai/sources':
        first=ai_refresh_sources(sym);warnings=list(first['warnings'])
        if other and other!=sym:warnings.extend(ai_refresh_sources(other)['warnings'])
        return {'ok':not warnings,'warnings':warnings,'evidence':ai_research_pack(sym,'company financial news comparison',other)}
    if path=='/api/ai/documents':
        with LOCK,contextlib.closing(db_connection()) as con,con:
            con.execute('BEGIN IMMEDIATE')
            if obj.get('action')=='delete':
                ident=str(obj.get('id',''))
                if not re.fullmatch('[a-f0-9]{32}',ident):raise ValueError('Invalid source ID.')
                con.execute('DELETE FROM ai_documents WHERE id=? AND symbol=?',(ident,sym))
            elif obj.get('action') in (None,'add'):research_ai.add_document(con,obj,int(time.time()*1000))
            else:raise ValueError('Unknown source action.')
            return {'documents':research_ai.documents(con,sym)}
    if path=='/api/ai/runs':
        ident=str(obj.get('id',''))
        if not re.fullmatch('[a-f0-9]{32}',ident):raise ValueError('Invalid saved draft ID.')
        with LOCK,contextlib.closing(db_connection()) as con,con:
            con.execute('DELETE FROM ai_runs WHERE id=? AND symbol=?',(ident,sym))
            library=research_ai.runs(con,sym)
        with research_ai.JOBS_LOCK:
            if ident in research_ai.JOBS and research_ai.JOBS[ident].get('status')!='running':research_ai.JOBS.pop(ident,None)
        return {'runs':library}
    if path=='/api/ai/ask':
        question=obj.get('question','');mode=obj.get('mode','answer');prior=''
        if not isinstance(question,str) or not 4<=len(question.strip())<=1600:raise ValueError('Enter a question between 4 and 1,600 characters.')
        if mode not in ('answer','report'):raise ValueError('Choose a question or report.')
        if obj.get('followupId'):
            with LOCK,contextlib.closing(db_connection()) as con:
                previous=research_ai.get_run(con,str(obj['followupId']),sym)
                prior=json.dumps({'question':previous['question'],'priorAIDraftNotSourceEvidence':[b['text'] for section in previous['draft']['sections'] for b in section['bullets']][:4]})
        evidence=ai_research_pack(sym,question+' '+prior[:500] if prior else question,other)
        return research_ai.start(str(obj.get('model','')),mode,question,evidence,ai_persist,prior)
    raise ValueError('Unknown AI action.')


def read_alerts():
    with LOCK, contextlib.closing(db_connection()) as con, con:
        con.execute('BEGIN')
        return price_alerts.snapshot(con,int(time.time()*1000))


def change_alerts(obj):
    with LOCK, contextlib.closing(db_connection()) as con, con:
        con.execute('BEGIN IMMEDIATE')
        now=int(time.time()*1000)
        ident=price_alerts.change(con,obj,now)
        return {'ok':True,'id':ident,**price_alerts.snapshot(con,now)}


def sec_saved(symbol):
    with LOCK,contextlib.closing(db_connection()) as con:
        try:return sec_accounts.read(con,valid_symbol(symbol))
        except sec_accounts.SECError:return {'status':'unsupported','symbol':valid_symbol(symbol),'annual':[],'quarterly':[],'notice':'SEC accounts are not supported for this instrument.'}


def sec_refresh(obj):
    if not isinstance(obj,dict):raise ValueError('Invalid SEC update request.')
    return sec_accounts.update(db_connection,valid_symbol(obj.get('symbol','')),tls_context=verified_tls_context()[0])


def handle_api(path, qs):
    if path.startswith('/api/v3/'):return lab3.get(path,qs,globals())
    if path == '/api/financials':
        return sec_saved(qs.get('symbol',['AAPL'])[0])
    if path == '/api/financials/compare':
        symbols=[valid_symbol(x) for x in qs.get('symbols',[''])[0].split(',') if x]
        if not 2<=len(symbols)<=3 or len(set(map(sec_accounts.canonical,symbols)))!=len(symbols):raise ValueError('Choose two or three different companies.')
        reports=[sec_saved(sym) for sym in symbols]
        ciks=[r['cik'] for r in reports if r.get('cik')]
        if len(set(ciks))!=len(ciks):raise ValueError('These listings belong to the same SEC issuer. Choose different companies.')
        return financials.compare(reports)
    if path == '/api/ai/status':
        return research_ai.status()
    if path == '/api/ai/job':
        return research_ai.job(qs.get('id',[''])[0])
    if path == '/api/ai/run':
        with LOCK,contextlib.closing(db_connection()) as con:
            return research_ai.get_run(con,qs.get('id',[''])[0],valid_symbol(qs.get('symbol',[''])[0]))
    if path == '/api/ai/evidence':
        return ai_evidence(valid_symbol(qs.get('symbol',[''])[0]),qs.get('q',['company chart news risks'])[0][:1600])
    if path == '/api/ai/library':
        sym=valid_symbol(qs.get('symbol',[''])[0])
        with LOCK,contextlib.closing(db_connection()) as con:
            return {'documents':research_ai.documents(con,sym),'runs':research_ai.runs(con,sym)}
    if path == '/api/alerts':
        return read_alerts()
    if path == '/api/intelligence':
        sym=valid_symbol(qs.get('symbol',['AAPL'])[0])
        now=int(time.time()*1000)
        observations=get_history(sym,0,5000)
        with LOCK, contextlib.closing(db_connection()) as con:
            rows=con.execute('SELECT ts_ms,c FROM massive_daily_bars WHERE symbol=? ORDER BY ts_ms', (sym,)).fetchall()
        daily=[{'t':t,'p':p,'source':'massive_daily'} for t,p in rows]
        return {'symbol':sym,'asOf':now,'hour':intelligence.overview(observations,now,1),
                'day':intelligence.overview(observations,now,24),'model':intelligence.daily_model(daily,now),
                'financial':{'summary':statements3.summary(sec_saved(sym)),'sources':statements3.evidence(sec_saved(sym))+financials.evidence(sec_saved(sym))},
                'retention':'At most 5000 local observations per symbol; older observations may have been removed.'}
    if path == '/api/desk':
        return desk_snapshot([x for x in qs.get('symbols',[''])[0].split(',') if x.strip()])
    if path == '/api/screener':
        symbols=[x for x in qs.get('symbols',[''])[0].split(',') if x.strip()]
        return screen_data(symbols)
    if path == '/api/macro':
        return world_bank_macro(refresh=(qs.get('refresh',['0'])[0]=='1'))
    if path == '/api/workspace':
        return read_workspace()
    if path == '/api/selftest':
        return local_health()
    if path == '/api/status':
        with LOCK:
            recent = len([t for t in REQUEST_LOG if time.monotonic()-t <= 60])
        return {'version':VERSION, 'configured': bool(get_key()), 'provider':'Finnhub', 'massive_configured':bool(get_massive_key()),
                'historical_provider':'Massive (EOD)' if get_massive_key() else 'Finnhub (subject to plan)',
                'observations':'Local SQLite',
                'api_used_last_60s':recent,'api_budget':48,'server_time':int(time.time()),'backgroundCollector':COLLECTOR is not None,
                'notice':'A connection is not proof of live market ticks. Live status requires verified trade messages.'}
    if path == '/api/diagnose':
        return diagnose_finnhub()
    if path == '/api/massive-diagnose':
        return diagnose_massive()
    if path == '/api/session':
        return {'local_only':True,'configured':bool(get_key())}
    if path == '/api/collector':
        return COLLECTOR.pulse(None,0,'') if COLLECTOR else {'status':{'stream':'Collector is not running in this server'}}
    if path == '/api/saved-quotes':
        symbols=list(dict.fromkeys(valid_symbol(x) for x in qs.get('symbols',[''])[0].split(',') if x))
        if len(symbols)>60:raise ValueError('Use up to 60 saved quotes.')
        with contextlib.closing(db_connection()) as con:
            return {'items':[{'symbol':sym,'quote':data,'receivedAt':stamp,'cached':True}
                             for sym in symbols for stamp,data in [screening.snapshot(con,sym,'quote')]
                             if valid_provider_quote(data)]}
    if path == '/api/quote' or path == '/api/quotes':
        if path == '/api/quote':
            syms = [valid_symbol(qs.get('symbol',['AAPL'])[0])]
        else:
            syms = [valid_symbol(x) for x in qs.get('symbols',[''])[0].split(',') if x.strip()]
        if not syms or len(syms)>12:
            raise ValueError('Request 1–12 symbols at a time.')
        out = []
        for i,sym in enumerate(syms):
            try:
                result, cached = provider_get('quote', {'symbol':sym}, ttl=25)
                if not isinstance(result, dict):
                    raise ProviderError(502,'Invalid quote response.')
                current = result.get('c')
                ts = result.get('t')
                valid = valid_provider_quote(result)
                if valid:
                    store_point(sym, int(ts)*1000, current, 'finnhub_quote')
                    quote_at=screen_source_time('quote',{'symbol':sym},result,cached)
                    screen_capture(sym,'quote',result,quote_at)
                out.append({'symbol':sym, 'quote':result if valid else None, 'cached':cached,
                            'status':'ok' if valid else 'unavailable', 'source':'Finnhub REST quote',
                            'stale': bool(valid and int(time.time()) - int(ts)>900),
                            'error':None if valid else 'No valid positive price and provider timestamp received.'})
            except ProviderError as exc:
                out.append({'symbol':sym,'status':'error','quote':None,'error':exc.message,
                            'code':exc.status,'kind':exc.kind,'retry_after':exc.retry_after})
                if exc.status==429 or exc.kind in ('tls_certificate','dns','timeout','connection_refused','tls_other','network','network_cooldown'):
                    # Report every omitted symbol as skipped; never silently hide unrequested quotes.
                    out.extend({'symbol':other,'status':'skipped','quote':None,
                                'error':'Not requested because the preceding Finnhub request failed or hit a cooldown.',
                                'kind':'skipped_due_to_provider_failure'} for other in syms[i+1:])
                    break
        return {'items':out,'received_at':int(time.time()*1000)}
    if path == '/api/search':
        q = qs.get('q',[''])[0].strip()[:80]
        if len(q)<1: return {'result':[]}
        return provider_get('search', {'q':q}, ttl=900)[0]
    if path == '/api/company':
        sym = valid_symbol(qs.get('symbol',[''])[0])
        profile, profile_cached = provider_get('stock/profile2',{'symbol':sym}, ttl=86400)
        metrics = {}
        metrics_cached = False
        metric_error = None
        try:
            metrics, metrics_cached = provider_get('stock/metric',{'symbol':sym,'metric':'all'},ttl=21600)
        except ProviderError as e:
            metric_error=e.message
        with LOCK:
            profile_at=CACHE_FETCHED_AT.get(('stock/profile2',(('symbol',sym),)))
            metric_at=CACHE_FETCHED_AT.get(('stock/metric',(('metric','all'),('symbol',sym)))) if metric_error is None else None
        screen_capture(sym,'profile',profile,screen_source_time('stock/profile2',{'symbol':sym},profile,profile_cached))
        if metric_error is None:screen_capture(sym,'metrics',metrics,screen_source_time('stock/metric',{'symbol':sym,'metric':'all'},metrics,metrics_cached))
        available=[stamp for stamp in (profile_at,metric_at) if isinstance(stamp,int)]
        return {'symbol':sym,'profile':profile,'metrics':metrics,'metrics_error':metric_error,
                'retrieved_at':min(available) if available else None,
                'profile_fetched_at':profile_at,'metrics_fetched_at':metric_at,
                'profile_cached':profile_cached,'metrics_cached':metrics_cached,
                'provenance_notice':'Source retrieval time refers to when the local server fetched provider data; financial reporting periods may be older.'}
    if path == '/api/saved-news':
        scope=valid_symbol(qs['symbol'][0]) if qs.get('symbol') else 'general'
        with contextlib.closing(db_connection()) as con:
            data=desk.read_news(con,[scope],int(time.time()*1000))[scope]
        return {'items':data['items'],'fetched_at':data['fetchedAt'],'cached':True}
    if path == '/api/news':
        sym = qs.get('symbol',[''])[0].strip()
        if sym:
            sym=valid_symbol(sym)
            today=dt.datetime.now(dt.timezone.utc).date()
            from_day=today-dt.timedelta(days=7)
            params={'symbol':sym,'from':str(from_day),'to':str(today)}
            news, news_cached = provider_get('company-news',params,ttl=420)
            news_path='company-news'
        else:
            params={'category':'general'}
            news, news_cached = provider_get('news',params, ttl=420)
            news_path='news'
        if not isinstance(news,list): news=[]
        fetched=screen_source_time(news_path,params,news,news_cached)
        with LOCK,contextlib.closing(db_connection()) as con,con:
            desk.remember_news(con,sym or 'general',news,fetched,int(time.time()*1000))
        return {'items':news[:36], 'symbol':sym or None, 'fetched_at':fetched}
    if path == '/api/saved-daily':
        sym=valid_symbol(qs.get('symbol',[''])[0])
        start=int(qs.get('from',['0'])[0]);end=int(qs.get('to',['0'])[0])
        if start<946684800 or end<=start or end>int(time.time())+86400 or end-start>86400*365*12:raise ValueError('Invalid historical range.')
        saved=read_massive_daily_bars(sym,start,end)
        if not saved:return {'status':'no_data','candles':None,'message':'No saved provider daily prices for this stock and period. Connect a provider in Settings, or import a daily-price file.','coverage':coverage41.daily([],int(time.time()*1000),'Massive · saved daily prices (offline)',True)}
        saved_daily={'status':'ok','candles':saved['bars'],'provider':'massive','cached':True,'adjusted':True,'source':'Massive · saved daily prices (offline)','as_of_ms':saved['last_ms'],'notice':'Saved provider daily prices only. No new data was requested; inspect actual dates and missing periods.'}
        saved_daily['coverage']=coverage41.from_candles(saved['bars'],int(time.time()*1000),saved_daily['source'],True)
        return saved_daily
    if path == '/api/imported-history':
        return imported_history(valid_symbol(qs.get('symbol',[''])[0]))
    if path == '/api/candles':
        sym=valid_symbol(qs.get('symbol',[''])[0])
        resolution=qs.get('resolution',['D'])[0]
        if resolution not in ('D','W','M','1','5','15','30','60'):
            raise ValueError('Unsupported chart resolution.')
        start=int(qs.get('from',['0'])[0]); end=int(qs.get('to',['0'])[0]); now=int(time.time())
        if start<946684800 or end<=start or end>now+86400 or end-start>86400*365*12:
            raise ValueError('Invalid historical range.')
        if resolution == 'D' and get_massive_key():
            try:
                loaded=massive_daily_candles(sym,start,end,bypass_cache=True) if qs.get('refresh',['0'])[0]=='1' else massive_daily_candles(sym,start,end)
                if loaded.get('candles'):
                    loaded['coverage']=coverage41.from_candles(loaded['candles'],int(time.time()*1000),loaded.get('source','Massive'),loaded.get('adjusted') is not False)
                return loaded
            except ProviderError as exc:
                return {'status':'entitlement' if exc.status in (401,403) else 'error',
                        'candles':None,'source':'Massive · EOD historical US stocks',
                        'provider':'massive','kind':exc.kind,'message':exc.message,'retry_after':exc.retry_after}
        try:
            candle_args={'symbol':sym,'resolution':resolution,'from':start,'to':end}
            candles,_=provider_get('stock/candle',candle_args,ttl=900,bypass_cache=True) if qs.get('refresh',['0'])[0]=='1' else provider_get('stock/candle',candle_args,ttl=900)
            if not valid_provider_candles(candles):
                return {'status':'no_data','candles':None,'message':'Finnhub did not provide a complete, internally consistent historical OHLC series for this symbol and range.'}
            loaded={'status':'ok','candles':candles,'source':'Finnhub historical OHLC', 'provider':'finnhub', 'adjusted':None}
            if resolution=='D':
                loaded['coverage']=coverage41.from_candles(candles,int(time.time()*1000),loaded['source'],None)
            else:
                loaded['coverage']=coverage41.intraday([{'t':stamp,'p':price} for stamp,price in zip(candles.get('t',[]),candles.get('c',[]))],int(time.time()*1000),loaded['source'])
            return loaded
        except ProviderError as exc:
            if exc.status in (401,403):
                return {'status':'entitlement','candles':None,
                        'message':'Historical OHLC candles require access on your Finnhub plan. No prices were manufactured.'}
            raise
    if path == '/api/tape':
        sym=valid_symbol(qs.get('symbol',['AAPL'])[0])
        since=max(0,int(qs.get('since',['0'])[0]))
        limit=min(4000,max(1,int(qs.get('limit',['3000'])[0])))
        day=qs.get('day',[''])[0]
        review=qs.get('last',['0'])[0]=='1'
        if day:
            date=dt.date.fromisoformat(day)
            if date.isoformat()!=day or date>dt.datetime.now(dt.timezone.utc).date():
                raise ValueError('Choose a saved UTC date.')
            start=int(dt.datetime.combine(date,dt.time(),dt.timezone.utc).timestamp()*1000)
            events=get_tape_events(sym,start,limit,until_ms=start+86400000-1)
        elif review:
            events=get_tape_events(sym,since,limit,True)
        else:
            events=get_tape_events(sym,since,limit)
        tape={'symbol':sym,'events':events,
                'recordingDays':tape_recording_days(sym) if review or day else [],
                'source':'Locally recorded Finnhub WebSocket trade messages',
                'complete_market_tape':False,
                'notice':'Partial captured trade stream. Volume and VWAP describe the captured sample.'}
        tape['coverage']=coverage41.intraday(events,int(time.time()*1000),tape['source'])
        return tape
    if path == '/api/history':
        sym=valid_symbol(qs.get('symbol',[''])[0])
        since=max(0,int(qs.get('since',['0'])[0]))
        history={'symbol':sym,'points':get_history(sym,since), 'source':'Locally recorded Finnhub observations',
                'notice':'Not a complete market-wide historical price series.'}
        history['coverage']=coverage41.intraday(history['points'],int(time.time()*1000),history['source'])
        return history
    raise FileNotFoundError(path)


class AppHandler(BaseHTTPRequestHandler):
    server_version='MarketDeskLocal/3.4.0'
    def log_message(self, fmt, *args):
        # Avoid logging secrets or paths containing tokens.
        print('[local] '+fmt.replace('%s','%s') % args, file=sys.stderr)
    def respond(self, obj, status=200):
        data=json.dumps(obj, ensure_ascii=False, allow_nan=False).encode('utf8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cross-Origin-Resource-Policy','same-origin')
        self.end_headers()
        self.wfile.write(data)
    def same_origin(self):
        host=self.headers.get('Host','')
        if not re.fullmatch(r'(127\.0\.0\.1|localhost):\d+',host): return False
        origin=self.headers.get('Origin')
        return not origin or origin in ('http://'+host,)
    def do_GET(self):
        if not self.same_origin(): return self.respond({'error':'Localhost only.'},403)
        split=urllib.parse.urlsplit(self.path)
        if split.path.startswith('/api/'):
            try:
                obj=handle_api(split.path, urllib.parse.parse_qs(split.query))
                return self.respond(obj)
            except (ValueError,TypeError) as e: return self.respond({'error':str(e)},400)
            except ProviderError as e: return self.respond({'error':e.message,'code':e.status,'kind':e.kind,'retry_after':e.retry_after},e.status if e.status in (401,403,429) else 502)
            except FileNotFoundError: return self.respond({'error':'Not found'},404)
            except Exception as e:
                print('Request failure',repr(e),file=sys.stderr)
                return self.respond({'error':'Unexpected server error; see local Terminal.'},500)
        mapping={'/workbench40.js':'workbench40.js','/crypto38.js':'crypto38.js','/crypto57.js':'crypto57.js','/stress58.js':'stress58.js','/pack59.js':'pack59.js','/workspace60.js':'workspace60.js','/annotate60.js':'annotate60.js','/overview60.js':'overview60.js','/desk61.js':'desk61.js','/showcase61.js':'showcase61.js','/earnings62.js':'earnings62.js','/tracker65.js':'tracker65.js','/practice67.js':'practice67.js','/desk68.js':'desk68.js','/desk61.css':'desk61.css','/crypto38.css':'crypto38.css','/truth36.js':'truth36.js','/truth36.css':'truth36.css','/research35.js':'research35.js','/research35.css':'research35.css','/analyst34.js':'analyst34.js','/analyst34.css':'analyst34.css','/briefing33.js':'briefing33.js','/briefing33.css':'briefing33.css','/projects32.js':'projects32.js','/projects32.css':'projects32.css','/v3.js':'v3.js','/v3.css':'v3.css','/financial-health.js':'financial-health.js','/events42.js':'events42.js','/v43.js':'v43.js','/v43.css':'v43.css','/chart43.js':'chart43.js','/replay43.js':'replay43.js','/shell43.js':'shell43.js','/shell43.css':'shell43.css','/look43.js':'look43.js','/look43.css':'look43.css','/smoke431.js':'smoke431.js','/move44.js':'move44.js','/financial-health.css':'financial-health.css','/design.js':'design.js','/design.css':'design.css','/desk.js':'desk.js','/desk.css':'desk.css','/heatmap.js':'heatmap.js','/heatmap.css':'heatmap.css','/motion.css':'motion.css','/screener.js':'screener.js','/screener.css':'screener.css','/navigation.js':'navigation.js','/sidebar.css':'sidebar.css','/ai-research.js':'ai-research.js','/modern.css':'modern.css','/ai-research.css':'ai-research.css','/alerts.js':'alerts.js','/alerts.css':'alerts.css','/stock-directory.css':'stock-directory.css','/intelligence.js':'intelligence.js','/ask48.js':'ask48.js','/journal49.js':'journal49.js','/desk50.js':'desk50.js','/overnight51.js':'overnight51.js','/compare52.js':'compare52.js','/scenario53.js':'scenario53.js','/strategy54.js':'strategy54.js','/scanner55.js':'scanner55.js','/intelligence.css':'intelligence.css','/':'index.html','/index.html':'index.html','/app.js':'app.js','/compare.js':'compare.js','/reports.js':'reports.js','/research-v17.css':'research-v17.css','/research-v18.css':'research-v18.css','/macro.js':'macro.js','/v19.js':'v19.js','/v19-models.js':'v19-models.js','/v19.css':'v19.css','/chart-research.js':'chart-research.js','/styles.css':'styles.css','/tape.js':'tape.js','/tape.css':'tape.css','/market-hours.js':'market-hours.js','/signal.css':'signal.css','/signal.js':'signal.js','/pro.css':'pro.css','/pro.js':'pro.js','/terminal.css':'terminal.css','/terminal.js':'terminal.js','/brand-mark.svg':'brand-mark.svg','/favicon.svg':'favicon.svg','/apple-touch-icon.png':'apple-touch-icon.png'}
        filename=mapping.get(split.path)
        if not filename: return self.send_error(404)
        p=SITE/filename
        try: content=p.read_bytes()
        except OSError: return self.send_error(404)
        self.send_response(200)
        self.send_header('Content-Type',{'workbench40.js':'text/javascript; charset=utf-8','crypto38.js':'text/javascript; charset=utf-8','crypto57.js':'text/javascript; charset=utf-8','stress58.js':'text/javascript; charset=utf-8','pack59.js':'text/javascript; charset=utf-8','workspace60.js':'text/javascript; charset=utf-8','annotate60.js':'text/javascript; charset=utf-8','overview60.js':'text/javascript; charset=utf-8','desk61.js':'text/javascript; charset=utf-8','showcase61.js':'text/javascript; charset=utf-8','earnings62.js':'text/javascript; charset=utf-8','tracker65.js':'text/javascript; charset=utf-8','practice67.js':'text/javascript; charset=utf-8','desk68.js':'text/javascript; charset=utf-8','desk61.css':'text/css; charset=utf-8','crypto38.css':'text/css; charset=utf-8','truth36.js':'text/javascript; charset=utf-8','truth36.css':'text/css; charset=utf-8','research35.js':'text/javascript; charset=utf-8','research35.css':'text/css; charset=utf-8','analyst34.js':'text/javascript; charset=utf-8','analyst34.css':'text/css; charset=utf-8','briefing33.js':'text/javascript; charset=utf-8','briefing33.css':'text/css; charset=utf-8','projects32.js':'text/javascript; charset=utf-8','projects32.css':'text/css; charset=utf-8','v3.js':'text/javascript; charset=utf-8','v3.css':'text/css; charset=utf-8','financial-health.js':'text/javascript; charset=utf-8','events42.js':'text/javascript; charset=utf-8','v43.js':'text/javascript; charset=utf-8','v43.css':'text/css; charset=utf-8','chart43.js':'text/javascript; charset=utf-8','replay43.js':'text/javascript; charset=utf-8','shell43.js':'text/javascript; charset=utf-8','shell43.css':'text/css; charset=utf-8','look43.js':'text/javascript; charset=utf-8','look43.css':'text/css; charset=utf-8','smoke431.js':'text/javascript; charset=utf-8','move44.js':'text/javascript; charset=utf-8','financial-health.css':'text/css; charset=utf-8','design.js':'text/javascript; charset=utf-8','design.css':'text/css; charset=utf-8','desk.js':'text/javascript; charset=utf-8','desk.css':'text/css; charset=utf-8','heatmap.js':'text/javascript; charset=utf-8','heatmap.css':'text/css; charset=utf-8','motion.css':'text/css; charset=utf-8','screener.js':'text/javascript; charset=utf-8','screener.css':'text/css; charset=utf-8','navigation.js':'text/javascript; charset=utf-8','sidebar.css':'text/css; charset=utf-8','ai-research.js':'text/javascript; charset=utf-8','modern.css':'text/css; charset=utf-8','ai-research.css':'text/css; charset=utf-8','alerts.js':'text/javascript; charset=utf-8','alerts.css':'text/css; charset=utf-8','stock-directory.css':'text/css; charset=utf-8','intelligence.js':'text/javascript; charset=utf-8','ask48.js':'text/javascript; charset=utf-8','journal49.js':'text/javascript; charset=utf-8','desk50.js':'text/javascript; charset=utf-8','overnight51.js':'text/javascript; charset=utf-8','compare52.js':'text/javascript; charset=utf-8','scenario53.js':'text/javascript; charset=utf-8','strategy54.js':'text/javascript; charset=utf-8','scanner55.js':'text/javascript; charset=utf-8','intelligence.css':'text/css; charset=utf-8','index.html':'text/html; charset=utf-8','app.js':'text/javascript; charset=utf-8','compare.js':'text/javascript; charset=utf-8','reports.js':'text/javascript; charset=utf-8','research-v17.css':'text/css; charset=utf-8','research-v18.css':'text/css; charset=utf-8','macro.js':'text/javascript; charset=utf-8','v19.js':'text/javascript; charset=utf-8','v19-models.js':'text/javascript; charset=utf-8','v19.css':'text/css; charset=utf-8','chart-research.js':'text/javascript; charset=utf-8','styles.css':'text/css; charset=utf-8','tape.js':'text/javascript; charset=utf-8','market-hours.js':'text/javascript; charset=utf-8','tape.css':'text/css; charset=utf-8','signal.css':'text/css; charset=utf-8','signal.js':'text/javascript; charset=utf-8','pro.css':'text/css; charset=utf-8','pro.js':'text/javascript; charset=utf-8','terminal.css':'text/css; charset=utf-8','terminal.js':'text/javascript; charset=utf-8','brand-mark.svg':'image/svg+xml','favicon.svg':'image/svg+xml','apple-touch-icon.png':'image/png'}[filename])
        self.send_header('Content-Length',str(len(content)))
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Cache-Control','no-cache')
        self.send_header('Content-Security-Policy',"default-src 'self'; connect-src 'self' https://finnhub.io wss://ws-feed.exchange.coinbase.com; img-src 'self' https: data:; script-src 'self'; style-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.end_headers(); self.wfile.write(content)
    def do_POST(self):
        if not self.same_origin() or self.headers.get('X-MD-Request')!='1':
            return self.respond({'error':'Local request token missing.'},403)
        if self.path not in ('/api/collector-pulse','/api/v3/heatmap-sync','/api/token','/api/massive-token','/api/ticks','/api/workspace','/api/alerts','/api/ai/ask','/api/ai/sources','/api/ai/documents','/api/ai/runs','/api/screener/refresh','/api/imported-history','/api/desk/refresh','/api/financials/refresh','/api/v3/market-values','/api/v3/drafts-validate','/api/v3/scenario-assist','/api/v3/forecast-record','/api/v3/forecast-archive','/api/v3/analyst-review','/api/v3/analyst-calculate','/api/v3/market-model','/api/v3/briefing','/api/v3/calculate','/api/v3/marks-from-quotes','/api/v3/events-export','/api/v3/macro-refresh','/api/v3/events-refresh','/api/v3/events42-refresh','/api/v3/listings-refresh','/api/v3/desk50-backup','/api/v3/overnight51','/api/v3/compare52','/api/v3/scenario53','/api/v3/strategy54','/api/v3/scanner55','/api/v3/crypto-follow','/api/v3/crypto57','/api/v3/stress58','/api/v3/pack59','/api/v3/workspace60','/api/v3/annotate60','/api/v3/desk61','/api/v3/earnings62','/api/v3/tracker65','/api/v3/practice67'): return self.respond({'error':'Not found'},404)
        try:
            length=int(self.headers.get('Content-Length','0'))
            max_length = 2500000 if self.path in ('/api/workspace','/api/imported-history','/api/v3/market-values','/api/v3/drafts-validate','/api/v3/scenario-assist','/api/v3/forecast-record','/api/v3/forecast-archive','/api/v3/analyst-review','/api/v3/analyst-calculate','/api/v3/market-model','/api/v3/briefing','/api/v3/calculate','/api/v3/marks-from-quotes','/api/v3/events-export') else 220000
            if length<1 or length>max_length: raise ValueError('Invalid request size.')
            obj=json.loads(self.rfile.read(length),parse_constant=lambda _: (_ for _ in ()).throw(ValueError('JSON numbers must be finite.')))
            if not isinstance(obj,dict):raise ValueError('Use a JSON object for this request.')
            if self.path=='/api/collector-pulse':
                symbol=valid_symbol(obj['priority']) if obj.get('priority') else None
                cursor=obj.get('cursor',0)
                if type(cursor) is not int:raise ValueError('Invalid collector cursor.')
                if not COLLECTOR:return self.respond({'status':{'stream':'Not started'},'events':[],'symbols':[]})
                return self.respond(COLLECTOR.pulse(symbol,cursor,obj.get('epoch','')))
            if self.path.startswith('/api/v3/'):return self.respond(lab3.post(self.path,obj,globals()))
            if self.path=='/api/financials/refresh':return self.respond(sec_refresh(obj))
            if self.path=='/api/desk/refresh':return self.respond(desk_refresh(obj))
            if self.path=='/api/imported-history':return self.respond(change_imported_history(obj))
            if self.path=='/api/screener/refresh':return self.respond(screen_refresh(obj))
            if self.path in ('/api/ai/ask','/api/ai/sources','/api/ai/documents','/api/ai/runs'):
                return self.respond(ai_action(self.path,obj))
            if self.path=='/api/alerts':
                return self.respond(change_alerts(obj))
            if self.path=='/api/workspace':
                stamp=write_workspace(obj.get('snapshot'))
                return self.respond({'ok':True,'updated_at':stamp})
            if self.path=='/api/massive-token':
                if obj.get('clear'):
                    clear_massive_key()
                    return self.respond({'configured':False,'provider':'Massive'})
                save_massive_key(obj.get('token',''))
                return self.respond({'configured':True,'provider':'Massive'})
            if self.path=='/api/token':
                if obj.get('clear'):
                    KEY_FILE.unlink(missing_ok=True)
                    with LOCK: CACHE.clear()
                    return self.respond({'configured':False})
                save_key(str(obj.get('token','')))
                return self.respond({'configured':True})
            ticks=obj.get('ticks',[])
            if not isinstance(ticks,list) or len(ticks)>150: raise ValueError('Invalid trade batch.')
            accepted=store_points_batch(ticks)
            return self.respond({'accepted':accepted})
        except (ValueError,TypeError,json.JSONDecodeError) as e:
            return self.respond({'error':str(e)},400)
        except Exception as e:
            print('POST failure',repr(e),file=sys.stderr)
            return self.respond({'error':'Unexpected server error'},500)


def main():
    global COLLECTOR
    background='--background' in sys.argv[1:]
    init_storage()
    port=8765
    url=f'http://127.0.0.1:{port}'
    try:
        httpd=ThreadingHTTPServer(('127.0.0.1',port),AppHandler)
    except OSError:
        if not background:
            try:
                with urllib.request.urlopen(url+'/api/status',timeout=2) as response:
                    running=json.load(response)
                if running.get('version')==VERSION:
                    webbrowser.open(url)
                    return
            except (OSError,ValueError):pass
        sys.exit('Port 8765 is occupied. Stop the previous Market Desk server before starting this release.')
    httpd.daemon_threads=True
    COLLECTOR=collector40.Collector(globals())
    COLLECTOR.start()
    print('Market Desk '+VERSION+' · '+url,flush=True)
    print('The collector runs while this local server and your Mac are running.',flush=True)
    if not background:
        try:webbrowser.open(url)
        except Exception:pass
    try:httpd.serve_forever(poll_interval=.3)
    except KeyboardInterrupt:pass
    finally:
        COLLECTOR.stop.set()
        httpd.server_close()

if __name__=='__main__': main()
