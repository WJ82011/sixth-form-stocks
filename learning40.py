"""Chronological ridge evaluation and persisted, reproducible local model reports."""
import contextlib
import hashlib
import json
import math
import statistics
import threading

import lab45
import market34
import market37
import scorecard41

METHOD = 'ridge-sessions-v4.1'
HORIZONS = (1, 5, 20)
LOCK = threading.Lock()


def init(con):
    con.execute('CREATE TABLE IF NOT EXISTS learning40(symbol TEXT PRIMARY KEY, revision TEXT, body TEXT, trained_at INTEGER)')


def evaluate(prices, horizon):
    # Fit each candidate on outcomes already observed at its decision point.
    samples = []
    features = [market34.features(prices, i) if i>=60 else None for i in range(len(prices))]
    targets = [{'i':i, 'x':features[i], 'y':math.log(prices[i+horizon]['p']/prices[i]['p'])}
               for i in range(60,len(prices)-horizon)]
    for anchor in range(160, len(prices)-horizon, horizon):
        train = [row for row in targets if row['i']+horizon<=anchor]
        if len(train) < 75:
            continue
        model = market34.fit(train)
        estimate = max(-.35, min(.35, market34.predict(model, features[anchor])))
        drift = max(-.35, min(.35, statistics.mean(row['y'] for row in train)))
        actual = math.log(prices[anchor+horizon]['p']/prices[anchor]['p'])
        samples.append((estimate, actual, drift, anchor))
    split = len(samples)//2
    calibration, test = samples[:split], samples[split:]
    result = {'horizon': horizon, 'calibrationCases': len(calibration), 'testCases': len(test)}
    if len(calibration)<8 or len(test)<8:
        return {**result, 'status': 'insufficient'}
    def error(rows, choice):
        def predicted(row):
            estimate, _actual, drift, _anchor = row
            if choice=='model': return estimate
            if choice=='drift': return drift
            return 0
        return statistics.mean(abs(math.expm1(predicted(row))-math.expm1(row[1]))*100 for row in rows)
    calibration_error,calibration_baseline=error(calibration, 'model'),error(calibration, 'flat')
    chosen=calibration_error<calibration_baseline
    result.update(calibrationErrorPP=calibration_error,calibrationBaselinePP=calibration_baseline,calibrationPassed=chosen)
    learned, baseline, drift_error = error(test, 'model'), error(test, 'flat'), error(test, 'drift')
    residual=[row[1]-row[0] for row in calibration]
    low_q, high_q = market34.quantile(residual,.1), market34.quantile(residual,.9)
    covered=sum(1 for estimate, actual, _drift, _anchor in test if low_q<=actual-estimate<=high_q)
    result.update(modelErrorPP=learned, baselineErrorPP=baseline, driftErrorPP=drift_error,
                  rangeCoveragePct=covered/len(test)*100, expectedCoveragePct=80)
    # The later block chooses whether a line may be shown. It is not used to fit that line.
    if not chosen or learned>=baseline:
        return {**result, 'status':'baseline'}
    first_test = test[0][3]
    training = [row for row in targets if row['i']+horizon<=first_test]
    fit=market34.fit(training)
    prediction=max(-.35,min(.35,market34.predict(fit,features[-1])))
    base=prices[-1]['p']
    return {**result, 'status':'learned',
            'returnPct':math.expm1(prediction)*100, 'price':base*math.exp(prediction),
            'low':base*math.exp(min(prediction,prediction+low_q)),
            'high':base*math.exp(max(prediction,prediction+high_q)),
            'weights':fit['coef'], 'trainingCases':len(training)}


def report(g, symbol):
    symbol=g['valid_symbol'](symbol)
    if not g['ai_catalog_entry'](symbol):
        raise ValueError('Choose a US stock directory symbol.')
    now=int(g['time'].time()*1000)
    history=g['read_massive_daily_bars'](symbol,946684800,now//1000)
    closes=history['bars'] if history else {'t':[],'c':[]}
    points=market34.clean([{'t':t*1000,'p':p} for t,p in zip(closes['t'],closes['c'])],now)
    saved_points=list(points)
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
    revision=hashlib.sha256(json.dumps(['v50',METHOD,points]).encode()).hexdigest()
    with LOCK:
        with contextlib.closing(g['db_connection']()) as con:
            saved=con.execute('SELECT revision,body,trained_at FROM learning40 WHERE symbol=?',(symbol,)).fetchone()
        if saved and saved[0]==revision:
            result=json.loads(saved[1])
            trained=saved[2]
        else:
            jump=any(points and abs(math.log(b['p']/a['p']))>.7 for a,b in zip(points,points[1:]))
            result={'method':METHOD,'symbol':symbol,'closes':len(points),'first':points[0]['t'] if points else None,
                    'anchor':points[-1] if points else None,'rows':[] if jump else [evaluate(points,h) for h in HORIZONS],
                    'quality':'Extreme price jump needs review. The saved prices were not changed.' if jump else '',
                    'lab':[] if jump else lab45.challenge(points)}
            if jump:
                result['lab']=[{'horizon':h,'status':'withheld','released':None,'models':[],'misses':[],
                    'reason':'A one-day move is large enough to be a stock split or a bad print. The learned forecast was withheld. Saved prices were not changed.'} for h in HORIZONS]
            trained=now
            with g['LOCK'],contextlib.closing(g['db_connection']()) as con,con:
                con.execute('INSERT OR REPLACE INTO learning40 VALUES(?,?,?,?)',(symbol,revision,json.dumps(result,allow_nan=False),trained))
                con.execute('DELETE FROM learning40 WHERE symbol NOT IN (SELECT symbol FROM learning40 ORDER BY trained_at DESC LIMIT 60)')
    used_dates=[market37.dt.datetime.fromtimestamp(p['t']/1000,market37.NY).date().isoformat() for p in points]
    saved_dates=[market37.dt.datetime.fromtimestamp(p['t']/1000,market37.NY).date().isoformat() for p in saved_points]
    payload={**result,'trainedAt':trained,'anchorDate':used_dates[-1] if used_dates else None,'latestEligibleDate':latest,
            'stale':not points or used_dates[-1]!=latest,
            'coverage':{'savedCloses':len(saved_points),'usedCloses':len(points),
                'droppedForGap':max(0,len(saved_points)-len(points)),
                'firstUsed':used_dates[0] if used_dates else None,'lastUsed':used_dates[-1] if used_dates else None,
                'latestSavedDate':saved_dates[-1] if saved_dates else None,
                'latestSavedPrice':saved_points[-1]['p'] if saved_points else None,
                'source':'Massive · saved daily closes. Read from this Mac. No network call for this test.'},
            'knownCloses':lab45.known_closes(points, used_dates[-1] if used_dates else None)}
    payload['scorecard']=scorecard41.sync(g,symbol,payload,saved_points)
    return payload
