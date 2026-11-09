"""Comparable completed-session heatmaps. Grouped EOD data, never quote-age returns."""
import contextlib,datetime as dt,json,math,threading
from zoneinfo import ZoneInfo
NY=ZoneInfo('America/New_York');SYNC=threading.Lock()
PERIODS={'1D':1,'3D':3,'1W':5}
SOURCE='https://massive.com/docs/rest/stocks/aggregates/daily-market-summary'
def init(c):
 c.execute('CREATE TABLE IF NOT EXISTS heat37_days(generation TEXT NOT NULL,day TEXT NOT NULL,body TEXT NOT NULL,fetched_at INTEGER NOT NULL,PRIMARY KEY(generation,day))')
def today(g):return dt.datetime.fromtimestamp(g['time'].time(),NY).date()
def observed(d):return d+dt.timedelta(days=1 if d.weekday()==6 else -1 if d.weekday()==5 else 0)
def nth(y,m,w,n):
 d=dt.date(y,m,1);return d+dt.timedelta(days=(w-d.weekday())%7+7*(n-1))
def holidays(y):
 # NYSE New Year on Saturday does not close the preceding Friday.
 a=y%19;b=y//100;c=y%100;d=b//4;e=b%4;f=(b+8)//25;h=(19*a+b-d-(b-f+1)//3+15)%30;i=c//4;k=c%4;l=(32+2*e+2*i-h-k)%7;m=(a+11*h+22*l)//451
 easter=dt.date(y,(h+l-7*m+114)//31,(h+l-7*m+114)%31+1)
 new=dt.date(y,1,1);out={new+dt.timedelta(days=1) if new.weekday()==6 else new,nth(y,1,0,3),nth(y,2,0,3),easter-dt.timedelta(days=2),nth(y,9,0,1),nth(y,11,3,4),observed(dt.date(y,7,4)),observed(dt.date(y,12,25))}
 may=dt.date(y,5,31);out.add(may-dt.timedelta(days=may.weekday()))
 if y>=2022:out.add(observed(dt.date(y,6,19)))
 if y==2025:out.add(dt.date(2025,1,9))
 return out

def sessions(end,n=6):
 if not 2025<=end.year<=2028:raise ValueError('Update the exchange calendar before loading heatmap periods outside 2025–2028.')
 out=[];d=end-dt.timedelta(days=1)
 while len(out)<n:
  if d.weekday()<5 and d not in holidays(d.year):out.append(d.isoformat())
  d-=dt.timedelta(days=1)
 return out

def directory(g):return json.loads((g['ROOT']/'ai_catalog.json').read_text())
def normalise(payload,day,wanted):
 if not isinstance(payload,dict) or payload.get('adjusted') is not True or payload.get('status') not in ('OK','DELAYED'):raise ValueError('Grouped prices must be marked split-adjusted by Massive.')
 rows=payload.get('results',[])
 if not isinstance(rows,list) or len(rows)>50000:raise ValueError('Invalid daily market summary.')
 found={};seen=set();invalid=[]
 for row in rows:
  if not isinstance(row,dict):continue
  sym=row.get('T')
  if sym not in wanted:continue
  if sym in seen:raise ValueError('Duplicate company in daily market summary.')
  seen.add(sym)
  try:
   t=row['t'];o,h,l,c,v=(row[k] for k in ('o','h','l','c','v'))
   if isinstance(t,bool) or not isinstance(t,int) or dt.datetime.fromtimestamp(t/1000,NY).date().isoformat()!=day:raise ValueError()
   if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in (o,h,l,c,v)):raise ValueError()
   if not (0<l<=o<=h<=1e9 and l<=c<=h and 0<=v<=1e13):raise ValueError()
   found[sym]={'t':t,'o':o,'h':h,'l':l,'c':c,'v':v}
  except (KeyError,ValueError,OverflowError,OSError,TypeError):invalid.append(sym)
 return {'rows':found,'invalid':invalid}

def saved(g):
 with contextlib.closing(g['db_connection']()) as c:rows=c.execute('SELECT generation,day,body,fetched_at FROM heat37_days ORDER BY generation DESC,day DESC').fetchall()
 result={}
 for gen,day,body,stamp in rows:
  try:
   value=json.loads(body)
   # Revalidate stored values too. Corruption is never a new price source.
   parsed=normalise({'status':'OK','adjusted':True,'results':[{'T':sym,**v} for sym,v in value['rows'].items()]},day,set(value['rows']))
   if parsed['invalid'] or not parsed['rows']:continue
   result.setdefault(gen,{})[day]={**parsed,'fetchedAt':stamp}
  except (ValueError,KeyError,TypeError):continue
 return result

def packet(g,period='1D',extra=''):
 if period not in PERIODS:raise ValueError('Choose 1D, 3D or 1W.')
 current=today(g);targets=sessions(current);gen=current.isoformat();all_saved=saved(g);days=all_saved.get(gen,{})
 # Retain an older usable map while a fresh update is being collected.
 usable=[k for k,v in all_saved.items() if len(v)>=PERIODS[period]+1 and k<=gen]
 selected=gen if all(x in days for x in targets[:PERIODS[period]+1]) else (max(usable) if usable else gen)
 source_days=all_saved.get(selected,{});chosen=sessions(dt.date.fromisoformat(selected));need=chosen[:PERIODS[period]+1];end,start=need[0],need[-1]
 entries=directory(g);known={x['symbol'] for x in entries};directory_symbols=set(known)
 for sym in list(dict.fromkeys(extra.split(',')))[:60]:
  if not sym:continue
  sym=g['valid_symbol'](sym)
  if sym not in known:entries.append({'symbol':sym,'name':sym,'category':'Other watched companies','currency':'USD'});known.add(sym)
 rows=[]
 for entry in entries:
  sym=entry['symbol'];points=[source_days.get(day,{}).get('rows',{}).get(sym) for day in reversed(need)];complete=all(points)
  change=(points[-1]['c']/points[0]['c']-1)*100 if complete else None
  if change is not None and not math.isfinite(change):change=None
  rows.append({'symbol':sym,'name':entry['name'],'category':entry['category'],'inDirectory':sym in directory_symbols,'listingCurrency':entry.get('currency','USD'),'change':change,'price':points[-1]['c'] if points[-1] else None,'start':start,'end':end,'period':period,'points':[{'date':d,'price':p['c']} for d,p in zip(reversed(need),points) if p] if complete else [],'reason':None if complete else 'Missing one or more required daily bars; load company history.','fetchedAt':max((source_days.get(d,{}).get('fetchedAt',0) for d in need),default=0)})
 return {'rows':rows,'period':period,'start':start,'end':end,'generation':selected,'latestAvailableSession':targets[0],'stale':end!=targets[0],'completed':sum(x in days for x in targets),'required':6,'nextDay':next((x for x in targets if x not in days),None),'configured':bool(g['get_massive_key']()),'asOf':int(g['time'].time()*1000),'source':SOURCE,'notice':'Split-adjusted close-to-close price change over 1, 3 or 5 completed US trading sessions. Not a rolling 24-hour or total return; no dividends or FX added. Same required dates for every company. Missing bars stay unavailable. Exchange calendar checked through 2028; extraordinary closures may require an update.'}

def step(g,obj):
 if not isinstance(obj,dict):raise ValueError('Use a company-history request object.')
 # One market-wide request per call. Shared provider budget controls all callers.
 if not SYNC.acquire(blocking=False):return {'status':'waiting','retryAfter':16,'message':'Another company-history update is in progress.'}
 try:
  gen=today(g).isoformat();target=sessions(today(g));days=saved(g).get(gen,{});day=next((x for x in target if x not in days),None)
  if not day:return {'status':'complete','completed':6,'required':6}
  if not g['get_massive_key']():return {'status':'connection','message':'Connect your free Massive key in Settings to load completed-day prices for the whole directory.'}
  wanted={x['symbol'] for x in directory(g)}
  if not isinstance(obj.get('symbols',[]),list) or len(obj.get('symbols',[]))>60:raise ValueError('Use up to 60 extra watched symbols.')
  for x in obj.get('symbols',[])[:60]:wanted.add(g['valid_symbol'](x))
  try:payload,_=g['massive_request']('v2/aggs/grouped/locale/us/market/stocks/'+day,{'adjusted':'true','include_otc':'false'},ttl=21600,max_bytes=8000000)
  except g['ProviderError'] as error:return {'status':'waiting' if error.status==429 else 'error','retryAfter':max(16,error.retry_after or 16),'message':error.message}
  value=normalise(payload,day,wanted)
  if not value['rows']:return {'status':'error','message':'No usable directory prices returned for '+day+'. An exceptional closure or unavailable dataset is not treated as zero.'}
  stamp=int(g['time'].time()*1000)
  with g['LOCK'],contextlib.closing(g['db_connection']()) as c,c:
   c.execute('INSERT OR REPLACE INTO heat37_days VALUES(?,?,?,?)',(gen,day,json.dumps(value,allow_nan=False),stamp))
   c.execute('DELETE FROM heat37_days WHERE generation NOT IN (SELECT DISTINCT generation FROM heat37_days ORDER BY generation DESC LIMIT 3)')
   c.executemany('INSERT OR REPLACE INTO massive_daily_bars VALUES(?,?,?,?,?,?,?,?)',[(sym,row['t'],row['o'],row['h'],row['l'],row['c'],row['v'],stamp//1000) for sym,row in value['rows'].items()])
   for sym in value['rows']:c.execute('DELETE FROM massive_daily_bars WHERE symbol=? AND ts_ms NOT IN (SELECT ts_ms FROM massive_daily_bars WHERE symbol=? ORDER BY ts_ms DESC LIMIT 550)',(sym,sym))
  return {'status':'complete' if len(days)+1==6 else 'progress','day':day,'completed':len(days)+1,'required':6,'companies':len(value['rows']),'invalid':len(value['invalid']),'retryAfter':16}
 finally:SYNC.release()
