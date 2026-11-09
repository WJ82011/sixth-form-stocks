"""Source-attributed capitalization endpoints. Never convert index points into money."""
import csv,io,json,decimal,contextlib,datetime as dt
import portfolio3,research32
D=decimal.Decimal
MARKETS={'US equities':'USD','UK equities':'GBP','Euro-area equities':'EUR','Japan equities':'JPY','Hong Kong equities':'HKD'}
def clean(rows):
 if not isinstance(rows,list) or len(rows)>1000:raise ValueError('Use up to 1,000 market-value observations.')
 out=[];seen=set();scopes={}
 for r in rows:
  if not isinstance(r,dict):raise ValueError('Invalid market-value row.')
  market=r.get('market');currency=r.get('currency');unit=r.get('unit')
  if market not in MARKETS or currency!=MARKETS[market] or unit not in ('millions','billions','trillions'):raise ValueError('Choose a supported market, its native currency and explicit units.')
  date=portfolio3.date(r.get('date')).isoformat();scope=research32.text(r.get('scope'),300,True);url=research32.public_url(r.get('source'));value=portfolio3.number(r.get('capitalization'),.0000001,1e18)*{'millions':D(1),'billions':D(1000),'trillions':D(1000000)}[unit]
  if (market,date) in seen:raise ValueError('Each market/date must have one observation.')
  if market in scopes and scopes[market]!=scope:raise ValueError('Do not mix different market coverage within one comparison series.')
  scopes[market]=scope;seen.add((market,date));out.append({'market':market,'currency':currency,'date':date,'capitalization':str(value),'unit':'millions','scope':scope,'source':url})
 return sorted(out,key=lambda r:(r['market'],r['date']))
def bundled():
 return clean([{'market':'US equities','currency':'USD','date':day,'capitalization':value,'unit':'millions','scope':'US-domiciled public companies on NYSE, Nasdaq and OTCQX; foreign-domiciled companies excluded','source':'https://siblisresearch.com/data/us-stock-market-value/'} for day,value in [('2026-06-30','75282047.1'),('2026-09-30','78737915.5')]])
def init(con):con.execute('CREATE TABLE IF NOT EXISTS market36_values(id INTEGER PRIMARY KEY CHECK(id=1),body TEXT NOT NULL,fetched_at INTEGER NOT NULL)')
def load(g):
 with contextlib.closing(g['db_connection']()) as c:
  row=c.execute("SELECT body FROM market36_values WHERE id=1").fetchone()
 if not row:return bundled(),False
 try:return clean(json.loads(row[0])['rows']),True
 except (ValueError,TypeError,KeyError):return [],True

def cards(g):
 rows,manual=load(g);out=[]
 for name,currency in MARKETS.items():
  values=[x for x in rows if x['market']==name];user_values=manual
  if not values and name=='US equities':values=bundled();user_values=False
  r={'name':name,'currency':currency,'change':None,'status':'No comparable sourced totals loaded. Add licensed or publicly reusable observations; no estimate is substituted.'}
  if len(values)>=2:
   a,b=values[-2:];delta=D(b['capitalization'])-D(a['capitalization']);r.update(change=float(delta),unit='millions',start=a['date'],end=b['date'],before=a['capitalization'],after=b['capitalization'],scope=b['scope'],sources=list(dict.fromkeys([a['source'],b['source']])),status='User-supplied source observations; not independently verified' if user_values else 'Published Siblis Research observations · attribution retained',checked='2026-11-06' if not user_values else None)
  out.append(r)
 return out

def import_csv(g,obj):
 text=obj.get('csv')
 if obj.get('coverageConfirmed') is not True or not isinstance(text,str) or len(text.encode())>500000:raise ValueError('Confirm consistent coverage and use a CSV under 500 KB.')
 reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
 if not reader.fieldnames or not {'market','currency','date','capitalization','unit','scope','source'}.issubset(reader.fieldnames):raise ValueError('CSV requires market,currency,date,capitalization,unit,scope,source.')
 rows=[]
 for row in reader:
  if len(rows)>=1000:raise ValueError('Use up to 1,000 observations.')
  rows.append(row)
 rows=clean(rows)
 if not rows:raise ValueError('The file has no usable observations.')
 if any(sum(x['market']==name for x in rows)==1 for name in MARKETS):raise ValueError('Provide at least two observations for each included market.')
 body=json.dumps({'rows':rows},allow_nan=False)
 with g['LOCK'],contextlib.closing(g['db_connection']()) as c,c:c.execute('INSERT OR REPLACE INTO market36_values VALUES(?,?,?)',(1,body,int(g['time'].time()*1000)))
 return {'markets':cards(g),'notice':'Imported values retain their source links and declared coverage. They are not independently verified. This replaces only the market-value dataset, not prices or research.'}

def export(g):
 rows,_=load(g)
 if not any(x['market']=='US equities' for x in rows):rows=bundled()+rows
 output=io.StringIO();fields=['market','currency','date','capitalization','unit','scope','source'];writer=csv.DictWriter(output,fieldnames=fields);writer.writeheader()
 for row in rows:
  safe={k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in row.items()};writer.writerow(safe)
 return {'csv':output.getvalue(),'notice':'Source observations in reported currency, not a live data feed. Preserve attribution and coverage.'}
