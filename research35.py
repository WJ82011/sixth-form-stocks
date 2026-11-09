"""Guided saved-source research and mechanical scenario explanations."""
import copy,decimal,re
import analyst34,brief33,market34,research_ai
D=decimal.Decimal
DRIVERS={'pricePct':'Selling-price change','volumePct':'Volume / demand change','unitCostPct':'Core unit-cost change','fixedCostPct':'Fixed operating-cost change'}
TEMPLATES={'Games':['Which launch dates are actually confirmed?','Are bookings, recognised revenue and company net receipts kept separate?','How much demand depends on recurring spending versus new releases?'],'Banking & finance':['Are funding costs, credit losses and capital requirements covered?','Is this business suitable for a simple price/volume cost model?','Which regulatory capital and liquidity disclosures are available?'],'Shops & travel':['How do selling prices and sales volumes interact?','Are margins affected by input costs or discounting?','Are seasonality and comparable-period dates aligned?'],'Technology':['Which product and service segments drive revenue?','Are launch assumptions supported by dated company statements?','What evidence supports pricing power and customer demand?']}
def guide(symbol,context,books,entry):
 aliases=[symbol]
 if entry:aliases += [entry.get('name','').split(' Inc')[0].split(' Corporation')[0]]
 if symbol=='TTWO':aliases+=['Take-Two','Take Two','Rockstar','Grand Theft Auto','GTA VI']
 if symbol=='AAPL':aliases+=['Apple','iPhone']
 def match(headline):return any(re.search(r'(?<![A-Za-z0-9])'+re.escape(a)+r'(?![A-Za-z0-9])',headline,re.I) for a in aliases if len(a)>=2)
 news=[x for x in context['news'] if match(x['headline'])][:4]
 price=next((x.get('current') for x in context['prices'] if x['symbol']==symbol),None)
 return {'symbol':symbol,'name':entry.get('name',symbol) if entry else symbol,'quote':price,'headlines':news,'events':context['upcoming'][:4],'filings':context['filings'][:3],'asOf':context['asOf'],'hasBaseline':bool(books),'questions':TEMPLATES.get((entry or {}).get('category'),['Which part of the business would this change affect?','What evidence would make your current view wrong?','Does the selling price reflect company receipts, or a retail price?']),'gaps':([] if books else ['Supported annual revenue and operating-profit facts are unavailable.'])+([] if price else ['No usable saved quote is available.'])+([] if news else ['No recent saved headlines matched the company title or ticker.'])+['Future sales, margins and launch outcomes remain assumptions.'],'notice':'Saved records only. Headline matching can miss relevant articles and include irrelevant ones. Prices retain their source time; calendar items are not guaranteed announcements.'}

def bridge(raw):
 c=analyst34.config(raw);b=c['baseline'];r=D(str(b['revenueM']));op=D(str(b['operatingProfitM']));f=D(str(c['shared']['affectedPct']))/100;v=D(str(c['shared']['variableCostPct']))/100;fixed=r-r*v-op;out=[]
 for case in c['scenarios']:
  p,q,cost,g=[D(str(case[k]))/100 for k in ('pricePct','volumePct','unitCostPct','fixedCostPct')];result=analyst34.case_result(b,c['shared'],case,c['capital'])
  effects=[('Selling prices',r*f*p),('Volume and its variable costs',r*f*(1+p)*q-r*v*f*q),('Core unit costs',-r*v*((1-f)+f*(1+q))*cost),('Fixed costs',-fixed*g),('Launch contribution',D(str(result['launchRevenueM']))-D(str(result['launchVariableCostM'])))]
  steps=[{'label':'Reported starting profit/loss','value':float(op),'total':True}]+[{'label':name,'value':float(value),'total':False} for name,value in effects]+[{'label':'Scenario profit/loss','value':result['operatingProfitM'],'total':True}]
  if abs(op+sum(value for _,value in effects)-D(str(result['operatingProfitM'])))>max(D('0.000001'),abs(D(str(result['operatingProfitM'])))*D('0.000000001')):raise ValueError('The visual explanation did not reconcile to the scenario.')
  out.append({'name':case['name'],'steps':steps})
 return {'currency':b['currency'],'unit':'millions','cases':out,'notice':'Mechanical model effects, holding other assumptions fixed in this sequence. Price is applied before volume, so their interaction is assigned to volume. This is not evidence of real-world causes.'}

def start_assistant(g,obj):
 symbol=g['valid_symbol'](obj.get('symbol',''));question=obj.get('question','');driver=obj.get('driver');value=obj.get('change')
 if driver not in DRIVERS or not isinstance(question,str) or not 4<=len(question.strip())<=1400:raise ValueError('Choose a business input and enter a question between 4 and 1,400 characters.')
 if value is not None:value=analyst34.num(value,-99,300)
 facts='Scenario-building method, not company guidance. Selling-price changes affect the affected share of existing revenue. Volume changes affect revenue and its variable costs. Core unit-cost changes affect core variable costs. Fixed-cost changes affect the remaining operating costs. Price and volume interact multiplicatively. A hypothetical change is not a predicted stock-price move. Numerical magnitudes must be supplied and approved by the user, not invented by the language model.'
 if value is not None:facts+=' User-entered, unapproved hypothesis: '+DRIVERS[driver]+' = '+str(value)+' percent. This is an assumption, not reported company data.'
 evidence=g['ai_evidence'](symbol,question);sources=[{'id':'H35','title':'Scenario mechanics and user hypothesis','kind':'method and user assumption','body':facts,'notice':'Hypothetical editable input; no assertion of company guidance or market causation.'},*evidence['sources']]
 question='Explore '+DRIVERS[driver]+'. Explain the mechanism, evidence and gaps. Suggest checks, not unsupported numbers. Treat any supplied change as a user hypothesis. Question: '+question
 packet=research_ai.packet(symbol,sources,evidence['asOf'],question)
 return research_ai.start(str(obj.get('model','')),'answer',question,packet,g['ai_persist'])
