"""Expanding-window ridge on historical daily-price factors. No news/fundamental backfill."""
import datetime as dt,math,statistics
DAY=86400000;HORIZON=5;LOOKBACK=60;TRAIN=100;RIDGE=.1
METHOD='price-factors-ridge-v1'
def finite(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def clean(raw,now):
 if not isinstance(raw,list):return []
 rows=[];seen=set()
 for p in raw:
  if not isinstance(p,dict) or not finite(p.get('t')) or not finite(p.get('p')) or p['t']!=int(p['t']) or not 946684800000<=p['t']<=now or not 0<p['p']<=1e9:continue
  if p['t'] in seen:raise ValueError('Duplicate daily labels are not a training series.')
  seen.add(p['t']);rows.append({'t':int(p['t']),'p':float(p['p'])})
 return sorted(rows,key=lambda p:p['t'])[-500:]
def solve(a,b):
 m=[list(row)+[y] for row,y in zip(a,b)];n=len(b)
 for k in range(n):
  pivot=max(range(k,n),key=lambda i:abs(m[i][k]));m[k],m[pivot]=m[pivot],m[k]
  if abs(m[k][k])<1e-12:raise ValueError('Model design matrix is singular.')
  v=m[k][k];m[k]=[x/v for x in m[k]]
  for i in range(n):
   if i==k:continue
   v=m[i][k];m[i]=[x-v*y for x,y in zip(m[i],m[k])]
 return [r[-1] for r in m]
def fit(rows):
 n=len(rows);k=len(rows[0]['x']);means=[sum(r['x'][j] for r in rows)/n for j in range(k)];scales=[math.sqrt(sum((r['x'][j]-means[j])**2 for r in rows)/n) or 1 for j in range(k)];my=sum(r['y'] for r in rows)/n
 z=[[(r['x'][j]-means[j])/scales[j] for j in range(k)] for r in rows];a=[[sum(v[i]*v[j] for v in z)/n+(RIDGE if i==j else 0) for j in range(k)] for i in range(k)];b=[sum(v[j]*(r['y']-my) for v,r in zip(z,rows))/n for j in range(k)];coef=solve(a,b)
 return {'means':means,'scales':scales,'meanY':my,'coef':coef,'count':n}
def predict(f,x):return f['meanY']+sum(c*(v-m)/s for c,v,m,s in zip(f['coef'],x,f['means'],f['scales']))
def quantile(a,p):
 a=sorted(a);pos=(len(a)-1)*p;lo=int(pos);hi=min(lo+1,len(a)-1);return a[lo]+(a[hi]-a[lo])*(pos-lo)
def features(points,i,benchmark=None):
 logs=[math.log(p['p']) for p in points];ret=[logs[j]-logs[j-1] for j in range(max(1,i-19),i+1)];mean=sum(ret)/len(ret)
 x=[logs[i]-logs[i-1],logs[i]-logs[i-5],logs[i]-logs[i-20],math.sqrt(sum((x-mean)**2 for x in ret)/len(ret)),logs[i]-max(logs[i-59:i+1])]
 if benchmark:x.extend([math.log(benchmark[i])-math.log(benchmark[i-1]),math.log(benchmark[i])-math.log(benchmark[i-5])])
 return x
def run(raw,benchmark=None,now=None):
 now=now or int(dt.datetime.now(dt.timezone.utc).timestamp()*1000);points=clean(raw,now);used=False;bench=None
 if benchmark:
  bm={p['t']:p['p'] for p in clean(benchmark,now)};suffix=[]
  for p in reversed(points):
   if p['t'] not in bm:break
   suffix.append(p)
  if len(suffix)>=220:points=list(reversed(suffix));bench=[bm[p['t']] for p in points];used=True
 base={'method':METHOD,'horizonObservations':HORIZON,'count':len(points),'required':220,'benchmarkUsed':used,'features':['previous close return','5-close momentum','20-close momentum','20-close volatility','60-close drawdown']+(['SPY previous close return','SPY 5-close momentum'] if used else []),'notice':'Daily-price factors only. Source dates are session labels; forecasts assume availability after the completed close. No historical news, product launches or restated fundamentals were supplied as predictive features. Split-adjusted provider history is not a point-in-time exchange archive. No learning while the app/Mac is off.'}
 if len(points)<220:return {**base,'status':'insufficient','reason':'At least 220 saved verified daily closes are needed. No imported/synthetic history is substituted.'}
 if any(not 20*3600000<=b['t']-a['t']<=5*DAY for a,b in zip(points,points[1:])):return {**base,'status':'withheld','reason':'Daily labels contain unsupported spacing or gaps.'}
 if any(abs(math.log(b['p'])-math.log(a['p']))>.7 for a,b in zip(points,points[1:])):return {**base,'status':'withheld','reason':'Extreme daily returns are outside this experimental model’s supported range.'}
 rows=[{'i':i,'knownBy':i+HORIZON,'x':features(points,i,bench),'y':math.log(points[i+HORIZON]['p'])-math.log(points[i]['p'])} for i in range(LOOKBACK,len(points)-HORIZON)]
 tests=[];errors=[];naive=[];residuals=[];covered=[]
 for i in range(LOOKBACK+TRAIN+HORIZON,len(points)-HORIZON,HORIZON):
  training=[r for r in rows if r['knownBy']<=i];x=features(points,i,bench);pred=predict(fit(training),x);actual=math.log(points[i+HORIZON]['p'])-math.log(points[i]['p'])
  if not math.isfinite(pred) or abs(pred)>1 or abs(actual)>2:return {**base,'status':'withheld','reason':'Predicted or realised return is outside the supported range.'}
  if len(residuals)>=20:covered.append(pred+quantile(residuals,.1)<=actual<=pred+quantile(residuals,.9))
  predictedReturn=math.expm1(pred)*100;actualReturn=math.expm1(actual)*100;errors.append(abs(predictedReturn-actualReturn));naive.append(abs(actualReturn));residuals.append(actual-pred)
  tests.append({'anchor':points[i]['t'],'target':points[i+HORIZON]['t'],'predictionLogReturn':pred,'actualLogReturn':actual,'trainingRows':len(training),'lastTrainingTarget':points[max(r['knownBy'] for r in training)]['t']})
 if not tests:return {**base,'status':'insufficient','reason':'No chronological holdout cases available.'}
 full=fit(rows);prediction=predict(full,features(points,len(points)-1,bench))
 if not math.isfinite(prediction) or abs(prediction)>1:return {**base,'status':'withheld','reason':'Current prediction is outside the supported range.'}
 mae=sum(errors)/len(errors);baseline=sum(naive)/len(naive);band=None
 if len(residuals)>=20:
  band={'lowPrice':points[-1]['p']*math.exp(prediction+quantile(residuals,.1)),'highPrice':points[-1]['p']*math.exp(prediction+quantile(residuals,.9)),'notice':'Central historical residual range, not a guaranteed probability interval.'}
 stale=now-points[-1]['t']>10*DAY
 return {**base,'status':'ok','anchor':points[-1],'stale':stale,'forecastPrice':None if stale else points[-1]['p']*math.exp(prediction),'forecastReturnPct':None if stale else math.expm1(prediction)*100,'range':None if stale else band,'backtest':{'cases':len(tests),'step':HORIZON,'absoluteReturnErrorPP':mae,'unchangedPriceErrorPP':baseline,'skillVsUnchangedPct':(1-mae/baseline)*100 if baseline else None,'sequentialRangeCases':len(covered),'sequentialRangeCoveragePct':sum(covered)/len(covered)*100 if covered else None,'notice':'Expanding training; labels must end by each test anchor. Test anchors are five observed closes apart. Range coverage uses only earlier holdout residuals. No favourable hyperparameter search on these results.'},'tests':tests,'training':{'rows':full['count'],'ridgePenalty':RIDGE,'meanLogReturn':full['meanY'],'factorWeightsPerTrainingStandardDeviation':full['coef'],'factorTrainingMeans':full['means'],'factorTrainingScales':full['scales'],'standardization':'Training rows only, recomputed per fold.'},'limitations':['This does not establish an edge, causal relationship or future profitability. Negative skill means it lost to an unchanged-price baseline.','News/product/fundamental variables need reliable historical availability timestamps before they can be added to a supervised backtest.','Forecast basis is the last saved close, not the live quote. No fixed future calendar date is invented.']}
