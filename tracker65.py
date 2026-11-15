"""Follow a company or a saved research entry and compare later saved records.

The original thesis and judgement stay as they were saved. A missing filing is
named and not filled in. A different period, unit or currency is not subtracted.
"""
import contextlib
import datetime as dt
import hashlib
import json

import desk50
import earnings62
import events42
import journal49
import scorecard41

METHOD = 'research-change-v6.5'
KINDS = ('announcement', 'filing', 'revision', 'forecast', 'alert', 'assumption', 'missing')
DEFAULTS = {
    'digest': {kind: True for kind in KINDS},
    'alert': {kind: False for kind in KINDS},
    'thresholdPP': 1,
}


def owns(text):
    words = str(text or '').lower()
    return 'assumptions should i revisit' in words or words.strip(' ?') == 'what changed since my last review'


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS tracker65_follows(
        id TEXT PRIMARY KEY, symbol TEXT NOT NULL, journal_id TEXT NOT NULL,
        baseline TEXT NOT NULL, settings TEXT NOT NULL, created_at INTEGER NOT NULL)''')
    con.execute('''CREATE TABLE IF NOT EXISTS tracker65_changes(
        id TEXT PRIMARY KEY, follow_id TEXT NOT NULL, symbol TEXT NOT NULL, kind TEXT NOT NULL,
        body TEXT NOT NULL, available_at INTEGER NOT NULL, detected_at INTEGER NOT NULL,
        gap INTEGER NOT NULL, acknowledged_at INTEGER, notify TEXT NOT NULL)''')
    con.execute('''CREATE TABLE IF NOT EXISTS tracker65_reviews(
        id TEXT PRIMARY KEY, follow_id TEXT NOT NULL, body TEXT NOT NULL, created_at INTEGER NOT NULL)''')


def _settings(raw):
    raw = raw if isinstance(raw, dict) else {}
    digest = {kind: bool((raw.get('digest') or {}).get(kind, True)) for kind in KINDS}
    alert = {kind: bool((raw.get('alert') or {}).get(kind, False)) for kind in KINDS}
    try:
        threshold = float(raw.get('thresholdPP', 1))
    except (TypeError, ValueError):
        threshold = 1
    if threshold < 0 or threshold > 100:
        threshold = 1
    return {'digest': digest, 'alert': alert, 'thresholdPP': threshold}


def _periods(report):
    rows = []
    for kind in ('annual', 'quarterly'):
        for period in (report or {}).get(kind) or []:
            revenue = (period.get('metrics') or {}).get('revenue') or {}
            profit = (period.get('metrics') or {}).get('profit') or {}
            if 'value' not in revenue and 'value' not in profit:
                continue
            filed = revenue.get('filedAt') if isinstance(revenue.get('filedAt'), int) else profit.get('filedAt') if isinstance(profit.get('filedAt'), int) else 0
            rows.append({
                'type': period.get('type') or kind, 'start': period.get('start') or '', 'end': period.get('end') or '',
                'currency': period.get('currency') or '', 'durationDays': period.get('durationDays'),
                'revenue': revenue.get('value'), 'revenueUnit': revenue.get('unit') or '',
                'profit': profit.get('value'), 'profitUnit': profit.get('unit') or '',
                'filed': revenue.get('filed') or profit.get('filed') or '', 'availableAt': filed,
            })
    return rows


def _forecasts(g, symbol):
    try:
        card = scorecard41.read(g, symbol)
    except Exception:
        return []
    rows = []
    for row in card.get('graded') or []:
        outcome = row.get('outcome') or {}
        rows.append({
            'anchorDay': row.get('anchorDay') or '', 'targetDay': row.get('targetDay') or '',
            'horizon': row.get('horizon'), 'forecastPrice': row.get('forecastPrice'),
            'actualPrice': outcome.get('actualPrice'), 'gradedAt': outcome.get('gradedAt') or 0,
        })
    return rows


def _alerts(g, symbol):
    try:
        with contextlib.closing(g['db_connection']()) as con:
            found = con.execute('SELECT price,received_at,rule_text FROM price_alert_events WHERE symbol=? ORDER BY received_at', (symbol,)).fetchall()
    except Exception:
        return []
    return [{'price': price, 'receivedAt': received, 'rule': rule or ''} for price, received, rule in found]


def _events(g, symbol):
    try:
        saved = events42.load(g, symbol) or {}
        rows = events42.dedupe([*(saved.get('events') or []), *events42.local_items(g, symbol)])
    except Exception:
        return []
    found = []
    for row in rows:
        published = row.get('publishedAt')
        if isinstance(published, int):
            found.append({'title': row.get('title') or '', 'publishedAt': published, 'source': row.get('source') or ''})
    return found


def snapshot(g, symbol, now_ms, note=None):
    symbol = g['valid_symbol'](symbol)
    note = note if isinstance(note, dict) else {}
    latest = journal49.latest(g, symbol, now_ms)
    report = {}
    try:
        report = g.get('sec_saved', lambda _symbol: {})(symbol) or {}
    except Exception:
        report = {}
    assumptions = note.get('assumptions') if isinstance(note.get('assumptions'), dict) else {}
    growth, margin = assumptions.get('growthPct'), assumptions.get('marginPct')
    return {
        'method': METHOD, 'symbol': symbol, 'journalId': str(note.get('journalId') or '')[:32],
        'title': str(note.get('title') or symbol)[:160],
        'start': str(note.get('start') or '')[:10], 'end': str(note.get('end') or '')[:10],
        'reviewDate': str(note.get('reviewDate') or '')[:10],
        'status': note.get('status') if note.get('status') in journal49.STATUSES else 'open',
        'expectation': str(note.get('expectation') or '')[:4000],
        'assumptions': {'growthPct': growth if isinstance(growth, (int, float)) and not isinstance(growth, bool) else None,
                        'marginPct': margin if isinstance(margin, (int, float)) and not isinstance(margin, bool) else None,
                        'scenarioId': str(assumptions.get('scenarioId') or '')[:40]},
        'price': latest.get('price'), 'priceDate': latest.get('date') or '', 'priceSource': latest.get('source') or '',
        'events': _events(g, symbol), 'periods': _periods(report), 'forecasts': _forecasts(g, symbol),
        'alerts': _alerts(g, symbol), 'capturedAt': int(now_ms),
    }


def _key(follow_id, kind, identity):
    return hashlib.sha256(f'{follow_id}|{kind}|{identity}'.encode()).hexdigest()[:16]


def _gap(g, start, end):
    try:
        import overnight51
        found = overnight51.gaps(g, start, end)
    except Exception:
        return False
    return bool(found)


def _notify(settings, kind):
    if settings['alert'].get(kind):
        return 'alert'
    if settings['digest'].get(kind):
        return 'digest'
    return 'hidden'


def _change(follow, kind, identity, body, available, detected, gap, settings):
    return {
        'id': _key(follow['id'], kind, identity), 'followId': follow['id'], 'symbol': follow['symbol'],
        'kind': kind, 'body': body, 'availableAt': int(available or 0), 'detectedAt': int(detected),
        'gap': bool(gap), 'acknowledgedAt': None, 'notify': _notify(settings, kind),
    }


def _period_key(row):
    return f"{row.get('type')}|{row.get('start')}|{row.get('end')}"


def _report_from_periods(periods):
    annual = sorted((row for row in periods if row.get('type') == 'annual'), key=lambda row: row.get('end') or '')
    built = {'annual': []}
    for row in annual:
        metrics = {}
        if row.get('revenue') is not None:
            metrics['revenue'] = {'value': row.get('revenue'), 'tag': 'Revenues', 'unit': row.get('revenueUnit') or 'USD'}
        if row.get('profit') is not None:
            metrics['profit'] = {'value': row.get('profit'), 'tag': 'NetIncomeLoss', 'unit': row.get('profitUnit') or 'USD'}
        built['annual'].append({
            'type': 'annual', 'start': row['start'], 'end': row['end'], 'durationDays': row.get('durationDays') or 365,
            'currency': row.get('currency') or 'USD', 'metrics': metrics,
        })
    return built


def _diffs(follow, current, now_ms, gapped, existing):
    base = follow['baseline']
    settings = follow['settings']
    found = []
    known = {(item['kind'], item.get('identity')) for item in existing}
    seen_events = {(row.get('title'), row.get('publishedAt')) for row in base.get('events') or []}
    for row in current.get('events') or []:
        if (row.get('title'), row.get('publishedAt')) in seen_events:
            continue
        found.append(_change(follow, 'announcement', f"{row.get('publishedAt')}|{row.get('title')}", {
            'identity': f"{row.get('publishedAt')}|{row.get('title')}",
            'title': 'New saved announcement', 'original': 'Not in the starting evidence', 'updated': row.get('title') or 'Untitled',
            'dates': row.get('publishedAt'), 'calculation': 'The publication time is after the follow was saved. A headline is not a cause.',
            'source': row.get('source') or 'Saved company announcement',
        }, row.get('publishedAt'), now_ms, gapped, settings))
    base_periods = {_period_key(row): row for row in base.get('periods') or []}
    remembered = {}
    for item in existing:
        if item['kind'] in ('filing', 'revision') and item.get('period') and item.get('updatedValue') is not None and item['period'] not in remembered:
            remembered[item['period']] = {'revenue': item['updatedValue'], 'currency': item.get('currency') or '', 'revenueUnit': item.get('unit') or '', 'type': 'annual'}
    for row in current.get('periods') or []:
        period_key = _period_key(row)
        previous = base_periods.get(period_key)
        if previous is None and period_key in remembered:
            previous = remembered[period_key]
        if previous is None:
            found.append(_change(follow, 'filing', period_key, {
                'identity': period_key, 'period': period_key, 'updatedValue': row.get('revenue'),
                'title': 'New saved statement period', 'original': 'No saved statement for this period',
                'updated': row.get('revenue'),
                'dates': f"{row.get('start')} to {row.get('end')}",
                'calculation': f"New {row.get('type')} period. Revenue {row.get('revenue')} {row.get('revenueUnit') or row.get('currency')}. It is not compared with a different period length.",
                'source': 'Saved SEC statement', 'currency': row.get('currency'),
            }, row.get('availableAt'), now_ms, gapped, settings))
            continue
        if previous.get('currency') != row.get('currency') or (previous.get('revenueUnit') and row.get('revenueUnit') and previous.get('revenueUnit') != row.get('revenueUnit')):
            found.append(_change(follow, 'revision', period_key + '|unlike', {
                'identity': period_key + '|unlike', 'period': period_key,
                'title': 'Saved figure not compared', 'original': previous.get('revenue'), 'updated': row.get('revenue'),
                'dates': f"{row.get('start')} to {row.get('end')}",
                'calculation': 'The currency or unit differs. No conversion was applied and the figures were not subtracted.',
                'source': 'Saved SEC statement',
            }, row.get('availableAt'), now_ms, gapped, settings))
            continue
        if previous.get('revenue') != row.get('revenue') and previous.get('revenue') is not None and row.get('revenue') is not None:
            found.append(_change(follow, 'revision', period_key + f"|{previous.get('revenue')}|{row.get('revenue')}", {
                'identity': period_key + f"|{previous.get('revenue')}|{row.get('revenue')}", 'period': period_key, 'updatedValue': row.get('revenue'),
                'title': 'Revised saved revenue', 'original': previous.get('revenue'), 'updated': row.get('revenue'),
                'dates': f"{row.get('start')} to {row.get('end')}",
                'calculation': f"Same {row.get('type')} period, {row.get('currency') or 'saved currency'}. Updated minus original is {row.get('revenue') - previous.get('revenue')}.",
                'source': 'Saved SEC statement', 'currency': row.get('currency'), 'unit': row.get('revenueUnit'),
            }, row.get('availableAt'), now_ms, gapped, settings))
    if not base.get('periods') and not current.get('periods') and ('missing', 'filing') not in known:
        found.append(_change(follow, 'missing', 'filing', {
            'identity': 'filing',
            'title': 'No saved statement', 'original': 'Not saved', 'updated': 'Still not saved',
            'dates': '', 'calculation': 'No supported SEC statement is saved. No revenue or profit was invented.',
            'source': 'Saved SEC facts',
        }, 0, now_ms, gapped, settings))
    seen_forecasts = {(row.get('anchorDay'), row.get('targetDay'), row.get('horizon')) for row in base.get('forecasts') or []}
    for row in current.get('forecasts') or []:
        identity = (row.get('anchorDay'), row.get('targetDay'), row.get('horizon'))
        if identity in seen_forecasts:
            continue
        found.append(_change(follow, 'forecast', '|'.join(str(part) for part in identity), {
            'identity': '|'.join(str(part) for part in identity),
            'title': 'Graded forecast', 'original': row.get('forecastPrice'), 'updated': row.get('actualPrice'),
            'dates': f"{row.get('anchorDay')} to {row.get('targetDay')}",
            'calculation': 'The issued forecast and the later saved close are the graded pair. A later training run does not replace the issued record.',
            'source': 'Issued forecast scorecard',
        }, row.get('gradedAt'), now_ms, gapped, settings))
    seen_alerts = {(row.get('receivedAt'), row.get('price')) for row in base.get('alerts') or []}
    for row in current.get('alerts') or []:
        if (row.get('receivedAt'), row.get('price')) in seen_alerts:
            continue
        found.append(_change(follow, 'alert', f"{row.get('receivedAt')}|{row.get('price')}", {
            'identity': f"{row.get('receivedAt')}|{row.get('price')}",
            'title': 'Triggered price alert', 'original': 'Not triggered at the start', 'updated': row.get('price'),
            'dates': row.get('receivedAt'), 'calculation': row.get('rule') or 'A saved alert event was recorded after the follow.',
            'source': 'Saved price alert',
        }, row.get('receivedAt'), now_ms, gapped, settings))
    growth = (base.get('assumptions') or {}).get('growthPct')
    if growth is not None and current.get('periods'):
        compared = earnings62.assumptions({'growthPct': growth, 'marginPct': (base.get('assumptions') or {}).get('marginPct')}, _report_from_periods(current.get('periods')))
        row = (compared.get('comparisons') or [None])[0]
        if row and row.get('differencePP') is not None and abs(row['differencePP']) >= settings['thresholdPP']:
            found.append(_change(follow, 'assumption', row.get('period') or 'growth', {
                'identity': row.get('period') or 'growth',
                'title': 'Assumption to revisit', 'original': growth, 'updated': row.get('reported'),
                'dates': row.get('period') or '',
                'calculation': f"Reported revenue growth minus the saved assumption is {row['differencePP']} percentage points. The assumption was not edited. An operating-margin assumption is not subtracted from net margin.",
                'source': 'Saved scenario assumption and saved filing',
            }, now_ms, now_ms, gapped, settings))
        elif growth is not None and not compared.get('comparisons'):
            found.append(_change(follow, 'assumption', 'unavailable', {
                'identity': 'unavailable',
                'title': 'Assumption not compared', 'original': growth, 'updated': 'No comparable revenue change',
                'dates': '', 'calculation': compared.get('notice') or 'The filing does not have a like-for-like revenue change.',
                'source': 'Saved scenario assumption',
            }, now_ms, now_ms, gapped, settings))
    return found


def follow(g, note, now_ms):
    symbol = g['valid_symbol']((note or {}).get('symbol') or '')
    journal_id = str((note or {}).get('journalId') or '')[:32]
    settings = _settings((note or {}).get('settings'))
    base = snapshot(g, symbol, now_ms, note)
    ident = hashlib.sha256(f'{symbol}|{journal_id}'.encode()).hexdigest()[:16]
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        existing = con.execute('SELECT id,baseline,created_at FROM tracker65_follows WHERE id=?', (ident,)).fetchone()
        if existing:
            con.execute('UPDATE tracker65_follows SET settings=? WHERE id=?', (json.dumps(settings), ident))
            saved = json.loads(existing[1])
            saved['settingsKept'] = True
            return {'id': ident, 'symbol': symbol, 'baseline': saved, 'settings': settings, 'createdAt': existing[2], 'notice': 'This follow was already saved. The starting evidence was kept.'}
        con.execute('INSERT INTO tracker65_follows VALUES(?,?,?,?,?,?)', (ident, symbol, journal_id, json.dumps(base), json.dumps(settings), int(now_ms)))
    sweep(g, now_ms)
    return {'id': ident, 'symbol': symbol, 'baseline': base, 'settings': settings, 'createdAt': int(now_ms), 'notice': 'Starting evidence saved. The thesis and judgement were copied and not edited.'}


def _load_follows(con):
    rows = []
    for ident, symbol, journal_id, baseline, settings, created in con.execute('SELECT id,symbol,journal_id,baseline,settings,created_at FROM tracker65_follows'):
        rows.append({'id': ident, 'symbol': symbol, 'journalId': journal_id, 'baseline': json.loads(baseline), 'settings': json.loads(settings), 'createdAt': created})
    return rows


def sweep(g, now_ms=None):
    now_ms = int(g['time'].time() * 1000) if now_ms is None else int(now_ms)
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        follows = _load_follows(con)
    added = 0
    for follow_row in follows:
        current = snapshot(g, follow_row['symbol'], now_ms, follow_row['baseline'])
        gapped = _gap(g, follow_row['baseline'].get('capturedAt') or follow_row['createdAt'], now_ms)
        with contextlib.closing(g['db_connection']()) as con:
            init(con)
            existing = [item for item in _rows(con, follow_row['symbol']) if item['followId'] == follow_row['id']]
        proposed = _diffs(follow_row, current, now_ms, gapped, existing)
        with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
            init(con)
            for item in proposed:
                if item['body'].get('calculation') and item['gap']:
                    item['body']['calculation'] += ' Found after a recording gap. The evidence time is the saved time, not the time Market Desk was running.'
                cursor = con.execute('''INSERT OR IGNORE INTO tracker65_changes
                    VALUES(?,?,?,?,?,?,?,?,?,?)''', (
                    item['id'], item['followId'], item['symbol'], item['kind'], json.dumps(item['body']),
                    item['availableAt'], item['detectedAt'], 1 if item['gap'] else 0, None, item['notify']))
                added += cursor.rowcount
    return {'checked': len(follows), 'added': added, 'method': METHOD}


def _rows(con, symbol=None):
    if symbol:
        found = con.execute('SELECT id,follow_id,symbol,kind,body,available_at,detected_at,gap,acknowledged_at,notify FROM tracker65_changes WHERE symbol=? ORDER BY detected_at DESC, id', (symbol,)).fetchall()
    else:
        found = con.execute('SELECT id,follow_id,symbol,kind,body,available_at,detected_at,gap,acknowledged_at,notify FROM tracker65_changes ORDER BY detected_at DESC, id').fetchall()
    items = []
    for row in found:
        body = json.loads(row[4])
        items.append({'id': row[0], 'followId': row[1], 'symbol': row[2], 'kind': row[3], **body,
                      'availableAt': row[5], 'detectedAt': row[6], 'gap': bool(row[7]), 'acknowledgedAt': row[8], 'notify': row[9]})
    return items


def review_list(g, symbol=None):
    symbol = g['valid_symbol'](symbol) if symbol else ''
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        follows = _load_follows(con)
        items = _rows(con, symbol or None)
        reviews = [{'id': row[0], 'followId': row[1], 'createdAt': row[3], **json.loads(row[2])} for row in con.execute('SELECT id,follow_id,body,created_at FROM tracker65_reviews ORDER BY created_at DESC')]
    if symbol:
        follows = [row for row in follows if row['symbol'] == symbol]
        reviews = [row for row in reviews if row.get('symbol') == symbol or any(row['followId'] == follow['id'] for follow in follows)]
    companies = []
    for follow_row in follows:
        base = follow_row['baseline']
        own = [item for item in items if item['followId'] == follow_row['id'] and item['notify'] != 'hidden']
        if any(item['kind'] in ('filing', 'revision') for item in own):
            own = [item for item in own if item['kind'] != 'missing']
        due = base.get('reviewDate') or ''
        own.sort(key=lambda item: (0 if due else 1, 0 if item['kind'] == 'assumption' else 1, item['acknowledgedAt'] is not None, -item['detectedAt']))
        companies.append({'symbol': follow_row['symbol'], 'followId': follow_row['id'], 'journalId': follow_row['journalId'],
                          'title': base.get('title') or follow_row['symbol'], 'status': base.get('status') or 'open',
                          'expectation': base.get('expectation') or '', 'reviewDate': due, 'thresholdPP': follow_row['settings'].get('thresholdPP'),
                          'settings': follow_row['settings'], 'items': own})
    return {'method': METHOD, 'companies': companies, 'reviews': reviews[:30],
            'notice': 'Original thesis and judgement stay as saved. Edit them in the research journal.'}


def acknowledge(g, follow_id, now_ms, change_ids=None):
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        follow_row = con.execute('SELECT baseline FROM tracker65_follows WHERE id=?', (str(follow_id),)).fetchone()
        if not follow_row:
            raise ValueError('That follow is not saved on this Mac.')
        base = json.loads(follow_row[0])
        chosen = _rows(con)
        chosen = [item for item in chosen if item['followId'] == follow_id and item['acknowledgedAt'] is None and (not change_ids or item['id'] in change_ids)]
        for item in chosen:
            con.execute('UPDATE tracker65_changes SET acknowledged_at=? WHERE id=?', (int(now_ms), item['id']))
        review = {'symbol': base.get('symbol'), 'status': base.get('status'), 'expectation': base.get('expectation'),
                  'items': [{'id': item['id'], 'title': item.get('title'), 'original': item.get('original'), 'updated': item.get('updated')} for item in chosen],
                  'notice': 'Acknowledged. The original thesis and judgement were not edited.'}
        ident = hashlib.sha256(json.dumps(review, sort_keys=True, default=str).encode()).hexdigest()[:16]
        con.execute('INSERT OR IGNORE INTO tracker65_reviews VALUES(?,?,?,?)', (ident, follow_id, json.dumps(review), int(now_ms)))
    return {'id': ident, **review}


def handle(g, question, context, now_ms):
    if not owns(question):
        return None
    symbol = str((context or {}).get('symbol') or '')
    try:
        symbol = g['valid_symbol'](symbol) if symbol else ''
    except Exception:
        symbol = ''
    words = str(question or '').lower()
    packet = review_list(g, symbol or None)
    companies = packet['companies']
    if 'assumptions' in words:
        items = [item for company in companies for item in company['items'] if item['kind'] == 'assumption' and not item['acknowledgedAt']]
        if not companies:
            text = 'Follow the company or the saved research entry first. No assumption was compared.'
        elif not items:
            text = 'No saved assumption is outside the threshold you chose. The original assumption was not edited.'
        else:
            text = ' '.join(f"{item['symbol']}: saved {item.get('original')} and the comparable figure is {item.get('updated')}. {item.get('calculation')}" for item in items[:4])
        return _answer(question, text, items, symbol, bool(items))
    if not companies:
        return None
    items = [item for company in companies for item in company['items'] if not item['acknowledgedAt'] and item['notify'] != 'hidden']
    if not items:
        text = 'Nothing newly saved is waiting since this follow. The original thesis and judgement were kept.'
    else:
        text = ' '.join(f"{item['symbol']} {item.get('title')}: {item.get('original')} then {item.get('updated')}. {item.get('dates')}" for item in items[:6])
    text += ' Your saved judgement was not changed.'
    return _answer(question, text, items, symbol or companies[0]['symbol'], True)


def _answer(question, text, items, symbol, supported):
    return {'question': question, 'kind': 'journal', 'offline': True, 'supported': supported, 'answer': text,
            'evidence': {'kind': 'observed fact', 'figures': [{'label': item.get('title') or item['kind'], 'value': item.get('updated'), 'unit': ''} for item in items[:6]],
                         'source': 'Saved follow comparison', 'gaps': [] if items else ['No unacknowledged change is saved.']},
            'context': {'kind': 'journal', 'symbol': symbol}}
