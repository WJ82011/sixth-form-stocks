/* Market Desk v1.6.4 — sourced-chart and uncertainty-only scenario helpers.
   All input prices must be authentic daily bars from the configured historical provider. No generated data
   may ever be mixed into observed price history. Plain JS for offline tests. */
(function(root){
  'use strict';
  const DAY=86400000;
  const POSITIVE=/\b(beat|beats|outperform|raises? guidance|raised guidance|record revenue|strong demand|upgrades?|higher profit|profit rises|growth accelerates|wins? contract|positive outlook)\b/i;
  const NEGATIVE=/\b(miss|misses|cuts? guidance|lowers? guidance|downgrades?|lawsuit|recall|investigation|profit falls|weak demand|restructuring|layoffs|negative outlook)\b/i;
  const bounded=(n,lo,hi)=>Math.max(lo,Math.min(hi,n));
  function normaliseDaily(raw,now=Date.now()){
    if(!Array.isArray(raw))return [];
    const rows=raw.map(x=>({t:Number(x.t),p:Number(x.p)}))
      .filter(x=>Number.isInteger(x.t)&&x.t>946684800000&&x.t<=now+DAY&&Number.isFinite(x.p)&&x.p>0&&x.p<1e9)
      .sort((a,b)=>a.t-b.t);
    const unique=[];
    for(const r of rows){if(unique.length&&unique[unique.length-1].t===r.t)unique[unique.length-1]=r;else unique.push(r)}
    return unique.slice(-5000);
  }
  function chartGapThreshold(range){
    // Session gaps are genuine missing recordings, not zero-valued prices.
    return ({'1H':5*60000,'1D':5*60000,'1W':3.5*DAY,'1M':5*DAY,'3M':10*DAY,'1Y':10*DAY,'6M':10*DAY,'2Y':10*DAY,'5Y':10*DAY,'10Y':10*DAY})[range]||90*60000;
  }
  function chartSegments(points,range){
    const ordered=(Array.isArray(points)?points:[]).filter(x=>Number.isFinite(x?.t)&&Number.isFinite(x?.p)&&x.p>0).slice().sort((a,b)=>a.t-b.t);
    if(!ordered.length)return [];
    const segments=[[ordered[0]]],gap=chartGapThreshold(range);
    for(let i=1;i<ordered.length;i++){
      if(ordered[i].t-ordered[i-1].t>gap)segments.push([]);
      segments[segments.length-1].push(ordered[i]);
    }
    return segments;
  }
  function chartGaps(points,range){
    const segments=chartSegments(points,range),gaps=[];
    for(let i=1;i<segments.length;i++)gaps.push({from:segments[i-1].at(-1).t,to:segments[i][0].t});
    return gaps;
  }
  function describeCoverage(packet){
    if(!packet||typeof packet!=='object')return '';
    const freshness={live:'Live',delayed:'Delayed',saved:'Saved'}[packet.freshness]||'Saved';
    const complete=packet.complete?'complete':'incomplete';
    const when=Number.isFinite(packet.asOf)?new Date(packet.asOf).toLocaleString('en-GB'):'timestamp unavailable';
    const gaps=Number(packet.tradingGapCount)||0;
    const closures=Number(packet.closureCount)||0;
    const parts=[freshness,complete,packet.source||'Source not labelled','latest '+when];
    parts.push(gaps?gaps+' trading-hour gap'+(gaps===1?'':'s'):'no trading-hour gaps');
    if(closures)parts.push(closures+' scheduled closure'+(closures===1?'':'s'));
    if(packet.splitNote)parts.push(packet.splitNote);
    if(gaps&&packet.fillable===false)parts.push('Free feed cannot fill these gaps');
    if(gaps&&packet.fillable)parts.push('Restart asks the free daily feed for supported gaps first');
    return parts.filter(Boolean).join(' · ');
  }
  function coverage(points,from,to){
    const sorted=points.filter(x=>x.t>=from&&x.t<=to).sort((a,b)=>a.t-b.t);
    const span=sorted.length>1?sorted[sorted.length-1].t-sorted[0].t:0;
    return {count:sorted.length,days:span/DAY,first:sorted[0]?.t||null,last:sorted[sorted.length-1]?.t||null};
  }
  function headlineSignal(items,asOf=Date.now()){
    const seen=new Set();let weighted=0,weight=0,used=0,positive=0,negative=0;
    for(const item of Array.isArray(items)?items:[]){
      const ts=Number(item?.datetime)*1000,head=String(item?.headline||'').trim();
      if(!head||!Number.isFinite(ts)||ts>asOf+60000||ts<asOf-7*DAY)continue;
      const key=head.toLowerCase().replace(/\s+/g,' ');if(seen.has(key))continue;seen.add(key);
      const p=POSITIVE.test(head),n=NEGATIVE.test(head);if(!p&&!n)continue;
      const dir=(p?1:0)-(n?1:0),w=Math.exp(-(asOf-ts)/DAY/3);
      weighted+=w*dir;weight+=w;used++;if(dir>0)positive++;else if(dir<0)negative++;
    }
    return {score:weight?bounded(weighted/weight,-1,1):0,used,positive,negative,available:Array.isArray(items)};
  }
  function priceSignals(prices){
    // Every signal uses closes available at the anchor. No future rows,
    // fabricated returns, randomness, or news-derived price targets.
    const logs=[];
    for(let i=1;i<prices.length;i++)logs.push(Math.log(prices[i]/prices[i-1]));
    const mean=n=>{const tail=logs.slice(-Math.min(logs.length,n));return tail.reduce((a,b)=>a+b,0)/tail.length};
    const recent5=mean(5),medium20=mean(20),long60=mean(60);
    // Exponentially weighted volatility; more responsive to new risks, with
    // a floor so a flat historical period never claims zero uncertainty.
    let weighted=0,variance=0;
    for(let i=0;i<logs.length;i++){
      const weight=Math.pow(.965,logs.length-i-1);
      variance+=weight*Math.pow(logs[i]-medium20,2);weighted+=weight;
    }
    const sigma=Math.max(.002,Math.sqrt(variance/Math.max(weighted,1)));
    const volatilityShrink=bounded(.018/(sigma+.008),.25,1);
    return {
      recent5,medium20,long60,sigma,volatilityShrink,
      // The three timescales deliberately decay at DIFFERENT rates. This
      // creates a naturally bending trajectory when trends change, without
      // making up market moves or adding artificial sine/random wiggles.
      long:bounded(.25*long60,-.0008,.0008)*volatilityShrink,
      medium:bounded(.40*medium20,-.0016,.0016)*volatilityShrink,
      fast:bounded(.24*(recent5-medium20),-.0018,.0018)*volatilityShrink
    };
  }
  // Match trend and volatility at earlier anchors. Each match's entire
  // outcome ends before the current anchor, including during walk-forward tests.
  function matchedPaths(prices,days){
    if(prices.length<160)return [];
    const logs=prices.map(Math.log),last=logs.length-1;
    const feature=i=>{
      const drift=(logs[i]-logs[i-20])/20;
      let sum=0;
      for(let j=i-19;j<=i;j++)sum+=(logs[j]-logs[j-1]-drift)**2;
      return [(logs[i]-logs[i-5])/5,drift,(logs[i]-logs[i-60])/60,Math.sqrt(sum/20)];
    };
    const current=feature(last),scale=Math.max(.002,current[3]);
    const candidates=[];
    for(let i=Math.max(60,last-750);i+days<=last-10;i++){
      const sample=feature(i);
      const distance=Math.hypot(...sample.map((v,j)=>(v-current[j])/scale*(j===0?3:j===1?4:j===2?5:1)));
      if(distance<=1.65)candidates.push({i,distance});
    }
    candidates.sort((a,b)=>a.distance-b.distance||b.i-a.i);
    const matches=[];
    for(const entry of candidates){
      // Spread anchors out to limit repeated near-identical matches.
      if(matches.every(i=>Math.abs(i-entry.i)>=Math.max(5,Math.ceil(days/3))))matches.push(entry.i);
      if(matches.length===12)break;
    }
    return matches.length>=8?matches.map(i=>logs.slice(i+1,i+days+1).map(v=>v-logs[i])):[];
  }
  function projectedPath(prices,horizon,signals,paths){
    const spot=prices[prices.length-1],days=bounded(Math.floor(horizon),1,60);
    const rows=[{day:0,price:spot,low:spot,high:spot}];
    let cumulativeLog=0;
    for(let d=1;d<=days;d++){
      const dailyDrift=bounded(
        signals.long*Math.exp(-(d-1)/55)+
        signals.medium*Math.exp(-(d-1)/14)+
        signals.fast*Math.exp(-(d-1)/4),-.0035,.0035);
      cumulativeLog+=dailyDrift;
      let centreLog=cumulativeLog;
      if(paths.length){
        const returns=paths.map(path=>path[d-1]).sort((a,b)=>a-b);
        const mid=Math.floor(returns.length/2);
        const median=returns.length%2?returns[mid]:(returns[mid-1]+returns[mid])/2;
        const influence=.55*signals.sigma*Math.sqrt(d);
        centreLog+=.35*bounded(median-cumulativeLog,-influence,influence);
      }
      const centre=spot*Math.exp(centreLog);
      // Wide illustrative volatility fan, deliberately NOT presented as a
      // statistical 80/95% probability or as empirically calibrated bounds.
      const spread=1.65*signals.sigma*Math.sqrt(d);
      rows.push({day:d,price:centre,low:centre*Math.exp(-spread),high:centre*Math.exp(spread)});
    }
    return rows;
  }
  function model(daily,news=[],asOf=Date.now(),horizon=20){
    const prices=normaliseDaily(daily,asOf).filter(point=>point.t<=asOf);
    if(prices.length<45)return null;
    // Gating prohibits local intraday ticks masquerading as daily bars,
    // and prevents stale history from producing a 'current' forecast.
    if(prices.at(-1).t-prices[0].t<55*DAY)return null;
    if(asOf-prices.at(-1).t>10*DAY)return null;
    const signals=priceSignals(prices.map(x=>x.p));
    const closes=prices.map(x=>x.p),days=bounded(Math.floor(horizon),1,60);
    const paths=matchedPaths(closes,days);
    const rows=projectedPath(closes,days,signals,paths);
    const sentiment=headlineSignal(news,asOf);
    return {anchor:prices.at(-1),rows,drift:Math.log(rows[1].price/rows[0].price),
      sigma:signals.sigma,signals,base:signals.long,momentumContribution:signals.medium+signals.fast,
      // News is shown as factual context only; an unvalidated keyword score
      // should not be allowed to alter a numerical target price.
      newsContribution:0,sentiment,sampleSize:prices.length,method:paths.length?'matched-path-blend':'damped-multi-horizon',matches:paths.length,
      description:paths.length?'Damped trend blended with '+paths.length+' similar historical paths. The volatility fan is illustrative.':'Damped 5/20/60-session trend with an illustrative volatility fan.'};
  }
  function walkForward(daily,days=5){
    const rows=normaliseDaily(daily,Number.MAX_SAFE_INTEGER);
    const horizon=bounded(Math.floor(days),1,60);
    if(rows.length<80+horizon)return null;
    const errors=[],baseline=[],directions=[];
    // Non-overlapping outcomes. Each past model sees ONLY earlier closes,
    // no full-sample future returns and no present-day headline signal.
    for(let end=Math.max(75,rows.length-400);end+horizon<=rows.length;end+=horizon){
      const past=rows.slice(0,end),asOf=past.at(-1).t+DAY;
      const prediction=model(past,[],asOf,horizon);
      if(!prediction)continue;
      const observed=rows[end+horizon-1].p,estimated=prediction.rows[horizon].price,anchor=past.at(-1).p;
      if(!(observed>0&&estimated>0))continue;
      errors.push(Math.abs(estimated-observed)/observed);
      baseline.push(Math.abs(anchor-observed)/observed);
      const actualDirection=Math.sign(observed-anchor),predictedDirection=Math.sign(estimated-anchor);
      if(actualDirection!==0)directions.push(actualDirection===predictedDirection?1:0);
    }
    if(errors.length<5)return null;
    const mean=values=>100*values.reduce((a,b)=>a+b,0)/values.length;
    return {samples:errors.length,modelMAPE:mean(errors),baselineMAPE:mean(baseline),horizon,
      directionAccuracy:directions.length?100*directions.reduce((a,b)=>a+b,0)/directions.length:null,
      beatBaseline:mean(errors)<mean(baseline),newsTested:false};
  }
  const API={normaliseDaily,coverage,describeCoverage,chartSegments,chartGaps,headlineSignal,model,walkForward};
  if(typeof module!=='undefined'&&module.exports)module.exports=API;
  root.ChartResearch=API;
})(typeof window!=='undefined'?window:globalThis);
