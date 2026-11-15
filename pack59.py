"""Company research packs. A saved edition is a snapshot, not a live recalculation.

Only sections with evidence are included. Edited wording does not replace the
source attached to a figure. A later edition is a new record.
"""
import contextlib
import datetime as dt
import hashlib
import html
import json
import math

import events42

METHOD = 'research-pack-v5.9'
SECTIONS = ('prices', 'move', 'events', 'financials', 'comparison', 'scenario', 'forecast', 'journal', 'annotations', 'earnings')
LABELS = {
    'prices': 'historical fact', 'move': 'historical fact', 'events': 'historical fact',
    'financials': 'historical fact', 'comparison': 'historical fact',
    'scenario': 'user assumption', 'forecast': 'model output', 'journal': 'user assumption',
    'annotations': 'user assumption', 'earnings': 'historical fact',
}
TITLES = {
    'prices': 'Price history', 'move': 'Move Review', 'events': 'Company events',
    'financials': 'Supported financials', 'comparison': 'Comparison',
    'scenario': 'Company simulator', 'forecast': 'Forecast scorecard', 'journal': 'Research journal',
    'annotations': 'Chart annotations', 'earnings': 'Results review',
}
SECRET = {'finnhub_key', 'massive_key', 'token', 'authorization', 'password', 'api_key', 'apikey'}


def _num(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return round(float(value), 4)


def _figure(label, value, source, kind, record=''):
    return {'label': label, 'value': value, 'source': source, 'kind': kind, 'record': record}


def _prices(points):
    clean = []
    for row in points or []:
        price = _num(row.get('price'))
        day = str(row.get('date') or '')[:10]
        if price is None or price <= 0 or len(day) != 10:
            continue
        clean.append({'date': day, 'price': price, 'source': str(row.get('source') or 'Saved daily close')[:180]})
    if len(clean) < 2:
        return None
    first, last = clean[0], clean[-1]
    change = (last['price'] / first['price'] - 1) * 100
    return {
        'id': 'prices', 'title': TITLES['prices'], 'kind': LABELS['prices'],
        'finding': f"Saved close moved from {first['price']:g} on {first['date']} to {last['price']:g} on {last['date']} ({change:.2f}%).",
        'coverage': f'{len(clean)} saved closes. No missing close was filled in.',
        'chart': clean[-40:],
        'figures': [_figure('Start close', first['price'], first['source'], 'historical fact', first['date']),
                    _figure('End close', last['price'], last['source'], 'historical fact', last['date'])],
    }


def _move(review):
    if not review or review.get('status') != 'ready':
        return None
    return {
        'id': 'move', 'title': TITLES['move'], 'kind': LABELS['move'],
        'finding': f"{review['symbol']} {review['returnPct']:.2f}% from {review['startPrice']:g} on {review['start']} to {review['endPrice']:g} on {review['end']}.",
        'coverage': review.get('evidence') or 'The saved records do not explain the move.',
        'figures': [_figure('Move return', round(review['returnPct'], 4), review.get('source') or 'Saved closes', 'historical fact', review['start'] + ' to ' + review['end'])],
    }


def _events(rows):
    usable = []
    for row in rows or []:
        title = str(row.get('title') or '').strip()
        if not title:
            continue
        usable.append({'title': title[:180], 'date': str(row.get('date') or row.get('published') or '')[:32],
                       'source': str(row.get('source') or 'Saved event')[:180]})
    if not usable:
        return None
    return {
        'id': 'events', 'title': TITLES['events'], 'kind': LABELS['events'],
        'finding': f'{len(usable)} saved event{"s" if len(usable) != 1 else ""}. The newest is “{usable[0]["title"]}”.',
        'coverage': 'Only saved events are listed. A missing announcement is not treated as “none happened”.',
        'figures': [_figure(row['title'], row['date'], row['source'], 'historical fact', row['date']) for row in usable[:8]],
    }


def _financials(statement):
    rows = [row for row in (statement or {}).get('rows') or [] if row.get('name') and _num(row.get('valueM')) is not None]
    if not rows:
        return None
    source = str(statement.get('source') or 'Saved filing')
    period = str(statement.get('period') or 'period not recorded')
    return {
        'id': 'financials', 'title': TITLES['financials'], 'kind': LABELS['financials'],
        'finding': f"{rows[0]['name']} is {rows[0]['valueM']:g} million {statement.get('currency') or 'USD'} for {period}.",
        'coverage': 'Figures are the saved filing amounts. Nothing was estimated.',
        'figures': [_figure(row['name'], row['valueM'], source, 'historical fact', period) for row in rows[:8]],
    }


def _comparison(saved):
    if not saved or not saved.get('symbols'):
        return None
    change = _num((saved.get('result') or {}).get('changePct'))
    if change is None:
        rows = saved.get('rows') or []
        lead = next((row for row in rows if row.get('symbol') == saved['symbols'][0]), rows[0] if rows else None)
        change = _num((lead or {}).get('returnPct'))
    if change is None:
        return None
    others = ', '.join(saved['symbols'][1:]) or 'the saved set'
    return {
        'id': 'comparison', 'title': TITLES['comparison'], 'kind': LABELS['comparison'],
        'finding': f"{saved['symbols'][0]} {change:.2f}% from {saved.get('start')} to {saved.get('end')} in the saved comparison with {others}.",
        'coverage': 'This is the comparison stored at the time. It was not recalculated for the pack.',
        'figures': [_figure(saved['symbols'][0] + ' saved return', change, 'Saved comparison', 'historical fact', saved.get('id') or '')],
    }


def _scenario(saved):
    if not saved:
        return None
    assumptions = saved.get('assumptions') or {}
    result = saved.get('result') or {}
    if assumptions.get('growthPct') is None and result.get('perShare') is None:
        return None
    figures = []
    if assumptions.get('growthPct') is not None:
        figures.append(_figure('Growth assumption', assumptions['growthPct'], 'Typed scenario assumption', 'user assumption', saved.get('id') or ''))
    if result.get('perShare') is not None:
        figures.append(_figure('Year-5 value per share', result['perShare'], 'Company simulator ' + str(saved.get('model') or ''), 'model output', saved.get('id') or ''))
    return {
        'id': 'scenario', 'title': TITLES['scenario'], 'kind': 'user assumption',
        'finding': 'The saved scenario keeps the assumptions and the year-5 result from when it was stored.',
        'coverage': 'A later filing does not rewrite this scenario.',
        'figures': figures,
    }


def _forecast(card):
    graded = (card or {}).get('graded') or []
    pending = (card or {}).get('pending') or []
    if not graded and not pending:
        return None
    figures = []
    for row in graded[:6]:
        when = str(row.get('targetDate') or '')
        figures.append(_figure('Graded ' + when, (row.get('outcome') or {}).get('absoluteErrorPP'),
                               str(row.get('method') or 'Issued forecast'), 'model output', when))
    for row in pending[:4]:
        when = str(row.get('targetDate') or '')
        figures.append(_figure('Pending ' + when, row.get('forecastPrice'), str(row.get('method') or 'Issued forecast'), 'model output', when))
    summary = (card or {}).get('summary') or {}
    finding = f"{len(graded)} graded and {len(pending)} waiting. "
    if summary.get('count'):
        finding += f"Average error {summary.get('averageErrorPP')} percentage points."
    else:
        finding += 'No graded error yet.'
    return {'id': 'forecast', 'title': TITLES['forecast'], 'kind': LABELS['forecast'], 'finding': finding,
            'coverage': 'Issued forecasts only. A historical backtest is not included.', 'figures': figures}


def _journal(entries):
    rows = []
    for entry in entries or []:
        title = str(entry.get('title') or '').strip()
        if not title:
            continue
        rows.append({'title': title[:160], 'evidence': str((entry.get('evidence') or {}).get('source') or 'Journal entry')[:180]})
    if not rows:
        return None
    return {
        'id': 'journal', 'title': TITLES['journal'], 'kind': LABELS['journal'],
        'finding': f'{len(rows)} journal entr{"ies" if len(rows) != 1 else "y"} copied into this edition.',
        'coverage': 'The wording here is the entry at the time of the snapshot.',
        'figures': [_figure(row['title'], row['title'], row['evidence'], 'user assumption', '') for row in rows[:8]],
    }


def _annotations(rows):
    items = [row for row in rows or [] if row.get('kind') in ('level', 'trend', 'note', 'measure')]
    if not items:
        return None
    figures = []
    for row in items[:8]:
        label = row.get('kind')
        value = row.get('changePct') if row.get('kind') == 'measure' else row.get('price', row.get('text', ''))
        figures.append(_figure(str(label), value, 'Saved chart annotation', 'user assumption', str(row.get('id') or '')))
    return {
        'id': 'annotations', 'title': TITLES['annotations'], 'kind': LABELS['annotations'],
        'finding': f'{len(items)} saved chart annotation{"s" if len(items) != 1 else ""} copied into this edition.',
        'coverage': 'Anchored to the saved instrument, price and time. Editing the overview does not move them.',
        'figures': figures,
    }


def _earnings(saved):
    cards = (saved or {}).get('cards') or []
    annual = next((card for card in cards if card.get('type') == 'annual' and (card.get('revenueChange') or {}).get('available')), None)
    if not annual:
        return None
    change = annual['revenueChange']['changePct']
    return {
        'id': 'earnings', 'title': TITLES['earnings'], 'kind': LABELS['earnings'],
        'finding': f"Saved revenue change {change:.2f}% for {annual['start']} to {annual['end']}.",
        'coverage': 'Copied from the saved results review. It was not recalculated. Operating profit was not added.',
        'figures': [_figure('Revenue change', round(change, 2), annual.get('currency') or 'USD', 'historical fact', saved.get('id') or '')],
    }


def build(symbol, name, parts, wording=''):
    """Assemble a pack. A section without evidence is named in omitted and left out."""
    makers = {
        'prices': _prices, 'move': _move, 'events': _events, 'financials': _financials,
        'comparison': _comparison, 'scenario': _scenario, 'forecast': _forecast,         'journal': _journal,
        'annotations': _annotations, 'earnings': _earnings,
    }
    chosen = parts.get('selected') or SECTIONS
    sections, omitted = [], []
    for key in SECTIONS:
        if key not in chosen:
            continue
        section = makers[key](parts.get(key))
        if section:
            sections.append(section)
        else:
            omitted.append({'id': key, 'title': TITLES[key], 'reason': 'No saved evidence for this section.'})
    overview = ' '.join(section['finding'] for section in sections) or 'No selected section had saved evidence.'
    text = str(wording or '').strip()
    return {
        'method': METHOD, 'symbol': symbol, 'name': name or symbol, 'edition': int(parts.get('edition') or 1),
        'previousId': parts.get('previousId'), 'overview': overview,
        'wording': text, 'wordingEdited': bool(text),
        'sections': sections, 'omitted': omitted,
        'createdAt': parts.get('createdAt'),
    }


def display_text(body):
    if body.get('wordingEdited') and body.get('wording'):
        return body['wording']
    return body.get('overview') or ''


def diff(older, newer):
    """Differences are calculated from the two saved editions only."""
    def events(body):
        section = next((item for item in body.get('sections') or [] if item['id'] == 'events'), None)
        return {(row['label'], str(row['value'])) for row in (section or {}).get('figures') or []}
    def figures(body, section_id, kind=None):
        section = next((item for item in body.get('sections') or [] if item['id'] == section_id), None)
        found = {}
        for row in (section or {}).get('figures') or []:
            if kind and row.get('kind') != kind:
                continue
            found[row['label']] = row.get('value')
        return found
    added = [{'title': label, 'date': value} for label, value in sorted(events(newer) - events(older))]
    financial_old, financial_new = figures(older, 'financials'), figures(newer, 'financials')
    changed_financials = [{'name': key, 'from': financial_old.get(key), 'to': financial_new[key]}
                          for key in financial_new if financial_old.get(key) != financial_new[key]]
    assume_old, assume_new = figures(older, 'scenario', 'user assumption'), figures(newer, 'scenario', 'user assumption')
    changed_assumptions = [{'name': key, 'from': assume_old.get(key), 'to': assume_new[key]}
                           for key in assume_new if key in assume_old and assume_old[key] != assume_new[key]]
    forecast_old = figures(older, 'forecast')
    forecast_new = figures(newer, 'forecast')
    newly_graded = [{'name': key, 'value': forecast_new[key]} for key in forecast_new if key.startswith('Graded') and key not in forecast_old]
    return {
        'olderEdition': older.get('edition'), 'newerEdition': newer.get('edition'),
        'newAnnouncements': added, 'changedFinancials': changed_financials,
        'changedAssumptions': changed_assumptions, 'newlyGraded': newly_graded,
        'notice': 'Compared from the two saved editions. Live records were not read.',
    }


def _public(value):
    if isinstance(value, dict):
        return {key: _public(item) for key, item in value.items() if key.lower() not in SECRET}
    if isinstance(value, list):
        return [_public(item) for item in value]
    return value


def html_export(body):
    body = _public(body)
    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8"><title>',
             html.escape(body.get('symbol') or 'Report'), ' research pack</title><style>',
             'body{font-family:Georgia,serif;color:#122033;margin:32px;line-height:1.45}',
             'h1,h2{font-family:-apple-system,sans-serif} .kind{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:#2756a8}',
             'svg{width:100%;height:160px;background:#f4f7fb;border-radius:12px} .appendix{margin-top:28px}',
             '@media print{body{margin:16mm} a{color:#122033;text-decoration:none} svg{break-inside:avoid}}',
             '</style></head><body><p class="kind">Research pack · edition ', html.escape(str(body.get('edition') or '')),
             '</p><h1>', html.escape(body.get('name') or ''), ' · ', html.escape(body.get('symbol') or ''), '</h1><p>',
             html.escape(display_text(body)), '</p>']
    if body.get('wordingEdited'):
        parts.append('<p class="kind">Edited wording. Source lines below are unchanged.</p>')
    for section in body.get('sections') or []:
        parts.append('<h2>' + html.escape(section['title']) + '</h2><p class="kind">' + html.escape(section['kind']) + '</p><p>' + html.escape(section['finding']) + '</p>')
        chart = section.get('chart') or []
        if len(chart) >= 2:
            prices = [row['price'] for row in chart]
            low, high = min(prices), max(prices)
            span = high - low or 1
            coords = []
            for index, price in enumerate(prices):
                x = index / (len(prices) - 1) * 100
                y = 10 + (high - price) / span * 80
                coords.append(f'{x:.2f},{y:.2f}')
            shown = ','.join(f'{price:g}' for price in prices)
            parts.append('<svg viewBox="0 0 100 100" role="img" data-prices="' + html.escape(shown) + '"><polyline fill="none" stroke="#2756a8" stroke-width="1.5" points="' + ' '.join(coords) + '"/></svg>')
        parts.append('<details><summary>Coverage and figures</summary><p>' + html.escape(section.get('coverage') or '') + '</p><ul>')
        for row in section.get('figures') or []:
            parts.append('<li>' + html.escape(f"{row['label']}: {row['value']} · {row['kind']} · {row['source']}") + '</li>')
        parts.append('</ul></details>')
    parts.append('<section class="appendix"><h2>Appendix</h2><p>Omitted sections had no saved evidence.</p><ul>')
    for row in body.get('omitted') or []:
        parts.append('<li>' + html.escape(row['title'] + ': ' + row['reason']) + '</li>')
    parts.append('</ul></section></body></html>')
    document = ''.join(parts)
    if any(secret in document.lower() for secret in ('finnhub_key', 'massive_key', 'authorization')):
        raise ValueError('The export contained a credential field and was stopped.')
    return document


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS pack59(
        id TEXT PRIMARY KEY, symbol TEXT NOT NULL, edition INTEGER NOT NULL,
        previous_id TEXT, body TEXT NOT NULL, created_at INTEGER NOT NULL)''')


def store(g, body, now_ms):
    body = _public(dict(body))
    body['createdAt'] = int(now_ms)
    ident = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:16]
    body['id'] = ident
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('INSERT OR REPLACE INTO pack59 VALUES(?,?,?,?,?,?)',
                    (ident, body['symbol'], body.get('edition') or 1, body.get('previousId'), json.dumps(body), int(now_ms)))
    return body


def read(g, ident):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        row = con.execute('SELECT body FROM pack59 WHERE id=?', (ident,)).fetchone()
    if not row:
        raise ValueError('That research pack was not found.')
    body = json.loads(row[0])
    body['notice'] = 'Opened from the saved edition. It was not rebuilt.'
    return body


def new_edition(g, previous_id, parts, wording, now_ms):
    previous = read(g, previous_id)
    if isinstance(parts, dict) and 'sections' in parts:
        body = dict(parts)
        body['symbol'] = previous['symbol']
        body['name'] = previous.get('name') or body.get('name') or previous['symbol']
    else:
        parts = dict(parts)
        parts['edition'] = int(previous.get('edition') or 1) + 1
        parts['previousId'] = previous_id
        body = build(previous['symbol'], previous.get('name') or previous['symbol'], parts, wording)
    body['edition'] = int(previous.get('edition') or 1) + 1
    body['previousId'] = previous_id
    if wording:
        body['wording'] = str(wording).strip()
        body['wordingEdited'] = bool(body['wording'])
    body.pop('notice', None)
    body.pop('id', None)
    return store(g, body, now_ms)


def edit_wording(g, ident, wording, now_ms):
    body = read(g, ident)
    sources = json.dumps([section.get('figures') for section in body.get('sections') or []])
    body.pop('notice', None)
    body['wording'] = str(wording or '').strip()
    body['wordingEdited'] = bool(body['wording'])
    body['id'] = ident
    if json.dumps([section.get('figures') for section in body.get('sections') or []]) != sources:
        raise RuntimeError('Editing the wording changed a source.')
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('UPDATE pack59 SET body=?, created_at=? WHERE id=?', (json.dumps(body), int(now_ms), ident))
    return body


def collect(g, symbol, selected=None, now_ms=None):
    symbol = g['valid_symbol'](symbol)
    now_ms = int(g['time'].time() * 1000) if now_ms is None else int(now_ms)
    parts = {'selected': selected or list(SECTIONS)}
    closes = []
    try:
        with contextlib.closing(g['db_connection']()) as con:
            rows = con.execute('SELECT ts_ms,c FROM massive_daily_bars WHERE symbol=? ORDER BY ts_ms', (symbol,)).fetchall()
        for stamp, price in rows:
            if isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0:
                continue
            day = dt.datetime.fromtimestamp(stamp / 1000, events42.NY).date()
            if events42.is_session(day):
                row = {'date': day.isoformat(), 'price': float(price), 'source': 'Massive split-adjusted daily close'}
                if closes and closes[-1]['date'] == row['date']:
                    closes[-1] = row
                else:
                    closes.append(row)
    except Exception:
        closes = []
    parts['prices'] = closes
    if len(closes) >= 2:
        try:
            import move44
            parts['move'] = move44.review(g, symbol, closes[-2]['date'], closes[-1]['date'], now_ms)
        except Exception:
            parts['move'] = None
    try:
        saved = events42.load(g, symbol) or {}
        parts['events'] = saved.get('events') or []
    except Exception:
        parts['events'] = []
    try:
        blob = g.get('sec_saved', lambda _symbol: {})(symbol) or {}
        annual = blob.get('annual') or blob.get('statements') or []
        parts['financials'] = annual if isinstance(annual, dict) else None
    except Exception:
        parts['financials'] = None
    try:
        with contextlib.closing(g['db_connection']()) as con:
            rows = con.execute('SELECT body FROM compare52 ORDER BY created_at DESC').fetchall()
        for (raw,) in rows:
            saved = json.loads(raw)
            if symbol in (saved.get('symbols') or []):
                parts['comparison'] = saved
                break
    except Exception:
        parts['comparison'] = None
    try:
        with contextlib.closing(g['db_connection']()) as con:
            row = con.execute('SELECT body FROM scenario53 WHERE symbol=? ORDER BY created_at DESC LIMIT 1', (symbol,)).fetchone()
        parts['scenario'] = json.loads(row[0]) if row else None
    except Exception:
        parts['scenario'] = None
    try:
        import scorecard41
        parts['forecast'] = scorecard41.read(g, symbol)
    except Exception:
        parts['forecast'] = None
    try:
        journal = ((g['read_workspace']().get('snapshot') or {}).get('journal') or [])
        parts['journal'] = [entry for entry in journal if str(entry.get('symbol') or '').upper() == symbol]
    except Exception:
        parts['journal'] = []
    try:
        import annotate60
        parts['annotations'] = annotate60.for_symbol(g, symbol)
    except Exception:
        parts['annotations'] = []
    name = symbol
    try:
        catalog = json.loads((g['ROOT'] / 'ai_catalog.json').read_text())
        name = next((row.get('name') or symbol for row in catalog if row.get('symbol') == symbol), symbol)
    except Exception:
        name = symbol
    return build(symbol, name, parts)


def question(text):
    words = str(text or '').lower()
    return 'research pack' in words or ('report' in words and 'edition' in words)


def explain(body):
    if not body:
        return 'Save the research pack first.', {'sampleSize': 0, 'gaps': ['No saved pack was included.']}
    lines = [display_text(body), f"Edition {body.get('edition')} keeps {len(body.get('sections') or [])} sections."]
    for section in body.get('sections') or []:
        lines.append(f"{section['title']} is labelled {section['kind']}.")
    if body.get('omitted'):
        lines.append('Left out: ' + ', '.join(row['title'] for row in body['omitted']) + '.')
    return ' '.join(lines), {
        'sampleSize': len(body.get('sections') or []),
        'qualification': 'The answer uses the saved edition. Edited wording does not change the source on a figure.',
        'source': 'Saved research pack on this Mac.',
        'gaps': [row['reason'] for row in body.get('omitted') or []],
    }
