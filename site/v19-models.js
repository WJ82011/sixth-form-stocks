/* Market Desk v1.9: deterministic analytics from authenticated historical data or explicit user assumptions. */
(function(root){'use strict';
 const finite=n=>typeof n==='number'&&Number.isFinite(n);
 const round=(n,d=4)=>Math.round((n+Number.EPSILON)*10**d)/10**d;
 const nvalid=(n,lo,hi)=>finite(n)&&n>=lo&&n<=hi;
 function indicators(raw){
  if(!Array.isArray(raw))return [];
  const rows=raw.map(x=>({t:Number(x.t),close:Number(x.p)})).filter(x=>finite(x.t)&&finite(x.close)&&x.close>0).sort((a,b)=>a.t-b.t);
  const clean=[];for(const x of rows){if(clean.length&&clean.at(-1).t===x.t)clean[clean.length-1]=x;else clean.push(x)}
  let gain=0,loss=0;
  return clean.map((x,i)=>{
   const arr=clean.slice(0,i+1).map(y=>y.close);
   const sma=n=>i>=n-1?arr.slice(-n).reduce((a,b)=>a+b,0)/n:null;
   const avg20=sma(20);
   const sigma20=avg20!==null?Math.sqrt(arr.slice(-20).reduce((a,b)=>a+(b-avg20)**2,0)/20):null;
   // Wilder RSI (14) seeded from the first 14 changes, then smoothed.
   if(i>0){const diff=arr[i]-arr[i-1],g=Math.max(0,diff),l=Math.max(0,-diff);
    if(i<=14){gain+=g;loss+=l;if(i===14){gain/=14;loss/=14}}
    else{gain=(gain*13+g)/14;loss=(loss*13+l)/14}}
   const rsi=i<14?null:loss===0?(gain===0?50:100):100-(100/(1+gain/loss));
   return {t:x.t,close:x.close,sma20:avg20,sma50:sma(50),rsi14:rsi,
    bbHigh:avg20===null?null:avg20+2*sigma20,bbLow:avg20===null?null:avg20-2*sigma20};
  });
 }
 function dcf(input){
  const f=Number(input.fcf),growth=Number(input.growth)/100,discount=Number(input.discount)/100,terminal=Number(input.terminal)/100,
   shares=Number(input.shares),netDebt=Number(input.netDebt),years=5;
  if(!nvalid(f,0,1e12)||!nvalid(shares,.000001,1e12)||!nvalid(netDebt,-1e12,1e12)||
     !nvalid(growth,-.8,1)||!nvalid(discount,.01,.5)||!nvalid(terminal,-.05,.12)||discount<=terminal+.005){
    throw Error('Enter valid assumptions. Discount rate must exceed terminal growth by at least 0.5 percentage points.');
  }
  let cash=f,pv=0;const forecast=[];
  for(let year=1;year<=years;year++){
   cash*=1+growth;
   const discounted=cash/(1+discount)**year;
   pv+=discounted;forecast.push({year,fcf:cash,presentValue:discounted});
  }
  const terminalValue=cash*(1+terminal)/(discount-terminal),pvTerminal=terminalValue/(1+discount)**years;
  const enterprise=pv+pvTerminal,equity=enterprise-netDebt,perShare=equity/shares;
  if(![enterprise,equity,perShare].every(finite))throw Error('The assumptions produce an invalid result.');
  return {forecast,pvOperations:pv,pvTerminal,enterprise,equity,perShare,terminalShare:enterprise>0?pvTerminal/enterprise:null,years};
 }
 function sensitivity(input){
  const discounts=[-2,0,2].map(v=>Number(input.discount)+v);
  const growths=[-2,0,2].map(v=>Number(input.growth)+v);
  return {discounts,growths,values:discounts.map(discount=>growths.map(growth=>{
    try{return dcf({...input,discount,growth}).perShare}catch{return null}
  }))};
 }
 function portfolio(capital,transactions,prices={}){
  const start=Number(capital);
  if(!nvalid(start,1,1e9))throw Error('Set initial virtual cash between $1 and $1 billion.');
  if(!Array.isArray(transactions)||transactions.length>250)throw Error('Maximum 250 paper trades.');
  const holdings={},ledger=[];let cash=start;
  for(const t of transactions){
   const sym=String(t.symbol||'').toUpperCase(),side=t.side,qty=Number(t.qty),price=Number(t.price);
   if(!/^[A-Z0-9][A-Z0-9.\-:_]{0,23}$/.test(sym)||!['BUY','SELL'].includes(side)||!nvalid(qty,.000001,1e8)||!nvalid(price,.000001,1e9))throw Error('Invalid paper trade.');
   const h=holdings[sym]||{symbol:sym,qty:0,cost:0,realized:0};const value=qty*price;
   if(side==='BUY'){
    if(cash+1e-7<value)throw Error('Not enough virtual cash for '+sym+'.');
    cash-=value;h.cost+=value;h.qty+=qty;
   }else{
    if(qty>h.qty+1e-8)throw Error('Cannot sell more virtual shares than owned for '+sym+'.');
    const avg=h.qty>0?h.cost/h.qty:0;
    h.cost-=avg*qty;h.qty-=qty;h.realized+=(price-avg)*qty;cash+=value;
    if(h.qty<1e-8){h.qty=0;h.cost=0}
   }
   holdings[sym]=h;ledger.push({...t,symbol:sym,side,qty,price,value});
  }
  let markedValue=cash;let missing=0;
  const positions=Object.values(holdings).filter(h=>h.qty>1e-8).map(h=>{
   const mark=prices[h.symbol];const markPrice=mark&&nvalid(Number(mark.price),.000001,1e9)?Number(mark.price):null;
   if(markPrice===null)missing++;else markedValue+=markPrice*h.qty;
   return {...h,avgCost:h.cost/h.qty,price:markPrice,marketValue:markPrice===null?null:markPrice*h.qty,
    unrealized:markPrice===null?null:markPrice*h.qty-h.cost,priceSource:mark?.source||null,priceTime:mark?.time||null};
  });
  return {capital:start,cash,positions,transactions:ledger,missing,totalValue:missing?null:markedValue,pnl:missing?null:markedValue-start};
 }
 const API={indicators,dcf,sensitivity,portfolio};
 if(typeof module!=='undefined'&&module.exports)module.exports=API;
 root.MD19Models=API;
})(typeof window!=='undefined'?window:globalThis);
