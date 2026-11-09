"""Bounded source snapshots for a local stock screener. No network or AI calls."""
import json,math,re
MAX_RECORDS=1500
PROFILE=('name','ticker','currency','exchange','finnhubIndustry')
METRICS=('peTTM','peBasicExclExtraTTM','revenueGrowthTTMYoy','netProfitMarginTTM')
def init(con):
 con.execute('CREATE TABLE IF NOT EXISTS screen_snapshots(symbol TEXT NOT NULL,kind TEXT NOT NULL,fetched_at INTEGER NOT NULL,body TEXT NOT NULL,PRIMARY KEY(symbol,kind))')
def number(value,positive=False):
 return value if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and abs(value)<=1e12 and (not positive or value>0) else None
def stamp(value,now):
 return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and 946684800000<=value<=now+60000
def sanitize(symbol,kind,raw,now):
 if not isinstance(raw,dict):return None
 if kind=='quote':
  price=number(raw.get('c'),True);ts=number(raw.get('t'),True)
  if price is None or price>1e9 or ts is None or not stamp(ts*1000,now):return None
  return {k:v for k,v in {'c':price,'pc':number(raw.get('pc'),True),'t':int(ts)}.items() if v is not None}
 if kind=='profile':
  if raw.get('ticker') and str(raw['ticker']).upper()!=symbol:return None
  data={k:re.sub(r'[\x00-\x1f\x7f]','',raw[k]).strip()[:180] for k in PROFILE if isinstance(raw.get(k),str) and raw[k].strip()}
  if 'currency' in data:data['currency']=data['currency'].upper()
  if 'currency' in data and not re.fullmatch('[A-Z]{3}',data['currency']):data.pop('currency')
  cap=number(raw.get('marketCapitalization'),True)
  if cap is not None:data['marketCapitalization']=cap
  return data or None
 if kind=='metrics':
  if raw.get('symbol') and str(raw['symbol']).upper()!=symbol:return None
  values=raw.get('metric',{})
  if not isinstance(values,dict):return None
  values={k:number(values[k]) for k in METRICS if k in values and number(values[k]) is not None}
  return {'metric':values} if values else None
 raise ValueError('Unknown snapshot type.')
def remember(con,symbol,kind,raw,fetched_at,now):
 if not re.fullmatch(r'[A-Z0-9][A-Z0-9.\-:_]{0,23}',symbol):return False
 if not stamp(fetched_at,now):return False
 clean=sanitize(symbol,kind,raw,now)
 if clean is None:return False
 old=con.execute('SELECT fetched_at,body FROM screen_snapshots WHERE symbol=? AND kind=?',(symbol,kind)).fetchone()
 if old:
  if fetched_at<old[0]:return False
  if kind=='quote' and clean['t']<json.loads(old[1]).get('t',0):return False
 con.execute('INSERT OR REPLACE INTO screen_snapshots VALUES(?,?,?,?)',(symbol,kind,int(fetched_at),json.dumps(clean,allow_nan=False)))
 con.execute('DELETE FROM screen_snapshots WHERE rowid NOT IN (SELECT rowid FROM screen_snapshots ORDER BY fetched_at DESC LIMIT ?)',(MAX_RECORDS,))
 return True
def snapshot(con,symbol,kind):
 row=con.execute('SELECT fetched_at,body FROM screen_snapshots WHERE symbol=? AND kind=?',(symbol,kind)).fetchone()
 return (row[0],json.loads(row[1])) if row else (None,None)
def rows(con,catalog,extras,now):
 saved={(s,k):(t,json.loads(b)) for s,k,t,b in con.execute('SELECT symbol,kind,fetched_at,body FROM screen_snapshots')}
 directory={x['symbol']:x for x in catalog};universe=dict(directory)
 for symbol in extras:universe.setdefault(symbol,{'symbol':symbol,'name':symbol,'category':'Outside directory','currency':'','exchange':''})
 result=[]
 for symbol,entry in universe.items():
  qt,q=saved.get((symbol,'quote'),(None,{}));pt,p=saved.get((symbol,'profile'),(None,{}));mt,m=saved.get((symbol,'metrics'),(None,{}));m=m.get('metric',{})
  price=number(q.get('c'),True);previous=number(q.get('pc'),True);quote_time=q.get('t',0)*1000
  if not stamp(quote_time,now) or price is None:price=None;previous=None;quote_time=None
  change=(price/previous-1)*100 if price is not None and previous is not None else None
  pe=number(m.get('peTTM'));pe_field='peTTM'
  if pe is None:pe=number(m.get('peBasicExclExtraTTM'));pe_field='peBasicExclExtraTTM'
  result.append({'symbol':symbol,'name':p.get('name') or entry['name'],'category':entry['category'],'exchange':entry.get('exchange',''),
   'listingCurrency':entry.get('currency',''),'filingCurrency':p.get('currency'),'inDirectory':symbol in directory,
   'price':price,'previousClose':previous,'change':number(change),'quoteTime':quote_time,'quoteFetchedAt':qt,
   'pe':pe,'peField':pe_field if pe is not None else None,'growth':number(m.get('revenueGrowthTTMYoy')),'margin':number(m.get('netProfitMarginTTM')),
   'marketCapMillions':number(p.get('marketCapitalization'),True),'marketCapCurrency':p.get('currency'),'marketCapFetchedAt':pt,
   'financialsFetchedAt':mt,'profileFetchedAt':pt,'financialPeriod':'Not supplied by this snapshot','source':'Finnhub',
   'profileUrl':'https://finnhub.io/docs/api/company-profile2','metricsUrl':'https://finnhub.io/docs/api/company-basic-financials','quoteUrl':'https://finnhub.io/docs/api/quote'})
 return {'asOf':now,'directoryCount':len(directory),'rows':result,'notice':'Bounded directory plus requested watchlist symbols. Not a whole-market scan. Retrieval dates are not financial reporting periods.'}
