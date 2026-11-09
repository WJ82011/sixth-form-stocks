"""Local-only review-point comparisons. Source dates are never review dates."""
import contextlib,datetime as dt,hashlib,json,math,re,urllib.parse
import desk,portfolio3
DAY=86400000
LIMITS={'news':200,'filings':200,'events':80}
def millis():return int(dt.datetime.now(dt.timezone.utc).timestamp()*1000)
def finite(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def stamp(x,now):return finite(x) and x==int(x) and 946684800000<=x<=now+60000
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def symbols(raw):
 if not isinstance(raw,list) or len(raw)>60:raise ValueError('Use up to 60 watched companies.')
 return sorted(set(portfolio3.symbol(x) for x in raw))
def scope(raw):return digest(symbols(raw))[:24]
def url(raw):
 if not isinstance(raw,str) or len(raw)>1800:return ''
 try:
  u=urllib.parse.urlsplit(raw)
  if u.scheme not in ('https','http') or not u.hostname or u.username or u.password:return ''
  if any(re.search(r'token|api.?key|auth|password|credential|signature|^key$|^sig$',k,re.I) for k,v in urllib.parse.parse_qsl(u.query)):return ''
  return raw
 except ValueError:return ''
def quote(raw,now):
 if not isinstance(raw,dict) or not finite(raw.get('price')) or not 0<raw['price']<=1e9 or not stamp(raw.get('time'),now):raise ValueError('Invalid saved quote comparison point.')
 currency=raw.get('currency','')
 if not isinstance(currency,str) or currency and not re.fullmatch('[A-Z]{3}',currency):raise ValueError('Invalid recorded quote currency.')
 fetched=raw.get('fetchedAt')
 if fetched is not None and not stamp(fetched,now):raise ValueError('Invalid quote retrieval date.')
 return {'price':raw['price'],'time':int(raw['time']),'currency':currency,'fetchedAt':int(fetched) if fetched else None,'provider':'Finnhub'}
def checkpoint(raw,now=None):
 now=now or millis()
 if not isinstance(raw,dict):raise ValueError('Invalid briefing review point.')
 syms=symbols(raw.get('symbols'));reviewed=raw.get('reviewedAt')
 if not stamp(reviewed,now):raise ValueError('Invalid briefing review date.')
 quotes=raw.get('quotes',{})
 if not isinstance(quotes,dict) or not set(quotes).issubset(syms):raise ValueError('Invalid briefing companies.')
 out={'scope':scope(syms),'symbols':syms,'reviewedAt':int(reviewed),'quotes':{s:quote(v,now) for s,v in quotes.items()}}
 if any(q['time']>reviewed+60000 or q['fetchedAt'] and q['fetchedAt']>reviewed+60000 for q in out['quotes'].values()):raise ValueError('A review point cannot contain future quote records.')
 for kind in ('news','filings'):
  ids=raw.get(kind,[])
  if not isinstance(ids,list) or len(ids)>LIMITS[kind] or any(not isinstance(x,str) or not re.fullmatch('[a-f0-9]{64}',x) for x in ids):raise ValueError('Invalid briefing source references.')
  out[kind]=list(dict.fromkeys(ids))
 events=raw.get('events',{})
 if not isinstance(events,dict) or len(events)>80:raise ValueError('Invalid briefing calendar records.')
 out['events']={}
 for key,e in events.items():
  if not isinstance(key,str) or not re.fullmatch('[a-f0-9]{64}',key) or not isinstance(e,dict):raise ValueError('Invalid briefing calendar identity.')
  date=e.get('date','');status=e.get('status');detail=e.get('detail')
  try:dt.date.fromisoformat(date)
  except (ValueError,TypeError):raise ValueError('Invalid briefing event date.') from None
  if status not in ('estimated','confirmed','cancelled') or not isinstance(detail,str) or not re.fullmatch('[a-f0-9]{64}',detail):raise ValueError('Invalid briefing event status.')
  out['events'][key]={'date':date,'status':status,'detail':detail}
 return out
def normalise(raw):
 if raw is None:raw={}
 if not isinstance(raw,dict) or not isinstance(raw.get('reviews',[]),list) or len(raw.get('reviews',[]))>8:raise ValueError('Use up to eight recent briefing company groups.')
 records=[checkpoint(x) for x in raw.get('reviews',[])]
 if len({x['scope'] for x in records})!=len(records):raise ValueError('Only one review point per company group is allowed.')
 out={'version':1,'reviews':records}
 if len(json.dumps(out).encode())>512000:raise ValueError('Briefing review storage is too large.')
 return out
def review(state,raw):
 current=normalise(state);point=checkpoint(raw)
 # A delayed tab cannot reset a newer review point backwards.
 old=next((x for x in current['reviews'] if x['scope']==point['scope']),None)
 if old and old['reviewedAt']>point['reviewedAt']:raise ValueError('A newer review point already exists. Reload the briefing.')
 return normalise({'reviews':sorted([x for x in current['reviews'] if x['scope']!=point['scope']]+[point],key=lambda x:x['reviewedAt'],reverse=True)[:8]})
def compare(current,old):
 rows=[]
 for sym in current['symbols']:
  a=(old or {}).get('quotes',{}).get(sym);b=current['quotes'].get(sym);change=None
  state='missing' if not b else 'first' if not a else 'older' if b['time']<a['time'] else 'same' if b['time']==a['time'] and b['price']==a['price'] and b['currency']==a['currency'] else 'revised' if b['time']==a['time'] else 'currency' if not a['currency'] or a['currency']!=b['currency'] else 'changed'
  if state=='changed':
   change=(b['price']/a['price']-1)*100
   if not math.isfinite(change):state='range';change=None
  rows.append({'symbol':sym,'previous':a,'current':b,'state':state,'changePct':change})
 return sorted(rows,key=lambda r:(r['changePct'] is None,-abs(r['changePct'] or 0),r['symbol']))
def build(g,syms,workspace):
 syms=symbols(syms);now=millis();warnings=[];library=normalise(workspace.get('briefing',{}));old=next((r for r in library['reviews'] if r['scope']==scope(syms)),None)
 quotes={}
 try:rows=g['screen_data'](syms)['rows']
 except (ValueError,TypeError,KeyError):rows=[];warnings.append('Saved quote coverage could not be read.')
 for r in rows:
  if r['symbol'] not in syms:continue
  try:quotes[r['symbol']]=quote({'price':r.get('price'),'time':r.get('quoteTime'),'currency':r.get('listingCurrency',''),'fetchedAt':r.get('quoteFetchedAt')},now)
  except ValueError:pass
 news={};filings={};events={};newsCoverage={};accounts=set()
 with contextlib.closing(g['db_connection']()) as c:
  for sym in syms:
   record=c.execute('SELECT fetched_at,body FROM desk_news WHERE scope=?',(sym,)).fetchone();newsCoverage[sym]=record[0] if record and stamp(record[0],now) else None
   if not record:continue
   try:
    raw_news=json.loads(record[1])
    if not isinstance(raw_news,list):raise ValueError('Invalid saved headline list')
    items=desk.news_rows(raw_news,now)
   except (ValueError,TypeError):warnings.append(sym+': saved headline data could not be read.');continue
   for n in items:
    link=url(n['url'])
    if not link:continue
    key=digest(link);entry=news.setdefault(key,{**n,'url':link,'key':key,'symbols':[],'fetchedAt':newsCoverage[sym]});entry['symbols'].append(sym)
  for sym,body,fetched in c.execute('SELECT l.symbol,a.body,a.fetched_at FROM sec_links l JOIN sec_accounts a ON a.cik=l.cik'):
   if sym not in syms:continue
   try:r=json.loads(body)
   except (ValueError,TypeError):warnings.append(sym+': saved filing data could not be read.');continue
   if not isinstance(r,dict) or not isinstance(r.get('filingEvents',[]),list):warnings.append(sym+': saved filing data has an unsupported shape.');continue
   accounts.add(sym)
   for f in r.get('filingEvents',[])[:50]:
    if not isinstance(f,dict) or not url(f.get('source')):continue
    try:day=dt.date.fromisoformat(f.get('date',''))
    except (ValueError,TypeError):continue
    if day>dt.datetime.now(dt.timezone.utc).date():continue
    key=digest(f.get('id') or f['source']);entry=filings.setdefault(key,{**f,'key':key,'symbols':[],'fetchedAt':fetched if stamp(fetched,now) else None});entry['symbols'].append(sym)
  raw_events=list(workspace['events'])
  for body,fetched in c.execute("SELECT body,fetched_at FROM v3_cache WHERE id LIKE 'earnings:%'"):
   try:
    r=json.loads(body)
    if not isinstance(r,dict) or not isinstance(r.get('events',[]),list):raise ValueError('Invalid cached events')
    raw_events.extend(e for e in r.get('events',[]) if isinstance(e,dict) and e.get('symbol') in syms)
   except (ValueError,TypeError):warnings.append('A saved earnings calendar could not be read.')
 today=dt.datetime.now(dt.timezone.utc).date()
 for e in raw_events:
  if e.get('symbol') and e['symbol'] not in syms:continue
  if e.get('status') not in ('estimated','confirmed','cancelled'):continue
  try:day=dt.date.fromisoformat(e.get('date',''))
  except (ValueError,TypeError):continue
  if not today-dt.timedelta(days=7)<=day<=today+dt.timedelta(days=30):continue
  key=digest([e.get('origin'),e.get('id')]);detail=digest({k:e.get(k,'') for k in ('date','time','zone','window','status','source')});events[key]={**e,'key':key,'detail':detail}
 news=sorted(news.values(),key=lambda x:x['datetime'],reverse=True);filings=sorted(filings.values(),key=lambda x:x['date'],reverse=True);events=sorted(events.values(),key=lambda x:(x['date']<today.isoformat(),x['date'] if x['date']>=today.isoformat() else str(99999999-int(x['date'].replace('-',''))),x.get('time','')))
 for kind,items in [('news',news),('filings',filings),('events',events)]:
  if len(items)>LIMITS[kind]:warnings.append('Only the newest/nearest '+str(LIMITS[kind])+' saved '+kind+' records are compared; older records are outside this briefing.')
 news=news[:200];filings=filings[:200];events=events[:80]
 point=checkpoint({'symbols':syms,'reviewedAt':now,'quotes':quotes,'news':[n['key'] for n in news],'filings':[f['key'] for f in filings],'events':{e['key']:{'date':e['date'],'status':e['status'],'detail':e['detail']} for e in events}},now)
 for kind,items in [('news',news),('filings',filings)]:
  seen=set((old or {}).get(kind,[]))
  for x in items:x['newToBriefing']=bool(old and x['key'] not in seen)
 changed=[]
 for e in events:
  prior=(old or {}).get('events',{}).get(e['key'])
  if prior and prior['detail']!=e['detail']:changed.append({'current':e,'previous':prior})
 upcoming=[e for e in events if today<=dt.date.fromisoformat(e['date'])<=today+dt.timedelta(days=14) and e['status']!='cancelled']
 return {'asOf':now,'scope':point['scope'],'symbols':syms,'previousReviewAt':old['reviewedAt'] if old else None,'checkpoint':point,'prices':compare(point,old),'news':news,'filings':filings,'eventChanges':changed,'upcoming':upcoming,'coverage':{'quoteCount':len(quotes),'companyCount':len(syms),'newsScopes':newsCoverage,'secSymbols':sorted(accounts),'warnings':warnings},'notice':'Saved records only. Newly loaded headlines/filings may predate your review. Recorded quote endpoints are not adjusted for stock splits or other corporate actions and exclude dividends, fees and FX and do not explain a cause or a complete market period. No collection while the Mac/app is off. Review points are user workspace records, not independently verified market history.'}
