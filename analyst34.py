"""Original business-driver worksheet. Conditional scenarios, not learned price targets."""
import copy,datetime as dt,decimal,json,re
import portfolio3,research32
D=decimal.Decimal
CASES=('Downside','Base','Upside')
CHANNELS=('pricing','demand','launch','costs','macro','competition','other')
METHOD='analyst-driver-v1'
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def num(v,lo,hi):
 n=portfolio3.number(v,lo,hi);return float(n)
def text(v,n,required=False):return research32.text(v,n,required)
def source(v):return portfolio3.source(v)
def evidence(raw):
 if not isinstance(raw,list) or len(raw)>30:raise ValueError('Use up to 30 evidence records.')
 out=[];seen=set()
 for e in raw:
  if not isinstance(e,dict):raise ValueError('Invalid analyst evidence.')
  ident=research32.ident(e.get('id'));kind=e.get('kind');channel=e.get('channel')
  if ident in seen or kind not in ('reported','guidance','news','assumption') or channel not in CHANNELS:raise ValueError('Choose a unique evidence ID, type and business channel.')
  seen.add(ident);day=portfolio3.date(e.get('date')).isoformat();link=source(e.get('source'))
  if kind!='assumption':link=research32.public_url(link)
  out.append({'id':ident,'kind':kind,'channel':channel,'title':text(e.get('title',''),150,True),'date':day,'source':link,'text':text(e.get('text',''),1400,True),'implication':text(e.get('implication',''),1000),'notice':'User-entered source claim or assumption; source text/relevance is not independently verified.'})
 return out
def baseline(raw):
 if not isinstance(raw,dict):raise ValueError('Load a supported source baseline first.')
 currency=raw.get('currency');basis=raw.get('taxonomy')
 if not isinstance(currency,str) or not re.fullmatch('[A-Z]{3}',currency) or basis not in ('us-gaap','ifrs-full'):raise ValueError('Keep statement basis and currency explicit.')
 start=portfolio3.date(raw.get('start')).isoformat();end=portfolio3.date(raw.get('end')).isoformat();filed=portfolio3.date(raw.get('filed')).isoformat()
 if not 330<=(dt.date.fromisoformat(end)-dt.date.fromisoformat(start)).days+1<=400 or filed<end:raise ValueError('Use a disclosed annual fiscal period and a later filing date.')
 return {'symbol':portfolio3.symbol(raw.get('symbol')),'currency':currency,'taxonomy':basis,'start':start,'end':end,'filed':filed,'url':research32.public_url(raw.get('url')),'accession':text(raw.get('accession',''),40,True),'revenueM':num(raw.get('revenueM'),.000001,1e9),'operatingProfitM':num(raw.get('operatingProfitM'),-1e9,1e9),'costSalesM':num(raw['costSalesM'],0,1e9) if raw.get('costSalesM') is not None else None,'notice':'Selected saved annual SEC facts converted to millions of disclosed currency. Latest filed versions may contain revisions; not a point-in-time backtest dataset.'}
def config(raw):
 if not isinstance(raw,dict):raise ValueError('Invalid analyst configuration.')
 b=baseline(raw.get('baseline'));ev=evidence(raw.get('evidence',[]));known={e['id'] for e in ev}
 shared=raw.get('shared',{})
 if not isinstance(shared,dict):raise ValueError('Invalid shared model assumptions.')
 out={'baseline':b,'evidence':ev,'shared':{'affectedPct':num(shared.get('affectedPct'),0,100),'variableCostPct':num(shared.get('variableCostPct'),0,200),'rationale':text(shared.get('rationale',''),2000,True)},'scenarios':[]}
 if shared.get('noDoubleCount') is not True:raise ValueError('Confirm that new-product receipts are excluded from core price/volume changes.')
 out['shared']['noDoubleCount']=True
 if not isinstance(raw.get('scenarios'),list):raise ValueError('Provide three scenario records.')
 for case in raw['scenarios']:
  if not isinstance(case,dict) or case.get('name') not in CASES:raise ValueError('Use Downside, Base and Upside scenarios.')
  refs=case.get('evidenceIds',[])
  if not isinstance(refs,list) or len(refs)>30 or any(x not in known for x in refs):raise ValueError('Scenario evidence references must exist in this saved evidence set.')
  c={'name':case['name'],'pricePct':num(case.get('pricePct'),-99,300),'volumePct':num(case.get('volumePct'),-99,300),'unitCostPct':num(case.get('unitCostPct'),-99,300),'fixedCostPct':num(case.get('fixedCostPct'),-99,300),'rationale':text(case.get('rationale',''),2000,True),'evidenceIds':list(dict.fromkeys(refs))}
  product=case.get('product',{'enabled':False})
  if not isinstance(product,dict) or not isinstance(product.get('enabled'),bool):raise ValueError('Choose whether the product/service launch is included.')
  c['product']={'enabled':product['enabled']}
  if product['enabled']:
   c['product'].update(name=text(product.get('name',''),120,True),unitsM=num(product.get('unitsM'),0,1e6),netPerUnit=num(product.get('netPerUnit'),0,1e6),launchMonth=num(product.get('launchMonth'),1,12),recognitionPct=num(product.get('recognitionPct'),0,100),cannibalPct=num(product.get('cannibalPct'),0,100),costPct=num(product.get('costPct'),0,200))
   if c['product']['launchMonth']!=int(c['product']['launchMonth']):raise ValueError('Launch month must be a whole number from 1 to 12.')
   if not refs:raise ValueError('Attach at least a sourced launch record or an explicitly labelled assumption to a product scenario.')
  val=case.get('valuation',{'method':'none'});method=val.get('method') if isinstance(val,dict) else None
  if method not in ('none','EV/Sales','EV/Operating profit'):raise ValueError('Choose an explicit valuation method.')
  c['valuation']={'method':method}
  if method!='none':c['valuation'].update(multiple=num(val.get('multiple'),.01,100),rationale=text(val.get('rationale',''),1000,True))
  out['scenarios'].append(c)
 if len(out['scenarios'])!=3 or {c['name'] for c in out['scenarios']}!=set(CASES):raise ValueError('Save one case each for Downside, Base and Upside.')
 out['scenarios'].sort(key=lambda x:CASES.index(x['name']))
 val=raw.get('capital',{'enabled':False})
 if not isinstance(val,dict) or not isinstance(val.get('enabled'),bool):raise ValueError('Choose whether listing-unit valuation is supported.')
 out['capital']={'enabled':val['enabled']}
 if val['enabled']:
  if val.get('unitsConfirmed') is not True:raise ValueError('Confirm the share, ADR/listing-unit and currency alignment.')
  out['capital'].update(sharesM=num(val.get('sharesM'),.000001,1e9),listingRatio=num(val.get('listingRatio'),.000001,1e6),netDebtM=num(val.get('netDebtM'),-1e9,1e9),otherClaimsM=num(val.get('otherClaimsM'),0,1e9),source=source(val.get('source')),unitsConfirmed=True)
 return out
def case_result(b,shared,c,capital):
 r=D(str(b['revenueM']));op=D(str(b['operatingProfitM']));f=D(str(shared['affectedPct']))/100;v=D(str(shared['variableCostPct']))/100
 fixed=r-r*v-op
 if fixed<0:raise ValueError('The variable-cost share implies negative baseline fixed costs. Revise the classification; this worksheet may not suit this company.')
 price=D(str(c['pricePct']))/100;vol=D(str(c['volumePct']))/100;cost=D(str(c['unitCostPct']))/100;fg=D(str(c['fixedCostPct']))/100
 core=r*((1-f)+f*(1+price)*(1+vol));corecost=r*v*((1-f)+f*(1+vol))*(1+cost);fixednew=fixed*(1+fg);launch=D(0);launchcost=D(0);p=c['product']
 if p['enabled']:
  launch=D(str(p['unitsM']))*D(str(p['netPerUnit']))*D(13-int(p['launchMonth']))/12*D(str(p['recognitionPct']))/100*(1-D(str(p['cannibalPct']))/100);launchcost=launch*D(str(p['costPct']))/100
 revenue=core+launch;profit=revenue-corecost-launchcost-fixednew;enterprise=None;equity=None;per=None;why='No valuation multiple selected.';vcase=c['valuation']
 if vcase['method']!='none':
  base=revenue if vcase['method']=='EV/Sales' else profit
  if base<=0:why='A positive denominator is required for this valuation multiple.'
  else:
   enterprise=base*D(str(vcase['multiple']));why='Enterprise value is conditional on the selected multiple, not a predicted trading price.'
   if capital['enabled']:
    equity=enterprise-D(str(capital['netDebtM']))-D(str(capital['otherClaimsM']))
    if equity>0:per=equity/D(str(capital['sharesM']))*D(str(capital['listingRatio']));why='Listing-unit equity value assumes the supplied net debt, claims, diluted shares and listing ratio.'
    else:why='Equity residual is non-positive; a usable per-listing-unit value is withheld.'
   else:why+=' Share/ADR/net-debt inputs are missing, so per-unit value is withheld.'
 def n(x):
  if x is None:return None
  if not x.is_finite() or abs(x)>D('1e15'):raise ValueError('Scenario exceeds the supported numeric range.')
  return float(x)
 return {'name':c['name'],'coreRevenueM':n(core),'launchRevenueM':n(launch),'revenueM':n(revenue),'coreVariableCostM':n(corecost),'launchVariableCostM':n(launchcost),'fixedCostM':n(fixednew),'operatingProfitM':n(profit),'operatingMarginPct':n(profit/revenue*100) if revenue>0 else None,'enterpriseValueM':n(enterprise),'equityValueM':n(equity),'valuePerListingUnit':n(per),'valuationNote':why}
def calculate(raw,as_of=None):
 as_of=research32.stamp(as_of or now());day=dt.datetime.fromisoformat(as_of).date()
 try:end=day.replace(year=day.year+1)
 except ValueError:end=day.replace(year=day.year+1,day=28)
 c=config(raw);results=[case_result(c['baseline'],c['shared'],x,c['capital']) for x in c['scenarios']];base=c['scenarios'][1];sensitivity=[]
 for key,label in [('pricePct','Affected-product price'),('volumePct','Affected-product volume'),('unitCostPct','Core unit cost'),('fixedCostPct','Fixed operating cost')]:
  values=[]
  for delta in (-2,2):
   changed=copy.deepcopy(base);changed[key]=max(-99,min(300,changed[key]+delta));r=case_result(c['baseline'],c['shared'],changed,c['capital']);values.append({'inputPct':changed[key],'operatingProfitM':r['operatingProfitM'],'valuePerListingUnit':r['valuePerListingUnit']})
  sensitivity.append({'driver':label,'step':'Up to two percentage points, clipped at supported bounds, one input at a time; not a probability range.','values':values})
 warnings=['The latest disclosed annual period is a scale reference, not trailing-twelve-month data or a current run rate. This assumes a fresh twelve-month model horizon; no missing quarterly results are filled in.','Reported operating profit/loss is unadjusted. One-off charges, acquisitions and business mix may make this simplified cost model unsuitable.','A conditional business model, not a trained news-to-price predictor. Scenario labels are not probabilities.','Cost behaviour is an assumption; reported cost of sales is not automatically a purely variable cost.','Product units are an annualized full-availability run rate; net receipts are not necessarily the retail price. Recognition/bookings, cannibalisation and timing must be distinguished.']
 if not results[0]['operatingProfitM']<=results[1]['operatingProfitM']<=results[2]['operatingProfitM']:warnings.append('Operating results do not follow the scenario labels. Check the underlying assumptions rather than trusting the labels.')
 return {'asOf':as_of,'horizonStart':(day+dt.timedelta(days=1)).isoformat(),'horizonEnd':end.isoformat(),'method':METHOD,'config':c,'cases':results,'sensitivity':sensitivity,'warnings':warnings,'notice':'All amounts are millions of the disclosed statement currency except per-unit amounts. This is not discounted cash flow, a probability estimate, an investment recommendation or a claim of consensus forecasts.'}
def source_pack(report,sym):
 out=[]
 for index,book in enumerate(report.get('statementBooks',[])):
  if not book.get('annual'):continue
  p=book['annual'][-1];m=p['metrics'];a=m.get('revenue');o=m.get('operatingProfit');cost=m.get('costSales')
  if not a or not o:continue
  if any(a.get(k)!=o.get(k) for k in ('start','end','unit','accession')) or a.get('unit')!=book.get('currency'):continue
  raw={'symbol':sym,'currency':book['currency'],'taxonomy':book['taxonomy'],'start':a['start'],'end':a['end'],'filed':max(a['filed'],o['filed']),'accession':a['accession'],'url':a['url'],'revenueM':a['value']/1e6,'operatingProfitM':o['value']/1e6,'costSalesM':cost['value']/1e6 if cost and all(cost.get(k)==a.get(k) for k in ('start','end','unit','accession')) else None}
  try:clean=baseline(raw)
  except (ValueError,TypeError):continue
  out.append({'bookIndex':index,'baseline':clean})
 return out
def normalise(raw):
 if raw is None:raw={}
 if not isinstance(raw,dict) or not isinstance(raw.get('snapshots',[]),list) or len(raw.get('snapshots',[]))>20:raise ValueError('Use up to 20 saved analyst snapshots.')
 out=[];ids=set()
 for x in raw.get('snapshots',[]):
  if not isinstance(x,dict):raise ValueError('Invalid saved analyst snapshot.')
  ident=research32.ident(x.get('id'))
  if ident in ids:raise ValueError('Analyst snapshot IDs must be unique.')
  ids.add(ident);c=config(x.get('config'));created=research32.stamp(x.get('createdAt'))
  if any(day>created[:10] for day in [c['baseline']['filed'],*[e['date'] for e in c['evidence']]]):raise ValueError('Saved evidence cannot postdate the analysis record.')
  calculate(c,created)
  out.append({'id':ident,'title':text(x.get('title',''),150,True),'createdAt':research32.stamp(x.get('createdAt')),'config':c,'archived':research32.flag(x.get('archived',False))})
 if len(json.dumps(out).encode())>650000:raise ValueError('Analyst snapshot storage exceeds 650 KB. Export and remove archived snapshots first.')
 return {'version':1,'snapshots':out}
def mutate(raw,action,obj):
 state=copy.deepcopy(normalise(raw))
 if action=='save':
  ident=research32.ident(obj.get('id'))
  if any(x['id']==ident for x in state['snapshots']):raise ValueError('Saved analysis snapshots are immutable. Create a new snapshot.')
  state['snapshots'].append({'id':ident,'title':obj.get('title'),'createdAt':now(),'config':config(obj.get('config')),'archived':False})
 elif action in ('archive','remove'):
  x=next((x for x in state['snapshots'] if x['id']==obj.get('id')),None)
  if x is None:raise ValueError('Saved analyst snapshot not found.')
  if action=='archive':x['archived']=research32.flag(obj.get('archived'))
  elif x['archived']:state['snapshots']=[r for r in state['snapshots'] if r['id']!=x['id']]
  else:raise ValueError('Archive before permanently removing an analyst snapshot.')
 else:raise ValueError('Unknown analyst action.')
 return normalise(state)
def evidence_packet(state,sym):
 records=[x for x in normalise(state)['snapshots'] if x['config']['baseline']['symbol']==sym and not x['archived']]
 if not records:return []
 x=max(records,key=lambda x:x['createdAt']);r=calculate(x['config'],x['createdAt']);b=r['config']['baseline'];body='User-saved conditional analyst worksheet, not reported guidance or trained price prediction. Saved '+x['createdAt']+'. Annual source '+b['start']+' to '+b['end']+'; filed '+b['filed']+'; '+b['taxonomy']+' '+b['currency']+'.\n'
 body+='Reported baseline as recorded in this user worksheet: revenue = '+str(b['revenueM'])+' million '+b['currency']+'; operating profit/loss = '+str(b['operatingProfitM'])+' million '+b['currency']+'.\n'
 body+='Shared assumptions: affected existing revenue '+str(r['config']['shared']['affectedPct'])+' percent; variable cost / baseline revenue '+str(r['config']['shared']['variableCostPct'])+' percent. User rationale: '+r['config']['shared']['rationale'][:350]+'.\n'
 body+='Cases are neither probabilities nor observed outcomes. Inspect the saved assumptions and original sources. No claim of market consensus, news causation or continuous learning.'
 packets=[]
 for index,(case,inputs) in enumerate(zip(r['cases'],r['config']['scenarios']),2):
  detail='Conditional '+case['name']+' scenario for '+r['horizonStart']+' to '+r['horizonEnd']+'. User assumptions, not reported guidance or probability.\n'
  detail+='Price change '+str(inputs['pricePct'])+' percent; volume '+str(inputs['volumePct'])+' percent; core unit cost '+str(inputs['unitCostPct'])+' percent; fixed cost '+str(inputs['fixedCostPct'])+' percent.\nUser rationale: '+inputs['rationale'][:700]+'.\n'
  detail+='Calculated revenue '+str(case['revenueM'])+' million '+b['currency']+'; operating profit/loss '+str(case['operatingProfitM'])+' million '+b['currency']+'.\n'
  if inputs['product']['enabled']:detail+='Assumed product inputs: '+json.dumps(inputs['product'],separators=(',',':'))+'. These are not independently verified sales or launch guidance.\n'
  if case['enterpriseValueM'] is not None:detail+='Conditional enterprise value '+str(case['enterpriseValueM'])+' million '+b['currency']+'; '+json.dumps(inputs['valuation'])+'. Not a trading-price prediction.\n'
  packets.append({'id':'A'+str(index),'title':case['name']+' conditional business case','kind':'user model assumptions','body':detail,'url':'','retrievedAt':int(dt.datetime.fromisoformat(x['createdAt']).timestamp()*1000),'notice':'User assumptions and calculations, not independently verified guidance.'})

 return [{'id':'A1','title':'Saved conditional analyst worksheet','kind':'user model assumptions','body':body,'url':b['url'],'retrievedAt':int(dt.datetime.fromisoformat(x['createdAt']).timestamp()*1000),'notice':'Source-linked calculations under user assumptions. Not an independent analyst rating.'}]+packets

def prioritise_sources(sources,question):
 """Keep the bounded local-AI packet focused without crowding out earlier tools."""
 q=str(question).lower();analyst=bool(re.search(r'analyst|worksheet|scenario|assumption|business case|saved.+case',q));news=bool(re.search(r'news|headline|announcement|product|launch',q));chart=bool(re.search(r'chart|past hour|24.hour|price|backtest|model',q))
 def rank(x):
  ident=x.get('id','');prefix=ident[:1]
  if analyst:return 0 if prefix=='A' else 1 if news and prefix=='N' else 2
  if prefix=='A':return 4
  if news:return 0 if prefix=='N' else 1 if prefix=='D' else 2
  if chart:return 0 if prefix in ('Q','P','M') else 1 if prefix=='D' else 2
  return 2
 return sorted(sources,key=rank)
