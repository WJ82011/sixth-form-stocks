"""Local evidence calculations. No network, credentials or generated observations."""
import math

INTRADAY_SOURCES = {'finnhub_quote', 'finnhub_websocket_trade', 'finnhub_websocket_update', 'finnhub_websocket'}

def clean(raw, now, sources=None):
    out = {}
    for x in raw:
        t, p = x.get('t'), x.get('p')
        if (isinstance(t, (int, float)) and not isinstance(t, bool) and math.isfinite(t)
            and 946684800000 <= t <= now and isinstance(p, (int, float))
            and not isinstance(p, bool) and math.isfinite(p) and 0 < p <= 1e9
            and (sources is None or x.get('source') in sources)):
            out[t] = dict(x)
    return sorted(out.values(), key=lambda x: x['t'])


def overview(raw, now, hours):
    start = now - hours * 3600000
    pts = [x for x in clean(raw, now, INTRADAY_SOURCES) if x['t'] >= start]
    # Coverage is occupied one-minute slots, NOT a claim of continuous capture.
    slots = len({int((x['t'] - start) // 60000) for x in pts if x['t'] < now})
    gaps = [{'from': a['t'], 'to': b['t']} for a, b in zip(pts, pts[1:]) if b['t']-a['t'] > 300000]
    result = dict(hours=hours, start=start, end=now, count=len(pts), occupiedMinutes=slots,
                  requestedMinutes=hours*60, gaps=gaps, first=pts[0] if pts else None,
                  last=pts[-1] if pts else None, sources=sorted({x['source'] for x in pts}),
                  stale=not pts or now-pts[-1]['t'] > 300000,
                  complete=False, points=pts)
    if len(pts) >= 2:
        low=min(pts,key=lambda x:x['p']); high=max(pts,key=lambda x:x['p'])
        result.update(changePct=(pts[-1]['p']/pts[0]['p']-1)*100, low=low, high=high)
    return result


def fit(rows):
    # Fixed ridge penalty; learned intercept and slope on lagged log returns.
    n=len(rows); mx=sum(x for x,y in rows)/n; my=sum(y for x,y in rows)/n
    slope=sum((x-mx)*(y-my) for x,y in rows)/(sum((x-mx)**2 for x,y in rows)+0.01)
    return my-slope*mx, slope


def daily_model(raw, now):
    pts=clean(raw, now)
    # Daily close series only. Never mix local ticks with EOD training data.
    pts=[x for x in pts if x.get('source') == 'massive_daily']
    pts=pts[-500:]
    base=dict(status='insufficient', count=len(pts), required=90, source='Stored Massive split-adjusted daily closes',
              method='Uses the last daily price change to estimate the next one (ridge AR(1), penalty 0.01). Each past test learns only from earlier data',
              computedAt=now, notice='Recalculates when you check saved data while the app runs. It does not learn while the Mac is off. News and company figures are not used to predict prices.')
    if len(pts)<90: return base
    if any(not 20*3600000 <= b['t']-a['t'] <= 5*86400000 for a,b in zip(pts,pts[1:])):
        return dict(base,status='invalid_spacing')
    returns=[math.log(b['p']/a['p']) for a,b in zip(pts,pts[1:])]
    rows=list(zip(returns[:-1],returns[1:]))
    errors=[]; baseline=[]; signed=[]; predictions=[]; actuals=[]
    for i in range(60,len(rows)):
        a,b=fit(rows[:i]); pred=a+b*rows[i][0]; target=rows[i][1]
        # Avoid numeric overflow on corrupt/extreme histories; no optimistic output.
        if abs(pred)>1 or abs(target)>1: return dict(base,status='extreme_returns')
        predictions.append(pred); actuals.append(target)
        errors.append(abs(math.exp(pred-target)-1)*100)
        baseline.append(abs(math.exp(-target)-1)*100)
        signed.append(target-pred)
    a,b=fit(rows); pred=a+b*returns[-1]
    if abs(pred)>1: return dict(base,status='extreme_returns')
    # Earlier OOS residuals form an empirical error band; final third evaluates it.
    cut=max(10,len(signed)*2//3)
    calibration=sorted(abs(x) for x in signed[:cut])
    radius=calibration[min(len(calibration)-1,math.ceil(.9*len(calibration))-1)]
    evaluation=signed[cut:]
    return dict(base,status='ok',trainFrom=pts[0]['t'],trainTo=pts[-1]['t'],
                stale=now-pts[-1]['t']>5*86400000, coefficients={'intercept':a,'lagReturn':b},
                samples=len(errors), maePct=sum(errors)/len(errors), baselineMaePct=sum(baseline)/len(baseline),
                directionAccuracy=sum((p>0)==(y>0) for p,y in zip(predictions,actuals))/len(errors),
                bandCalibration=len(calibration),bandTests=len(evaluation),
                bandCoverage=sum(abs(x)<=radius for x in evaluation)/len(evaluation) if evaluation else None,
                nextChangePct=math.expm1(pred)*100, lastClose=pts[-1]['p'],
                lower=pts[-1]['p']*math.exp(pred-radius),upper=pts[-1]['p']*math.exp(pred+radius),
                predictedClose=pts[-1]['p']*math.exp(pred), empiricalRadius=radius)
