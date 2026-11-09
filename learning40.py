"""Chronological ridge evaluation and persisted, reproducible local model reports."""
import contextlib
import hashlib
import json
import math
import statistics
import threading

import market34
import market37

METHOD = 'ridge-sessions-v4.1'
HORIZONS = (1, 5, 20)
LOCK = threading.Lock()


def init(con):
    con.execute('CREATE TABLE IF NOT EXISTS learning40(symbol TEXT PRIMARY KEY, revision TEXT, body TEXT, trained_at INTEGER)')


def evaluate(prices, horizon):
    # Fit each candidate on outcomes already observed at its decision point.
    samples = []
    features = [market34.features(prices, i) if i>=60 else None for i in range(len(prices))]
    targets = [{'x':features[i], 'y':math.log(prices[i+horizon]['p']/prices[i]['p'])}
               for i in range(60,len(prices)-horizon)]
    for anchor in range(160, len(prices)-horizon, horizon):
        train = targets[:anchor-horizon-59]
        if len(train) < 75:
            continue
        model = market34.fit(train)
        estimate = max(-.35, min(.35, market34.predict(model, features[anchor])))
        actual = math.log(prices[anchor+horizon]['p']/prices[anchor]['p'])
        samples.append((estimate, actual))
    split = len(samples)//2
    calibration, test = samples[:split], samples[split:]
    result = {'horizon': horizon, 'calibrationCases': len(calibration), 'testCases': len(test)}
    if len(calibration)<8 or len(test)<8:
        return {**result, 'status': 'insufficient'}
    def error(rows, use_model):
        return statistics.mean(abs(math.expm1(p if use_model else 0)-math.expm1(a))*100 for p,a in rows)
    calibration_error,calibration_baseline=error(calibration, True),error(calibration, False)
    chosen=calibration_error<calibration_baseline
    result.update(calibrationErrorPP=calibration_error,calibrationBaselinePP=calibration_baseline,calibrationPassed=chosen)
    learned, baseline = error(test, True), error(test, False)
    # A failed independent check withholds the learned projection. The table
    # still reports the candidate's original scores, including failed runs.
    if not chosen or learned>=baseline:
        return {**result, 'status':'baseline', 'modelErrorPP':learned, 'baselineErrorPP':baseline}
    training = targets
    fit=market34.fit(training)
    prediction=max(-.35,min(.35,market34.predict(fit,features[-1])))
    residual=[a-p for p,a in calibration]
    base=prices[-1]['p']
    return {**result, 'status':'learned', 'modelErrorPP':learned, 'baselineErrorPP':baseline,
            'returnPct':math.expm1(prediction)*100, 'price':base*math.exp(prediction),
            'low':base*math.exp(min(prediction,prediction+market34.quantile(residual,.1))),
            'high':base*math.exp(max(prediction,prediction+market34.quantile(residual,.9))),
            'weights':fit['coef'], 'trainingCases':len(training)}


def report(g, symbol):
    symbol=g['valid_symbol'](symbol)
    if not g['ai_catalog_entry'](symbol):
        raise ValueError('Choose a US stock directory symbol.')
    now=int(g['time'].time()*1000)
    history=g['read_massive_daily_bars'](symbol,946684800,now//1000)
    closes=history['bars'] if history else {'t':[],'c':[]}
    points=market34.clean([{'t':t*1000,'p':p} for t,p in zip(closes['t'],closes['c'])],now)
    latest=market37.sessions(market37.today(g),1)[0]
    dates=[market37.dt.datetime.fromtimestamp(p['t']/1000,market37.NY).date().isoformat() for p in points]
    # Keep the continuous suffix of scheduled sessions. A missing bar cannot
    # silently shorten the supervised target horizon.
    if dates:
        expected=market37.sessions(market37.dt.date.fromisoformat(dates[-1])+market37.dt.timedelta(days=1),len(dates))
        count=0
        for actual,wanted in zip(reversed(dates),expected):
            if actual!=wanted:break
            count+=1
        points=points[-count:] if count else []
    revision=hashlib.sha256(json.dumps([METHOD,points]).encode()).hexdigest()
    with LOCK:
        with contextlib.closing(g['db_connection']()) as con:
            saved=con.execute('SELECT revision,body,trained_at FROM learning40 WHERE symbol=?',(symbol,)).fetchone()
        if saved and saved[0]==revision:
            result=json.loads(saved[1])
            trained=saved[2]
        else:
            jump=any(abs(math.log(b['p']/a['p']))>.7 for a,b in zip(points,points[1:]))
            result={'method':METHOD,'symbol':symbol,'closes':len(points),'first':points[0]['t'] if points else None,
                    'anchor':points[-1] if points else None,'rows':[] if jump else [evaluate(points,h) for h in HORIZONS],
                    'quality':'Extreme price jump needs review.' if jump else ''}
            trained=now
            with g['LOCK'],contextlib.closing(g['db_connection']()) as con,con:
                con.execute('INSERT OR REPLACE INTO learning40 VALUES(?,?,?,?)',(symbol,revision,json.dumps(result,allow_nan=False),trained))
                con.execute('DELETE FROM learning40 WHERE symbol NOT IN (SELECT symbol FROM learning40 ORDER BY trained_at DESC LIMIT 60)')
    return {**result,'trainedAt':trained,'anchorDate':dates[-1] if dates and points else None,'latestEligibleDate':latest,
            'stale':not points or dates[-1]!=latest}
