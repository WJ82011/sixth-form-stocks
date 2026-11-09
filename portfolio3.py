"""Private hypothetical accounting. Decimal FIFO, explicit FX and dated sources.
No brokerage orders, leverage, shorting, automatic corporate-action guesses or tax advice.
"""
import copy,datetime as dt,decimal,hashlib,json,math,re,urllib.parse
D=decimal.Decimal
KINDS=('DEPOSIT','WITHDRAW','FEE','BUY','SELL','DIVIDEND','SPLIT')
CURRENCIES=('USD','GBP','EUR','CAD','AUD','JPY','CHF','HKD','NZD','SEK','NOK','DKK','CNY','TWD','KRW','INR','BRL','MXN','ZAR','SGD')
class LedgerError(ValueError):pass

def number(v,lo=0,hi=1e12):
 if isinstance(v,bool) or not isinstance(v,(int,float,str)):raise LedgerError('Use a finite number.')
 try:n=D(str(v))
 except decimal.InvalidOperation:raise LedgerError('Use a valid number.') from None
 if not n.is_finite() or not D(str(lo))<=n<=D(str(hi)):raise LedgerError('Number is outside the supported range.')
 return n

def plain(n):
 with decimal.localcontext() as ctx:
  ctx.prec=60
  return float(n.quantize(D('0.00000001')))
def date(s):
 if not isinstance(s,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',s):raise LedgerError('Use a date in YYYY-MM-DD format.')
 try:d=dt.date.fromisoformat(s)
 except ValueError:raise LedgerError('Use a valid date.') from None
 if not dt.date(2000,1,1)<=d<=dt.datetime.now(dt.timezone.utc).date():raise LedgerError('Use a date from 2000 through today.')
 return d

def text(v,n=180):return str(v or '').strip()[:n]
def source(v):
 value=text(v,600)
 if not value:raise LedgerError('Add the source or explanation for this record.')
 if value.startswith(('http:','https:')):
  u=urllib.parse.urlsplit(value)
  if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment:raise LedgerError('Use a public HTTPS source link without credentials or tracking parameters, or a short source description.')
 return value

def symbol(s):
 if not isinstance(s,str):raise LedgerError('Use an asset symbol written as text.')
 s=str(s).strip().upper()
 if not re.fullmatch(r'[A-Z0-9][A-Z0-9.\-:_]{0,23}',s):raise LedgerError('Use a valid asset symbol.')
 return s

def events(raw):
 if not isinstance(raw,list) or len(raw)>750:raise LedgerError('Use at most 750 ledger records.')
 out=[];ids=set()
 for index,r in enumerate(raw):
  if not isinstance(r,dict) or r.get('kind') not in KINDS:raise LedgerError('Unknown ledger record type.')
  ident=text(r.get('id'),64)
  if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',ident) or ident in ids:raise LedgerError('Each ledger record needs a unique ID.')
  ids.add(ident);day=date(r.get('date')).isoformat();kind=r['kind']
  e={'id':ident,'kind':kind,'date':day,'source':source(r.get('source')),'note':text(r.get('note'),500),'order':index}
  if kind in ('DEPOSIT','WITHDRAW','FEE'):e['amount']=plain(number(r.get('amount'),.00000001));e['currency']='USD';e['fx']=1
  elif kind=='SPLIT':e.update(symbol=symbol(r.get('symbol')),ratio=plain(number(r.get('ratio'),.000001,1000)))
  else:
   currency=r.get('currency','USD')
   if currency not in CURRENCIES:raise LedgerError('Choose a supported currency.')
   fx=number(r.get('fx',1),.00000001,1000000)
   if currency=='USD' and fx!=1:raise LedgerError('USD records must use an exchange rate of one.')
   e.update(currency=currency,fx=plain(fx),fee=plain(number(r.get('fee',0))),symbol=symbol(r.get('symbol')))
   if currency!='USD':e['fxSource']=source(r.get('fxSource'))
   if kind=='DIVIDEND':
    amount=number(r.get('amount'),.00000001)
    if number(e['fee'])>amount:raise LedgerError('Dividend deductions cannot exceed the dividend.')
    e['amount']=plain(amount)
   else:e.update(quantity=plain(number(r.get('quantity'),.00000001,1e9)),price=plain(number(r.get('price'),.00000001,1e9)),assetType=r.get('assetType','stock'))
   if e.get('assetType','stock') not in ('stock','ETF','crypto','other'):raise LedgerError('Unknown asset category.')
  out.append(e)
 return out

def marks(raw):
 if not isinstance(raw,list) or len(raw)>1500:raise LedgerError('Use at most 1,500 dated price marks.')
 result=[];seen=set()
 for r in raw:
  if not isinstance(r,dict):raise LedgerError('Invalid price mark.')
  sym=symbol(r.get('symbol'));day=date(r.get('date')).isoformat();currency=r.get('currency','USD')
  if (sym,day) in seen:raise LedgerError('Only one price mark per symbol and date is allowed; edit the existing mark.')
  seen.add((sym,day))
  if currency not in CURRENCIES:raise LedgerError('Unsupported price currency.')
  fx=number(r.get('fx',1),.00000001,1e6)
  if currency=='USD' and fx!=1:raise LedgerError('USD marks need an exchange rate of one.')
  m={'symbol':sym,'date':day,'price':plain(number(r.get('price'),0,1e9)),'currency':currency,'fx':plain(fx),'source':source(r.get('source')),'kind':'user mark'}
  if currency!='USD':m['fxSource']=source(r.get('fxSource'))
  result.append(m)
 return result

def fingerprint(ledger,day):
 items=[e for e in ledger if e['date']<=day]
 return hashlib.sha256(json.dumps(items,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def calculate(ledger,price_marks=None,as_of=None,exact_date=False):
 clean=events(ledger);latest=as_of or dt.datetime.now(dt.timezone.utc).date().isoformat();date(latest)
 cash=D(0);realised=D(0);fees=D(0);income=D(0);deposits=D(0);withdrawals=D(0);lots={};currencies={};history=[]
 for e in sorted((e for e in clean if e['date']<=latest),key=lambda e:(e['date'],e['order'])):
  kind=e['kind'];sym=e.get('symbol');fx=D(str(e.get('fx',1)));fee=D(str(e.get('fee',0)))*fx
  if kind=='DEPOSIT':cash+=D(str(e['amount']));deposits+=D(str(e['amount']))
  elif kind=='WITHDRAW':cash-=D(str(e['amount']));withdrawals+=D(str(e['amount']))
  elif kind=='FEE':cash-=D(str(e['amount']));fees+=D(str(e['amount']))
  elif kind=='DIVIDEND':cash+=(D(str(e['amount']))*fx-fee);income+=D(str(e['amount']))*fx-fee;fees+=fee
  elif kind=='SPLIT':
   if not lots.get(sym):raise LedgerError('A split needs a holding on its effective date: '+sym)
   for lot in lots[sym]:lot['quantity']*=D(str(e['ratio']))
   if sum((lot['quantity'] for lot in lots[sym]),D(0))<D('0.00000001'):raise LedgerError('The split would create a holding below the supported quantity precision.')
  elif kind=='BUY':
   if sym in currencies and currencies[sym]!=e['currency']:raise LedgerError('One asset symbol must keep the same quote currency. Use a distinct listing symbol for another currency.')
   currencies[sym]=e['currency'];q=D(str(e['quantity']));cost=q*D(str(e['price']))*fx+fee;cash-=cost;fees+=fee
   lots.setdefault(sym,[]).append({'quantity':q,'cost':cost,'date':e['date']})
  elif kind=='SELL':
   if currencies.get(sym)!=e['currency']:raise LedgerError('Sale currency must match the holding.')
   q=D(str(e['quantity']));held=sum((x['quantity'] for x in lots.get(sym,[])),D(0))
   if q>held:raise LedgerError('A sale exceeds the holding on its date: '+sym)
   remaining=q;cost=D(0)
   while remaining>0:
    lot=lots[sym][0];take=min(lot['quantity'],remaining);basis=lot['cost']*take/lot['quantity'];cost+=basis;lot['cost']-=basis;lot['quantity']-=take;remaining-=take
    if lot['quantity']==0:lots[sym].pop(0)
   net=q*D(str(e['price']))*fx-fee;cash+=net;realised+=net-cost;fees+=fee
  if cash<D('-0.00000001'):raise LedgerError('This record would make cash negative on '+e['date']+'. Add the actual deposit or correct the record.')
  if any(sum((lot['quantity'] for lot in owned),D(0))>D('1e12') for owned in lots.values()):raise LedgerError('Position quantity is too large after corporate actions.')
  if abs(cash)>D('1e15'):raise LedgerError('Ledger value is too large.')
  history.append({'id':e['id'],'date':e['date'],'cash':plain(cash),'realised':plain(realised)})
 usable=marks(price_marks or []);holdings=[];known_value=max(D(0),cash);unrealised=D(0);missing=[]
 for sym,positions in lots.items():
  if not positions:continue
  qty=sum((x['quantity'] for x in positions),D(0));basis=sum((x['cost'] for x in positions),D(0));eligible=[m for m in usable if m['symbol']==sym and m['date']<=latest and (not exact_date or m['date']==latest)]
  m=max(eligible,key=lambda x:x['date']) if eligible else None
  if m and m['currency']!=currencies[sym]:m=None
  age=(date(latest)-date(m['date'])).days if m else None
  value=qty*D(str(m['price']))*D(str(m['fx'])) if m and age<=7 else None
  if value is not None:known_value+=value;unrealised+=value-basis
  else:missing.append(sym)
  holdings.append({'symbol':sym,'quantity':plain(qty),'costBasisUSD':plain(basis),'averageCostUSD':plain(basis/qty),'currency':currencies[sym],'valueUSD':plain(value) if value is not None else None,'unrealisedUSD':plain(value-basis) if value is not None else None,'mark':m,'markAgeDays':age,'staleMark':bool(age is not None and age>7),'lots':[{'quantity':plain(x['quantity']),'costUSD':plain(x['cost']),'date':x['date']} for x in positions]})
 complete=not missing;total=plain(known_value) if complete else None
 for h in holdings:h['weightPct']=h['valueUSD']/total*100 if total and h['valueUSD'] is not None else None
 return {'baseCurrency':'USD','asOf':latest,'cashUSD':plain(max(D(0),cash)),'depositsUSD':plain(deposits),'withdrawalsUSD':plain(withdrawals),'netContributionsUSD':plain(deposits-withdrawals),'realisedUSD':plain(realised),'netDividendsUSD':plain(income),'feesUSD':plain(fees),'knownUnrealisedUSD':plain(unrealised),'knownSubtotalUSD':plain(known_value),'totalValueUSD':total,'gainAfterCashFlowsUSD':plain(known_value+withdrawals-deposits) if complete else None,'holdings':holdings,'unpriced':missing,'complete':complete,'history':history,'notice':'Hypothetical FIFO accounting, not tax reporting. FX rates and corporate actions are explicit dated records. Missing marks withhold total value and allocation weights; marks older than seven calendar days withhold the current total and keep their original dates. Fees are included in cash and profit. No live trading.'}

def checkpoint(ledger,price_marks,day):
 date(day);clean=events(ledger);r=calculate(clean,price_marks,day,True)
 if not r['complete'] or not any(e['date']<=day for e in clean):raise LedgerError('A checkpoint needs ledger records and a same-date price/FX mark for every holding. Explicit zero-value marks are allowed.')
 return {'date':day,'equityUSD':r['totalValueUSD'],'ledgerHash':fingerprint(clean,day),'sources':[h['mark'] for h in r['holdings']],'method':'Same-date hypothetical closing valuation; cash flows and transactions on this date are included.'}

def performance(ledger,checkpoints,benchmark):
 clean=events(ledger);valid=[c for c in checkpoints if c.get('ledgerHash')==fingerprint(clean,c.get('date',''))]
 if len(valid)<2:return {'status':'insufficient','notice':'Capture two valid dated portfolio checkpoints. Editing earlier ledger records invalidates affected checkpoints.'}
 valid.sort(key=lambda c:c['date']);a,b=valid[0],valid[-1];days=(date(b['date'])-date(a['date'])).days
 if days<=0:return {'status':'insufficient','notice':'Use checkpoints on different dates.'}
 flows=[e for e in clean if a['date']<e['date']<=b['date'] and e['kind'] in ('DEPOSIT','WITHDRAW')]
 net=D(0);weighted=D(0)
 for e in flows:
  amount=D(str(e['amount']))*(1 if e['kind']=='DEPOSIT' else -1);net+=amount;weighted+=amount*D((date(b['date'])-date(e['date'])).days)/D(days)
 denominator=D(str(a['equityUSD']))+weighted
 if denominator<=0:return {'status':'unavailable','notice':'The cash-flow-weighted capital base is not positive.'}
 dietz=(D(str(b['equityUSD']))-D(str(a['equityUSD']))-net)/denominator*100
 points={x['date']:x for x in benchmark if isinstance(x,dict) and isinstance(x.get('price'),(int,float)) and not isinstance(x['price'],bool) and math.isfinite(x['price']) and x['price']>0}
 pa,pb=points.get(a['date']),points.get(b['date'])
 return {'status':'ok','start':a,'end':b,'modifiedDietzPct':plain(dietz),'benchmarkPriceChangePct':(pb['price']/pa['price']-1)*100 if pa and pb else None,'benchmarkSources':[pa,pb] if pa and pb else [],'externalFlows':flows,'invalidatedCheckpoints':len(checkpoints)-len(valid),'notice':'Modified Dietz is a cash-flow-weighted approximation, not time-weighted return. Flows are treated at day end. Benchmark uses prices on the exact same endpoint dates; missing dates are not interpolated. Benchmark price change excludes dividends, fees and FX; portfolio figures include recorded dividends/fees/FX, so this is not a total-return outperformance claim.'}
