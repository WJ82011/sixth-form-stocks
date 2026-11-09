"""Three statement research with explicit standard taxonomy/currency and derived periods.
Custom/company-extension rows are kept separate as unverified manual research.
"""
import copy,datetime as dt,decimal,math,re
import financials as f
D=decimal.Decimal
EXTRA={
 'costSales':('Cost of sales',('CostOfRevenue','CostOfGoodsAndServicesSold'),'duration','income'),
 'grossProfit':('Gross profit',('GrossProfit',),'duration','income'),
 'operatingProfit':('Operating profit/loss',('OperatingIncomeLoss',),'duration','income'),
 'tax':('Income tax expense/benefit',('IncomeTaxExpenseBenefit',),'duration','income'),
 'currentAssets':('Current assets',('AssetsCurrent',),'instant','balance'),
 'currentLiabilities':('Current liabilities',('LiabilitiesCurrent',),'instant','balance'),
 'equity':('Shareholders equity',('StockholdersEquity',),'instant','balance'),
 'inventory':('Inventory',('InventoryNet',),'instant','balance'),
 'receivables':('Receivables',('AccountsReceivableNetCurrent',),'instant','balance'),
 'investingCash':('Cash from investing',('NetCashProvidedByUsedInInvestingActivities',),'duration','cashflow'),
 'financingCash':('Cash from financing',('NetCashProvidedByUsedInFinancingActivities',),'duration','cashflow'),
 'capex':('Purchases of property, plant and equipment',('PaymentsToAcquirePropertyPlantAndEquipment',),'duration','cashflow'),
 'dividendsPaid':('Cash dividends paid',('PaymentsOfDividends',),'duration','cashflow'),
 'buybacks':('Cash used for share repurchases',('PaymentsForRepurchaseOfCommonStock',),'duration','cashflow'),
}
GROUP={**{k:('income' if k in ('revenue','profit') else 'cashflow' if k=='operatingCash' else 'balance') for k in f.METRICS},**{k:v[3] for k,v in EXTRA.items()}}
DEFS={**f.METRICS,**{k:v[:3] for k,v in EXTRA.items()}}
IFRS={
 'revenue':('Revenue',),'profit':('ProfitLoss',),'operatingCash':('CashFlowsFromUsedInOperatingActivities',),
 'cash':('CashAndCashEquivalents',),'assets':('Assets',),'liabilities':('Liabilities',),
 'debtCurrent':('CurrentBorrowings',),'debtNoncurrent':('NoncurrentBorrowings',),
 'costSales':('CostOfSales',),'grossProfit':('GrossProfit',),'operatingProfit':('ProfitLossFromOperatingActivities',),
 'tax':('IncomeTaxExpenseContinuingOperations',),'currentAssets':('CurrentAssets',),'currentLiabilities':('CurrentLiabilities',),
 'equity':('Equity',),'inventory':('Inventories',),'receivables':('TradeAndOtherCurrentReceivables',),
 'investingCash':('CashFlowsFromUsedInInvestingActivities',),'financingCash':('CashFlowsFromUsedInFinancingActivities',),
 'capex':('PurchaseOfPropertyPlantAndEquipment',),'dividendsPaid':('DividendsPaidClassifiedAsFinancingActivities',),'buybacks':('PaymentsForRepurchaseOfOwnShares',)
}
NOTICE=('Selected standardized consolidated statement facts, not every line or note in a filing. '
 'Taxonomies and currencies are separate. IFRS borrowing and profit concepts can differ from US GAAP; no cross-basis ranking is implied. '
 'Derived values are arithmetic research calculations, not reported quotations. Custom/manual rows are separate and unverified. '
 'Historical series use latest available filed versions, not point-in-time backtest data.')

def build(raw,cik,submissions,today=None):
 today=today or dt.datetime.now(dt.timezone.utc).date();facts=raw.get('facts',{})
 books=[]
 for taxonomy in ('us-gaap','ifrs-full'):
  gaap=facts.get(taxonomy,{})
  if not isinstance(gaap,dict) or not gaap:continue
  defs=DEFS if taxonomy=='us-gaap' else {k:(v[0],IFRS.get(k,()),v[2]) for k,v in DEFS.items()}
  currencies=set()
  for key in ('revenue','profit'):
   for tag in defs[key][1]:
    obj=gaap.get(tag,{})
    if isinstance(obj,dict):currencies.update(u for u in obj.get('units',{}) if re.fullmatch('[A-Z]{3}',u))
  for currency in sorted(currencies,key=lambda u:(u!='USD',u))[:4]:
   r=f.normalise_facts(raw,cik,submissions,today,metric_defs=defs,taxonomy=taxonomy,currency=currency,annual_forms=('10-K','10-K/A','20-F','20-F/A','40-F','40-F/A'),quarter_forms=('10-Q','10-Q/A','6-K','6-K/A'))
   r.update(taxonomy=taxonomy,currency=currency,notice=NOTICE,groups=GROUP,labels={k:v[0] for k,v in defs.items()})
   if taxonomy=='ifrs-full':
    r['labels'].update(profit='Reported IFRS profit/loss',debtCurrent='Current borrowings',debtNoncurrent='Non-current borrowings',tax='Tax expense, continuing operations',equity='Total equity')
    # IFRS borrowings are not equivalent to the US-GAAP long-term debt components.
    for periods in (r['annual'],r['quarterly']):
     for p in periods:p['longTermDebt']=None;p['debtScope']='IFRS current/non-current borrowings are shown separately; a US-GAAP long-term-debt total is not inferred.'
   r['derivedQuarters']=derived_quarters(gaap,defs,currency,cik,today)
   r['ttmDirect']=ttm(r['quarterly'])
   r['ttmWithDerived']=ttm(merge_quarters(r['quarterly'],r['derivedQuarters']))
   if r['annual'] or r['quarterly']:books.append(r)
 return books

def derived_quarters(gaap,defs,currency,cik,today):
 """Discrete Q2/Q3/Q4 = later fiscal-YTD minus preceding fiscal-YTD.
Require identical concept/currency/start, contiguous quarter distance, monotonic filing
sequence and no same-date conflicts. Never replace a directly reported quarter.
"""
 by_period={}
 for key,(_,tags,kind) in defs.items():
  if kind!='duration':continue
  for tag in tags:
   rows=gaap.get(tag,{}).get('units',{}).get(currency,[]) if isinstance(gaap.get(tag),dict) else []
   unique={}
   for row in rows:
    if not isinstance(row,dict):continue
    start,end,filed=f.day(row.get('start')),f.day(row.get('end')),f.day(row.get('filed'))
    if not start or not end or not filed or not start<end<=filed<=today or not f.finite(row.get('val')) or not f.accession_url(cik,row.get('accn')) or row.get('form') not in ('10-K','10-K/A','10-Q','10-Q/A','20-F','20-F/A','6-K','6-K/A'):continue
    length=(end-start).days+1
    if not 75<=length<=400:continue
    k=(start,end);old=unique.get(k)
    if not old or row['filed']>old['filed']:unique[k]=row
    elif row['filed']==old['filed'] and row['val']!=old['val']:unique[k]={**old,'ambiguous':True}
   ordered=sorted(unique.items(),key=lambda x:(x[0][0],x[0][1]))
   for (start,end),r in ordered:
    if (end-start).days+1<=105 or r.get('ambiguous'):continue
    previous=[(e,p) for (s,e),p in unique.items() if s==start and 75<=(end-e).days<=105 and not p.get('ambiguous') and p['filed']<=r['filed']]
    if len(previous)!=1:continue
    prev_end,p=previous[0];qs=(prev_end+dt.timedelta(days=1)).isoformat();qe=end.isoformat();amount=float(D(str(r['val']))-D(str(p['val'])))
    fact={'value':amount,'unit':currency,'start':qs,'end':qe,'filed':r['filed'],'form':r['form'],'accession':r['accn'],'url':f.accession_url(cik,r['accn']),'tag':tag,'taxonomy':'ifrs-full' if tag in {t for ts in IFRS.values() for t in ts} else 'us-gaap','derived':True,'calculation':'Later fiscal YTD minus preceding fiscal YTD','inputs':[{'value':x['val'],'start':x['start'],'end':x['end'],'filed':x['filed'],'url':f.accession_url(cik,x['accn']),'tag':tag} for x in (r,p)]}
    entry=by_period.setdefault((qs,qe),{'start':qs,'end':qe,'type':'derived quarter','durationDays':(end-prev_end).days,'currency':currency,'metrics':{},'warnings':['Calculated from cumulative figures in different reporting periods. Revisions or accounting changes can limit comparability; inspect both input filings.']})
    if key not in entry['metrics']:entry['metrics'][key]=fact
 out=sorted(by_period.values(),key=lambda x:x['end'])[-8:]
 return out

def merge_quarters(direct,derived):
 out={(p['start'],p['end']):copy.deepcopy(p) for p in derived}
 for p in direct:
  key=(p['start'],p['end']);row=out.setdefault(key,copy.deepcopy(p))
  for k,v in p['metrics'].items():
   if v and 'value' in v:row['metrics'][k]=v
  row['type']='direct/derived quarter' if any(v and v.get('derived') for v in row['metrics'].values()) else 'quarterly'
 return sorted(out.values(),key=lambda x:x['end'])

def ttm(periods):
 rows=sorted(periods,key=lambda x:x['end']);result=[]
 for end in range(3,len(rows)):
  window=rows[end-3:end+1]
  if any((f.day(b['start'])-f.day(a['end'])).days!=1 for a,b in zip(window,window[1:])) or not 330<=(f.day(window[-1]['end'])-f.day(window[0]['start'])).days+1<=400:continue
  metrics={}
  for k in DEFS:
   values=[p.get('metrics',{}).get(k) for p in window]
   if DEFS[k][2]=='instant':
    value=values[-1]
    if value and 'value' in value:metrics[k]=copy.deepcopy(value)
    continue
   if not all(v and f.finite(v.get('value')) for v in values) or len({v['tag'] for v in values})!=1 or len({v['unit'] for v in values})!=1:continue
   metrics[k]={'value':sum(v['value'] for v in values),'unit':values[0]['unit'],'tag':values[0]['tag'],'start':window[0]['start'],'end':window[-1]['end'],'derived':True,'calculation':'Sum of four contiguous non-overlapping quarters','inputs':values}
  result.append({'start':window[0]['start'],'end':window[-1]['end'],'currency':window[0]['currency'],'type':'calculated TTM','metrics':metrics,'warnings':['TTM is a calculation, not a directly reported annual figure. Missing or mismatched quarters withhold the affected line.']})
 return result[-4:]

def manual_rows(raw):
 if not isinstance(raw,list) or len(raw)>300:raise ValueError('Use at most 300 manual statement rows.')
 out=[];ids=set()
 for r in raw:
  if not isinstance(r,dict):raise ValueError('Invalid manual statement row.')
  ident=str(r.get('id',''))[:64]
  if not re.fullmatch('[A-Za-z0-9_-]{1,64}',ident) or ident in ids:raise ValueError('Manual rows need unique IDs.')
  ids.add(ident);start,end=f.day(r.get('start')),f.day(r.get('end'));unit=str(r.get('currency',''))
  if (r.get('start') and not start) or not end or end>dt.datetime.now(dt.timezone.utc).date() or (start and start>end):raise ValueError('Use valid historical statement dates.')
  if not re.fullmatch('[A-Z]{3}',unit) or not f.finite(r.get('value')):raise ValueError('Use a stated currency and finite amount.')
  from portfolio3 import source,symbol
  group=r.get('statement')
  if group not in ('income','balance','cashflow'):raise ValueError('Choose a statement category.')
  if group!='balance' and not start:raise ValueError('Income and cash-flow rows need an explicit period start.')
  label=str(r.get('label','')).strip()[:120]
  if not label:raise ValueError('Name the exact statement line.')
  out.append({'id':ident,'symbol':symbol(r.get('symbol')),'statement':group,'label':label,'value':r['value'],'currency':unit,'start':start.isoformat() if start else None,'end':end.isoformat(),'source':source(r.get('source')),'note':str(r.get('note',''))[:600],'verified':False})
 return out

def evidence(report):
 books=report.get('statementBooks',[])
 if not books:return []
 book=books[0];period=(book.get('annual') or [None])[-1]
 if not period:return []
 groups={}
 for key,record in period['metrics'].items():
  if record and f.finite(record.get('value')):groups.setdefault(record['accession'],[]).append((key,record))
 sources=[]
 ordered=sorted(groups.items(),key=lambda x:(any(k=='profit' for k,_ in x[1]),len(x[1])),reverse=True)
 for _,items in ordered:
  for offset in range(0,len(items),8):
   chunk=items[offset:offset+8];record=chunk[0][1]
   body=f"Market Desk normalized SEC statement facts for {report.get('name','this issuer')}. Basis {book['taxonomy']}; disclosed currency {book['currency']}, not necessarily functional or listing currency. No FX or ADR conversion is inferred. Annual period {period['start']} to {period['end']}. In words: {f.readable_date(period['start'])} to {f.readable_date(period['end'])}. Filing {record['form']} filed {record['filed']} ({f.readable_date(record['filed'])}). "
   for key,value in chunk:
    amount=D(str(value['value']));body+=f"{book['labels'][key]} = {amount} {book['currency']} ({amount/D(1000000)} million {book['currency']}); {value['taxonomy']}:{value['tag']}. "
    if key=='profit' and amount<0:body+=f"Net loss magnitude = {-amount} {book['currency']} ({-amount/D(1000000)} million {book['currency']}). "
   body+='Normalized fields and exact unit presentations, not verbatim filing quotations. Selected lines only; missing notes are not invented.'
   sources.append({'id':'T'+str(len(sources)+1),'title':'V3 statement facts: '+str(report.get('name',''))+' · '+period['end'],'kind':'normalized SEC statement facts','body':body,'url':record['url'],'published':record['filed'],'retrievedAt':report.get('fetchedAt'),'notice':NOTICE})
   if len(sources)>=4:return sources
 return sources

def summary(report):
 books=report.get('statementBooks',[])
 if not books:return f.overview(report)
 book=books[0]
 if book['taxonomy']=='us-gaap' and book['currency']=='USD':return f.overview(report)
 period=(book.get('annual') or [None])[-1]
 if not period:return 'No supported annual statement window is saved for this company.'
 lines=[f"SEC annual statement research: {report.get('name','')}, {period['start']} to {period['end']}. {book['taxonomy']}; amounts in {book['currency']}. This is the currency of the disclosed fact records, which may include a translated presentation. No conversion to the share listing currency is performed."]
 for k in ('revenue','profit','operatingCash','cash','assets','liabilities'):
  value=period['metrics'].get(k)
  lines.append(book['labels'][k]+': '+(f"{value['value']:,.2f} {book['currency']}; filed {value['filed']} ({value['form']})." if value and f.finite(value.get('value')) else 'Unavailable.'))
 return '\n'.join(lines+[NOTICE])
