"""Prospective, locally recorded five-session forecasts. No historical prediction backfill."""
import contextlib,datetime as dt,hashlib,json,math,re,uuid
from zoneinfo import ZoneInfo
import market34
NY=ZoneInfo('America/New_York');GRACE=15*60*1000;CAP=200
CLOSED={2026:'01-01 01-19 02-16 04-03 05-25 06-19 07-03 09-07 11-26 12-25'.split(),2027:'01-01 01-18 02-15 03-26 05-31 06-18 07-05 09-06 11-25 12-24'.split(),2028:'01-17 02-21 04-14 05-29 06-19 07-04 09-04 11-23 12-25'.split()}
EARLY={2026:['11-27','12-24'],2027:['11-26'],2028:['07-03','11-24']}
NOTICE='Scheduled NYSE regular equity sessions, 2026–2028; unexpected closures are possible. Local records are not independently audited. No forecasts or outcomes are invented while this app or Mac is off.'
def millis():return int(dt.datetime.now(dt.timezone.utc).timestamp()*1000)
def day(t):return dt.datetime.fromtimestamp(t/1000,NY).date()
def close_at(d):
 if d.year not in CLOSED:raise ValueError('The bundled session calendar covers 2026–2028 only.')
 if d.weekday()>4 or d.strftime('%m-%d') in CLOSED[d.year]:return None
 return int(dt.datetime.combine(d,dt.time(13 if d.strftime('%m-%d') in EARLY[d.year] else 16),NY).timestamp()*1000)
def last_session(now):
 d=day(now)
 for _ in range(12):
  close=close_at(d)
  if close is not None and close+GRACE<=now:return d
  d-=dt.timedelta(days=1)
 raise ValueError('A recent completed session could not be established.')
def future_sessions(d):
 out=[]
 while len(out)<5:
  d+=dt.timedelta(days=1)
  if close_at(d) is not None:out.append(d.isoformat())
 return out
def init(con):
 con.execute('CREATE TABLE IF NOT EXISTS forecast35(id TEXT PRIMARY KEY,symbol TEXT NOT NULL,anchor_day TEXT NOT NULL,issued_at INTEGER NOT NULL,body TEXT NOT NULL,outcome TEXT,archived INTEGER NOT NULL DEFAULT 0,UNIQUE(symbol,anchor_day))')
def encoded(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(x):return hashlib.sha256(encoded(x).encode()).hexdigest()
def series(g,symbol,now):
 saved=g['read_massive_daily_bars'](symbol,946684800,now//1000)
 if not saved:return []
 with contextlib.closing(g['db_connection']()) as c:fetches=dict(c.execute('SELECT ts_ms,fetched_at FROM massive_daily_bars WHERE symbol=?',(symbol,)))
 out=[];seen=set()
 for t,p in zip(saved['bars']['t'],saved['bars']['c']):
  stamp=t*1000;fetched=fetches.get(stamp);fetched=fetched*1000 if market34.finite(fetched) else None;date=day(stamp)
  if date.year>max(CLOSED):continue
  close=close_at(date) if date.year in CLOSED else (int(dt.datetime.combine(date,dt.time(16),NY).timestamp()*1000) if date.weekday()<5 else None)
  if close is not None and close+GRACE<=now and market34.finite(fetched) and close+GRACE<=fetched<=now:
   if date in seen:return []
   seen.add(date);out.append({'t':stamp,'p':p})
 return out

def create(g,symbol,now=None):
 now=millis() if now is None else now;entry=g['ai_catalog_entry'](symbol)
 if not entry or entry.get('exchange','').lower() not in ('nasdaq','nyse') or entry.get('currency')!='USD':raise ValueError('Prospective tracking currently requires a verified Nasdaq/NYSE USD listing from the local directory.')
 with g['LOCK']:
  points=series(g,symbol,now);benchmark=series(g,'SPY',now) if symbol!='SPY' else []
  model=market34.run(points,benchmark,now)
  if model['status']!='ok' or model.get('stale') or model.get('forecastPrice') is None:raise ValueError(model.get('reason') or 'The model needs recent supported daily closes before a forecast can be recorded.')
  anchor=day(model['anchor']['t'])
  if anchor!=last_session(now):raise ValueError('The most recently completed scheduled session is missing or was fetched too early. Update daily history first; old predictions cannot be recorded retrospectively.')
  targets=future_sessions(anchor);first_close=close_at(dt.date.fromisoformat(targets[0]))
  if first_close<=now:raise ValueError('The first forecast session has already closed. A fresh starting point is required.')
  receipt={'version':1,'id':uuid.uuid4().hex,'symbol':symbol,'currency':'USD','issuedAt':now,'anchorDay':anchor.isoformat(),'targetDays':targets,'method':market34.METHOD,'model':{k:v for k,v in model.items() if k!='tests'},'trainingPrices':points[-500:],'benchmarkPrices':benchmark[-500:] if model['benchmarkUsed'] else [],'notice':NOTICE}
  receipt['hash']=digest(receipt)
  with contextlib.closing(g['db_connection']()) as c,c:
   c.execute('BEGIN IMMEDIATE')
   if c.execute('SELECT count(*) FROM forecast35').fetchone()[0]>=CAP:raise ValueError('The journal has reached its 200-record limit. Export your records; none were automatically deleted.')
   if c.execute('SELECT 1 FROM forecast35 WHERE symbol=? AND anchor_day=?',(symbol,anchor.isoformat())).fetchone():raise ValueError('This company already has a forecast for that starting session. It cannot be replaced with a more favourable result.')
   c.execute('INSERT INTO forecast35(id,symbol,anchor_day,issued_at,body) VALUES(?,?,?,?,?)',(receipt['id'],symbol,anchor.isoformat(),now,encoded(receipt)))
 return receipt

def validate_receipt(raw):
 if not isinstance(raw,dict) or raw.get('hash')!=digest({k:v for k,v in raw.items() if k!='hash'}):raise ValueError('The saved forecast record failed its integrity check.')
 if raw.get('method')!=market34.METHOD or len(raw.get('targetDays',[]))!=5:raise ValueError('The saved forecast method is unsupported.')
 return raw

def evaluate(receipt,points,now,outcome=None):
 r=validate_receipt(receipt);m=r['model'];bydate={day(p['t']).isoformat():p for p in points};known={p['t']:p['p'] for p in points};anchor=r['anchorDay'];target=r['targetDays']
 for p in r['trainingPrices']:
  if p['t'] in known and not math.isclose(p['p'],known[p['t']],rel_tol=1e-10,abs_tol=1e-12):return {'status':'revised','reason':'Saved training prices changed; a split, correction or adjustment may be involved. Scoring is withheld.'}
 if outcome:
  if not isinstance(outcome,dict) or outcome.get('hash')!=digest({k:v for k,v in outcome.items() if k!='hash'}):raise ValueError('The outcome record failed its integrity check.')
  if len(outcome.get('targetPrices',[]))!=5 or not market34.finite(outcome.get('assessedAt')) or not close_at(dt.date.fromisoformat(target[-1]))+GRACE<=outcome['assessedAt']<=now:raise ValueError('Invalid outcome timing.')
  if any(not isinstance(p,dict) or not market34.finite(p.get('t')) or not market34.finite(p.get('p')) or not 0<p['p']<=1e9 or day(p['t']).isoformat()!=d for d,p in zip(target,outcome['targetPrices'])):raise ValueError('Invalid frozen outcome prices.')
  actual=outcome['targetPrices'][-1]['p'];ret=(actual/m['anchor']['p']-1)*100;error=abs(ret-m['forecastReturnPct'])
  for key,value in [('actualPrice',actual),('actualReturnPct',ret),('absoluteErrorPP',error),('unchangedErrorPP',abs(ret))]:
   if not market34.finite(outcome.get(key)) or not math.isclose(outcome[key],value,rel_tol=1e-10,abs_tol=1e-10):raise ValueError('The recorded score does not match its frozen prices.')
  if outcome.get('inRange')!=(m['range']['lowPrice']<=actual<=m['range']['highPrice'] if m.get('range') else None):raise ValueError('The recorded range result does not match its prices.')
  if any(d in bydate and not math.isclose(bydate[d]['p'],p['p'],rel_tol=1e-10,abs_tol=1e-12) for d,p in zip(target,outcome['targetPrices'])):return {'status':'revised','reason':'Outcome prices changed after the recorded assessment. Scoring is withheld; the original assessment is retained.'}
  return {'status':'resolved','outcome':outcome,'rechecked':all(d in bydate for d in [anchor,*target])}
 completed=sum(close_at(dt.date.fromisoformat(d))+GRACE<=now for d in target)
 if completed<5:return {'status':'waiting','completedSessions':completed,'availableCloses':sum(d in bydate for d in target),'reason':'Waiting for the five scheduled future sessions to finish and their verified closes to arrive.'}
 if anchor not in bydate or any(d not in bydate for d in target):return {'status':'missing','reason':'The target period has finished, but required saved closes are missing. Later dates are not substituted.'}
 actual=bydate[target[-1]]['p'];base=m['anchor']['p'];ret=(actual/base-1)*100;error=abs(ret-m['forecastReturnPct']);naive=abs(ret)
 if not all(math.isfinite(x) and abs(x)<1e9 for x in (ret,error,naive)):return {'status':'withheld','reason':'The outcome exceeds the supported scoring range.'}
 result={'assessedAt':now,'targetPrices':[bydate[d] for d in target],'actualPrice':actual,'actualReturnPct':ret,'absoluteErrorPP':error,'unchangedErrorPP':naive,'inRange':m['range']['lowPrice']<=actual<=m['range']['highPrice'] if m.get('range') else None}
 result['hash']=digest(result)
 return {'status':'resolved','outcome':result,'rechecked':True}

def totals(rows):
 scored=[x for x in rows if x['evaluation']['status']=='resolved'];cohort=[];last={}
 for x in sorted(scored,key=lambda x:(x['issuedAt'],x['id'])):
  if x['anchorDay']>=last.get(x['symbol'],''):
   cohort.append(x);last[x['symbol']]=x['targetDays'][-1]
 def metrics(items):
  if not items:return {'count':0,'modelErrorPP':None,'unchangedErrorPP':None,'skillPct':None,'rangeCount':0,'rangeCoveragePct':None}
  outcomes=[x['evaluation']['outcome'] for x in items];mae=sum(x['absoluteErrorPP'] for x in outcomes)/len(items);baseline=sum(x['unchangedErrorPP'] for x in outcomes)/len(items);ranges=[x['inRange'] for x in outcomes if x['inRange'] is not None]
  return {'count':len(items),'modelErrorPP':mae,'unchangedErrorPP':baseline,'skillPct':100*(1-mae/baseline) if baseline else None,'rangeCount':len(ranges),'rangeCoveragePct':sum(ranges)/len(ranges)*100 if ranges else None}
 return {'all':metrics(scored),'nonOverlapping':metrics(cohort),'notice':'All archived records remain included. The non-overlapping cohort is selected chronologically within each company; cross-company results can still be correlated. Small samples do not establish an edge. Errors exclude fees, spreads, dividends, FX and execution.'}

def read(g,now=None,export=False):
 now=millis() if now is None else now
 with g['LOCK'],contextlib.closing(g['db_connection']()) as c,c:
  stored=c.execute('SELECT id,symbol,issued_at,body,outcome,archived FROM forecast35 ORDER BY issued_at DESC,id').fetchall();cache={};rows=[]
  for ident,symbol,issued,body,outcome,archived in stored:
   try:
    receipt=validate_receipt(json.loads(body))
    if receipt['id']!=ident or receipt['symbol']!=symbol or receipt['issuedAt']!=issued:raise ValueError('Forecast metadata no longer matches its receipt.')
    if symbol not in cache:cache[symbol]=series(g,symbol,now)
    e=evaluate(receipt,cache[symbol],now,json.loads(outcome) if outcome else None)
    if not outcome and e['status']=='resolved':c.execute('UPDATE forecast35 SET outcome=? WHERE id=? AND outcome IS NULL',(encoded(e['outcome']),ident))
    item={k:v for k,v in receipt.items() if export or k not in ('trainingPrices','benchmarkPrices')};item.update(archived=bool(archived),evaluation=e);rows.append(item)
   except (ValueError,TypeError,KeyError,OverflowError):rows.append({'id':ident,'symbol':symbol,'issuedAt':issued,'archived':bool(archived),'evaluation':{'status':'damaged','reason':'This local record could not be verified. It was retained and excluded from scores.'}})
 return {'version':1,'asOf':now,'rows':rows,'summary':totals(rows),'limit':CAP,'notice':NOTICE,'storageNotice':'Journal receipts and outcomes live in the private price database, separately from research JSON backups. Download the journal to keep an audit copy; it is not an import or restore file.'}
def archive(g,ident,value):
 if not isinstance(ident,str) or not re.fullmatch('[a-f0-9]{32}',ident) or not isinstance(value,bool):raise ValueError('Choose a valid forecast record and archive setting.')
 with g['LOCK'],contextlib.closing(g['db_connection']()) as c,c:
  if c.execute('UPDATE forecast35 SET archived=? WHERE id=?',(int(value),ident)).rowcount!=1:raise ValueError('Forecast record not found.')
