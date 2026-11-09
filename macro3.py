"""Bounded public FRED series, independent from market-provider keys and budgets."""
import csv,datetime as dt,io,math,re,threading,time,urllib.request,urllib.error
SERIES={
 'UNRATE':{'title':'US unemployment','unit':'% of labour force','frequency':'monthly','source':'U.S. Bureau of Labor Statistics','adjustment':'Seasonally adjusted'},
 'CPIAUCSL':{'title':'US consumer prices','unit':'Index, 1982–1984 = 100','frequency':'monthly','source':'U.S. Bureau of Labor Statistics','adjustment':'Seasonally adjusted'},
 'FEDFUNDS':{'title':'US effective federal funds rate','unit':'% · monthly average','frequency':'monthly','source':'Federal Reserve Board','adjustment':'Not seasonally adjusted; not a target-rate announcement'},
 'GDPC1':{'title':'US real GDP','unit':'Billions of chained 2017 USD, annual rate','frequency':'quarterly','source':'U.S. Bureau of Economic Analysis','adjustment':'Seasonally adjusted annual rate'},
}
LOCK=threading.Lock();LAST=0.0
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise ValueError('Macro source redirected the request; no alternate host was used.')

def parse(code,text,today=None):
 if code not in SERIES:raise ValueError('Unknown official macro series.')
 today=today or dt.datetime.now(dt.timezone.utc).date();rows={}
 reader=csv.DictReader(io.StringIO(text))
 if not reader.fieldnames or code not in reader.fieldnames:raise ValueError('Official macro CSV headers did not match the requested series.')
 for row in reader:
  stamp=row.get('observation_date') or row.get('DATE')
  try:day=dt.date.fromisoformat(stamp);value=float(row.get(code,''))
  except (ValueError,TypeError):continue
  if day>today or not math.isfinite(value) or abs(value)>1e9:continue
  if code in ('CPIAUCSL','GDPC1') and value<=0:continue
  if day.day!=1 or (code=='GDPC1' and day.month not in (1,4,7,10)):continue
  rows[day.isoformat()]={'date':day.isoformat(),'value':value}
 result=[rows[k] for k in sorted(rows)][-180:]
 if not result:raise ValueError('No usable dated observations were returned.')
 latest=result[-1];prior=rows.get(str(int(latest['date'][:4])-1)+latest['date'][4:]);yoy=(latest['value']/prior['value']-1)*100 if prior and prior['value']>0 and code in ('CPIAUCSL','GDPC1') else None
 return {**SERIES[code],'id':code,'url':'https://fred.stlouisfed.org/series/'+code,'observations':result,'latest':latest,'yearAgoChangePct':yoy,'notice':'Observation date identifies its month or quarter, not publication day. Values may be revised and are not point-in-time forecasts. Changes are computed only against an exact matching year-ago period. Source attribution: '+SERIES[code]['source']+', retrieved via FRED, Federal Reserve Bank of St. Louis.'}

def fetch(code,context):
 global LAST
 if code not in SERIES:raise ValueError('Unknown macro series.')
 if not LOCK.acquire(blocking=False):raise ValueError('Another official macro update is running.')
 try:
  delay=1-(time.monotonic()-LAST)
  if delay>0:time.sleep(delay)
  LAST=time.monotonic();start=str(dt.datetime.now(dt.timezone.utc).year-15)+'-01-01'
  url='https://fred.stlouisfed.org/graph/fredgraph.csv?id='+code+'&cosd='+start
  req=urllib.request.Request(url,headers={'User-Agent':'MarketDeskReborn/3.0 PersonalEducationalResearch','Accept':'text/csv'})
  try:
   with urllib.request.build_opener(NoRedirect,urllib.request.HTTPSHandler(context=context)).open(req,timeout=20) as response:body=response.read(500001)
  except (OSError,urllib.error.URLError,TimeoutError):raise ValueError('Official macro source is unavailable. Earlier saved observations keep their original dates.') from None
  if len(body)>500000:raise ValueError('Macro response exceeded the size limit.')
  return parse(code,body.decode('utf-8-sig'))
 finally:LOCK.release()
