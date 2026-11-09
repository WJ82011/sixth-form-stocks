"""Source-linked event records and RFC5545 exports; never invent earnings times."""
import datetime as dt,hashlib,re
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from portfolio3 import source,symbol,text

def normalise(raw):
 if not isinstance(raw,list) or len(raw)>300:raise ValueError('Use at most 300 personal events.')
 out=[];seen=set();today=dt.datetime.now(dt.timezone.utc).date()
 for r in raw:
  if not isinstance(r,dict):raise ValueError('Invalid event record.')
  ident=text(r.get('id'),64)
  if not re.fullmatch('[A-Za-z0-9_-]{1,64}',ident) or ident in seen:raise ValueError('Events need unique IDs.')
  seen.add(ident);title=text(r.get('title'),160);status=r.get('status','estimated');day=str(r.get('date',''))
  if not title or status not in ('confirmed','estimated','cancelled'):raise ValueError('Add a title and a valid confirmation status.')
  try:d=dt.date.fromisoformat(day)
  except (ValueError,TypeError):raise ValueError('Use a valid event date.') from None
  if not dt.date(2000,1,1)<=d<=today+dt.timedelta(days=3660):raise ValueError('Event date is outside the supported range.')
  e={'id':ident,'title':title,'date':day,'status':status,'symbol':symbol(r['symbol']) if r.get('symbol') else '', 'source':source(r.get('source')),'note':text(r.get('note'),1200),'allDay':not bool(r.get('time')),'origin':'user event','zone':str(r.get('zone','Europe/London'))[:60]}
  try:zone=ZoneInfo(e['zone'])
  except (ZoneInfoNotFoundError,ValueError):raise ValueError('Choose a valid IANA time zone.') from None
  if not e['allDay']:
   tm=str(r.get('time',''))
   if not re.fullmatch(r'\d{2}:\d{2}',tm):raise ValueError('Use a time in HH:MM format.')
   try:naive=dt.datetime.fromisoformat(day+'T'+tm)
   except ValueError:raise ValueError('Use a valid event time.') from None
   options=[]
   for fold in (0,1):
    local=naive.replace(tzinfo=zone,fold=fold);utc=local.astimezone(dt.timezone.utc)
    if utc.astimezone(zone).replace(tzinfo=None)==naive:options.append(utc)
   distinct=set(options)
   if len(distinct)!=1:raise ValueError('This local time is ambiguous or does not exist during a clock change. Enter its known UTC time with the UTC zone.')
   e.update(time=tm,utc=next(iter(distinct)).isoformat())
  history=r.get('history',[])
  e['history']=[]
  if isinstance(history,list):
   for h in history[-12:]:
    if isinstance(h,dict):e['history'].append({k:text(h.get(k),600 if k=='source' else 180) for k in ('date','time','zone','status','source','changedAt')})
  out.append(e)
 return out

def earnings(raw,sym,fetched_at):
 items=raw.get('earningsCalendar',[]) if isinstance(raw,dict) else []
 if not isinstance(items,list):raise ValueError('The provider did not return an earnings calendar.')
 out=[];seen=set()
 for x in items[:300]:
  if not isinstance(x,dict) or x.get('symbol')!=sym:continue
  try:day=dt.date.fromisoformat(x.get('date','')).isoformat()
  except (ValueError,TypeError):continue
  key=sym+':'+day
  if key in seen:continue
  seen.add(key);window={'bmo':'Before US market open','amc':'After US market close','dmh':'During US market hours'}.get(x.get('hour'),'Time not supplied')
  out.append({'id':'earn-'+hashlib.sha256(key.encode()).hexdigest()[:20],'symbol':sym,'title':sym+' earnings (provider-listed)','date':day,'allDay':True,'zone':'America/New_York','window':window,'status':'estimated','origin':'Finnhub calendar','source':'https://finnhub.io/docs/api/earnings-calendar','fetchedAt':fetched_at,'note':'Date/window supplied by the provider; not independently confirmed with company IR. No exact release time is inferred.'})
 return out

def filings(submissions,cik):
 recent=submissions.get('filings',{}).get('recent',{}) if isinstance(submissions,dict) else {};out=[]
 if not isinstance(recent,dict):return out
 from financials import accession_url,day
 for i,accn in enumerate(recent.get('accessionNumber',[])[:200]):
  form=(recent.get('form',[])+['']*200)[i];date=(recent.get('filingDate',[])+['']*200)[i]
  if form not in ('10-K','10-Q','10-K/A','10-Q/A','8-K','20-F','20-F/A','6-K','40-F') or not day(date) or day(date)>dt.datetime.now(dt.timezone.utc).date():continue
  url=accession_url(cik,accn)
  if url:out.append({'id':'sec-'+str(cik)+'-'+accn,'title':form+' filed','date':date,'form':form,'source':url,'status':'completed','origin':'SEC filing','allDay':True,'zone':'America/New_York','note':'Actual filing date, not a confirmed earnings-call date or time.'})
 return out[:50]

def ics(events):
 def esc(v):return str(v or '').replace('\\','\\\\').replace('\n','\\n').replace(';','\\;').replace(',','\\,').replace('\r','')
 def fold(line):
  # RFC5545 octet-safe line folding for Unicode titles.
  pieces=[];current='';size=0
  for c in line:
   n=len(c.encode())
   if size+n>73:pieces.append(current);current=' ';size=1
   current+=c;size+=n
  pieces.append(current);return '\r\n'.join(pieces)
 lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Market Desk//Personal Research Calendar 3//EN','CALSCALE:GREGORIAN','METHOD:PUBLISH']
 for e in events[:500]:
  ident=hashlib.sha256(str(e.get('id','')).encode()).hexdigest();lines+=['BEGIN:VEVENT','UID:'+ident+'@marketdesk.local','DTSTAMP:'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')]
  if e.get('utc'):
   stamp=dt.datetime.fromisoformat(e['utc']).astimezone(dt.timezone.utc);lines.append('DTSTART:'+stamp.strftime('%Y%m%dT%H%M%SZ'))
  else:
   day=dt.date.fromisoformat(e['date']);lines+=['DTSTART;VALUE=DATE:'+day.strftime('%Y%m%d'),'DTEND;VALUE=DATE:'+(day+dt.timedelta(days=1)).strftime('%Y%m%d')]
  lines+=['SUMMARY:'+esc(e.get('title')),'DESCRIPTION:'+esc(str(e.get('status'))+' · '+str(e.get('origin'))+'\n'+str(e.get('note',''))+'\nZone: '+str(e.get('zone',''))+'; window: '+str(e.get('window','not specified'))+'\nSource: '+str(e.get('source','')))]
  if str(e.get('source','')).startswith('https://'):lines.append('URL:'+esc(e['source']))
  if e.get('status')=='cancelled':lines.append('STATUS:CANCELLED')
  elif e.get('status')=='estimated':lines.append('STATUS:TENTATIVE')
  else:lines.append('STATUS:CONFIRMED')
  lines.append('END:VEVENT')
 lines.append('END:VCALENDAR');return '\r\n'.join(fold(x) for x in lines)+'\r\n'
