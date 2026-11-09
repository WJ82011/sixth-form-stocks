/* Exchange schedule, not streaming proof. Published NYSE/Nasdaq 2026–2028 calendars.
   No external calls, no dependency on Mac local timezone. Special closures can occur
   without warning; this is the *scheduled regular* equity session only.
   https://www.nyse.com/trade/hours-calendars
   https://nasdaqtrader.com/Trader.aspx?id=Calendar */
(function(root){
  'use strict';
  const US_CLOSED={
    2026:['01-01','01-19','02-16','04-03','05-25','06-19','07-03','09-07','11-26','12-25'],
    2027:['01-01','01-18','02-15','03-26','05-31','06-18','07-05','09-06','11-25','12-24'],
    2028:['01-17','02-21','04-14','05-29','06-19','07-04','09-04','11-23','12-25']
  };
  const US_EARLY={2026:['11-27','12-24'],2027:['11-26'],2028:['07-03','11-24']};
  const ET_FORMAT=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit',weekday:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
  function usTicker(symbol){
    const s=String(symbol||'').toUpperCase();
    // Exchange-prefixed, non-US suffix, currencies, and crypto cannot be safely
    // assigned NYSE/Nasdaq hours from their ticker alone.
    if(/[:\-_]/.test(s)||/\.(?:L|TO|V|PA|DE|MI|AS|SW|HK|T|AX|SS|SZ|KS|KQ|ST|OL|CO|HE|BR|WA|MC|LS|TA|SI|NS|BO)$/.test(s))return false;
    return /^[A-Z]{1,5}(?:\.[AB])?$/.test(s);
  }
  function marketSessionFor(symbol,date=new Date()){
    const base={exchange:'US equities',source:'NYSE / Nasdaq published schedule',hours:'09:30–16:00 America/New_York',isSchedule:true};
    if(!usTicker(symbol))return {state:'unknown',label:'HOURS UNKNOWN',detail:'Market venue cannot be verified from this ticker. No open/closed claim is made.',isOpen:false,isSchedule:false};
    const p={};for(const part of ET_FORMAT.formatToParts(date)){if(part.type!=='literal')p[part.type]=part.value}
    const year=Number(p.year),md=p.month+'-'+p.day,minutes=Number(p.hour)*60+Number(p.minute);
    if(!Object.hasOwn(US_CLOSED,year))return {state:'unknown',label:'HOURS UNKNOWN',detail:'A published exchange calendar is not bundled for '+year+'.',isOpen:false,isSchedule:false};
    if(['Sat','Sun'].includes(p.weekday))return {...base,state:'closed',label:'MARKET CLOSED',detail:'Weekend · US regular equity session is closed',isOpen:false};
    if(US_CLOSED[year].includes(md))return {...base,state:'closed',label:'MARKET CLOSED',detail:'US exchange holiday · regular session closed',isOpen:false};
    const early=US_EARLY[year].includes(md),close=early?13*60:16*60;
    if(minutes>=9*60+30&&minutes<close)return {...base,state:'open',label:'MARKET OPEN',detail:'Scheduled regular US equity session'+(early?' · early close 13:00 ET':''),isOpen:true};
    if(minutes>=4*60&&minutes<9*60+30)return {...base,state:'premarket',label:'PRE-MARKET',detail:'Before regular session · availability of extended-hours trades depends on your data plan',isOpen:false};
    if(minutes>=close&&minutes<20*60)return {...base,state:'afterhours',label:'AFTER-HOURS',detail:'Regular session ended'+(early?' early at 13:00 ET':' at 16:00 ET')+' · extended-hours coverage may vary',isOpen:false};
    return {...base,state:'closed',label:'MARKET CLOSED',detail:'Outside published regular and extended US equity sessions',isOpen:false};
  }
  root.marketSessionFor=marketSessionFor;
  if(typeof module!=='undefined'&&module.exports)module.exports={marketSessionFor,usTicker};
})(typeof globalThis==='object'?globalThis:this);
