"""Bounded incomplete Analyst Lab drafts, distinct from immutable saved analyses."""
import json,math
import analyst34,research32,portfolio3
FORMS={'shared':{'affectedPct','variableCostPct','rationale','noDoubleCount'},'capital':{'enabled','sharesM','listingRatio','netDebtM','otherClaimsM','source','unitsConfirmed'},'evidence':{'title','kind','channel','date','source','text','implication'},'assistant':{'question','driver','change','case'}}
def short(v,limit=2000):
 if not isinstance(v,str) or len(v)>limit:raise ValueError('A draft field exceeds its supported length.')
 return v

def normalise(raw):
 if raw is None:raw={}
 if not isinstance(raw,dict) or not isinstance(raw.get('records',[]),list) or len(raw.get('records',[]))>10:raise ValueError('Draft recovery supports up to ten companies.')
 rows=[];seen=set()
 for x in raw.get('records',[]):
  if not isinstance(x,dict):raise ValueError('Invalid draft record.')
  symbol=portfolio3.symbol(x.get('symbol'));revision=research32.ident(x.get('revision'));updated=research32.stamp(x.get('updatedAt'))
  if symbol in seen:raise ValueError('Only one active recovery draft per company is supported.')
  seen.add(symbol);book=x.get('book');c=x.get('config')
  if not isinstance(book,dict) or not isinstance(c,dict):raise ValueError('A draft needs its original source and inputs.')
  index=book.get('bookIndex');selected=x.get('caseIndex',1)
  if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<=20 or isinstance(selected,bool) or selected not in (0,1,2):raise ValueError('Invalid draft selection.')
  b=analyst34.baseline(book.get('baseline'))
  if b['symbol']!=symbol or analyst34.baseline(c.get('baseline'))!=b:raise ValueError('Draft company and original source do not agree.')
  def number(v):
   if v is None:return None
   if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>1e12:raise ValueError('Invalid incomplete numeric draft input.')
   return v
  scenarios=c.get('scenarios',[])
  if not isinstance(scenarios,list) or len(scenarios) not in (0,3):raise ValueError('Draft cases must be empty or contain all three cases.')
  ev=analyst34.evidence(c.get('evidence',[]));known={e['id'] for e in ev};cases=[]
  for i,case in enumerate(scenarios):
   if not isinstance(case,dict) or case.get('name')!=analyst34.CASES[i]:raise ValueError('Invalid draft case order.')
   refs=case.get('evidenceIds',[])
   if not isinstance(refs,list) or len(refs)>30 or any(not isinstance(v,str) or v not in known for v in refs):raise ValueError('Invalid draft evidence references.')
   item={'name':case['name'],**{k:number(case.get(k)) for k in ('pricePct','volumePct','unitCostPct','fixedCostPct')},'rationale':short(case.get('rationale','')),'evidenceIds':refs}
   product=case.get('product',{});val=case.get('valuation',{})
   if not isinstance(product,dict) or not isinstance(val,dict):raise ValueError('Invalid draft launch or valuation.')
   item['product']={'enabled':research32.flag(product.get('enabled',False))}
   if item['product']['enabled']:item['product'].update({'name':short(product.get('name',''),120),**{k:number(product.get(k)) for k in ('unitsM','netPerUnit','launchMonth','recognitionPct','cannibalPct','costPct')}})
   if val.get('method','none') not in ('none','EV/Sales','EV/Operating profit'):raise ValueError('Invalid draft valuation method.')
   item['valuation']={'method':val.get('method','none')}
   if item['valuation']['method']!='none':item['valuation'].update(multiple=number(val.get('multiple')),rationale=short(val.get('rationale',''),1000))
   cases.append(item)
  forms=x.get('forms',{})
  if not isinstance(forms,dict):raise ValueError('Invalid draft form buffer.')
  buffers={}
  for form,keys in FORMS.items():
   values=forms.get(form,{})
   if not isinstance(values,dict):raise ValueError('Invalid draft form fields.')
   buffers[form]={k:(v if isinstance(v,bool) else short(v)) for k,v in values.items() if k in keys}
  rows.append({'symbol':symbol,'revision':revision,'updatedAt':updated,'book':{'bookIndex':index,'baseline':b},'caseIndex':selected,'config':{'baseline':b,'evidence':ev,'scenarios':cases,'capital':{'enabled':False}},'forms':buffers})
 out={'version':1,'records':rows}
 if len(json.dumps(out,allow_nan=False,ensure_ascii=False,separators=(',',':')).encode())>450000:raise ValueError('Draft recovery exceeds its 450 KB limit. Download older drafts before replacing them.')
 return out
