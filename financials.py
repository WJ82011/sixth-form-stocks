"""Conservative SEC Company Facts extraction. No price models, inferred quarters or scores.

Only USD, standard US-GAAP, consolidated 10-K/10-Q facts are supported initially.
SEC FY labels often describe the filing year, not the fact's period: use actual dates.
"""
from __future__ import annotations
import datetime as dt
import decimal
import json
import math
import re

METHOD='sec-us-gaap-usd-v1'
METRICS={
 'revenue':('Revenue',('RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet'),'duration'),
 'profit':('Net profit or loss',('NetIncomeLoss',),'duration'),
 'operatingCash':('Cash from operations',('NetCashProvidedByUsedInOperatingActivities',),'duration'),
 'cash':('Cash and cash equivalents',('CashAndCashEquivalentsAtCarryingValue',),'instant'),
 'assets':('Total assets',('Assets',),'instant'),
 'liabilities':('Total liabilities',('Liabilities',),'instant'),
 'debtCurrent':('Current portion of long-term debt',('LongTermDebtCurrent',),'instant'),
 'debtNoncurrent':('Non-current long-term debt',('LongTermDebtNoncurrent',),'instant'),
}
NOTICE=('Selected standard US-GAAP facts in USD, not a complete set of financial statements. '
        'Company-specific tags and IFRS are not extracted. Missing values are not zero. '
        'Historical periods use the latest available filed version, not what was known at that time. '
        'This is not a credit rating, investment recommendation or price forecast.')

def day(value):
 if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):return None
 try:return dt.date.fromisoformat(value)
 except ValueError:return None

def accession_url(cik,accn):
 if not re.fullmatch(r'\d{10}-\d{2}-\d{6}',str(accn)):return ''
 return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn.replace("-","")}/{accn}-index.html'

def finite(value):
 return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and abs(value)<1e16

def normalise_facts(raw,cik,submissions,now=None,*,metric_defs=None,taxonomy="us-gaap",currency="USD",annual_forms=("10-K","10-K/A"),quarter_forms=("10-Q","10-Q/A")):
 """Never stitch nine-month cash flow into a quarter or mix currency and duration."""
 today=now or dt.datetime.now(dt.timezone.utc).date()
 if not isinstance(raw,dict) or raw.get('cik')!=int(cik):raise ValueError('SEC financial data did not match the requested issuer.')
 if not isinstance(submissions,dict) or str(submissions.get('cik','')).lstrip('0')!=str(int(cik)):raise ValueError('SEC company identity did not match.')
 facts=raw.get('facts',{})
 if not isinstance(facts,dict):raise ValueError('SEC financial facts were not in the expected format.')
 definitions=metric_defs or METRICS
 gaap=facts.get(taxonomy,{})
 if not isinstance(gaap,dict):gaap={}
 candidates={key:[] for key in definitions};other_units=set();rejected=0
 for key,(_,tags,kind) in definitions.items():
  for priority,tag in enumerate(tags):
   definition=gaap.get(tag,{})
   if not isinstance(definition,dict) or not isinstance(definition.get('units'),dict):continue
   for unit,rows in definition['units'].items():
    if not isinstance(rows,list):continue
    for row in rows:
     if not isinstance(row,dict):continue
     end,filed,start=day(row.get('end')),day(row.get('filed')),day(row.get('start'))
     form=row.get('form');accn=row.get('accn');value=row.get('val')
     if not end or not filed or end>filed or filed>today or end>today or not finite(value) or not accession_url(cik,accn) or form not in annual_forms+quarter_forms:
      rejected+=1;continue
     if unit!=currency:
      if re.fullmatch('[A-Z]{3}',str(unit)):other_units.add(unit)
      continue
     if key not in ('profit','operatingCash','operatingProfit','tax','equity','investingCash','financingCash') and value<0:continue
     if kind=='duration':
      if not start or start>=end:continue
      days=(end-start).days+1
      period='annual' if 330<=days<=400 and form in annual_forms else 'quarterly' if 75<=days<=105 else None
      if not period:continue
     else:
      if row.get('start') is not None:continue
      period='instant';days=None
     candidates[key].append({'value':value,'unit':currency,'start':row.get('start') if kind=='duration' else None,'end':end.isoformat(),'filed':filed.isoformat(),'form':form,'accession':accn,'url':accession_url(cik,accn),'tag':tag,'taxonomy':taxonomy,'periodType':period,'durationDays':days,'amended':form.endswith('/A'),'priority':priority})
 def choose(key,start,end,period):
  rows=[x for x in candidates[key] if x['end']==end and (x['periodType']=='instant' or (x['start']==start and x['periodType']==period))]
  if not rows:return None
  # Later filings can contain revised comparative figures. Do not label them as point-in-time history.
  rows.sort(key=lambda x:(x['filed'],x['accession'],-x['priority']),reverse=True)
  latest=rows[0];same=[x for x in rows if (x['filed'],x['tag'])==(latest['filed'],latest['tag'])]
  if len({x['value'] for x in same})>1:return {'missing':'Conflicting values for the same concept and period on the latest filing date; exact filing order is not inferred.'}
  result={k:v for k,v in latest.items() if k!='priority'}
  versions={(x['accession'],x['value']) for x in rows if x['tag']==latest['tag']}
  result['versionsSeen']=len(versions);result['valuesDifferAcrossFilings']=len({v for _,v in versions})>1
  return result
 output={};excluded=[]
 for period in ('annual','quarterly'):
  anchors={(x['start'],x['end']) for key in ('revenue','profit') for x in candidates[key] if x['periodType']==period}
  periods=[]
  # Avoid duplicate windows ending on the same date. Different starts are not silently merged.
  ends=sorted({end for _,end in anchors},reverse=True)[:6 if period=='annual' else 8]
  for end in ends:
   windows=[start for start,e in anchors if e==end]
   if len(windows)!=1:
    excluded.append(period+' ending '+end+': conflicting start dates; this period was not merged or shown.');continue
   start=windows[0];metrics={key:choose(key,start,end,period) for key in definitions}
   report={'start':start,'end':end,'type':period,'currency':currency,'durationDays':(day(end)-day(start)).days+1,'metrics':metrics,'warnings':[]}
   for key,f in metrics.items():
    if f and f.get('valuesDifferAcrossFilings'):report['warnings'].append(definitions[key][0]+': values differ across filings; the latest filed version is shown. This is not a determination of why the figure changed.')
    if f and f.get('amended'):report['warnings'].append(definitions[key][0]+': from an amended filing.')
   def coherent(keys):
    facts=[metrics[k] for k in keys]
    return all(f and 'value' in f for f in facts) and len({f['accession'] for f in facts})==1
   if coherent(('revenue','profit')) and metrics['revenue']['value']>0:
    report['netMarginPct']=metrics['profit']['value']/metrics['revenue']['value']*100
   else:report['netMarginPct']=None
   if coherent(('debtCurrent','debtNoncurrent')):
    report['longTermDebt']=metrics['debtCurrent']['value']+metrics['debtNoncurrent']['value']
   else:report['longTermDebt']=None
   report['debtScope']='Long-term debt: current and non-current portions only. Other short-term borrowings and lease obligations are not added; this is not total debt.'
   periods.append(report)
  periods.sort(key=lambda x:x['end'])
  for i,p in enumerate(periods):
   p['revenueGrowthPct']=None
   if period!='annual' or i==0:continue
   before=periods[i-1];a=p['metrics']['revenue'];b=before['metrics']['revenue']
   aligned=abs(p['durationDays']-before['durationDays'])<=14 and abs((day(p['start'])-day(before['end'])).days-1)<=7 and 350<=(day(p['end'])-day(before['end'])).days<=380
   if a and b and 'value' in a and 'value' in b and b['value']>0 and a['tag']==b['tag'] and aligned:p['revenueGrowthPct']=(a['value']/b['value']-1)*100
  output[period]=periods
 name=str(submissions.get('name') or raw.get('entityName') or '')[:160]
 return {'status':'ok' if output['annual'] or output['quarterly'] else 'unsupported','method':METHOD,'cik':str(int(cik)).zfill(10),'name':name,'annual':output['annual'],'quarterly':output['quarterly'],'notice':NOTICE,'otherCurrenciesNotUsed':sorted(other_units),'supportedTaxonomy':taxonomy,'coverage':'Up to six full annual periods and eight directly reported quarters. No inferred fourth quarter or trailing-twelve-month totals. Balance-sheet facts match each period end.','unit':currency,'rejectedRecords':rejected,'excludedPeriods':excluded}

def readable_date(value):
 d=day(value)
 if not d:return str(value)
 months=('January','February','March','April','May','June','July','August','September','October','November','December')
 return f'{months[d.month-1]} {d.day}, {d.year}'

def money(value):
 if not finite(value):return 'unavailable'
 return f'USD {value:,.0f}'

def overview(report):
 periods=report.get('annual',[])
 if not periods:return 'No supported annual SEC accounts are saved. Open Company financial health and update the accounts. No financial figures have been inferred.'
 p=periods[-1];m=p['metrics'];lines=[f"SEC annual accounts: {report['name']}, {p['start']} to {p['end']}. Figures are USD, not live prices."]
 for key in ('revenue','profit','operatingCash','cash','liabilities'):
  f=m.get(key)
  lines.append(f"{METRICS[key][0]}: {money(f.get('value') if f else None)}"+(f"; filed {f['filed']} ({f['form']})." if f and 'value' in f else '.'))
 if p.get('netMarginPct') is not None:lines.append(f"Calculated net profit margin: {p['netMarginPct']:.2f}% of revenue; both inputs cover the same period and filing.")
 if p.get('revenueGrowthPct') is not None:lines.append(f"Calculated revenue change versus the preceding comparable saved year: {p['revenueGrowthPct']:.2f}%.")
 lines.append('Long-term debt (current and non-current portions): '+money(p.get('longTermDebt'))+'. '+p['debtScope'])
 if len(periods)>1:
  previous=periods[-2];a=m.get('profit');b=previous['metrics'].get('profit')
  if a and b and 'value' in a and 'value' in b and a['tag']==b['tag'] and abs((day(p['start'])-day(previous['end'])).days-1)<=7 and abs(p['durationDays']-previous['durationDays'])<=14:
   delta=a['value']-b['value'];word='higher' if delta>0 else 'lower' if delta<0 else 'unchanged'
   lines.append(f"Reported net profit/loss is {word} than in {previous['start']} to {previous['end']} ({money(b['value'])}). This alone does not establish overall financial health or predict the stock price.")
 lines.extend(p['warnings'][:3]);lines.append('Saved figures may be old or incomplete. '+NOTICE)
 return '\n'.join(lines)

def evidence(report):
 if report.get('status')!='ok':return []
 result=[]
 for i,p in enumerate(reversed(report.get('annual',[])[-2:])):
  # One source per filing: do not cite one filing for facts selected from a different filing.
  grouped={}
  for key,f in p['metrics'].items():
   if not f or 'value' not in f:continue
   grouped.setdefault(f['accession'],[]).append((key,f))
  for _,items in sorted(grouped.items(),key=lambda x:(any(k=='profit' for k,_ in x[1]),any(k=='revenue' for k,_ in x[1]),x[0]),reverse=True)[:2]:
   f=items[0][1];body=f"{report['name']}. SEC {f['form']} filed {f['filed']} ({readable_date(f['filed'])}). Annual period {p['start']} to {p['end']}. In words: {readable_date(p['start'])} to {readable_date(p['end'])}. USD. "
   for k,v in items:
    amount=decimal.Decimal(str(v['value']));millions=format(amount/decimal.Decimal(1000000),'f')
    body+=f" {METRICS[k][0]} = {v['value']} USD; same amount = {millions} million USD (us-gaap:{v['tag']}; fact end {v['end']})."
    if k=='profit' and amount<0:body+=f" Net loss amount = {format(-amount,'f')} USD ({format(-amount/decimal.Decimal(1000000),'f')} million USD)."
   body+=' Market Desk normalized these SEC fact fields; million-USD amounts are exact unit conversions, not verbatim filing quotations. '+NOTICE
   result.append({'id':'S'+str(len(result)+1),'title':'SEC accounts: '+report['name']+' · '+p['end'],'kind':'normalized SEC financial facts','body':body,'url':f['url'],'published':f['filed'],'retrievedAt':report.get('fetchedAt'),'notice':'Selected latest-filed facts. Not complete statements or point-in-time backtest evidence.'})
 return result[:3]

def compare(reports):
 """Common annual dates only; never silently call different fiscal years like-for-like."""
 if not 2<=len(reports)<=3:raise ValueError('Choose two or three companies.')
 common=[]
 for p in reports[0].get('annual',[]):
  matched=[p]
  for report in reports[1:]:
   candidates=[x for x in report.get('annual',[]) if abs((day(x['start'])-day(p['start'])).days)<=7 and abs((day(x['end'])-day(p['end'])).days)<=7 and abs(x['durationDays']-p['durationDays'])<=14]
   if len(candidates)!=1:break
   matched.append(candidates[0])
  if len(matched)==len(reports):common.append(matched)
 aligned=bool(common);selected=common[-1] if common else [r.get('annual',[None])[-1] if r.get('annual') else None for r in reports]
 rows=[]
 for report,p in zip(reports,selected):
  rows.append({'symbol':report.get('symbol'),'name':report.get('name'),'cik':report.get('cik'),'fetchedAt':report.get('fetchedAt'),'period':p})
 return {'aligned':aligned,'rows':rows,'basis':'Matched annual windows within seven days; small 52/53-week differences remain. Inspect each actual date.' if aligned else 'No shared annual reporting window was found. Latest saved annual figures are shown with their dates, without rankings or like-for-like differences.','notice':NOTICE+' Revenue concepts can differ across issuers; inspect the tags. Similar accounting periods do not make different businesses equivalent.'}
