"""Dated price comparisons; no whole-market value inferred from an index percentage."""
import contextlib,datetime as dt,json,math
from zoneinfo import ZoneInfo
import brief33,workspace3,re,market36
NY=ZoneInfo('America/New_York')
def day(t):return dt.datetime.fromtimestamp(t/1000,NY).date().isoformat()
def packet(g,symbols=''):
 now=int(g['time'].time()*1000);rows=g['screen_data']([x for x in symbols.split(',') if x][:60])['rows'];out=[]
 for r in rows:
  if r.get('price') and r.get('previousClose') and r.get('quoteTime'):
   change=(r['price']/r['previousClose']-1)*100
   if not math.isfinite(change):continue
   out.append({'symbol':r['symbol'],'price':r['price'],'previous':r['previousClose'],'changePct':(r['price']/r['previousClose']-1)*100,'time':r['quoteTime'],'session':day(r['quoteTime']),'basis':'Finnhub quote versus provider previous close','currency':r.get('listingCurrency',''),'fetchedAt':r.get('quoteFetchedAt')})
 completed=[]
 for sym in [x for x in symbols.split(',') if x][:60]:
  history=g['read_massive_daily_bars'](sym,(now//1000)-20*86400,now//1000)
  if not history:continue
  points=[(t*1000,c) for t,c in zip(history['bars']['t'],history['bars']['c']) if day(t*1000)<day(now)]
  if len(points)<2:continue
  a,b=points[-2:];change=(b[1]/a[1]-1)*100
  if math.isfinite(change):completed.append({'symbol':sym,'session':day(b[0]),'previousSession':day(a[0]),'previous':a[1],'price':b[1],'changePct':change,'basis':'Saved Massive split-adjusted daily closes; session labels, not intraday timestamps'})
 context=brief33.build(g,[x for x in symbols.split(',') if x][:60],workspace3.normalise({})) if symbols else {'news':[]}
 news=[]
 for item in context['news']:
  if item['datetime']*1000<now-600000:continue
  if not any(re.search(r'(?<![A-Za-z0-9])'+re.escape(sym)+r'(?![A-Za-z0-9])',item['headline'],re.I) or ((g['ai_catalog_entry'](sym) or {}).get('name','____').split(' Inc')[0].lower() in item['headline'].lower()) for sym in item['symbols']):continue
  news.append(item)
 return {'completedSessions':completed,'headlines':news[:20],'asOf':now,'rows':out,'notice':'Quote changes compare the recorded quote with the provider previous close. They are not the first-to-last change within an intraday chart. Source timestamps may be old.','markets':market36.cards(g)}
