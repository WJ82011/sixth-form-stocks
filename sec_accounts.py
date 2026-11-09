"""Bounded, cached SEC reads, independent of Finnhub/Massive budgets.
No requests on view, no retries or alternate-host bypasses, no private credentials.
"""
import contextlib
import datetime as dt
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
import financials
import statements3
import events3

DIRECTORY='https://www.sec.gov/files/company_tickers.json'
API='https://data.sec.gov/'
# Bootstrap CIKs are candidates only: every refresh verifies the ticker against SEC submissions.
SEEDS={'AAPL':320193,'MSFT':789019,'NVDA':1045810,'TTWO':946581,'TSM':1046179}
NETWORK=threading.Lock()
LAST_REQUEST=0.0
BACKOFF=0.0
TTL=86400000
MAX_BYTES=20*1024*1024
class SECError(ValueError):pass
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise SECError('SEC redirected the request. It was stopped; no alternate host was used.')

def init(con):
 con.execute('CREATE TABLE IF NOT EXISTS sec_accounts (cik TEXT PRIMARY KEY,body TEXT NOT NULL,fetched_at INTEGER NOT NULL)')
 con.execute('CREATE TABLE IF NOT EXISTS sec_links (symbol TEXT PRIMARY KEY,cik TEXT NOT NULL)')
 con.execute('CREATE TABLE IF NOT EXISTS sec_directory (id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL,fetched_at INTEGER NOT NULL)')

def canonical(symbol):
 symbol=str(symbol).upper().strip()
 if not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}',symbol):raise SECError('SEC company accounts support listed company tickers, not currencies, indices or crypto symbols.')
 return symbol.replace('.','-')

def fetch_json(url,tls_context=None):
 global LAST_REQUEST,BACKOFF
 if not (url==DIRECTORY or re.fullmatch(r'https://data\.sec\.gov/(submissions/CIK\d{10}\.json|api/xbrl/companyfacts/CIK\d{10}\.json)',url)):raise SECError('Unsupported SEC endpoint.')
 now=time.monotonic()
 if now<BACKOFF:raise SECError('SEC requests are cooling down. Try again in a few minutes; saved accounts remain available.')
 wait=1.05-(now-LAST_REQUEST)
 if wait>0:time.sleep(wait)
 LAST_REQUEST=time.monotonic()
 agent=os.environ.get('MARKETDESK_SEC_USER_AGENT','MarketDeskReborn/3.0.0 PersonalEducationalResearch')
 if not isinstance(agent,str) or not 10<=len(agent)<=200 or any(ord(c)<32 or ord(c)>126 for c in agent):raise SECError('Use a valid SEC application User-Agent setting.')
 request=urllib.request.Request(url,headers={'User-Agent':agent,'Accept':'application/json','Accept-Encoding':'identity'})
 try:
  with urllib.request.build_opener(NoRedirect,urllib.request.HTTPSHandler(context=tls_context)).open(request,timeout=25) as response:
   body=response.read(MAX_BYTES+1)
   if len(body)>MAX_BYTES:raise SECError('SEC response was too large. Saved accounts have been kept.')
   result=json.loads(body)
   if not isinstance(result,dict):raise SECError('SEC did not return a JSON object.')
   return result
 except urllib.error.HTTPError as exc:
  if exc.code in (403,429):BACKOFF=time.monotonic()+300
  raise SECError('SEC access is temporarily unavailable (HTTP '+str(exc.code)+'). No figures were invented and no access restriction was bypassed.') from None
 except (urllib.error.URLError,TimeoutError,OSError,ValueError) as exc:
  if isinstance(exc,SECError):raise
  raise SECError('SEC could not be reached or its response could not be read. Saved accounts have been kept.') from None

def read(con,symbol,now=None):
 sym=canonical(symbol);stamp=now or int(time.time()*1000)
 row=con.execute('SELECT a.body,a.fetched_at FROM sec_links l JOIN sec_accounts a ON a.cik=l.cik WHERE l.symbol=?',(sym,)).fetchone()
 if not row:return {'status':'not_loaded','symbol':symbol,'annual':[],'quarterly':[],'notice':'No SEC accounts saved for this company. Choose Update SEC accounts to request them.'}
 try:report=json.loads(row[0])
 except (ValueError,TypeError):return {'status':'not_loaded','symbol':symbol,'annual':[],'quarterly':[],'notice':'Saved SEC accounts could not be read. Update this company to replace them.'}
 report.update(symbol=symbol,fetchedAt=row[1],stale=stamp-row[1]>7*TTL,fromCache=True)
 report['ageNotice']='Saved SEC response; not a current verification. Last retrieved '+dt.datetime.fromtimestamp(row[1]/1000,dt.timezone.utc).isoformat()+'.'
 return report

def update(connect,symbol,now=None,tls_context=None):
 sym=canonical(symbol);stamp=now or int(time.time()*1000)
 if not NETWORK.acquire(blocking=False):raise SECError('Another SEC update is running. Wait for it to finish.')
 try:
  with contextlib.closing(connect()) as con:
   old=read(con,symbol,stamp)
   if old.get('method')==financials.METHOD and 'statementBooks' in old and stamp-old.get('fetchedAt',0)<TTL:return {**old,'cached':True,'refreshNotice':'Using the saved SEC response from the last 24 hours. Its original retrieval date is unchanged.'}
   link=con.execute('SELECT cik FROM sec_links WHERE symbol=?',(sym,)).fetchone()
   directory_row=con.execute('SELECT body,fetched_at FROM sec_directory WHERE id=1').fetchone()
  cik=int(link[0]) if link else SEEDS.get(sym)
  if not cik:
   mapping={}
   if directory_row and stamp-directory_row[1]<7*TTL:
    try:mapping=json.loads(directory_row[0])
    except ValueError:pass
   if not mapping:
    raw=fetch_json(DIRECTORY,tls_context)
    for row in raw.values():
     if not isinstance(row,dict):continue
     ticker=row.get('ticker');candidate=row.get('cik_str')
     if isinstance(ticker,str) and re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,14}',ticker) and isinstance(candidate,int) and not isinstance(candidate,bool) and 0<candidate<10**10:
      key=canonical(ticker)
      if key in mapping and mapping[key]!=candidate:mapping[key]=None
      else:mapping[key]=candidate
    if not mapping:raise SECError('The SEC ticker directory had no usable entries.')
    with contextlib.closing(connect()) as con,con:con.execute('INSERT OR REPLACE INTO sec_directory VALUES(1,?,?)',(json.dumps(mapping,separators=(',',':')),stamp))
   cik=mapping.get(sym)
  if not isinstance(cik,int) or not 0<cik<10**10:raise SECError('No unique SEC issuer match was found. This listing may be unsupported; no issuer was guessed.')
  submissions=fetch_json(API+'submissions/CIK'+str(cik).zfill(10)+'.json',tls_context)
  tickers=submissions.get('tickers')
  if not isinstance(tickers,list) or sym not in [canonical(t) for t in tickers if isinstance(t,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9.\-]{0,14}',t)]:raise SECError('The SEC issuer no longer lists this ticker. The mapping needs review; saved figures were not relabelled.')
  raw=fetch_json(API+'api/xbrl/companyfacts/CIK'+str(cik).zfill(10)+'.json',tls_context)
  report=financials.normalise_facts(raw,cik,submissions,dt.datetime.fromtimestamp(stamp/1000,dt.timezone.utc).date())
  report['statementBooks']=statements3.build(raw,cik,submissions,dt.datetime.fromtimestamp(stamp/1000,dt.timezone.utc).date())
  report['filingEvents']=events3.filings(submissions,cik)
  report['identity']={'name':report['name'],'cik':report['cik'],'tickers':[t for t in tickers if isinstance(t,str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9.\-]{0,14}',t)][:20],'verifiedWith':'SEC submissions ticker list','url':API+'submissions/CIK'+str(cik).zfill(10)+'.json'}
  report['sourceUrl']=API+'api/xbrl/companyfacts/CIK'+str(cik).zfill(10)+'.json'
  # Store selected facts, not multi-megabyte raw filings or addresses. Retain at most 60 issuers.
  with contextlib.closing(connect()) as con,con:
   con.execute('INSERT OR REPLACE INTO sec_accounts VALUES(?,?,?)',(report['cik'],json.dumps(report,allow_nan=False,separators=(',',':')),stamp))
   con.execute('INSERT OR REPLACE INTO sec_links VALUES(?,?)',(sym,report['cik']))
   con.execute('DELETE FROM sec_accounts WHERE cik NOT IN (SELECT cik FROM sec_accounts ORDER BY fetched_at DESC,cik LIMIT 60)')
   con.execute('DELETE FROM sec_links WHERE cik NOT IN (SELECT cik FROM sec_accounts)')
   result=read(con,symbol,stamp)
  return {**result,'fromCache':False,'cached':False,'refreshNotice':'SEC accounts retrieved. Check the actual reporting and filing dates.'}
 finally:NETWORK.release()
