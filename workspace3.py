"""Validated V3 research state, independent from credentials and market recordings."""
import copy,datetime as dt,hashlib,json,re
import portfolio3,events3,statements3,research32,brief33,analyst34
MODULES=('watchlist','portfolio','events','economy','research')

def normalise(raw):
 if raw is None:raw={}
 if not isinstance(raw,dict):raise ValueError('Invalid V3 workspace.')
 ledger=portfolio3.events(raw.get('ledger',[]));marks=portfolio3.marks(raw.get('marks',[]))
 portfolio3.calculate(ledger,marks)
 checkpoints=raw.get('checkpoints',[])
 if not isinstance(checkpoints,list) or len(checkpoints)>120:raise ValueError('Use up to 120 portfolio checkpoints.')
 clean=[];days=set()
 for cp in checkpoints:
  if not isinstance(cp,dict):raise ValueError('Invalid portfolio checkpoint.')
  date=portfolio3.date(cp.get('date')).isoformat()
  if date in days:raise ValueError('Only one checkpoint per date is allowed.')
  days.add(date);sources=portfolio3.marks(cp.get('sources',[]));equity=portfolio3.plain(portfolio3.number(cp.get('equityUSD'),0,1e15));stamp=str(cp.get('ledgerHash',''))
  if not re.fullmatch('[a-f0-9]{64}',stamp):raise ValueError('Checkpoint ledger reference is invalid.')
  # Recompute from the captured marks if the ledger still matches; never accept an edited NAV.
  if portfolio3.fingerprint(ledger,date)==stamp:
   check=portfolio3.checkpoint(ledger,sources,date)
   if abs(check['equityUSD']-equity)>.0000001:raise ValueError('Checkpoint value does not match its captured holdings and marks.')
  clean.append({'date':date,'equityUSD':equity,'ledgerHash':stamp,'sources':sources,'method':'Same-date hypothetical closing valuation; edited earlier ledger records invalidate this checkpoint.'})
 layout=raw.get('home',{})
 if not isinstance(layout,dict):layout={}
 order=layout.get('order',list(MODULES));hidden=layout.get('hidden',[])
 if not isinstance(order,list) or not isinstance(hidden,list):raise ValueError('Invalid home layout.')
 order=list(dict.fromkeys(x for x in order if x in MODULES));order+=[x for x in MODULES if x not in order]
 hidden=list(dict.fromkeys(x for x in hidden if x in MODULES))
 return {'analyst':analyst34.normalise(raw.get('analyst',{})),'briefing':brief33.normalise(raw.get('briefing',{})),'research':research32.normalise(raw.get('research',{})),'version':3,'ledger':ledger,'marks':marks,'checkpoints':clean,'events':events3.normalise(raw.get('events',[])),'manualStatements':statements3.manual_rows(raw.get('manualStatements',[])),'home':{'order':order,'hidden':hidden},'benchmark':portfolio3.symbol(raw.get('benchmark','SPY')),'researchFocus':str(raw.get('researchFocus',''))[:2000]}

def mutate(state,action,obj):
 candidate=copy.deepcopy(normalise(state))
 if action=='briefing.review':candidate['briefing']=brief33.review(candidate['briefing'],obj.get('checkpoint'))
 elif isinstance(action,str) and action.startswith('analyst.'):
  candidate['analyst']=analyst34.mutate(candidate['analyst'],action[8:],obj)
 elif isinstance(action,str) and action.startswith('research.'):
  candidate['research']=research32.mutate(candidate['research'],action[9:],obj)
 elif action=='ledger.add':candidate['ledger'].append(obj.get('event'))
 elif action=='ledger.remove':candidate['ledger']=[x for x in candidate['ledger'] if x['id']!=obj.get('id')]
 elif action=='mark.add':
  mark=obj.get('mark',{})
  if not isinstance(mark,dict):raise ValueError('Invalid price mark.')
  candidate['marks']=[x for x in candidate['marks'] if (x['symbol'],x['date'])!=(mark.get('symbol'),mark.get('date'))];candidate['marks'].append(mark)
 elif action=='checkpoint.add':
  cp=portfolio3.checkpoint(candidate['ledger'],candidate['marks'],obj.get('date'));candidate['checkpoints']=[x for x in candidate['checkpoints'] if x['date']!=cp['date']];candidate['checkpoints'].append(cp)
 elif action=='checkpoint.remove':candidate['checkpoints']=[x for x in candidate['checkpoints'] if x['date']!=obj.get('date')]
 elif action=='event.add':
  event=copy.deepcopy(obj.get('event',{}))
  if not isinstance(event,dict):raise ValueError('Invalid event record.')
  old=next((x for x in candidate['events'] if x['id']==event.get('id')),None)
  if old:
   event['history']=old.get('history',[])+[{**{k:old.get(k,'') for k in ('date','time','zone','status','source')},'changedAt':dt.datetime.now(dt.timezone.utc).isoformat()}]
  candidate['events']=[x for x in candidate['events'] if x['id']!=event.get('id')];candidate['events'].append(event)
 elif action=='event.remove':candidate['events']=[x for x in candidate['events'] if x['id']!=obj.get('id')]
 elif action=='statement.add':candidate['manualStatements'].append(obj.get('row'))
 elif action=='statement.import':
  import csv,io,uuid
  body=obj.get('csv','')
  if not isinstance(body,str) or len(body.encode())>600000:raise ValueError('Use a statement CSV under 600 KB.')
  reader=csv.DictReader(io.StringIO(body.lstrip('\ufeff')))
  required={'statement','label','value','currency','end','source'}
  if not reader.fieldnames or not required.issubset(reader.fieldnames):raise ValueError('CSV needs statement, label, value, currency, end and source columns.')
  rows=[]
  for r in reader:
   if len(rows)>=300:raise ValueError('Use at most 300 custom rows.')
   try:value=float(r.get('value',''))
   except (ValueError,TypeError):raise ValueError('Every custom row needs a finite numeric value.') from None
   rows.append({**{k:r.get(k,'') for k in ('statement','label','currency','start','end','source','note')},'id':uuid.uuid4().hex,'symbol':obj.get('symbol'),'value':value})
  candidate['manualStatements']+=rows
 elif action=='statement.remove':candidate['manualStatements']=[x for x in candidate['manualStatements'] if x['id']!=obj.get('id')]
 elif action=='home':candidate['home']=obj.get('home')
 elif action=='benchmark':candidate['benchmark']=obj.get('symbol')
 elif action=='focus':candidate['researchFocus']=obj.get('text','')
 elif action=='restore':candidate=obj.get('state')
 elif action=='legacy.import':
  if candidate['ledger']:raise ValueError('Import an older ledger only into an empty V3 ledger; the older tool remains available separately.')
  legacy=obj.get('portfolio',{})
  if not isinstance(legacy,dict):raise ValueError('Invalid older ledger.')
  trades=legacy.get('trades',[])
  if not isinstance(trades,list):raise ValueError('Invalid older ledger.')
  day=obj.get('date');portfolio3.date(day)
  candidate['ledger']=[{'id':'legacy-cash','kind':'DEPOSIT','date':day,'amount':legacy.get('capital'),'source':'Imported V2 hypothetical starting capital','note':'No recorded fees in V2; imported fees are explicitly assumed zero.'}]
  for i,t in enumerate(trades):
   if not isinstance(t,dict):raise ValueError('Invalid older trade.')
   date=str(t.get('date',''))[:10];portfolio3.date(date)
   if date<day:raise ValueError('Starting-capital date must be on or before every imported trade.')
   candidate['ledger'].append({'id':'legacy-'+str(i),'kind':t.get('side'),'date':date,'symbol':t.get('symbol'),'quantity':t.get('qty'),'price':t.get('price'),'fee':0,'currency':'USD','fx':1,'source':'Imported V2 hypothetical trade; date and fee assumptions need review.'})
 else:raise ValueError('Unknown V3 action.')
 return normalise(candidate)
