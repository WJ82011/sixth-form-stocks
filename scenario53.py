"""Three saved valuation scenarios from sourced figures and labelled assumptions.

The company value uses the analyst worksheet's enterprise multiple:
next year's sales, or next year's operating profit, times the multiple.
It is not a discounted cash-flow model and not a predicted trading price.
"""
import contextlib
import json
import math
import re

IDENT = re.compile(r'^[a-f0-9]{16}$')
NAMES = ('cautious', 'central', 'optimistic')
METHODS = ('EV/Sales', 'EV/Operating profit')
MODEL = 'scenario-multiple-v5.3'
YEARS = 5


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS scenario53(
        id TEXT PRIMARY KEY, symbol TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL, created_at INTEGER NOT NULL)''')


def _num(value, lo, hi, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(label + ' needs a finite number.')
    if not lo <= value <= hi:
        raise ValueError(label + ' is outside the supported range.')
    return float(value)


def _fact(period, key):
    fact = ((period or {}).get('metrics') or {}).get(key) or {}
    if 'value' not in fact:
        return None
    return fact


def _line(name, value, period, currency, source, kind, note):
    return {'name': name, 'valueM': value, 'unit': 'millions of ' + currency if value is not None else '',
            'period': period, 'currency': currency, 'source': source, 'kind': kind, 'note': note}


def figures(g, symbol):
    symbol = g['valid_symbol'](symbol)
    if not g['ai_catalog_entry'](symbol):
        raise ValueError(symbol + ' is not in the supported directory.')
    try:
        report = g['sec_saved'](symbol) or {}
    except Exception:
        report = {}
    annual = report.get('annual') or []
    period = annual[-1] if annual else None
    currency = (period or {}).get('currency') or report.get('unit') or ''
    window = ((period or {}).get('start') or '') + ' to ' + ((period or {}).get('end') or '') if period else ''
    revenue = _fact(period, 'revenue')
    cash = _fact(period, 'cash')
    profit = _fact(period, 'operatingProfit')
    debt = (period or {}).get('longTermDebt')
    rows = []
    if revenue and currency == 'USD':
        rows.append(_line('revenue', revenue['value'] / 1e6, window, currency, revenue.get('url') or '', 'sourced', 'Saved annual revenue divided by one million. Tag ' + str(revenue.get('tag') or '') + '.'))
    else:
        rows.append(_line('revenue', None, window, currency or 'not recorded', '', 'missing', 'No supported annual revenue is saved. Enter it in millions with a source note.'))
    if profit and revenue and profit.get('accession') == revenue.get('accession') and profit.get('unit') == currency:
        rows.append(_line('operating profit', profit['value'] / 1e6, window, currency, profit.get('url') or '', 'sourced', 'Saved operating profit from the same filing as revenue.'))
    else:
        rows.append(_line('operating profit', None, window, currency or 'not recorded', '', 'missing', 'Operating profit is not in the saved SEC facts. The margin you enter is an assumption, not a reported figure.'))
    if cash and cash.get('unit') == currency:
        rows.append(_line('cash', cash['value'] / 1e6, (period or {}).get('end') or '', currency, cash.get('url') or '', 'sourced', 'Cash and cash equivalents at the period end.'))
    else:
        rows.append(_line('cash', None, '', currency or 'not recorded', '', 'missing', 'Cash is missing. Equity value stays hidden until you enter it in the same currency.'))
    if isinstance(debt, (int, float)) and not isinstance(debt, bool) and math.isfinite(debt) and currency == 'USD':
        rows.append(_line('debt', debt / 1e6, (period or {}).get('end') or '', currency, '', 'sourced', (period or {}).get('debtScope') or 'Long-term debt portions only.'))
    else:
        rows.append(_line('debt', None, '', currency or 'not recorded', '', 'missing', 'Debt is missing or is not in the statement currency. It is not treated as zero.'))
    rows.append(_line('shares', None, '', currency or 'not recorded', '', 'missing', 'Share count is not taken from these statements. Enter diluted shares in millions with a source note before a per-share value is shown.'))
    history = []
    for item in annual[-6:]:
        sales = _fact(item, 'revenue')
        operating = _fact(item, 'operatingProfit')
        if not sales:
            continue
        history.append({'kind': 'history', 'end': item.get('end') or '', 'start': item.get('start') or '', 'currency': item.get('currency') or '',
                        'revenueM': sales['value'] / 1e6, 'operatingProfitM': operating['value'] / 1e6 if operating and operating.get('accession') == sales.get('accession') else None,
                        'source': sales.get('url') or '', 'note': 'Saved annual filing. Not a simulated year.'})
    return {'symbol': symbol, 'currency': currency or 'not recorded', 'start': (period or {}).get('start') or '', 'end': (period or {}).get('end') or '',
            'rows': rows, 'history': history, 'model': MODEL,
            'method': 'Each simulated year grows revenue by your rate and applies your operating margin. Company value equals that year\'s sales, or that year\'s operating profit, times your multiple. Equity value subtracts debt and adds cash. Value per share divides equity value by diluted shares. Year 5 is the value shown for the scenario.',
            'notice': 'Sourced rows come from saved annual SEC facts. Blank rows are not zero. Amounts are millions of the statement currency. Forecast Lab is a separate statistical record and is not used here.'}


def _manual(raw, name, currency):
    if not isinstance(raw, dict):
        return None
    if str(raw.get('unit') or '') != 'millions':
        raise ValueError(name + ' must be entered in millions of ' + currency + '.')
    if str(raw.get('currency') or '') != currency:
        raise ValueError(name + ' uses a different currency, so it is not combined with the statement figures.')
    note = str(raw.get('source') or '').strip()
    if len(note) < 8:
        raise ValueError(name + ' needs a source note.')
    return _num(raw.get('valueM'), -1e9, 1e9, name), note[:300]


def _baseline(payload):
    rows = {row['name']: row for row in payload.get('rows') or []}
    currency = str(payload.get('currency') or '')
    if not re.fullmatch(r'[A-Z]{3}', currency):
        raise ValueError('A three-letter statement currency is required before the scenarios can be combined.')
    revenue = rows.get('revenue') or {}
    value = revenue.get('valueM')
    note = 'Sourced annual revenue.'
    if value is None:
        value, note = _manual(payload.get('manual', {}).get('revenue'), 'Revenue', currency)
    revenue_m = _num(value, 0.000001, 1e9, 'Revenue')
    cash = (rows.get('cash') or {}).get('valueM')
    debt = (rows.get('debt') or {}).get('valueM')
    shares = None
    manuals = payload.get('manual') or {}
    if cash is None and manuals.get('cash'):
        cash, _note = _manual(manuals['cash'], 'Cash', currency)
    if debt is None and manuals.get('debt'):
        debt, _note = _manual(manuals['debt'], 'Debt', currency)
    if manuals.get('shares'):
        shares, _note = _manual(manuals['shares'], 'Shares', currency)
        shares = _num(shares, 0.000001, 1e9, 'Shares')
    return {'currency': currency, 'revenueM': revenue_m, 'cashM': cash, 'debtM': debt, 'sharesM': shares,
            'start': payload.get('start') or '', 'end': payload.get('end') or '', 'sourceNote': note}


def _one(base, case):
    growth = _num(case.get('growthPct'), -90, 300, case['name'] + ' revenue growth')
    margin = _num(case.get('marginPct'), -100, 80, case['name'] + ' operating margin')
    multiple = _num(case.get('multiple'), 0.01, 100, case['name'] + ' multiple')
    method = case.get('method')
    if method not in METHODS:
        raise ValueError('Choose EV/Sales or EV/Operating profit.')
    years = []
    revenue = base['revenueM']
    for year in range(1, YEARS + 1):
        revenue = revenue * (1 + growth / 100)
        profit = revenue * (margin / 100)
        denominator = revenue if method == 'EV/Sales' else profit
        enterprise = None
        reason = ''
        if denominator <= 0:
            reason = 'Company value is hidden because ' + ('sales' if method == 'EV/Sales' else 'operating profit') + ' is not positive.'
        else:
            enterprise = denominator * multiple
            reason = 'Year ' + str(year) + ' company value = ' + format(denominator, '.4f') + ' million ' + base['currency'] + ' × ' + format(multiple, '.4f') + '.'
        equity = None
        per_share = None
        if enterprise is None:
            pass
        elif base['cashM'] is None or base['debtM'] is None:
            reason += ' Equity value is hidden until cash and debt are both available in ' + base['currency'] + '.'
        else:
            equity = enterprise - (base['debtM'] - base['cashM'])
            reason += ' Equity value = company value − (debt − cash).'
            if base['sharesM'] is None:
                reason += ' Value per share is hidden until diluted shares are entered in millions.'
            elif equity <= 0:
                reason += ' Value per share is hidden because the equity value is not positive.'
            else:
                per_share = equity / base['sharesM']
                reason += ' Value per share = equity value ÷ diluted shares.'
        for amount in (revenue, profit, enterprise, equity, per_share):
            if amount is not None and abs(amount) > 1e12:
                raise ValueError('This scenario is outside the supported numeric range.')
        years.append({'year': year, 'kind': 'simulated', 'revenueM': revenue, 'operatingProfitM': profit, 'enterpriseM': enterprise,
                      'equityM': equity, 'valuePerShare': per_share, 'calculation': reason})
    last = years[-1]
    return {'name': case['name'], 'growthPct': growth, 'marginPct': margin, 'multiple': multiple, 'method': method,
            'revenueM': last['revenueM'], 'operatingProfitM': last['operatingProfitM'], 'enterpriseM': last['enterpriseM'],
            'equityM': last['equityM'], 'valuePerShare': last['valuePerShare'], 'years': years,
            'unit': 'million ' + base['currency'], 'calculation': last['calculation'] + ' Cash and debt stay at the latest saved amounts in every simulated year.'}


def _sensitivity(base, central):
    probes = (('revenue growth', 'growthPct', 2), ('operating margin', 'marginPct', 2), ('valuation multiple', 'multiple', 0.5))
    rows = []
    origin = _one(base, central)['enterpriseM']
    for label, key, step in probes:
        moved = []
        for sign in (-1, 1):
            trial = dict(central)
            trial[key] = central[key] + sign * step
            try:
                value = _one(base, trial)['enterpriseM']
            except ValueError:
                value = None
            moved.append(value)
        deltas = [None if value is None or origin is None else value - origin for value in moved]
        span = max((abs(item) for item in deltas if item is not None), default=None)
        rows.append({'driver': label, 'step': step, 'lower': moved[0], 'higher': moved[1], 'span': span})
    ranked = sorted((row for row in rows if row['span'] is not None), key=lambda row: row['span'], reverse=True)
    return {'centralEnterpriseM': origin, 'rows': rows, 'strongest': ranked[0]['driver'] if ranked else ''}


def calculate(payload):
    base = _baseline(payload)
    incoming = payload.get('scenarios') or []
    if not isinstance(incoming, list):
        raise ValueError('Add the cautious, central and optimistic assumptions.')
    found = []
    for name in NAMES:
        case = next((row for row in incoming if isinstance(row, dict) and row.get('name') == name), None)
        if not case:
            raise ValueError('Add the ' + name + ' assumptions.')
        found.append(_one(base, {**case, 'name': name}))
    central = next(row for row in incoming if row.get('name') == 'central')
    axes = payload.get('axes') if isinstance(payload.get('axes'), list) else ['growthPct', 'marginPct']
    return {'model': MODEL, 'baseline': base, 'cases': found, 'sensitivity': _sensitivity(base, {**central, 'name': 'central'}),
            'grid': _grid(base, {**central, 'name': 'central'}, axes[:2]), 'notes': _notes(payload.get('notes')),
            'notice': 'Growth, margin and the multiple are your assumptions. Saved history stops at the latest filing. Years 1 to 5 are conditional calculations, not a Forecast Lab result. Cash and debt are not grown.'}


def _notes(raw):
    if not raw:
        return []
    if not isinstance(raw, list) or len(raw) > 8:
        raise ValueError('Attach up to 8 dated notes.')
    notes = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError('A note needs a date, a source and your assumption.')
        day = str(item.get('date') or '')[:10]
        try:
            __import__('datetime').date.fromisoformat(day)
        except ValueError:
            raise ValueError('Use a dated source for the note.')
        source = str(item.get('source') or '').strip()
        text = str(item.get('assumption') or '').strip()
        if len(source) < 8 or len(text) < 8:
            raise ValueError('Write the source and your own assumption. The source is not checked for you.')
        notes.append({'date': day, 'source': source[:300], 'assumption': text[:500], 'kind': 'assumption'})
    return notes


def _grid(base, central, axes):
    labels = {'growthPct': 'revenue growth', 'marginPct': 'operating margin', 'multiple': 'valuation multiple'}
    chosen = [axis for axis in axes if axis in labels][:2]
    if len(chosen) < 2:
        chosen = ['growthPct', 'marginPct']
    steps = {'growthPct': (-5, 0, 5), 'marginPct': (-5, 0, 5), 'multiple': (-1, 0, 1)}
    columns = [central[chosen[0]] + step for step in steps[chosen[0]]]
    rows = []
    for step in steps[chosen[1]]:
        values = []
        for column in columns:
            trial = dict(central)
            trial[chosen[0]] = column
            trial[chosen[1]] = central[chosen[1]] + step
            try:
                values.append(_one(base, trial)['enterpriseM'])
            except ValueError:
                values.append(None)
        rows.append({'input': central[chosen[1]] + step, 'values': values})
    return {'x': labels[chosen[0]], 'y': labels[chosen[1]], 'columns': columns, 'rows': rows,
            'notice': 'Each cell changes only the two selected assumptions. The other assumption stays at the central case. Empty cells are outside the supported result.'}


def solve(payload):
    base = _baseline(payload)
    case = payload.get('case') if isinstance(payload.get('case'), dict) else None
    if not case:
        case = next((row for row in payload.get('scenarios') or [] if isinstance(row, dict) and row.get('name') == 'central'), None)
    if not case:
        raise ValueError('Choose the assumptions to hold fixed.')
    target = _num(payload.get('price'), 0.01, 1e7, 'Share price')
    unknown = payload.get('unknown')
    if unknown not in ('growthPct', 'multiple'):
        raise ValueError('Solve for revenue growth or the valuation multiple.')
    if base['sharesM'] is None or base['cashM'] is None or base['debtM'] is None:
        return {'status': 'unsolved', 'reason': 'A share price needs diluted shares, cash and debt in the same currency before one assumption can be solved.'}
    net_debt = base['debtM'] - base['cashM']
    equity = target * base['sharesM']
    enterprise = equity + net_debt
    if enterprise <= 0:
        return {'status': 'unsolved', 'reason': 'The share price implies a company value that is not positive after adding debt and subtracting cash. No growth rate or multiple in this model produces it.'}
    held = _one(base, {**case, 'name': 'central'})
    growth = held['growthPct']
    margin = held['marginPct']
    multiple = held['multiple']
    method = held['method']
    if unknown == 'multiple':
        revenue = base['revenueM'] * (1 + growth / 100) ** YEARS
        denominator = revenue if method == 'EV/Sales' else revenue * (margin / 100)
        if denominator <= 0:
            return {'status': 'unsolved', 'reason': 'The fixed margin and growth do not produce a positive figure to divide into. The multiple cannot be solved.'}
        solved = enterprise / denominator
        if not 0.01 <= solved <= 100:
            return {'status': 'unsolved', 'reason': 'The required multiple is ' + format(solved, '.2f') + ', outside 0.01 to 100.'}
        shown = _one(base, {**case, 'name': 'central', 'multiple': solved})
        label = 'valuation multiple'
    else:
        if method == 'EV/Operating profit' and margin <= 0:
            return {'status': 'unsolved', 'reason': 'Operating profit is not positive at the fixed margin, so revenue growth cannot be solved for this multiple.'}
        denominator_ratio = enterprise / multiple
        revenue = denominator_ratio if method == 'EV/Sales' else denominator_ratio / (margin / 100)
        if revenue <= 0:
            return {'status': 'unsolved', 'reason': 'The share price does not lead to positive year-five revenue.'}
        solved = (revenue / base['revenueM']) ** (1 / YEARS) - 1
        solved *= 100
        if not -90 <= solved <= 300:
            return {'status': 'unsolved', 'reason': 'The required revenue growth is ' + format(solved, '.2f') + '%, outside -90% to 300%.'}
        shown = _one(base, {**case, 'name': 'central', 'growthPct': solved})
        label = 'revenue growth'
    return {'status': 'solved', 'unknown': unknown, 'label': label, 'value': solved, 'price': target, 'held': {'growthPct': growth, 'marginPct': margin, 'multiple': multiple, 'method': method},
            'result': shown, 'historyEnd': base.get('end') or '', 'startingRevenueM': base['revenueM'],
            'reason': 'The solved ' + label + ' is the only input that changed. Cash, debt and shares stay at the saved figures. This is not a forecast.'}


def answer(g, question, ident):
    opened = read(g, ident, 0)
    saved = opened['saved']
    result = saved.get('result') or {}
    text = str(question or '').lower()
    base = result.get('baseline') or {}
    cases = result.get('cases') or []
    if 'largest' in text and 'effect' in text:
        strongest = (result.get('sensitivity') or {}).get('strongest') or 'not identified'
        return 'On the central case, ' + strongest + ' changes the year-five company value the most when each assumption is moved on its own. The other assumptions stay fixed. This is a conditional calculation, not the Forecast Lab record.', {'sampleSize': len(cases), 'sensitivity': result.get('sensitivity'), 'qualification': 'The largest effect is measured on year-five company value.', 'source': base.get('sourceNote') or ''}
    if 'changed' in text and 'result' in text:
        comparison = opened.get('comparison') or {}
        original = comparison.get('originalRevenueM')
        latest = comparison.get('latestRevenueM')
        sentence = 'The saved scenario still starts from ' + format(original or 0, '.2f') + ' million. '
        if latest is None:
            sentence += 'No later annual revenue is saved.'
        elif original is not None and abs(latest - original) > 1e-6:
            sentence += 'The latest saved annual revenue is ' + format(latest, '.2f') + ' million. The scenario was not rewritten.'
        else:
            sentence += 'The latest saved annual revenue is the same figure.'
        sentence += ' ' + (comparison.get('note') or '')
        return sentence, {'sampleSize': 1, 'comparison': comparison, 'qualification': 'A new filing is shown beside the saved scenario. It does not replace the saved assumptions.', 'source': base.get('sourceNote') or ''}
    if 'happens' in text or ('grows' in text and 'margin' in text):
        central = next((row for row in cases if row['name'] == 'central'), None)
        if not central:
            return 'Save a central scenario first.', {'sampleSize': 0}
        try:
            shown = _one(base, {**central, 'name': 'central', 'growthPct': 10, 'marginPct': central['marginPct'] - 5})
        except ValueError as error:
            return str(error), {'sampleSize': 0, 'qualification': 'The illustration stayed inside the supported ranges.'}
        sentence = 'This illustration keeps your central multiple and sets revenue growth to 10% while cutting the operating margin by 5 percentage points. '
        sentence += 'Year-five revenue would be ' + format(shown['revenueM'], '.2f') + ' million ' + base.get('currency', '') + ' and operating profit ' + format(shown['operatingProfitM'], '.2f') + ' million. '
        sentence += shown['calculation'] + ' The 10% and 5 point steps are labels for this question, not a forecast.'
        return sentence, {'sampleSize': 1, 'cases': [shown], 'qualification': 'User assumptions are separate from the sourced starting revenue.', 'source': base.get('sourceNote') or ''}
    lines = []
    for row in cases:
        value = 'company value hidden' if row.get('enterpriseM') is None else format(row['enterpriseM'], '.2f') + ' million'
        lines.append(row['name'] + ': growth ' + format(row['growthPct'], '.2f') + '%, margin ' + format(row['marginPct'], '.2f') + '%, multiple ' + format(row['multiple'], '.2f') + ' ' + row['method'] + ', ' + value + '.')
    sentence = 'The starting revenue is ' + format(base.get('revenueM', 0), '.2f') + ' million ' + str(base.get('currency') or '') + ' for ' + str(base.get('start') or '') + ' to ' + str(base.get('end') or '') + '. That figure is sourced. Growth, margin and the multiple are your assumptions. ' + ' '.join(lines)
    return sentence, {'sampleSize': len(cases), 'cases': cases, 'qualification': saved.get('notice') or result.get('notice') or '', 'source': base.get('sourceNote') or ''}


def save(g, body, now_ms):
    symbol = g['valid_symbol'](body.get('symbol') or '')
    loaded = figures(g, symbol)
    stored = {'symbol': symbol, 'currency': body.get('currency') or loaded['currency'], 'start': body.get('start', loaded['start']),
              'end': body.get('end', loaded['end']), 'rows': body.get('rows') or loaded['rows']}
    manual = body.get('manual') or {}
    result = calculate({**stored, 'manual': manual, 'scenarios': body.get('scenarios'), 'notes': body.get('notes'), 'axes': body.get('axes')})
    ident = __import__('secrets').token_hex(8)
    payload = {'symbol': symbol, 'model': MODEL, 'title': str(body.get('title') or symbol + ' scenarios')[:160], 'figures': stored,
               'manual': manual, 'notes': result.get('notes') or [], 'scenarios': body.get('scenarios'), 'result': result, 'savedAt': int(now_ms), 'notice': result['notice']}
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('INSERT INTO scenario53 VALUES(?,?,?,?,?)', (ident, symbol, payload['title'], json.dumps(payload, allow_nan=False), int(now_ms)))
        con.execute('DELETE FROM scenario53 WHERE id NOT IN (SELECT id FROM scenario53 ORDER BY created_at DESC LIMIT 40)')
    return {'id': ident, 'saved': payload}


def read(g, ident, now_ms):
    if not IDENT.fullmatch(str(ident or '')):
        raise ValueError('Choose a saved scenario.')
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        row = con.execute('SELECT body FROM scenario53 WHERE id=?', (ident,)).fetchone()
    if not row:
        raise ValueError('That scenario is not saved on this Mac.')
    saved = json.loads(row[0])
    current = figures(g, saved['symbol'])
    original = next((item.get('valueM') for item in (saved.get('figures') or {}).get('rows') or [] if item.get('name') == 'revenue'), None)
    latest = next((item.get('valueM') for item in current['rows'] if item.get('name') == 'revenue'), None)
    return {'saved': saved, 'current': current, 'openedAt': int(now_ms),
            'comparison': {'originalRevenueM': original, 'latestRevenueM': latest,
                           'samePeriod': (saved.get('figures') or {}).get('end') == current.get('end'),
                           'note': 'The saved scenario keeps its original figures. The latest saved annual revenue is shown beside it and does not replace the scenario.'}}


def listed(g, symbol=''):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        if symbol:
            rows = con.execute('SELECT id,symbol,title,created_at FROM scenario53 WHERE symbol=? ORDER BY created_at DESC LIMIT 40', (g['valid_symbol'](symbol),)).fetchall()
        else:
            rows = con.execute('SELECT id,symbol,title,created_at FROM scenario53 ORDER BY created_at DESC LIMIT 40').fetchall()
    return [{'id': row[0], 'symbol': row[1], 'title': row[2], 'createdAt': row[3]} for row in rows]
