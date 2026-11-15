"""Portfolio insights from the existing practice ledger. No new prices are invented."""
import datetime as dt

import portfolio3


def _note(holding):
    mark = holding.get('mark')
    if not mark:
        return 'No saved price. This holding is left out of the current total.'
    if holding.get('staleMark'):
        return 'Price dated ' + mark['date'] + ' is ' + str(holding.get('markAgeDays')) + ' days old. It is not used in the current total.'
    return 'Valued with the saved price dated ' + mark['date'] + '.'


def _groups(rows, key):
    found = {}
    for row in rows:
        name = row[key]
        bucket = found.setdefault(name, {'label': name, 'sharePct': 0, 'costUSD': 0, 'valueUSD': 0})
        bucket['sharePct'] += row['sharePct'] or 0
        bucket['costUSD'] += row['costBasisUSD']
        if row['valueUSD'] is not None:
            bucket['valueUSD'] += row['valueUSD']
    groups = list(found.values())
    for group in groups:
        group['large'] = group['sharePct'] >= 25
    groups.sort(key=lambda group: (-group['sharePct'], group['label']))
    return groups


def comparison(ledger, marks, spy, as_of=None):
    """Modified Dietz from the first practice date to the valuation date, beside SPY closes on those exact dates."""
    try:
        clean = portfolio3.events(ledger)
    except portfolio3.LedgerError as error:
        return {'status': 'withheld', 'notice': str(error)}
    if not clean:
        return {'status': 'empty', 'notice': 'Add a practice record before comparing with SPY.'}
    start = min(row['date'] for row in clean)
    end = as_of or dt.datetime.now(dt.timezone.utc).date().isoformat()
    try:
        portfolio3.date(end)
        opening = portfolio3.checkpoint(clean, marks, start)
        closing = portfolio3.checkpoint(clean, marks, end)
    except portfolio3.LedgerError as error:
        return {'status': 'withheld', 'start': start, 'end': end, 'notice': str(error) + ' The SPY comparison waits until every holding has a saved price on the first practice date and on the valuation date.'}
    result = portfolio3.performance(clean, [opening, closing], spy or [])
    result['start'] = start
    result['end'] = end
    result['flows'] = [{'date': row['date'], 'kind': row['kind'], 'amount': row['amount']} for row in result.get('externalFlows') or []]
    result['explanation'] = 'The portfolio figure is Modified Dietz. The starting value is the practice account on the first record date, after that day’s records. Later deposits and withdrawals are weighted by how many days they were in the account. Buys, sells, fees and dividends stay inside the result. SPY is the change between its saved closes on those two dates only. A missing SPY close is left missing. SPY dividends are not added, so this is not a total-return comparison.'
    if result.get('status') == 'ok' and result.get('benchmarkPriceChangePct') is None:
        result['spyNote'] = 'No saved SPY close on ' + start + ' and ' + end + ' together. The portfolio figure is still shown. The SPY percentage is withheld.'
    elif result.get('status') == 'ok':
        result['spyNote'] = 'SPY uses the saved close on ' + start + ' and the saved close on ' + end + '.'
    return result


def build(ledger, marks, sectors=None, spy=None, as_of=None):
    account = portfolio3.calculate(ledger, marks, as_of)
    sectors = sectors or {}
    cost = sum(row['costBasisUSD'] for row in account['holdings'])
    basis = 'value' if account['complete'] else 'cost'
    rows = []
    for holding in account['holdings']:
        if basis == 'value' and account['totalValueUSD']:
            share = holding['valueUSD'] / account['totalValueUSD'] * 100
        elif cost:
            share = holding['costBasisUSD'] / cost * 100
        else:
            share = None
        realised = holding.get('realisedUSD') or 0
        unrealised = holding.get('unrealisedUSD')
        rows.append({
            'symbol': holding['symbol'],
            'sector': sectors.get(holding['symbol']) or 'Sector not recorded',
            'costBasisUSD': holding['costBasisUSD'],
            'valueUSD': holding['valueUSD'],
            'realisedUSD': realised,
            'unrealisedUSD': unrealised,
            'contributionUSD': None if unrealised is None else realised + unrealised,
            'sharePct': share,
            'shareBasis': basis,
            'large': share is not None and share >= 25,
            'priceDate': (holding.get('mark') or {}).get('date'),
            'priceNote': _note(holding),
        })
    rows.sort(key=lambda row: (-(row['sharePct'] or 0), row['symbol']))
    return {
        'openCostUSD': cost,
        'recordedValueUSD': account['totalValueUSD'],
        'cashUSD': account['cashUSD'],
        'realisedUSD': account['realisedUSD'],
        'unrealisedUSD': account['knownUnrealisedUSD'] if account['complete'] else None,
        'complete': account['complete'],
        'shareBasis': basis,
        'holdings': rows,
        'companies': _groups(rows, 'symbol'),
        'sectors': _groups(rows, 'sector'),
        'closed': account.get('closedRealised') or [],
        'unpriced': account['unpriced'],
        'comparison': comparison(ledger, marks, spy, account['asOf']),
        'notice': 'Allocation uses current recorded value when every holding has a price from the last seven days. Otherwise the bars show share of open cost and are labelled as cost, not value. A holding of 25% or more is marked as a large exposure. Sector names come from the saved company directory. A symbol that is not listed there stays “Sector not recorded”.',
    }
