"""Company event timeline and same-window price comparisons. No invented announcements."""
import contextlib
import datetime as dt
import hashlib
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit
from zoneinfo import ZoneInfo

import desk
import events3
import market37

NY = ZoneInfo('America/New_York')
EARLY = {
    2025: {dt.date(2025, 7, 3), dt.date(2025, 11, 28), dt.date(2025, 12, 24)},
    2026: {dt.date(2026, 11, 27), dt.date(2026, 12, 24)},
    2027: {dt.date(2027, 11, 26)},
    2028: {dt.date(2028, 7, 3), dt.date(2028, 11, 24)},
}
COMPANY_HOSTS = ('businesswire.com', 'prnewswire.com', 'globenewswire.com', 'take2games.com', 'rockstargames.com')
BASIS = 'Split-adjusted daily close. Dividends and fees are not included.'


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS events42(
        symbol TEXT PRIMARY KEY, body TEXT NOT NULL, updated_at INTEGER NOT NULL)''')


def is_session(day):
    return day.weekday() < 5 and day not in market37.holidays(day.year)


def close_on(day):
    if not is_session(day):
        return None
    hour = 13 if day in EARLY.get(day.year, ()) else 16
    return dt.datetime.combine(day, dt.time(hour), NY)


def previous_session(day):
    cursor = day
    for _ in range(14):
        cursor -= dt.timedelta(days=1)
        if is_session(cursor):
            return cursor
    raise ValueError('No earlier trading session was found.')


def sessions_after(day, count):
    found = []
    cursor = day
    for _ in range(count * 6 + 14):
        cursor += dt.timedelta(days=1)
        if is_session(cursor):
            found.append(cursor)
            if len(found) == count:
                return found
    raise ValueError('The following trading sessions are outside the calendar that is loaded.')


def host(url):
    try:
        name = urlsplit(str(url or '')).netloc.lower()
    except ValueError:
        return ''
    return name[4:] if name.startswith('www.') else name


GENERIC = {'inc', 'corp', 'corporation', 'ltd', 'plc', 'company', 'group', 'holdings', 'software', 'systems', 'services', 'technologies', 'technology', 'international', 'interactive'}


def aliases(symbol, name):
    found = {str(symbol or '').lower()}
    words = [word.lower() for word in re.findall(r'[A-Za-z0-9]+', name or '') if len(word) >= 3 and word.lower() not in GENERIC]
    if len(words) >= 2:
        found.add(words[0] + ' ' + words[1])
        found.add(words[0] + '-' + words[1])
    return {alias for alias in found if alias}


def mentions_company(title, symbol, name):
    text = str(title or '').lower()
    for alias in aliases(symbol, name):
        if ' ' in alias or '-' in alias:
            if alias in text:
                return True
        elif re.search(r'\b' + re.escape(alias) + r'\b', text):
            return True
    return False


def explain(symbol, events, name=''):
    """Keep the provider's ticker association and say why each item is included."""
    rows = []
    for item in events:
        row = normalise(item)
        if not row:
            continue
        row = dict(row)
        row['association'] = 'The provider associated this item with ' + symbol + '.'
        if row['kind'] == 'filing':
            row['reason'] = row['association'] + ' The source is an SEC filing.'
        elif row['kind'] == 'company':
            row['reason'] = row['association'] + ' The link is on a company or newswire host, so it is labelled a company announcement.'
        elif row['kind'] == 'earnings':
            row['reason'] = row['association'] + ' The source is a third-party earnings calendar, not a company announcement.'
        elif mentions_company(row['title'], symbol, name):
            row['reason'] = row['association'] + ' The title names the company, so it is third-party reporting, not a company announcement.'
        else:
            row['kind'] = 'market'
            row['kindLabel'] = 'Broader market coverage'
            row['reason'] = row['association'] + ' The title does not name ' + symbol + ' or the company, so this is broader market coverage.'
        rows.append(row)
    return rows


def kind_for(item):
    origin = str(item.get('origin') or '')
    if origin == 'SEC filing' or host(item.get('source')) == 'sec.gov' or 'sec.gov' in host(item.get('source')):
        return 'filing', 'Regulatory filing'
    if origin == 'Finnhub calendar':
        return 'earnings', 'Third-party calendar'
    if any(name in host(item.get('source')) or name in str(item.get('publisher') or '').lower() for name in COMPANY_HOSTS):
        return 'company', 'Company announcement'
    return 'reporting', 'Third-party reporting'


def canonical_source(url):
    parts = urlsplit(str(url or ''))
    if parts.scheme not in ('http', 'https') or not parts.netloc:
        return str(url or '')
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        name = key.lower()
        if name == 'utm' or name.startswith('utm_') or name in ('fbclid', 'gclid', 'mc_cid', 'mc_eid'):
            continue
        query.append((key, value))
    return parts._replace(query=urlencode(query), fragment='').geturl()


def event_id(item):
    source = canonical_source(item.get('source') or item.get('url') or '')
    key = source or (str(item.get('title') or '') + '|' + str(item.get('date') or ''))
    return hashlib.sha256(key.encode()).hexdigest()[:24]


def normalise(item):
    title = str(item.get('title') or item.get('headline') or '').strip()
    if not title:
        return None
    kind, label = kind_for(item)
    published = item.get('publishedAt', item.get('datetime'))
    if isinstance(published, bool) or not isinstance(published, (int, float)):
        published = None
    else:
        published = int(published if published > 10_000_000_000 else published * 1000)
    date = str(item.get('date') or '')
    if published and not date:
        date = dt.datetime.fromtimestamp(published / 1000, NY).date().isoformat()
    try:
        dt.date.fromisoformat(date)
    except ValueError:
        return None
    zone = 'America/New_York'
    when = item.get('window') or ''
    timing = 'timestamp' if published else 'date'
    return {
        'id': event_id({**item, 'source': item.get('source') or item.get('url'), 'title': title, 'date': date}),
        'title': title[:240],
        'kind': kind,
        'kindLabel': label,
        'source': canonical_source(item.get('source') or item.get('url') or ''),
        'origin': str(item.get('origin') or '')[:80],
        'publisher': str(item.get('publisher') or item.get('origin') or label)[:120],
        'date': date,
        'publishedAt': published,
        'zone': zone,
        'timeLabel': (dt.datetime.fromtimestamp(published / 1000, NY).strftime('%Y-%m-%d %H:%M') + ' America/New_York') if published else date + ' · date only',
        'timing': timing,
        'window': when,
        'note': (str(item.get('note') or '') or ('Link supplied by the news provider. It is not a company announcement or filing.' if host(item.get('source') or item.get('url')) == 'finnhub.io' and kind == 'reporting' else ''))[:400],
    }


def dedupe(items):
    found = {}
    for item in items:
        row = normalise(item)
        if not row:
            continue
        old = found.get(row['id'])
        if old is None or (row['publishedAt'] or 0) >= (old['publishedAt'] or 0):
            found[row['id']] = row
    rows = sorted(found.values(), key=lambda row: (row['publishedAt'] or 0, row['date'], row['id']), reverse=True)
    direct = [row for row in rows if row['kind'] in ('filing', 'company', 'earnings')][:20]
    chosen = {row['id'] for row in direct}
    kept = list(direct)
    for row in rows:
        if row['id'] in chosen:
            continue
        if len(kept) >= 60:
            break
        kept.append(row)
    return sorted(kept, key=lambda row: (row['publishedAt'] or 0, row['date'], row['id']), reverse=True)


def mentions_gta_text(text):
    text = str(text or '').lower()
    return 'gta vi' in text or 'gta 6' in text or 'grand theft auto vi' in text or 'grand theft auto 6' in text


def mentions_gta(events):
    return any(mentions_gta_text(row['title'] + ' ' + row.get('note', '')) for row in events)


def gaps(symbol, events, limits):
    notes = list(limits or [])
    if not any(row['kind'] == 'filing' for row in events):
        notes.append('No saved SEC filing is in this timeline. Update SEC accounts on this page to load filings. None were invented.')
    if not any(row['kind'] == 'earnings' for row in events):
        notes.append('No saved earnings release is in this timeline. The free calendar may be unavailable on this plan.')
    if symbol == 'TTWO' and not mentions_gta(events):
        notes.append('No saved headline or filing in this timeline mentions GTA VI. Recent news and saved SEC filings were checked. Older announcements are not backfilled.')
    elif symbol == 'TTWO' and not any(row['kind'] in ('company', 'filing') and mentions_gta_text(row['title'] + ' ' + row.get('note', '')) for row in events):
        notes.append('Saved items mention GTA VI, but they are third-party reports. No saved company announcement or SEC filing in this timeline is the original GTA VI announcement. Older announcements are not backfilled.')
    if not events:
        notes.append('This company has no saved events yet.')
    return notes


def anchor_for(event):
    day = dt.date.fromisoformat(event['date'])
    published = event.get('publishedAt')
    if not published:
        anchor = day if is_session(day) else previous_session(day)
        return anchor, 'uncertain', 'The source gave a date without a time. The reaction starts on the first full trading session after that date.'
    moment = dt.datetime.fromtimestamp(published / 1000, NY)
    close = close_on(moment.date())
    if close and moment >= close:
        return moment.date(), 'after_close', 'Published after the New York close, so that day’s close is the starting price and the reaction starts the next trading session.'
    if close and moment < close:
        return previous_session(moment.date()), 'during_session', 'The starting price is the last eligible close before publication.'
    return previous_session(moment.date()), 'outside_session', 'Published outside a regular session. The starting price is the last eligible close before publication.'


def reaction(symbol, event, horizon, stock, spy, now_ms):
    if horizon not in (1, 5):
        raise ValueError('Choose 1 session or 5 sessions.')
    try:
        anchor, timing, timing_note = anchor_for(event)
        targets = sessions_after(anchor, horizon)
    except ValueError as error:
        return {'status': 'withheld', 'reason': str(error), 'explanation': 'No price comparison is shown.'}
    target = targets[-1]
    finished = close_on(target)
    if finished is None or int(finished.timestamp() * 1000) > now_ms:
        return {'status': 'withheld', 'reason': 'This window is still open. The target session has not finished.', 'anchor': anchor.isoformat(), 'target': target.isoformat(), 'timing': timing, 'timingNote': timing_note, 'explanation': 'No price comparison is shown until both closes can be read.'}
    start_price = stock.get(anchor.isoformat())
    end_price = stock.get(target.isoformat())
    spy_start = spy.get(anchor.isoformat())
    spy_end = spy.get(target.isoformat())
    missing = []
    if start_price is None or end_price is None:
        missing.append(symbol)
    if spy_start is None or spy_end is None:
        missing.append('SPY')
    if missing:
        return {'status': 'withheld', 'reason': 'Missing saved closes for ' + ' and '.join(missing) + ' on ' + anchor.isoformat() + ' or ' + target.isoformat() + '.', 'anchor': anchor.isoformat(), 'target': target.isoformat(), 'timing': timing, 'timingNote': timing_note, 'explanation': 'The comparison is withheld. A missing price is not filled in.'}
    stock_pp = (end_price / start_price - 1) * 100
    spy_pp = (spy_end / spy_start - 1) * 100
    diff = stock_pp - spy_pp
    if diff >= .05:
        sentence = symbol + ' moved ' + f'{diff:.2f}' + ' percentage points more than SPY over this window.'
    elif diff <= -.05:
        sentence = symbol + ' moved ' + f'{abs(diff):.2f}' + ' percentage points less than SPY over this window.'
    else:
        sentence = symbol + ' moved about the same as SPY over this window.'
    return {
        'status': 'ready', 'horizon': horizon, 'timing': timing, 'timingNote': timing_note,
        'anchor': anchor.isoformat(), 'target': target.isoformat(),
        'anchorPrice': start_price, 'targetPrice': end_price,
        'benchmark': 'SPY', 'benchmarkAnchorPrice': spy_start, 'benchmarkTargetPrice': spy_end,
        'stockReturnPct': stock_pp, 'benchmarkReturnPct': spy_pp, 'differencePP': diff,
        'sentence': sentence, 'basis': BASIS,
        'sessions': [day.isoformat() for day in targets],
        'explanation': 'This is the difference between the two price changes. It does not show why the price moved.',
        'computedAt': now_ms,
    }


def closes(g, symbol, now_ms):
    saved = g['read_massive_daily_bars'](symbol, 946684800, now_ms // 1000 + 86400)
    if not saved:
        return {}
    found = {}
    for stamp, price in zip(saved['bars']['t'], saved['bars']['c']):
        if isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0:
            continue
        found[dt.datetime.fromtimestamp(stamp, NY).date().isoformat()] = float(price)
    return found


def load(g, symbol):
    with contextlib.closing(g['db_connection']()) as con:
        row = con.execute('SELECT body,updated_at FROM events42 WHERE symbol=?', (symbol,)).fetchone()
    if not row:
        return None
    try:
        body = json.loads(row[0])
    except ValueError:
        return None
    body['updatedAt'] = row[1]
    return body


def store(g, symbol, body, now_ms):
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('INSERT OR REPLACE INTO events42 VALUES(?,?,?)', (symbol, json.dumps(body, allow_nan=False), now_ms))


def local_items(g, symbol):
    items = []
    report = g['sec_saved'](symbol) if 'sec_saved' in g else {}
    for row in report.get('filingEvents') or []:
        items.append(row)
    with contextlib.closing(g['db_connection']()) as con:
        news = con.execute('SELECT body FROM desk_news WHERE scope=?', (symbol,)).fetchone()
        cached = con.execute("SELECT body FROM v3_cache WHERE id=?", ('earnings:' + symbol,)).fetchone()
    if news:
        try:
            for row in json.loads(news[0]):
                items.append({'title': row.get('headline'), 'source': row.get('url'), 'publisher': row.get('source'), 'datetime': row.get('datetime'), 'origin': 'news'})
        except ValueError:
            pass
    if cached:
        try:
            items.extend(json.loads(cached[0]).get('events') or [])
        except ValueError:
            pass
    return items


def cache_daily(g, symbol, now_ms):
    """Use the existing free daily-history download when a key is already saved."""
    download = g.get('massive_daily_candles')
    if not download:
        return
    end = now_ms // 1000
    try:
        download(symbol, end - 86400 * 120, end)
    except Exception:
        return


def with_reactions(g, symbol, events, saved, now_ms):
    stock = closes(g, symbol, now_ms)
    spy = closes(g, 'SPY', now_ms) if symbol != 'SPY' else stock
    previous = (saved or {}).get('comparisons') or {}
    comparisons = {}
    for event in events:
        comparisons[event['id']] = {}
        for horizon in (1, 5):
            current = reaction(symbol, event, horizon, stock, spy, now_ms)
            old = (previous.get(event['id']) or {}).get(str(horizon)) or (previous.get(event['id']) or {}).get(horizon)
            if current['status'] != 'ready' and old and old.get('status') == 'ready':
                current = {**old, 'savedCopy': True, 'reason': current.get('reason') or old.get('reason')}
            comparisons[event['id']][str(horizon)] = current
    return comparisons


def issuer_name(g, symbol):
    try:
        report = g.get('sec_saved', lambda _symbol: {})(symbol) or {}
    except Exception:
        return ''
    return str((report.get('identity') or {}).get('name') or report.get('name') or '')


def packet(g, symbol, now_ms=None):
    symbol = g['valid_symbol'](symbol)
    now_ms = int(g['time'].time() * 1000) if now_ms is None else now_ms
    saved = load(g, symbol)
    events = explain(symbol, dedupe([*((saved or {}).get('events') or []), *local_items(g, symbol)]), issuer_name(g, symbol))
    if saved and saved.get('events'):
        limits = saved.get('limits') or []
        updated = saved.get('updatedAt') or now_ms
    else:
        limits = ['Opened from records already saved on this Mac. Update events to check the free news and earnings sources.']
        updated = now_ms
    comparisons = with_reactions(g, symbol, events, saved, now_ms)
    body = {'events': events, 'limits': limits, 'comparisons': comparisons, 'gaps': gaps(symbol, events, limits)}
    store(g, symbol, body, updated if saved else now_ms)
    return {**body, 'symbol': symbol, 'updatedAt': updated if saved else now_ms, 'offline': True,
            'notice': 'Event facts, measured moves and possible explanations are separate. A source page opens only when you choose its link.'}


def refresh(g, symbol):
    symbol = g['valid_symbol'](symbol)
    now_ms = int(g['time'].time() * 1000)
    items = local_items(g, symbol)
    limits = []
    try:
        today = dt.datetime.fromtimestamp(now_ms / 1000, dt.timezone.utc).date()
        params = {'symbol': symbol, 'from': str(today - dt.timedelta(days=7)), 'to': str(today)}
        news, _cached = g['provider_get']('company-news', params, ttl=420)
        if isinstance(news, list):
            items.extend({'title': row.get('headline'), 'source': row.get('url'), 'publisher': row.get('source'), 'datetime': row.get('datetime'), 'origin': 'news'} for row in news if isinstance(row, dict))
            with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
                desk.remember_news(con, symbol, news, now_ms, now_ms)
        else:
            limits.append('The news source did not return a headline list.')
    except Exception:
        limits.append('Company news could not be updated. Saved events were kept.')
    try:
        today = dt.datetime.fromtimestamp(now_ms / 1000, dt.timezone.utc).date()
        params = {'symbol': symbol, 'from': str(today - dt.timedelta(days=30)), 'to': str(today + dt.timedelta(days=90))}
        data, _cached = g['provider_get']('calendar/earnings', params, ttl=86400)
        fetched = int(g['time'].time() * 1000)
        earnings = events3.earnings(data, symbol, fetched)
        items.extend(earnings)
        import lab3
        lab3.remember(g, 'earnings:' + symbol, {'symbol': symbol, 'events': earnings}, fetched)
    except Exception:
        limits.append('The free earnings calendar could not be updated. A saved calendar was kept when one exists.')
    saved = load(g, symbol) or {}
    # Keep events that disappeared from the latest short news feed.
    events = explain(symbol, dedupe([*(saved.get('events') or []), *items]), issuer_name(g, symbol))
    cache_daily(g, symbol, now_ms)
    if symbol != 'SPY':
        cache_daily(g, 'SPY', now_ms)
    comparisons = with_reactions(g, symbol, events, saved, now_ms)
    body = {'events': events, 'limits': limits, 'comparisons': comparisons, 'gaps': gaps(symbol, events, limits)}
    store(g, symbol, body, now_ms)
    return {**body, 'symbol': symbol, 'updatedAt': now_ms, 'offline': False,
            'notice': 'Newly checked free sources were merged into the saved timeline. Headlines older than the provider’s recent window are not backfilled.'}
