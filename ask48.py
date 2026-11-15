"""Answer a chart question from saved closes, events and issued forecasts.

No provider call and no language-model draft. A follow-up can change the
company or the dates; the returned context is what the answer covers.
"""
import contextlib
import datetime as dt
import json
import re

import crypto38
import crypto57
import stress58
import pack59
import desk61
import forecast61
import earnings62
import intelligence64
import tracker65
import workspace60
import compare52
import scenario53
import scanner55
import desk50
import events42
import move44
import scorecard41

NY = events42.NY
SUPPORTED = (
    'How much did the stock move in the dates shown?',
    'How did it compare with SPY?',
    'What announcements were published during this move?',
    'How accurate have its forecasts been?',
    'What changed since my last review?',
    'Which of my assumptions should I revisit?',
    'Which evidence supports or challenges my saved idea?',
    'Was the latest move unusual compared with this company’s own history?',
    'How has this model performed on this stock?',
    'Which company performed best over these dates?',
    'How do their operating margins compare?',
    'What assumptions produce this value?',
    'What happens if revenue grows but margins fall?',
    'What changed this result?',
    'Which assumption has the largest effect?',
    'Why did this company match?',
    'How has this crypto model performed?',
    'What drives this portfolio result?',
    'What does this research pack say?',
    'What changed in this workspace?',
    "Investigate TTWO's latest completed weekly move.",
    'How was this forecast chosen?',
    'What changed in these results?',
    'Did revenue and profit move together?',
    'How does this compare with last year?',
    'Why did this company match my scan?',
    'Which holding contributed most to this portfolio change?',
    'How did these results differ from my saved scenario?',
    'Has this forecast model beaten its baseline?',
    'What changed since I saved this investigation?',
)
SKIP = {'SPY', 'USD', 'SEC', 'ETF', 'IPO', 'EPS', 'GAAP', 'NYSE'}


def init(con):
    con.execute('''CREATE TABLE IF NOT EXISTS ask48 (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL, question TEXT NOT NULL, start_day TEXT NOT NULL, end_day TEXT NOT NULL,
        body TEXT NOT NULL, created_at INTEGER NOT NULL,
        UNIQUE(symbol, question, start_day, end_day))''')


def _completed(now_ms):
    probe = dt.datetime.fromtimestamp(now_ms / 1000, NY).date() + dt.timedelta(days=1)
    for _ in range(12):
        probe -= dt.timedelta(days=1)
        if not events42.is_session(probe):
            continue
        close = events42.close_on(probe)
        if close is not None and int(close.timestamp() * 1000) <= now_ms:
            return probe
    raise ValueError('No completed session is available for this question.')


def _span(end, count):
    days = [end]
    while len(days) < count:
        days.append(events42.previous_session(days[-1]))
    return days[-1].isoformat(), end.isoformat()


def _week(now_ms):
    return _span(_completed(now_ms), 5)


def _month_before(start, end, now_ms):
    if start:
        anchor = events42.previous_session(dt.date.fromisoformat(start))
    else:
        anchor = events42.previous_session(dt.date.fromisoformat(end) if end else _completed(now_ms))
    return _span(anchor, 21)


def _catalog(g):
    try:
        rows = json.loads((g['ROOT'] / 'ai_catalog.json').read_text())
    except (OSError, ValueError):
        return {}
    return {row['symbol']: row.get('name') or '' for row in rows if isinstance(row, dict) and row.get('symbol')}


def _mentioned(question, names):
    text = question.upper()
    found = []
    for symbol in sorted(names, key=len, reverse=True):
        if symbol in SKIP or len(symbol) < 2:
            continue
        if re.search(r'\b' + re.escape(symbol) + r'\b', text):
            found.append(symbol)
            continue
        name = names[symbol].lower()
        if len(name) > 4 and name in question.lower():
            found.append(symbol)
    return found


def _kind(question):
    text = question.lower()
    if 'unusual' in text:
        return 'unusual'
    if 'since' in text and 'review' in text:
        return 'since'
    if 'saved idea' in text or ('support' in text and 'challenge' in text):
        return 'idea'
    if 'model' in text and 'perform' in text:
        return 'model'
    if 'why' in text and 'match' in text:
        return 'scan-match'
    if 'changed' in text and 'result' in text:
        return 'scenario-change'
    if 'largest' in text and 'effect' in text:
        return 'scenario-effect'
    if 'assumptions' in text and 'value' in text:
        return 'scenario'
    if 'grows' in text and 'margin' in text:
        return 'scenario-stress'
    if 'operating margin' in text:
        return 'margins'
    if 'which company' in text and ('best' in text or 'perform' in text):
        return 'best'
    if any(word in text for word in ('forecast', 'accurate', 'accuracy', 'scorecard')):
        return 'forecast'
    if any(word in text for word in ('announcement', 'announce', 'published', 'filing', 'headline', 'news')):
        return 'announcements'
    if 'spy' in text or any(word in text for word in ('compare', 'comparison', 'versus', ' vs ')):
        return 'compare'
    if any(word in text for word in ('move', 'moved', 'change', 'return', 'week', 'month', 'price')):
        return 'move'
    return 'unsupported'


def _freshness(g, symbol):
    try:
        with contextlib.closing(g['db_connection']()) as con:
            events42.init(con)
            prices = con.execute('SELECT MAX(fetched_at) FROM massive_daily_bars WHERE symbol IN (?,?)', (symbol, 'SPY')).fetchone()[0]
            events = con.execute('SELECT updated_at FROM events42 WHERE symbol=?', (symbol,)).fetchone()
        return {'pricesFetchedAt': prices, 'eventsUpdatedAt': events[0] if events else None}
    except Exception:
        return {'pricesFetchedAt': None, 'eventsUpdatedAt': None}


def _context(g, question, context, now_ms):
    context = context or {}
    names = _catalog(g)
    symbol = str(context.get('symbol') or 'AAPL').strip().upper()
    symbol = g['valid_symbol'](symbol)
    tickers = [item for item in _mentioned(question, names) if item != symbol]
    follow = any(phrase in question.lower() for phrase in ('what about', 'how about', 'switch to'))
    chosen = next((item for item in tickers if item != 'SPY'), None)
    if chosen:
        symbol = g['valid_symbol'](chosen)
    start = str(context.get('start') or '')
    end = str(context.get('end') or '')
    label = str(context.get('range') or '')
    text = question.lower()
    if 'previous month' in text or 'last month' in text:
        start, end = _month_before(start, end, now_ms)
        label = '1M'
    elif 'this week' in text or 'last week' in text:
        start, end = _week(now_ms)
        label = '1W'
    kind = _kind(question)
    if kind == 'unsupported' and context.get('kind') in ('move', 'compare', 'announcements', 'forecast') and (follow or 'month' in text):
        kind = context['kind']
    return {
        'symbol': symbol, 'range': label, 'start': start, 'end': end, 'kind': kind,
        'capturedAt': context.get('capturedAt') or '', 'originalPrice': context.get('originalPrice') or '',
        'expectation': context.get('expectation') or '', 'journalStatus': context.get('journalStatus') or '',
        'compareSymbols': str(context.get('compareSymbols') or ''),
        'scenarioId': str(context.get('scenarioId') or ''),
        'scanId': str(context.get('scanId') or ''),
    }, kind


def _move_answer(review, kind):
    if review.get('status') != 'ready':
        return review.get('reason') or 'The move could not be calculated from saved closes.', review
    start, end = review['startPrice'], review['endPrice']
    sentence = f"{review['symbol']} moved {review['returnPct']:.2f}% from {start:g} on {review['start']} to {end:g} on {review['end']}."
    if kind == 'compare':
        comparison = review['comparison']
        if comparison.get('status') == 'ready':
            sentence += f" SPY moved {comparison['returnPct']:.2f}% over the same dates. The difference is {comparison['differencePP']:.2f} percentage points."
        else:
            sentence += ' ' + comparison.get('reason', 'The SPY comparison is not available.')
    return sentence, review


def _forecast_answer(card, symbol):
    summary = card.get('summary') or {}
    pending = len(card.get('pending') or [])
    graded = summary.get('count') or 0
    if graded == 0 and pending == 0:
        return f'No issued forecast is saved for {symbol}.', {'sampleSize': 0, 'rows': []}
    if graded == 0:
        return f'{pending} issued forecast{"s" if pending != 1 else ""} for {symbol} {"are" if pending != 1 else "is"} saved and not scored yet. The target close is not in the saved prices.', {'sampleSize': 0, 'pending': pending, 'rows': card.get('pending') or []}
    better = 'The issued forecasts were closer than an unchanged price on average.' if summary.get('beatBaseline') else 'An unchanged price was at least as close on average.'
    sentence = f"{graded} scored forecast{'s' if graded != 1 else ''} for {symbol}. Average error {summary['averageErrorPP']:.2f} percentage points, against {summary['baselineAverageErrorPP']:.2f} for an unchanged price. {better}"
    if pending:
        sentence += f' {pending} more {"are" if pending != 1 else "is"} still waiting for the target close.'
    return sentence, {'sampleSize': graded, 'summary': summary, 'rows': (card.get('graded') or [])[:8], 'pending': pending}


def _desk_answer(g, kind, ctx, now_ms):
    symbol = ctx['symbol']
    if kind == 'unusual':
        result = desk50.unusual(g, symbol, now_ms)
        if result.get('status') != 'ready':
            return result['reason'], {**result, 'sampleSize': result.get('sampleSize', 0), 'qualification': 'This uses saved closes only. A split-sized jump is not called unusual.'}
        word = 'larger than' if result['unusual'] else 'not larger than'
        gap = ' The previous saved session is not the previous trading session, so this is a newly observed comparison, not a move watched session by session.' if result['gap'] else ''
        text = f"{symbol} moved {result['movePct']:.2f}% from {result['startPrice']:g} on {result['start']} to {result['endPrice']:g} on {result['end']}. That is {word} the 90th percentile of {result['sampleSize']} earlier moves, which was {result['percentilePct']:.2f}%.{gap}"
        return text, {**result, 'qualification': 'This compares one completed session with that company’s own earlier moves. It does not say why the price moved.', 'source': result['source']}
    if kind == 'model':
        report = desk50.model_report(g, symbol)
        text, evidence = _forecast_answer(report['scorecard'], symbol)
        cached = report.get('cached') or {}
        lab = cached.get('lab') or []
        durable = [row.get('durability') for row in lab if row.get('durability')]
        if durable:
            latest = durable[0]
            text += f" On the most recent part of the 1-session test, the volatility error was {latest['lateErrorPP']:.2f} percentage points against {latest['lateBaselineErrorPP']:.2f} for an unchanged price."
            evidence['durability'] = latest
        evidence['qualification'] = 'Issued forecasts stay as they were saved. A training cache is separate and can be recalculated. An unchanged price is kept when it wins.'
        evidence['source'] = 'Issued forecasts and the saved Forecast Lab cache on this Mac.'
        evidence['sampleSize'] = evidence.get('sampleSize') or 0
        return text, evidence
    captured = ctx.get('capturedAt')
    try:
        captured = int(captured)
    except (TypeError, ValueError):
        captured = 0
    try:
        original = float(ctx.get('originalPrice'))
    except (TypeError, ValueError):
        original = None
    change = desk50.changed_since(g, symbol, captured, original, now_ms)
    latest = change['latest']
    if kind == 'since':
        if not captured:
            return f'No saved review time was included for {symbol}. Open the research journal entry and ask again.', {'sampleSize': 0, 'gaps': ['The journal review time was not sent with the question.']}
        if latest.get('price') is None:
            text = f'No later saved close is available for {symbol}. ' + latest.get('reason', '')
        else:
            text = f"Since the review saved at the included time, the latest saved close for {symbol} is {latest['price']:g} on {latest['date']}."
            if original:
                text += f" The idea recorded {original:g}."
        if change['newEventCount']:
            text += f" {change['newEventCount']} saved items are timestamped after that review."
        else:
            text += ' No saved announcement is timestamped after that review.'
        return text, {'sampleSize': change['newEventCount'], 'endPrice': latest.get('price'), 'end': latest.get('date'), 'startPrice': original, 'items': change['newEvents'], 'qualification': 'This does not replace the original journal evidence. The judgement on that entry stays the one you saved.', 'source': latest.get('source') or '', 'gaps': []}
    if not (ctx.get('expectation') or captured):
        return f'No saved idea for {symbol} was included. Save one from the chart, a move, an alert or an answer first.', {'sampleSize': 0, 'gaps': ['There is no saved idea in this request.']}
    direction = 'higher' if any(word in str(ctx.get('expectation')).lower() for word in ('rise', 'higher', 'up', 'gain')) else 'lower' if any(word in str(ctx.get('expectation')).lower() for word in ('fall', 'lower', 'down', 'drop')) else ''
    text = f"Your saved status is {ctx.get('journalStatus') or 'open'}. Market Desk does not change that judgement."
    if original and latest.get('price'):
        moved = 'higher' if latest['price'] > original else 'lower' if latest['price'] < original else 'unchanged'
        text += f" The recorded price was {original:g}. The latest saved close is {latest['price']:g} on {latest['date']}, which is {moved}."
        if direction:
            text += ' That agrees with the direction written in the idea.' if moved == direction else ' That does not agree with the direction written in the idea.' if moved != 'unchanged' else ' The saved close is unchanged.'
    else:
        text += ' A price comparison needs both the recorded price and a later saved close.'
    text += ' A headline or a later price is not proof that the idea was right.'
    try:
        accounts = g.get('sec_saved', lambda _symbol: {})(symbol) or {}
    except Exception:
        accounts = {}
    if accounts.get('fetchedAt'):
        text += ' Saved financial statements were last stored on this Mac. They were not recalculated for this answer.'
    return text, {'sampleSize': change['newEventCount'], 'startPrice': original, 'endPrice': latest.get('price'), 'end': latest.get('date'), 'items': change['newEvents'], 'qualification': 'The saved idea and its original evidence stay as written. This comparison is an updated view.', 'source': latest.get('source') or ''}


def answer(g, question, context=None, now_ms=None):
    question = str(question or '').strip()
    now_ms = int(g['time'].time() * 1000) if now_ms is None else int(now_ms)
    if not question:
        raise ValueError('Enter a question.')
    context = context or {}
    import practice67
    practised = practice67.handle(g, question, context, now_ms)
    if practised:
        return {**practised, 'supportedQuestions': list(SUPPORTED)}
    connected = intelligence64.handle(g, question, context, now_ms)
    tracked = tracker65.handle(g, question, context, now_ms)
    if tracked:
        return {**tracked, 'supportedQuestions': list(SUPPORTED)}
    if connected:
        packet = {'question': question, 'kind': connected['area'], 'offline': True, 'supported': connected['supported'],
                'answer': connected['answer'], 'evidence': connected['evidence'],
                'context': {'kind': connected['area'], 'symbol': context.get('symbol') or '', 'range': context.get('range') or '',
                            'start': context.get('start') or '', 'end': context.get('end') or '',
                            'scanId': context.get('scanId') or '', 'stressId': context.get('stressId') or '',
                            'scenarioId': context.get('scenarioId') or '', 'investigationId': context.get('investigationId') or '',
                            'product': context.get('product') or ''},
                'supportedQuestions': list(SUPPORTED)}
        if connected['supported']:
            _store(g, packet, now_ms)
        return packet
    if earnings62.question(question):
        symbol = g['valid_symbol'](str((context or {}).get('symbol') or 'AAPL'))
        report = g.get('sec_saved', lambda _symbol: {})(symbol) or {}
        text = earnings62.answer(report, question)
        return {'question': question, 'kind': 'earnings', 'offline': True, 'supported': True,
                'answer': text, 'evidence': {'sampleSize': 1 if report.get('annual') else 0, 'gaps': [] if report.get('annual') else ['No saved SEC statement was included.']},
                'context': {'kind': 'earnings', 'symbol': symbol}, 'supportedQuestions': list(SUPPORTED)}
    if forecast61.question(question):
        symbol = str((context or {}).get('symbol') or 'TTWO')
        packet = forecast61.for_symbol(g, symbol, now_ms)
        return {'question': question, 'kind': 'forecast', 'offline': True, 'supported': True,
                'answer': forecast61.explain(packet),
                'evidence': {'sampleSize': packet.get('observations') or 0, 'gaps': [] if packet.get('status') == 'learned' else [packet.get('notice') or 'The learned path is withheld.']},
                'context': {'kind': 'forecast', 'symbol': packet.get('symbol')},
                'supportedQuestions': list(SUPPORTED)}
    if desk61.question(question):
        plan = desk61.propose(g, question, now_ms)
        return {'question': question, 'kind': 'investigation', 'offline': True, 'supported': True,
                'answer': plan['summary'] + ' The steps are: ' + '; '.join(item['title'] for item in plan['steps']) + '.',
                'evidence': {'sampleSize': 0, 'steps': plan['steps'], 'gaps': ['No return has been calculated yet.']},
                'context': {'kind': 'investigation', 'symbol': plan['symbol']},
                'supportedQuestions': list(SUPPORTED)}
    if workspace60.question(question):
        try:
            current = workspace60.listed(g)
            active = next((row for row in current['workspaces'] if row['id'] == current.get('activeId')), None)
            since = workspace60.changed(g, active) if active else {'notice': 'Save a workspace first.'}
            text = (active['name'] + '. ' if active else '') + since.get('notice', '')
        except Exception:
            text = 'Save a workspace first.'
            since = {'packs': []}
        return {'question': question, 'kind': 'workspace', 'offline': True, 'supported': True,
                'answer': text, 'evidence': {'sampleSize': len(since.get('packs') or []), 'gaps': [] if since.get('packs') else ['No later research pack is saved.']},
                'context': {'kind': 'workspace', 'packId': context.get('packId') or ''},
                'supportedQuestions': list(SUPPORTED)}
    if pack59.question(question):
        saved = None
        if context.get('packId'):
            try:
                saved = pack59.read(g, context.get('packId'))
            except ValueError:
                saved = None
        text, evidence = pack59.explain(saved)
        return {'question': question, 'kind': 'pack', 'offline': True, 'supported': True,
                'answer': text, 'evidence': evidence, 'context': {'kind': 'pack', 'packId': context.get('packId') or ''},
                'supportedQuestions': list(SUPPORTED)}
    if stress58.question(question):
        if not context.get('stressId'):
            return {'question': question, 'kind': 'stress', 'offline': True, 'supported': True,
                    'answer': 'Save the portfolio stress test first. The explanation uses that saved arithmetic.',
                    'evidence': {'sampleSize': 0, 'gaps': ['No saved stress test was included.']},
                    'context': {'kind': 'stress'}, 'supportedQuestions': list(SUPPORTED)}
        try:
            saved = stress58.read(g, context.get('stressId'))
        except ValueError:
            saved = None
        text, evidence = stress58.explain(saved)
        return {'question': question, 'kind': 'stress', 'offline': True, 'supported': True,
                'answer': text, 'evidence': evidence, 'context': {'kind': 'stress', 'stressId': context.get('stressId')},
                'supportedQuestions': list(SUPPORTED)}
    product = crypto57.named_product(question) or str(context.get('product') or context.get('symbol') or '').upper()
    if product in crypto38.PRODUCTS and crypto57.question(question):
        text, evidence = crypto57.explain(g, product)
        return {'question': question, 'kind': 'crypto-forecast', 'offline': True, 'supported': True,
                'answer': text, 'evidence': evidence, 'context': {'symbol': product, 'product': product, 'kind': 'crypto-forecast'},
                'supportedQuestions': list(SUPPORTED)}
    ctx, kind = _context(g, question, context, now_ms)
    fresh = _freshness(g, ctx['symbol'])
    base = {
        'question': question, 'context': ctx, 'kind': kind, 'offline': True,
        'supported': kind != 'unsupported', 'freshness': fresh,
        'supportedQuestions': list(SUPPORTED),
    }
    if kind == 'unsupported':
        base.update({
            'answer': 'This question needs information Market Desk does not calculate here. Ask how the stock moved, how that compares with SPY, which announcements were published during the move, or how accurate its saved forecasts have been.',
            'evidence': {'gaps': ['No price, event or forecast calculation was run for this wording.']},
        })
        return base
    if kind == 'scan-match':
        if not ctx.get('scanId'):
            base.update({'answer': 'Save the scan first. The answer uses that saved calculation.', 'evidence': {'sampleSize': 0, 'gaps': ['No saved scan was included.']}})
            return base
        text, evidence = scanner55.answer(g, ctx['scanId'], ctx['symbol'])
        base.update({'answer': text, 'evidence': evidence})
        _store(g, base, now_ms)
        return base
    if kind in ('scenario', 'scenario-stress', 'scenario-change', 'scenario-effect'):
        if not ctx.get('scenarioId'):
            base.update({'answer': 'Save the scenario first. The question uses that saved arithmetic.', 'evidence': {'sampleSize': 0, 'gaps': ['No saved scenario was included.']}})
            return base
        text, evidence = scenario53.answer(g, question, ctx['scenarioId'])
        base.update({'answer': text, 'evidence': evidence})
        _store(g, base, now_ms)
        return base
    if kind in ('best', 'margins'):
        text, evidence = compare52.answer(g, question, ctx.get('compareSymbols') or ctx['symbol'], ctx.get('start') or '', ctx.get('end') or '')
        if evidence.get('start'):
            ctx['start'], ctx['end'] = evidence['start'], evidence['end']
            ctx['symbol'] = (evidence.get('symbols') or [ctx['symbol']])[0]
        base['context'] = ctx
        base.update({'answer': text, 'evidence': evidence})
        _store(g, base, now_ms)
        return base
    if kind == 'forecast':
        card = scorecard41.read(g, ctx['symbol'])
        text, evidence = _forecast_answer(card, ctx['symbol'])
        evidence['qualification'] = 'These figures are the issued-forecast scorecard. They are not a prediction for the next session, and a later training run does not replace them.'
        evidence['source'] = 'Issued forecasts saved on this Mac.'
        base.update({'answer': text, 'evidence': evidence})
        _store(g, base, now_ms)
        return base
    if kind in ('since', 'idea', 'unusual', 'model'):
        text, evidence = _desk_answer(g, kind, ctx, now_ms)
        if evidence.get('start') and evidence.get('end'):
            ctx = {**ctx, 'start': evidence['start'], 'end': evidence['end'], 'range': ctx.get('range') or 'session'}
            base['context'] = ctx
        base.update({'answer': text, 'evidence': evidence})
        _store(g, base, now_ms)
        return base
    if not ctx['start'] or not ctx['end']:
        base.update({
            'supported': True,
            'answer': 'Choose a chart period with two completed sessions, or ask about this week. A single price cannot show a move.',
            'evidence': {'gaps': ['The start or end date was not carried through.']},
        })
        return base
    review = move44.review(g, ctx['symbol'], ctx['start'], ctx['end'], now_ms)
    if kind == 'announcements':
        if review.get('status') != 'ready':
            text = review.get('reason') or 'The move is not available, so announcements cannot be placed against it.'
        else:
            count = review['beforeCount'] + review['uncertainCount']
            text = review['evidence'] if count else 'No saved announcement or filing falls before or during this move.'
            if count:
                text = f"{count} saved item{'s' if count != 1 else ''} fall before or during {ctx['symbol']} from {review['start']} to {review['end']}. " + review['evidence']
        evidence = {
            'startPrice': review.get('startPrice'), 'endPrice': review.get('endPrice'),
            'start': review.get('start'), 'end': review.get('end'),
            'sampleSize': len(review.get('sessions') or []),
            'items': (review.get('before') or []) + (review.get('uncertain') or []),
            'after': review.get('after') or [],
            'gaps': review.get('gaps') or [],
            'qualification': review.get('evidence') or 'A headline is not a cause.',
            'source': move44.SOURCE, 'basis': review.get('basis'),
        }
    else:
        text, review = _move_answer(review, kind)
        evidence = {
            'startPrice': review.get('startPrice'), 'endPrice': review.get('endPrice'),
            'start': review.get('start'), 'end': review.get('end'),
            'returnPct': review.get('returnPct'),
            'sampleSize': len(review.get('sessions') or []),
            'sessions': review.get('sessions') or [],
            'comparison': review.get('comparison'),
            'gaps': review.get('gaps') or [],
            'qualification': 'This is the change between two saved closes. It does not show why the price moved.',
            'source': review.get('source') or move44.SOURCE, 'basis': review.get('basis'),
        }
    base.update({'answer': text, 'evidence': evidence})
    _store(g, base, now_ms)
    return base


def _store(g, packet, now_ms):
    ctx = packet.get('context') or {}
    with g['LOCK'], contextlib.closing(g['db_connection']()) as con, con:
        init(con)
        con.execute('''INSERT OR IGNORE INTO ask48 (symbol,question,start_day,end_day,body,created_at)
            VALUES(?,?,?,?,?,?)''', (str(ctx.get('symbol') or ''), packet['question'], str(ctx.get('start') or ''), str(ctx.get('end') or ''), json.dumps(packet, allow_nan=False), now_ms))


def saved(g, symbol=None):
    with contextlib.closing(g['db_connection']()) as con:
        init(con)
        if symbol:
            rows = con.execute('SELECT id,body,created_at FROM ask48 WHERE symbol=? ORDER BY id DESC LIMIT 30', (symbol,)).fetchall()
        else:
            rows = con.execute('SELECT id,body,created_at FROM ask48 ORDER BY id DESC LIMIT 30').fetchall()
    items = []
    for ident, body, created in rows:
        try:
            item = json.loads(body)
        except ValueError:
            continue
        item['id'] = ident
        item['savedAt'] = created
        items.append(item)
    return items
