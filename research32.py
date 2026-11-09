"""Bounded private research projects and watchlists; never fetches or trains on sources."""
import copy,datetime as dt,json,math,re,urllib.parse
from portfolio3 import symbol
MAX_BYTES=750000
STAGES=('Exploring','Building a view','Ready to review')
RANGES=('1H','1D','1W','1M','3M','6M','1Y','2Y','5Y','10Y')
def text(v,limit,required=False):
 if not isinstance(v,str) or len(v)>limit:raise ValueError('Use text within the stated character limit.')
 v=v.strip()
 if required and not v:raise ValueError('Complete the required text fields.')
 return v
def ident(v,limit=80):
 if not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,'+str(limit)+'}',v):raise ValueError('Invalid research record ID.')
 return v
def stamp(v):
 if not isinstance(v,str):raise ValueError('Invalid research date.')
 try:t=dt.datetime.fromisoformat(v.replace('Z','+00:00'))
 except ValueError:raise ValueError('Invalid research date.') from None
 if t.tzinfo is None or t.year<2000 or t>dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=5):raise ValueError('Use a recorded date with a time zone.')
 return t.astimezone(dt.timezone.utc).isoformat()
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def flag(v):
 if not isinstance(v,bool):raise ValueError('Invalid archive setting.')
 return v
def public_url(v):
 v=text(v,1200,True)
 try:u=urllib.parse.urlsplit(v)
 except ValueError:raise ValueError('Use a valid public HTTPS link.') from None
 if u.scheme!='https' or not u.hostname or u.username or u.password or u.query:raise ValueError('Use a public HTTPS link without credentials or query parameters.')
 return v
def symbols(raw):
 if not isinstance(raw,list) or len(raw)>60:raise ValueError('Use up to 60 symbols in a watchlist.')
 return list(dict.fromkeys(symbol(x) for x in raw))
def chart(raw,sym):
 if not isinstance(raw,dict) or raw.get('symbol')!=sym or raw.get('range') not in RANGES:raise ValueError('Capture the selected project company and a supported chart range.')
 points=raw.get('points')
 if not isinstance(points,list) or not 1<=len(points)<=600:raise ValueError('Capture between 1 and 600 actual plotted prices.')
 end=int(dt.datetime.now(dt.timezone.utc).timestamp()*1000)+60000;clean=[];previous=0
 for p in points:
  if not isinstance(p,dict):raise ValueError('Invalid captured price.')
  t=p.get('t');price=p.get('p')
  if isinstance(t,bool) or not isinstance(t,(int,float)) or not math.isfinite(t) or t!=int(t) or not 946684800000<=t<=end or t<=previous:raise ValueError('Captured prices need genuine ordered timestamps.')
  if isinstance(price,bool) or not isinstance(price,(int,float)) or not math.isfinite(price) or not 0<price<=1e9:raise ValueError('Captured prices must be finite positive values.')
  previous=t;clean.append({'t':int(t),'p':price,'source':text(p.get('source',''),100)})
 count=raw.get('displayedCount',len(clean))
 if isinstance(count,bool) or not isinstance(count,int) or not len(clean)<=count<=5000:raise ValueError('Invalid chart coverage count.')
 return {'symbol':sym,'range':raw['range'],'source':text(raw.get('source',''),250,True),'points':clean,'displayedCount':count,'currency':text(raw.get('currency',''),3),'notice':'Frozen recorded prices, not a live chart or future forecast. Original dates and gaps remain. Imported data retains its unverified source label.'}
def item(raw,sym):
 if not isinstance(raw,dict) or raw.get('kind') not in ('note','source','chart','report'):raise ValueError('Choose a supported research item.')
 kind=raw['kind'];r={'id':ident(raw.get('id')),'kind':kind,'title':text(raw.get('title',''),160,True),'body':text(raw.get('body',''),26000 if kind=='note' else 4000),'archived':flag(raw.get('archived',False)),'createdAt':stamp(raw.get('createdAt')),'updatedAt':stamp(raw.get('updatedAt',raw.get('createdAt')))}
 if kind=='source':r['url']=public_url(raw.get('url'));r['sourceDate']=text(raw.get('sourceDate',''),80)
 if kind=='report':r['reportId']=ident(raw.get('reportId'))
 if kind=='chart':r['chart']=chart(raw.get('chart'),sym)
 return r
def project(raw):
 if not isinstance(raw,dict):raise ValueError('Invalid research project.')
 sym=symbol(raw.get('symbol'));items=raw.get('items',[])
 if not isinstance(items,list) or len(items)>40:raise ValueError('Use up to 40 items in a project, including archived items.')
 out={'id':ident(raw.get('id')),'title':text(raw.get('title',''),120,True),'symbol':sym,'question':text(raw.get('question',''),2000),'thesis':text(raw.get('thesis',''),6000),'risks':text(raw.get('risks',''),6000),'stage':raw.get('stage','Exploring'),'archived':flag(raw.get('archived',False)),'createdAt':stamp(raw.get('createdAt')),'updatedAt':stamp(raw.get('updatedAt')),'items':[item(x,sym) for x in items]}
 if out['stage'] not in STAGES:raise ValueError('Choose a supported research stage.')
 if len({x['id'] for x in out['items']})!=len(out['items']):raise ValueError('Research item IDs must be unique.')
 return out
def normalise(raw):
 if raw is None:raw={}
 if not isinstance(raw,dict):raise ValueError('Invalid research library.')
 projects=raw.get('projects',[]);lists=raw.get('watchlists',[])
 if not isinstance(projects,list) or len(projects)>24:raise ValueError('Use up to 24 research projects, including archived projects.')
 if not isinstance(lists,list) or len(lists)>16:raise ValueError('Use up to 16 named watchlists, including archived lists.')
 out={'version':1,'initialised':flag(raw.get('initialised',False)),'projects':[project(x) for x in projects],'watchlists':[]}
 for x in lists:
  if not isinstance(x,dict):raise ValueError('Invalid watchlist.')
  out['watchlists'].append({'id':ident(x.get('id')),'name':text(x.get('name',''),80,True),'symbols':symbols(x.get('symbols',[])),'archived':flag(x.get('archived',False)),'createdAt':stamp(x.get('createdAt')),'updatedAt':stamp(x.get('updatedAt'))})
 for key in ('projects','watchlists'):
  if len({x['id'] for x in out[key]})!=len(out[key]):raise ValueError('Research record IDs must be unique.')
 if len(json.dumps(out,ensure_ascii=False,allow_nan=False).encode())>MAX_BYTES:raise ValueError('The research library exceeds 750 KB. Export your research before reducing stored content.')
 return out
def mutate(raw,action,obj):
 state=copy.deepcopy(normalise(raw));time=now()
 def find(key,id):
  row=next((x for x in state[key] if x['id']==id),None)
  if row is None:raise ValueError('This research record no longer exists. Reload the workspace.')
  return row
 if action=='watchlist.bootstrap':
  if not state['initialised']:
   if state['watchlists']:state['initialised']=True
   else:state['watchlists']=[{'id':'original-watchlist','name':'My original watchlist','symbols':symbols(obj.get('symbols',[])),'archived':False,'createdAt':time,'updatedAt':time}];state['initialised']=True
 elif action=='watchlist.save':
  x=obj.get('watchlist')
  if not isinstance(x,dict):raise ValueError('Invalid watchlist.')
  id=ident(x.get('id'));old=next((r for r in state['watchlists'] if r['id']==id),None)
  if old and x.get('baseUpdatedAt')!=old['updatedAt']:raise ValueError('This watchlist changed after you opened it. Reload before saving.')
  if old is None and x.get('baseUpdatedAt'):raise ValueError('This watchlist was removed. Create a new list instead.')
  record={**x,'createdAt':old['createdAt'] if old else time,'updatedAt':time,'archived':old['archived'] if old else False}
  state['watchlists']=[r for r in state['watchlists'] if r['id']!=id]+[record]
 elif action=='watchlist.remove':
  x=find('watchlists',obj.get('id'))
  if not x['archived'] or x['id']=='original-watchlist':raise ValueError('Only an archived additional watchlist can be removed. Keep your original list.')
  state['watchlists']=[r for r in state['watchlists'] if r['id']!=x['id']]
 elif action=='watchlist.archive':
  x=find('watchlists',obj.get('id'));x['archived']=flag(obj.get('archived'));x['updatedAt']=time
 elif action=='project.save':
  x=obj.get('project')
  if not isinstance(x,dict):raise ValueError('Invalid research project.')
  id=ident(x.get('id'));old=next((r for r in state['projects'] if r['id']==id),None)
  if old is None and x.get('baseUpdatedAt'):raise ValueError('This project was removed. Create a new project instead.')
  if old and x.get('baseUpdatedAt')!=old['updatedAt']:raise ValueError('This project changed after you opened the form. Reload it before saving your changes.')
  if old and x.get('symbol')!=old['symbol']:raise ValueError('A project keeps its original company. Create a separate project for another listing.')
  record={**x,'items':old['items'] if old else [],'archived':old['archived'] if old else False,'createdAt':old['createdAt'] if old else time,'updatedAt':time}
  state['projects']=[r for r in state['projects'] if r['id']!=id]+[record]
 elif action=='project.remove':
  x=find('projects',obj.get('id'))
  if not x['archived']:raise ValueError('Archive a project before removing it. Export a backup first.')
  state['projects']=[r for r in state['projects'] if r['id']!=x['id']]
 elif action=='project.archive':
  x=find('projects',obj.get('id'));x['archived']=flag(obj.get('archived'));x['updatedAt']=time
 elif action=='item.add':
  x=find('projects',obj.get('projectId'));r=obj.get('item')
  if not isinstance(r,dict):raise ValueError('Invalid research item.')
  x['items'].append({**r,'createdAt':time,'archived':False});x['updatedAt']=time
 elif action=='item.update':
  x=find('projects',obj.get('projectId'));r=obj.get('item')
  if not isinstance(r,dict):raise ValueError('Invalid research item.')
  old=next((i for i in x['items'] if i['id']==r.get('id')),None)
  if old is None or old['kind'] not in ('note','source') or r.get('kind')!=old['kind']:raise ValueError('Only an existing note or source can be edited. Chart snapshots remain frozen.')
  if r.get('baseUpdatedAt')!=old['updatedAt']:raise ValueError('This item changed after you opened it. Reload before saving.')
  x['items']=[{**r,'createdAt':old['createdAt'],'updatedAt':time,'archived':old['archived']} if i['id']==old['id'] else i for i in x['items']];x['updatedAt']=time
 elif action=='item.remove':
  x=find('projects',obj.get('projectId'));r=next((i for i in x['items'] if i['id']==obj.get('id')),None)
  if r is None or not r['archived']:raise ValueError('Archive an item before removing it. Export a backup first.')
  x['items']=[i for i in x['items'] if i['id']!=r['id']];x['updatedAt']=time
 elif action=='item.archive':
  x=find('projects',obj.get('projectId'));r=next((i for i in x['items'] if i['id']==obj.get('id')),None)
  if r is None:raise ValueError('Research item not found.')
  r['archived']=flag(obj.get('archived'));x['updatedAt']=time
 else:raise ValueError('Unknown research action.')
 return normalise(state)
