"""Connected Intelligence. Read-only calls into the tools the screens already use.

A number is shown only after the same calculation the screen uses. A save is a
proposal until it is confirmed. News text is evidence, not a cause.
"""
import contextlib
import hashlib
import json

import earnings62
import forecast61
import scanner55

METHOD = 'connected-intelligence-v6.4'
AREAS = ('chart', 'crypto', 'heatmap', 'comparison', 'events', 'financials', 'forecast', 'alerts', 'scan', 'portfolio', 'scenario', 'strategy', 'journal', 'report')


def question(text):
    words = str(text or '').lower()
    return any(phrase in words for phrase in (
        'match my scan', 'contributed most', 'saved scenario', 'beaten its baseline',
        'saved this investigation', 'what about it',
    ))


def _packet(area, answer, *, kind='observed fact', figures=None, coverage='', source='', gaps=None, supported=True):
    return {
        'method': METHOD, 'area': area, 'kind': kind, 'supported': supported, 'offline': True,
        'answer': answer, 'figures': figures or [], 'coverage': coverage, 'source': source,
        'evidence': {'kind': kind, 'figures': figures or [], 'gaps': gaps or [], 'source': source, 'coverage': coverage},
    }


def chart_return(start, end):
    if not start or not end or start <= 0 or end <= 0:
        return _packet('chart', 'The chart does not have two saved prices for this period.', supported=False, gaps=['No return was calculated.'])
    change = (end / start - 1) * 100
    shown = round(change, 2)
    if abs(shown - change) > 0.05:
        return _packet('chart', 'The rounded return does not match the prices. No figure is shown.', supported=False, gaps=['Validation failed.'])
    return _packet('chart', f'The displayed prices move by {shown:.2f}%.', kind='observed fact',
                   figures=[{'label': 'Return', 'value': shown, 'unit': 'percent'}],
                   coverage='Calculated from the two displayed prices. Dividends are not added.',
                   source='Saved chart closes')


def forecast_claim(packet):
    lines = []
    for row in (packet or {}).get('horizons') or []:
        model, base = row.get('modelErrorPP'), row.get('baselineErrorPP')
        if model is None or base is None:
            continue
        learned = row.get('status') == 'learned'
        if learned and not model < base:
            return _packet('forecast', 'The record says the model won, but its error is not smaller than an unchanged price. No claim is shown.',
                           supported=False, gaps=['The forecast status and the errors disagree.'])
        if learned:
            word = 'beat an unchanged price'
        elif model < base:
            word = 'was closer on the later block, but the earlier block did not choose it, so it is not shown as a win against an unchanged price'
        else:
            word = 'did not beat an unchanged price'
        lines.append(f"The {row.get('horizon')} session check {word} ({model:.2f} versus {base:.2f} percentage points).")
    if not lines:
        return _packet('forecast', 'No baseline comparison is saved for this company.', supported=False, gaps=['No horizon errors were included.'])
    return _packet('forecast', ' '.join(lines), kind='model output', source=forecast61.SOURCE if hasattr(forecast61, 'SOURCE') else 'Saved forecast check',
                   coverage='The later block is separate from the choice. A later-only win is not treated as a win.')


def contribution(saved):
    result = (saved or {}).get('result') or saved or {}
    largest = result.get('largest')
    if not largest or largest.get('contributionUSD') is None:
        return _packet('portfolio', 'No saved portfolio change has a holding contribution. Nothing was invented.',
                       supported=False, gaps=['No saved stress test was attached.'])
    currencies = {row.get('currency') for row in result.get('holdings') or [] if row.get('currency')}
    if len(currencies) > 1:
        return _packet('portfolio', 'The holdings use more than one currency. No contribution is converted or ranked.',
                       supported=False, kind='observed fact', gaps=['Mixed currencies were not converted.'])
    return _packet('portfolio', f"{largest['symbol']} contributed {largest['contributionUSD']} USD in the saved test.",
                   kind='model output', figures=[{'label': largest['symbol'], 'value': largest['contributionUSD'], 'unit': 'USD'}],
                   source='Saved portfolio stress test', coverage=result.get('notice') or 'Opened from the saved test. It was not recalculated.')


def scenario_difference(saved_case, report):
    compared = earnings62.assumptions(saved_case or {}, report or {})
    if not compared.get('comparisons'):
        return _packet('scenario', compared.get('notice') or 'The scenario and the filing are not compared.',
                       kind='user assumption', supported=True, gaps=[compared.get('notice') or 'No comparable revenue change.'])
    row = compared['comparisons'][0]
    return _packet('scenario', f"Saved revenue growth {row['assumption']}% . Reported {row['reported']}% . Difference {row['differencePP']} percentage points. {compared.get('margin')}",
                   kind='user assumption', figures=[{'label': 'Growth difference', 'value': row['differencePP'], 'unit': 'percentage points'}],
                   source=row.get('period') or 'Saved scenario and saved filing', coverage='The original assumptions are unchanged. Operating margin is not subtracted from net margin.')


def scan_match(symbol, opened):
    result = (opened or {}).get('result') or {}
    found = next((match for match in result.get('matches') or [] if match.get('symbol') == symbol), None)
    if not found:
        return _packet('scan', f'{symbol or "This company"} is not in the saved scan result.', supported=True,
                       gaps=['The saved scan was not recalculated.'], source='Saved scan')
    return _packet('scan', found['symbol'] + ' matched on ' + found['date'] + '. ' + found.get('calculation', ''),
                   kind='observed fact', source='Saved scan', coverage='The stored calculation was not rerun.',
                   figures=[{'label': 'Close', 'value': found.get('close'), 'unit': found.get('currency') or 'saved price'}])


def investigation_change(saved):
    if not saved:
        return _packet('report', 'No saved investigation was attached.', supported=False, gaps=['Choose the saved investigation first.'])
    if saved.get('previousId'):
        text = 'A later version exists. The original investigation was kept.'
    else:
        text = 'No later version is saved. The original finding is unchanged.'
    return _packet('report', text, kind='observed fact', source='Saved investigation', coverage=saved.get('notice') or 'Reopened. It was not rebuilt.')


def ambiguous():
    return _packet('chart', 'Name the company, the dates, or the saved record. No calculation was run for this wording.',
                   supported=False, gaps=['The question does not choose a tool.'])


def handle(g, question, context, now_ms):
    words = str(question or '').lower().strip()
    context = context or {}
    if words in ('what about it', 'what about it?') or len(words) < 8:
        return ambiguous()
    if 'match' in words and 'scan' in words:
        if not context.get('scanId'):
            return _packet('scan', 'Choose a saved scan first. No match was guessed.', supported=False, gaps=['No scan id was attached.'])
        try:
            opened = scanner55.read(g, context.get('scanId'), now_ms)
        except ValueError as error:
            return _packet('scan', str(error), supported=False, gaps=[str(error)])
        return scan_match(str(context.get('symbol') or ''), opened)
    if 'contributed' in words:
        if not context.get('stressId'):
            return _packet('portfolio', 'Save the portfolio stress test first. No holding was ranked.', supported=False, gaps=['No saved stress test was attached.'])
        import stress58
        try:
            saved = stress58.read(g, context.get('stressId'))
        except ValueError as error:
            return _packet('portfolio', str(error), supported=False, gaps=[str(error)])
        return contribution(saved)
    if 'saved scenario' in words or 'differ from my saved' in words:
        import scenario53
        if not context.get('scenarioId'):
            return _packet('scenario', 'Choose a saved scenario first. No assumption was compared.', kind='user assumption', supported=False, gaps=['No scenario id was attached.'])
        try:
            opened = scenario53.read(g, context.get('scenarioId'), now_ms)
        except ValueError as error:
            return _packet('scenario', str(error), kind='user assumption', supported=False, gaps=[str(error)])
        case = next((item for item in (opened.get('saved') or {}).get('cases') or [] if item.get('name') == 'central'), None) or {}
        symbol = (opened.get('saved') or {}).get('symbol') or context.get('symbol')
        report = g.get('sec_saved', lambda _symbol: {})(symbol) or {}
        return scenario_difference({'growthPct': case.get('growthPct'), 'marginPct': case.get('marginPct')}, report)
    if 'baseline' in words and 'forecast' in words:
        symbol = str(context.get('symbol') or 'TTWO')
        packet = forecast61.for_symbol(g, symbol, now_ms, remember_result=False)
        return forecast_claim(packet)
    if 'saved this investigation' in words:
        import desk61
        if not context.get('investigationId'):
            return _packet('report', 'Choose a saved investigation first.', supported=False, gaps=['No investigation id was attached.'])
        try:
            saved = desk61.read(g, context.get('investigationId'))
        except ValueError as error:
            return _packet('report', str(error), supported=False, gaps=[str(error)])
        return investigation_change(saved)
    return None


def propose(action, detail):
    return {'method': METHOD, 'status': 'proposed', 'saved': False, 'action': str(action or '')[:40],
            'change': str(detail or '')[:500], 'notice': 'Nothing was saved. Confirm to keep a copy of this request. It does not arm an alert or edit a scenario.'}


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS intelligence64(
        id TEXT PRIMARY KEY, symbol TEXT NOT NULL, body TEXT NOT NULL, created_at INTEGER NOT NULL)''')


def save(g, packet, now_ms):
    body = dict(packet or {})
    body['savedAt'] = int(now_ms)
    body['notice'] = 'Saved on this Mac. Reopening reads this copy and does not rebuild it.'
    ident = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:16]
    body['id'] = ident
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('INSERT OR REPLACE INTO intelligence64 VALUES(?,?,?,?)', (ident, str(body.get('symbol') or '')[:16], json.dumps(body, default=str), int(now_ms)))
    return body


def confirm(g, proposal, accepted, now_ms):
    if not accepted:
        return {'status': 'cancelled', 'saved': False, 'notice': 'The proposed change was not saved.'}
    if not isinstance(proposal, dict) or proposal.get('status') != 'proposed':
        raise ValueError('Confirm the proposal that was just shown.')
    stored = save(g, {'symbol': '', 'area': 'request', 'kind': 'user assumption', 'answer': proposal.get('change') or '',
                      'proposal': proposal}, now_ms)
    stored['notice'] = 'The request was saved. No alert was armed and no scenario number was changed.'
    return stored


def read(g, ident):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        row = con.execute('SELECT body FROM intelligence64 WHERE id=?', (str(ident or ''),)).fetchone()
    if not row:
        raise ValueError('That investigation is not saved on this Mac.')
    saved = json.loads(row[0])
    saved['notice'] = 'Opened from the saved investigation. It was not rebuilt.'
    return saved
