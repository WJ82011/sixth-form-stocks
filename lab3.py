"""V3 orchestration: explicit refreshes, pure research calculations and bounded caches."""
import contextlib,datetime as dt,json,math,re,time
import truth36,market36,market37,crypto38,crypto57,session38,learning40,scorecard41,coverage41,events42,move44
import brief33,analyst34,market34,forecast35,draft35,research35,ask48,journal49,desk50,overnight51,compare52,scenario53,strategy54,scanner55
import workspace3,portfolio3,events3,macro3,sec_accounts,financials,insights46,stress58,pack59,workspace60,annotate60,overview60,desk61,forecast61,earnings62,tracker65,practice67

def init(con):
 forecast35.init(con)
 market36.init(con)
 market37.init(con)
 crypto38.init(con)
 crypto57.init(con)
 session38.init(con)
 learning40.init(con)
 scorecard41.init(con)
 events42.init(con)
 ask48.init(con)
 tracker65.init(con)
 practice67.init(con)
 overnight51.init(con)
 compare52.init(con)
 scenario53.init(con)
 strategy54.init(con)
 scanner55.init(con)
 desk61.init(con)
 con.execute('CREATE TABLE IF NOT EXISTS v3_cache(id TEXT PRIMARY KEY,body TEXT NOT NULL,fetched_at INTEGER NOT NULL)')
 con.execute('CREATE TABLE IF NOT EXISTS v3_listings(symbol TEXT PRIMARY KEY,cik TEXT NOT NULL,name TEXT NOT NULL,checked_at INTEGER NOT NULL)')

def cached(g,key):
 with contextlib.closing(g['db_connection']()) as c:row=c.execute('SELECT body,fetched_at FROM v3_cache WHERE id=?',(key,)).fetchone()
 return {**json.loads(row[0]),'fetchedAt':row[1]} if row else None

def remember(g,key,value,stamp):
 with contextlib.closing(g['db_connection']()) as c,c:
  c.execute('INSERT OR REPLACE INTO v3_cache VALUES(?,?,?)',(key,json.dumps(value,allow_nan=False),stamp))
  c.execute('DELETE FROM v3_cache WHERE rowid NOT IN (SELECT rowid FROM v3_cache ORDER BY fetched_at DESC LIMIT 90)')

def state(g):return (g['read_workspace']().get('snapshot') or {}).get('v3') or workspace3.normalise({})

def sectors(g):
 catalog=json.loads((g['ROOT']/'ai_catalog.json').read_text())
 return {row['symbol']:row.get('category') or '' for row in catalog if isinstance(row,dict) and row.get('symbol')}

def prices(g,sym):
 with contextlib.closing(g['db_connection']()) as c:rows=c.execute('SELECT ts_ms,c FROM massive_daily_bars WHERE symbol=? ORDER BY ts_ms',(sym,)).fetchall()
 return [{'date':dt.datetime.fromtimestamp(t/1000,dt.timezone.utc).date().isoformat(),'price':p,'source':'Massive saved split-adjusted daily close','symbol':sym} for t,p in rows if isinstance(p,(int,float)) and math.isfinite(p) and p>0]

def timeline(g,manual=None):
 out=list(manual if manual is not None else state(g)['events']);seen=set()
 with contextlib.closing(g['db_connection']()) as c:
  for body,stamp in c.execute('SELECT body,fetched_at FROM sec_accounts'):
   r=json.loads(body);symbols=r.get('identity',{}).get('tickers',[]);sym=symbols[0] if symbols else ''
   for e in r.get('filingEvents',[]):
    if e['id'] in seen:continue
    seen.add(e['id']);out.append({**e,'symbol':sym,'fetchedAt':stamp})
  for body,stamp in c.execute("SELECT body,fetched_at FROM v3_cache WHERE id LIKE 'earnings:%'"):
   for e in json.loads(body).get('events',[]):out.append(e)
 return sorted(out,key=lambda e:(e['date'],e.get('time',''),e['id']))[-1000:]

def account_rows(g):
 out=[]
 with contextlib.closing(g['db_connection']()) as c:
  for sym,cik,body,stamp in c.execute('SELECT l.symbol,a.cik,a.body,a.fetched_at FROM sec_links l JOIN sec_accounts a ON a.cik=l.cik'):
   r=json.loads(body);p=(r.get('annual') or [None])[-1]
   if not p:continue
   m=p['metrics'];out.append({'symbol':sym,'name':r['name'],'cik':cik,'currency':'USD','start':p['start'],'end':p['end'],'fetchedAt':stamp,'revenue':m.get('revenue',{}).get('value') if m.get('revenue') else None,'profit':m.get('profit',{}).get('value') if m.get('profit') else None,'margin':p.get('netMarginPct'),'growth':p.get('revenueGrowthPct'),'source':next((f['url'] for f in m.values() if f and f.get('url')),''),'notice':'Saved annual US-GAAP USD facts only. Dates/definitions differ; not a whole-market or same-period screen.'})
 return out

def listing_search(g,q):
 query=str(q or '').strip()[:80];pattern='%'+query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
 with contextlib.closing(g['db_connection']()) as c:
  total,stamp=c.execute('SELECT count(*),max(checked_at) FROM v3_listings').fetchone()
  rows=c.execute("SELECT symbol,cik,name FROM v3_listings WHERE symbol LIKE ? ESCAPE '\\' OR name LIKE ? ESCAPE '\\' ORDER BY symbol LIMIT 100",(pattern,pattern)).fetchall()
 if not total:
  catalog=json.loads((g['ROOT']/'ai_catalog.json').read_text());rows=[(x['symbol'],'',x['name']) for x in catalog if query.lower() in (x['symbol']+' '+x['name']).lower()][:100];total=len(catalog)
 return {'total':total,'checkedAt':stamp,'rows':[{'symbol':a,'cik':b,'name':c} for a,b,c in rows],'source':'SEC ticker associations' if stamp else 'Curated offline directory','notice':'Listing discovery, not complete financial coverage or a live quote feed. SEC associations can change; account refresh independently verifies issuer identity.'}

def get(path,qs,g):
 if path=='/api/v3/learning':return learning40.report(g,qs.get('symbol',['AAPL'])[0])
 if path=='/api/v3/events42':return events42.packet(g,qs.get('symbol',['AAPL'])[0])
 if path=='/api/v3/move44':return move44.review(g,qs.get('symbol',[''])[0],qs.get('start',[''])[0],qs.get('end',[''])[0])
 if path=='/api/v3/journal49':return journal49.latest(g,qs.get('symbol',[''])[0])
 if path=='/api/v3/desk50':
  if qs.get('part',['status'])[0]=='storage':return desk50.storage(g)
  if qs.get('part',[''])[0]=='since':
   symbols=[g['valid_symbol'](item) for item in qs.get('symbols',[''])[0].split(',') if item]
   return desk50.since(g,int(qs.get('since',['0'])[0] or 0),symbols,int(g['time'].time()*1000))
  return desk50.price_status(g,qs.get('symbol',[''])[0],int(g['time'].time()*1000))
 if path=='/api/v3/overnight51':
  now=int(g['time'].time()*1000)
  part=qs.get('part',['status'])[0]
  if part=='morning':return overnight51.morning(g,int(qs.get('since',['0'])[0] or now-86400000),now)
  if part=='jobs':return {'jobs':overnight51.jobs(g)}
  return overnight51.status(g,now)
 if path=='/api/v3/compare52':
  now=int(g['time'].time()*1000)
  if qs.get('part',[''])[0]=='list':return {'saved':compare52.listed(g)}
  if qs.get('id',[''])[0]:return compare52.read(g,qs.get('id',[''])[0],now)
  return compare52.build(g,qs.get('symbols',[''])[0],qs.get('start',[''])[0],qs.get('end',[''])[0])
 if path=='/api/v3/scenario53':
  now=int(g['time'].time()*1000)
  if qs.get('part',[''])[0]=='list':return {'saved':scenario53.listed(g,qs.get('symbol',[''])[0])}
  if qs.get('id',[''])[0]:return scenario53.read(g,qs.get('id',[''])[0],now)
  return scenario53.figures(g,qs.get('symbol',['TTWO'])[0])
 if path=='/api/v3/strategy54':
  now=int(g['time'].time()*1000)
  if qs.get('part',[''])[0]=='list':return {'saved':strategy54.listed(g)}
  if qs.get('id',[''])[0]:return strategy54.read(g,qs.get('id',[''])[0],now)
  return {'model':strategy54.MODEL,'symbols':['TTWO','AMD','AAPL'],'frequency':strategy54.FREQUENCY}
 if path=='/api/v3/scanner55':
  now=int(g['time'].time()*1000)
  if qs.get('part',[''])[0]=='presets':return {'presets':scanner55.presets()}
  if qs.get('part',[''])[0]=='list':return {'saved':scanner55.listed(g)}
  if qs.get('id',[''])[0]:return scanner55.read(g,qs.get('id',[''])[0],now)
  return scanner55.explain(qs.get('preset',['large-move'])[0])
 if path=='/api/v3/ask48':
  if qs.get('saved',[''])[0]=='1':return {'saved':ask48.saved(g,qs.get('symbol',[''])[0] or None)}
  context={'symbol':qs.get('symbol',[''])[0],'range':qs.get('range',[''])[0],'start':qs.get('start',[''])[0],'end':qs.get('end',[''])[0],'kind':qs.get('kind',[''])[0],'capturedAt':qs.get('capturedAt',[''])[0],'originalPrice':qs.get('originalPrice',[''])[0],'expectation':qs.get('expectation',[''])[0],'journalStatus':qs.get('journalStatus',[''])[0],'compareSymbols':qs.get('compareSymbols',[''])[0],'scenarioId':qs.get('scenarioId',[''])[0],'scanId':qs.get('scanId',[''])[0],'product':qs.get('product',[''])[0],'stressId':qs.get('stressId',[''])[0],'packId':qs.get('packId',[''])[0],'investigationId':qs.get('investigationId',[''])[0],'practiceId':qs.get('practiceId',[''])[0]}
  return ask48.answer(g,qs.get('question',[''])[0],context)
 if path=='/api/v3/crypto-chart':return crypto38.packet(g,qs.get('product',['BTC-USD'])[0],qs.get('range',['1D'])[0])
 if path=='/api/v3/crypto-quote':return crypto38.packet(g,qs.get('product',['BTC-USD'])[0],'quote')
 if path=='/api/v3/crypto-board':return crypto38.board(g)
 if path=='/api/v3/crypto57':return crypto57.read(g,qs.get('product',['BTC-USD'])[0])
 if path=='/api/v3/stress58':
  if qs.get('id',[''])[0]:return stress58.read(g,qs.get('id',[''])[0])
  return stress58.current(g)
 if path=='/api/v3/workspace60':return workspace60.listed(g)
 if path=='/api/v3/annotate60':return {'items':annotate60.for_symbol(g,qs.get('symbol',[''])[0])}
 if path=='/api/v3/overview60':return overview60.build(g)
 if path=='/api/v3/forecast61':return forecast61.for_symbol(g,qs.get('symbol',['TTWO'])[0])
 if path=='/api/v3/tracker65':return tracker65.review_list(g, qs.get('symbol',[''])[0] or None)
 if path=='/api/v3/practice67':
  if qs.get('id',[''])[0]:return practice67.read(g, qs.get('id',[''])[0])
  return practice67.preview(g, qs.get('symbol',['TTWO'])[0], qs.get('day',[''])[0])
 if path=='/api/v3/earnings62':
  if qs.get('id',[''])[0]:return earnings62.read(g,qs.get('id',[''])[0])
  symbol=g['valid_symbol'](qs.get('symbol',['AAPL'])[0])
  return earnings62.review(g.get('sec_saved', lambda _symbol: {})(symbol) or {})
 if path=='/api/v3/desk61':
  part=qs.get('part',[''])[0]
  if part=='board':return desk61.read_board(g,qs.get('id',[''])[0])
  if part=='investigation':return desk61.read(g,qs.get('id',[''])[0])
  if part=='trace':return desk61.trace(desk61.read(g,qs.get('id',[''])[0]))
  if part=='models':return {'experiments':desk61.experiments(g),'criteria':list(desk61.CRITERIA)}
  if part=='health':return desk61.inspect(g,qs.get('symbol',['TTWO'])[0])
  return {'method':desk61.METHOD,'criteria':list(desk61.CRITERIA)}
 if path=='/api/v3/pack59':
  if qs.get('export',[''])[0]=='1':return {'html':pack59.html_export(pack59.read(g,qs.get('id',[''])[0]))}
  if qs.get('id',[''])[0]:return pack59.read(g,qs.get('id',[''])[0])
  return {'sections':list(pack59.SECTIONS)}
 if path=='/api/v3/equity-session':return session38.packet(g,qs.get('symbol',[''])[0])
 if path=='/api/v3/heatmap':return market37.packet(g,qs.get('period',['1D'])[0],qs.get('symbols',[''])[0])
 if path=='/api/v3/market-values':return market36.export(g)
 if path=='/api/v3/market-truth':return truth36.packet(g,qs.get('symbols',[''])[0])
 if path=='/api/v3/forecast-journal':return forecast35.read(g,export=qs.get('export',[''])[0]=='1')
 if path=='/api/v3/analyst-source':
  sym=g['valid_symbol'](qs.get('symbol',[''])[0]);report=g['sec_saved'](sym)
  context=brief33.build(g,[sym],state(g))
  return {'symbol':sym,'books':analyst34.source_pack(report,sym),'fetchedAt':report.get('fetchedAt'),'headlines':context['news'][:6],'newsFetchedAt':context['coverage']['newsScopes'].get(sym),'guide':research35.guide(sym,context,analyst34.source_pack(report,sym),g['ai_catalog_entry'](sym)),'macro':[x for code in macro3.SERIES if (x:=cached(g,'macro:'+code))],'notice':'Saved annual SEC facts only. Refresh Company accounts explicitly if unavailable. No price, launch sales or analyst consensus is invented.'}
 if path=='/api/v3/state':return {'state':state(g)}
 if path=='/api/v3/overview':
  s=state(g);p=portfolio3.calculate(s['ledger'],s['marks']);return {'portfolio':p,'events':timeline(g,s['events']),'accounts':account_rows(g),'macro':[x for code in macro3.SERIES if (x:=cached(g,'macro:'+code))],'state':s}
 if path=='/api/v3/events':return {'events':timeline(g)}
 if path=='/api/v3/listings':return listing_search(g,qs.get('q',[''])[0])
 if path=='/api/v3/screen':return {'rows':account_rows(g),'notice':'A local screen of accounts you explicitly loaded. Missing figures remain unavailable; this is not a whole-market scan.'}
 if path=='/api/v3/macro':return {'series':[x for code in macro3.SERIES if (x:=cached(g,'macro:'+code))],'available':macro3.SERIES}
 if path=='/api/v3/valuation-source':
  sym=g['valid_symbol'](qs.get('symbol',['AAPL'])[0]);r=g['sec_saved'](sym);books=r.get('statementBooks',[])
  if not books or not books[0].get('annual'):return {'status':'insufficient','notice':'Load expanded annual SEC statements first. Valuation inputs are not invented.'}
  book=books[0];period=book['annual'][-1];m=period['metrics'];a,b=m.get('operatingCash'),m.get('capex')
  usable=bool(a and b and financials.finite(a.get('value')) and financials.finite(b.get('value')) and b['value']>=0 and a['accession']==b['accession'] and a['unit']==b['unit'] and a['start']==b['start'] and a['end']==b['end'])
  return {'status':'ok','symbol':sym,'currency':book['currency'],'taxonomy':book['taxonomy'],'start':period['start'],'end':period['end'],'operatingCash':a,'capex':b,'cashFlowProxy':a['value']-b['value'] if usable else None,'components':{k:m.get(k) for k in ('cash','debtCurrent','debtNoncurrent')},'notice':'Operating cash minus PPE purchases is a sourced cash-flow proxy, not automatically unlevered free cash flow for the enterprise DCF. Interest/tax treatment and business specifics may require adjustments. Borrowing components are not necessarily complete net debt. No share count, ADR ratio, FX conversion or price target is inferred. The retained DCF uses explicit user assumptions in USD millions.'}
 if path=='/api/v3/statements':
  sym=g['valid_symbol'](qs.get('symbol',['AAPL'])[0]);r=g['sec_saved'](sym);return {'symbol':sym,'books':r.get('statementBooks',[]),'fetchedAt':r.get('fetchedAt'),'notice':'Update SEC accounts for expanded V3 statements. Custom extensions need a separate manual source row.'}
 if path=='/api/v3/chart-compare':
  syms=[g['valid_symbol'](x) for x in qs.get('symbols',['AAPL,MSFT'])[0].split(',') if x]
  if not 2<=len(syms)<=3 or len(set(syms))!=len(syms):raise ValueError('Choose two or three different symbols.')
  data=[{p['date']:p for p in prices(g,s)} for s in syms];common=set.intersection(*(set(x) for x in data));dates=sorted(common)[-500:]
  if len(dates)<2:return {'status':'insufficient','notice':'At least two shared saved provider daily-close dates are needed. Load daily charts for each company first. No prices are invented.'}
  chart={'status':'ok','dates':dates,'rows':[{'symbol':s,'points':[{'date':d,'price':p[d]['price'],'index':p[d]['price']/p[dates[0]]['price']*100} for d in dates]} for s,p in zip(syms,data)],'notice':'Split-adjusted saved daily closes rebased to 100 on the same starting date. Shared observed dates only; dividends, fees, FX and non-shared dates are excluded. Not a total-return chart.'}
  chart['coverage']=coverage41.daily([{'t':int(dt.datetime.combine(dt.date.fromisoformat(day),dt.time(16),market37.NY).timestamp()*1000),'p':1} for day in dates],int(g['time'].time()*1000),'Massive saved split-adjusted daily closes',True)
  return chart
 if path=='/api/v3/sources':
  with contextlib.closing(g['db_connection']()) as c:
   accounts=c.execute('SELECT count(*),min(fetched_at),max(fetched_at) FROM sec_accounts').fetchone();listings=c.execute('SELECT count(*),max(checked_at) FROM v3_listings').fetchone()
  return {'accounts':{'count':accounts[0],'oldestFetch':accounts[1],'latestFetch':accounts[2]},'listings':{'count':listings[0],'checkedAt':listings[1]},'macro':[{'id':x['id'],'date':x['latest']['date'],'fetchedAt':x['fetchedAt'],'url':x['url']} for code in macro3.SERIES if (x:=cached(g,'macro:'+code))],'limits':['Finnhub requests share the existing 48/minute local budget. Endpoint access still depends on your plan.','SEC updates are explicit, serialized and paced; missing/custom concepts are not fabricated.','FRED observations have monthly/quarterly dates and can be revised.','Manual records and FX are user sourced, not independently verified.','The language model is not trained by this update. The separate price model remains price-only and experimental.','No background collection when this server or Mac is off.']}
 raise FileNotFoundError(path)

def post(path,obj,g):
 if path=='/api/v3/heatmap-sync':return market37.step(g,obj)
 if not isinstance(obj,dict):raise ValueError('Invalid V3 request.')
 if path=='/api/v3/desk50-backup':
  action=obj.get('action')
  if action=='backup':return desk50.create_backup(g)
  if action=='restore':return desk50.restore_backup(g,obj.get('file'),obj.get('confirm'))
  if action=='trim':return desk50.trim_backups(g,obj.get('confirm'))
  raise ValueError('Choose backup, restore or trim.')
 if path=='/api/v3/overnight51':
  now=int(g['time'].time()*1000)
  action=obj.get('action')
  if action=='save':return overnight51.save_schedule(g,obj,now)
  if action=='pause':return overnight51.set_paused(g,True,now)
  if action=='resume':return overnight51.set_paused(g,False,now)
  raise ValueError('Choose save, pause or resume.')
 if path=='/api/v3/compare52':
  if obj.get('action')!='save':raise ValueError('Choose save.')
  return compare52.save(g,obj,int(g['time'].time()*1000))
 if path=='/api/v3/scenario53':
  now=int(g['time'].time()*1000)
  if obj.get('action')=='calculate':return scenario53.calculate(obj)
  if obj.get('action')=='solve':return scenario53.solve(obj)
  if obj.get('action')=='save':return scenario53.save(g,obj,now)
  raise ValueError('Choose calculate, solve or save.')
 if path=='/api/v3/strategy54':
  now=int(g['time'].time()*1000)
  if obj.get('action')=='preview':return strategy54.describe(obj)
  if obj.get('action')=='run':return strategy54.evaluate(g,obj)
  if obj.get('action')=='save':return strategy54.save(g,obj,now)
  raise ValueError('Choose preview, run or save.')
 if path=='/api/v3/scanner55':
  now=int(g['time'].time()*1000)
  if obj.get('action')=='explain':return scanner55.explain(obj)
  if obj.get('action')=='run':return scanner55.run(g,obj,now,record=False)
  if obj.get('action')=='save':return scanner55.save(g,obj,now)
  if obj.get('action')=='refresh':
   recent=len([t for t in g.get('REQUEST_LOG',[]) if hasattr(g.get('time'),'monotonic') and g['time'].monotonic()-t<=60]) if g.get('REQUEST_LOG') is not None else 0
   return scanner55.refresh(g,obj.get('symbols') or [],max(0,min(5,48-recent)))
  raise ValueError('Choose explain, run, save or refresh.')
 if path=='/api/v3/crypto-follow':
  return crypto38.follow(g, obj.get('products') or [], int(g['time'].time()*1000))
 if path=='/api/v3/crypto57':
  product=obj.get('product') or 'BTC-USD'
  if obj.get('action')=='grade':return crypto57.grade(g,product)
  return crypto57.report(g,product)
 if path=='/api/v3/stress58':
  now=int(g['time'].time()*1000)
  if obj.get('action')=='save':return stress58.save(g,obj,now)
  return stress58.run(g,obj)
 if path=='/api/v3/workspace60':
  now=int(g['time'].time()*1000)
  if obj.get('action')=='open':return workspace60.activate(g,obj.get('id'))
  return workspace60.save(g,obj,now)
 if path=='/api/v3/tracker65':
  now=int(g['time'].time()*1000)
  action=obj.get('action')
  if action=='follow':return tracker65.follow(g, obj, now)
  if action=='sweep':return tracker65.sweep(g, now)
  if action=='acknowledge':return tracker65.acknowledge(g, obj.get('followId'), now, obj.get('ids'))
  raise ValueError('Choose follow, sweep or acknowledge.')
 if path=='/api/v3/practice67':
  now=int(g['time'].time()*1000)
  action=obj.get('action')
  ident=obj.get('id')
  if action=='preview':return practice67.preview(g, obj.get('symbol') or 'TTWO', obj.get('day') or '')
  if action=='start':return practice67.start(g, obj.get('symbol') or 'TTWO', obj.get('day') or '', obj.get('startAt'), now, obj.get('startMode') or 'open')
  if action=='step':return practice67.advance(g, ident, 'step', obj.get('speed'), now)
  if action=='play':return practice67.advance(g, ident, 'play', obj.get('speed'), now)
  if action=='pause':return practice67.pause(g, ident, now)
  if action=='restart':return practice67.restart(g, ident, now)
  if action=='end':return practice67.end(g, ident, now)
  if action=='decide':return practice67.decide(g, ident, obj, now)
  if action=='reflect':return practice67.reflect(g, obj.get('decisionId'), obj.get('assessment'), obj.get('learned'), now)
  if action=='review':return practice67.outcome(g, obj.get('decisionId'))
  if action=='journal':return practice67.journal_entry(g, obj.get('decisionId'), now)
  raise ValueError('Choose a practice action.')
 if path=='/api/v3/earnings62':
  now=int(g['time'].time()*1000)
  symbol=g['valid_symbol'](obj.get('symbol') or 'AAPL')
  saved=g.get('sec_saved', lambda _symbol: {})(symbol) or {}
  if obj.get('action')=='save':return earnings62.save(g,symbol,saved,now)
  if obj.get('action')=='reaction':return earnings62.reaction(g,symbol,obj.get('publishedAt'),now)
  if obj.get('action')=='assumptions':return earnings62.assumptions(obj.get('saved') or {}, saved)
  if obj.get('action')=='ask':return {'answer':earnings62.answer(saved, obj.get('question') or '')}
  raise ValueError('Choose save, reaction, assumptions or ask.')
 if path=='/api/v3/desk61':
  now=int(g['time'].time()*1000)
  action=obj.get('action')
  if action=='propose':return desk61.propose(g,obj.get('question') or '',now)
  if action=='start':return desk61.start(g,obj.get('question') or '',now)
  if action=='step':return desk61.step(g,obj.get('id'),now)
  if action=='run':return desk61.run_all(g,obj.get('id'),now)
  if action=='cancel':return desk61.cancel(g,obj.get('id'),now)
  if action=='resume':return desk61.resume(g,obj.get('id'),now)
  if action=='refresh':return desk61.refresh(g,obj.get('id'),now)
  if action=='board':return desk61.build(g,obj,now)
  if action=='board-save':return desk61.save_board(g,obj,now)
  if action=='evaluate':return desk61.evaluate_symbol(g,obj.get('symbol') or 'TTWO',now)
  if action=='inspect':return desk61.inspect(g,obj.get('symbol') or 'TTWO',now)
  if action=='repair':return desk61.repair(g,obj.get('symbol') or '',obj.get('inspectId'),now)
  if action=='undo-repair':return desk61.undo_repair(g,obj.get('symbol') or '')
  raise ValueError('Choose an investigation, board, model or repair action.')
 if path=='/api/v3/annotate60':
  now=int(g['time'].time()*1000)
  if obj.get('action')=='undo':return annotate60.undo(g,obj.get('symbol'))
  if obj.get('action')=='remove':return annotate60.remove(g,obj.get('symbol'),obj.get('id'))
  return annotate60.replace(g,obj.get('symbol'),obj.get('items') or [],now)
 if path=='/api/v3/pack59':
  now=int(g['time'].time()*1000)
  if obj.get('action')=='edition':
   previous=pack59.read(g,obj.get('id'))
   fresh=pack59.collect(g,previous['symbol'],obj.get('selected'),now)
   return pack59.new_edition(g,obj.get('id'),fresh,obj.get('wording') or '',now)
  if obj.get('action')=='edit':return pack59.edit_wording(g,obj.get('id'),obj.get('wording') or '', now)
  if obj.get('action')=='compare':return pack59.diff(pack59.read(g,obj.get('older')), pack59.read(g,obj.get('newer')))
  body=pack59.collect(g,obj.get('symbol') or 'TTWO', obj.get('selected'), now)
  if obj.get('wording'):body['wording']=str(obj.get('wording')).strip();body['wordingEdited']=bool(body['wording'])
  if obj.get('action')=='save':return pack59.store(g,body,now)
  return body
 if path=='/api/v3/market-values':return market36.import_csv(g,obj)
 if path=='/api/v3/drafts-validate':return draft35.normalise(obj.get('drafts'))
 if path=='/api/v3/scenario-assist':return research35.start_assistant(g,obj)
 if path=='/api/v3/forecast-record':return {'receipt':forecast35.create(g,g['valid_symbol'](obj.get('symbol','')))}
 if path=='/api/v3/forecast-archive':
  forecast35.archive(g,obj.get('id'),obj.get('archived'));return forecast35.read(g)
 if path=='/api/v3/analyst-review':
  record=analyst34.normalise({'snapshots':[obj.get('snapshot')]})['snapshots'][0]
  return {**analyst34.calculate(record['config'],record['createdAt']),'bridge':research35.bridge(record['config']),'recordTitle':record['title'],'recordNotice':'Recomputed from frozen user-recorded assumptions; original source claims are not independently authenticated.'}
 if path=='/api/v3/analyst-calculate':
  sym=g['valid_symbol'](obj.get('symbol',''));books=analyst34.source_pack(g['sec_saved'](sym),sym);book=next((x for x in books if x['bookIndex']==obj.get('bookIndex')),None)
  if not book:raise ValueError('Load supported annual SEC revenue and operating profit first. No baseline has been invented.')
  config=dict(obj.get('config',{}))
  if analyst34.baseline(config.get('baseline'))!=book['baseline']:raise ValueError('The saved accounts changed or the source inputs do not match. Reload the source and review your assumptions before calculating.')
  config['baseline']=book['baseline'];return {**analyst34.calculate(config),'bridge':research35.bridge(config)}
 if path=='/api/v3/market-model':
  sym=g['valid_symbol'](obj.get('symbol',''));end=int(time.time())
  def series(symbol):
   saved=g['read_massive_daily_bars'](symbol,946684800,end)
   today=dt.datetime.now(__import__('zoneinfo').ZoneInfo('America/New_York')).date()
   return ([{'t':t*1000,'p':p} for t,p in zip(saved['bars']['t'],saved['bars']['c']) if dt.datetime.fromtimestamp(t,__import__('zoneinfo').ZoneInfo('America/New_York')).date()<today],saved.get('fetched_at')) if saved else ([],None)
  points,fetched=series(sym);benchmark,_=series('SPY') if sym!='SPY' else ([],None)
  return {**market34.run(points,benchmark),'symbol':sym,'fetchedAt':fetched,'source':'Saved Massive split-adjusted daily closes; current New York session excluded; no new provider request.'}
 if path=='/api/v3/briefing':return brief33.build(g,obj.get('symbols',[]),workspace3.normalise(obj.get('state',{})))
 if path=='/api/v3/calculate':
  s=workspace3.normalise(obj.get('state',{}));s=workspace3.mutate(s,obj['action'],obj) if obj.get('action') else s
  account=portfolio3.calculate(s['ledger'],s['marks']);benchmark=prices(g,s.get('benchmark') or 'SPY')
  return {'state':s,'portfolio':account,'performance':portfolio3.performance(s['ledger'],s['checkpoints'],benchmark),'insights':insights46.build(s['ledger'],s['marks'],sectors(g),prices(g,'SPY'))}
 if path=='/api/v3/marks-from-quotes':
  s=workspace3.normalise(obj.get('state',{}));p=portfolio3.calculate(s['ledger'],s['marks']);wanted=[h['symbol'] for h in p['holdings'] if h['currency']=='USD'];packet=g['screen_data'](wanted);now=int(time.time()*1000);added=[]
  for r in packet['rows']:
   if r['symbol'] not in wanted or r.get('listingCurrency')!='USD' or not r.get('price') or not r.get('quoteTime') or (r['quoteTime']>now or now-r['quoteTime']>3*86400000):continue
   mark={'symbol':r['symbol'],'price':r['price'],'currency':'USD','fx':1,'date':dt.datetime.fromtimestamp(r['quoteTime']/1000,dt.timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York')).date().isoformat(),'source':'Finnhub recorded quote at '+dt.datetime.fromtimestamp(r['quoteTime']/1000,dt.timezone.utc).isoformat()+'; retrieved '+(dt.datetime.fromtimestamp(r['quoteFetchedAt']/1000,dt.timezone.utc).isoformat() if r.get('quoteFetchedAt') else 'not recorded')}
   s=workspace3.mutate(s,'mark.add',{'mark':mark});added.append(r['symbol'])
  return {'state':s,'portfolio':portfolio3.calculate(s['ledger'],s['marks']),'added':added,'notice':'Only saved USD listing quotes up to three days old were used; no new price request or FX assumption was made.'}
 if path=='/api/v3/events-export':return {'ics':events3.ics(events3.normalise(obj.get('events',[])) if obj.get('personalOnly') else timeline(g,workspace3.normalise(obj.get('state',{}))['events']))}
 if path=='/api/v3/macro-refresh':
  code=obj.get('id');old=cached(g,'macro:'+str(code));stamp=int(time.time()*1000)
  if old and stamp-old['fetchedAt']<6*3600000:return {**old,'cached':True}
  result=macro3.fetch(code,g['verified_tls_context']()[0]);remember(g,'macro:'+code,result,stamp);return {**result,'fetchedAt':stamp,'cached':False}
 if path=='/api/v3/events42-refresh':return events42.refresh(g,g['valid_symbol'](obj.get('symbol','')))
 if path=='/api/v3/events-refresh':
  sym=g['valid_symbol'](obj.get('symbol',''));today=dt.datetime.now(dt.timezone.utc).date();params={'symbol':sym,'from':str(today-dt.timedelta(days=30)),'to':str(today+dt.timedelta(days=90))};key='earnings:'+sym;old=cached(g,key);now=int(time.time()*1000)
  if old and now-old['fetchedAt']<86400000:return old
  data,_=g['provider_get']('calendar/earnings',params,ttl=86400);cache_id=('calendar/earnings',tuple(sorted((k,str(v)) for k,v in params.items())));stamp=g['CACHE_FETCHED_AT'].get(cache_id)
  if not stamp:raise ValueError('The original provider retrieval time was unavailable; no fresh date was assigned.')
  events=events3.earnings(data,sym,stamp);result={'symbol':sym,'events':events,'notice':'Provider-listed dates are unconfirmed; verify company IR. Access may be restricted by the provider plan.'};remember(g,key,result,stamp);return {**result,'fetchedAt':stamp}
 if path=='/api/v3/listings-refresh':
  now=int(time.time()*1000)
  with contextlib.closing(g['db_connection']()) as c:count,stamp=c.execute('SELECT count(*),max(checked_at) FROM v3_listings').fetchone()
  if count and now-stamp<7*86400000:return listing_search(g,'')
  if not sec_accounts.NETWORK.acquire(blocking=False):raise ValueError('Another SEC request is running.')
  try:raw=sec_accounts.fetch_json(sec_accounts.DIRECTORY,g['verified_tls_context']()[0])
  finally:sec_accounts.NETWORK.release()
  rows={};ambiguous=set()
  for x in raw.values():
   if not isinstance(x,dict):continue
   try:sym=sec_accounts.canonical(x.get('ticker',''));cik=int(x.get('cik_str'));name=str(x.get('title',''))[:180]
   except (ValueError,TypeError):continue
   if isinstance(x.get('cik_str'),bool):continue
   if 0<cik<10**10 and name:
    if sym in rows and rows[sym][1]!=str(cik).zfill(10):ambiguous.add(sym)
    rows[sym]=(sym,str(cik).zfill(10),name,now)
  for sym in ambiguous:rows.pop(sym,None)
  if not rows:raise ValueError('No usable SEC listings were returned.')
  with contextlib.closing(g['db_connection']()) as c,c:
   c.execute('DELETE FROM v3_listings');c.executemany('INSERT INTO v3_listings VALUES(?,?,?,?)',list(rows.values())[:30000]);c.execute('INSERT OR REPLACE INTO sec_directory VALUES(1,?,?)',(json.dumps({s:int(r[1]) for s,r in rows.items()}),now))
  return listing_search(g,'')
 raise FileNotFoundError(path)
