/* Public spot trades and closed candles stay separate from the equity workspace. */
const Crypto38=(()=>{
  const names={'BTC-USD':'Bitcoin','ETH-USD':'Ethereum','SOL-USD':'Solana','XRP-USD':'XRP','DOGE-USD':'Dogecoin','ADA-USD':'Cardano','LINK-USD':'Chainlink','AVAX-USD':'Avalanche','LTC-USD':'Litecoin','BCH-USD':'Bitcoin Cash','DOT-USD':'Polkadot','ATOM-USD':'Cosmos','UNI-USD':'Uniswap','AAVE-USD':'Aave','NEAR-USD':'NEAR','SUI-USD':'Sui','HBAR-USD':'Hedera','ICP-USD':'Internet Computer','FIL-USD':'Filecoin','INJ-USD':'Injective','ARB-USD':'Arbitrum','OP-USD':'Optimism','SEI-USD':'Sei','TIA-USD':'Celestia','FET-USD':'Fetch.ai','RENDER-USD':'Render','APT-USD':'Aptos','ENA-USD':'Ethena','POL-USD':'Polygon','SHIB-USD':'Shiba Inu','PEPE-USD':'Pepe','WIF-USD':'dogwifhat','BONK-USD':'Bonk','XLM-USD':'Stellar'};
  const labels={'1H':'1 hour','1D':'24 hours','1W':'1 week','1M':'30 days','1Y':'1 year'};
  const money=new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'});
  const date=new Intl.DateTimeFormat('en-GB',{dateStyle:'medium',timeStyle:'short',timeZone:'UTC'});
  const shortTime=new Intl.DateTimeFormat('en-GB',{hour:'2-digit',minute:'2-digit',timeZone:'UTC'});
  const shortDate=new Intl.DateTimeFormat('en-GB',{day:'numeric',month:'short',timeZone:'UTC'});
  const byId=id=>document.getElementById(id);
  const usablePrice=p=>Number.isFinite(p)&&p>0&&p<=1e9;
  let product='BTC-USD',range='1D',active=false,chart=null,quote=null,stream=null,board=null;
  let chartRequest=0,quoteRequest=0,retryTimer=0,quoteTimer=0,chartTimer=0,frame=0,attempt=0;
  let livePoints=[],streamHasTrade=false;
  const visible=()=>active&&!document.hidden;

  function acceptTick(message, expected, now){
    if(message?.type!=='ticker'||message.product_id!==expected||!['number','string'].includes(typeof message.price)||typeof message.time!=='string')return null;
    const price=Number(message.price),time=Date.parse(message.time);
    return usablePrice(price)&&Number.isFinite(time)&&time>=now-60000&&time<=now+5000
      ?{price,time,kind:'stream'}:null;
  }

  function currentQuote(){
    const last=livePoints.at(-1);
    if(last&&(!quote||last.t>=quote.time)){
      return {price:last.p,time:last.t,kind:streamHasTrade&&stream?.readyState===1?'stream':'saved'};
    }
    return quote;
  }

  function scheduleDraw(){
    if(frame||!visible())return;
    frame=requestAnimationFrame(()=>{frame=0;render();});
  }

  function render(){
    const q=currentQuote();
    const age=q?Date.now()-q.time:Infinity;
    byId('crypto38-price').textContent=q?money.format(q.price):'—';
    byId('crypto38-source').textContent=q
      ?(q.kind==='stream'&&age<=30000?'Live Coinbase Exchange trade':age<=30000&&q.kind==='snapshot'?'Latest Coinbase snapshot':'Saved Coinbase trade')
        +' · '+date.format(q.time)+' UTC'
      :'Waiting for a Coinbase Exchange price';
    const closes=chart?.points||[];
    if(closes.length>=2){
      const first=closes[0],last=closes.at(-1);
      const change=(last.p/first.p-1)*100;
      byId('crypto38-change').textContent=(change>0?'+':'')+change.toFixed(2)+'% across displayed closes';
      byId('crypto38-dates').textContent=date.format(first.t)+' → '+date.format(last.t)+' UTC';
    }else{
      byId('crypto38-change').textContent='Change needs two recorded closes';
      byId('crypto38-dates').textContent='';
    }
    plot(closes);
  }

  function plot(closes){
    const canvas=byId('crypto38-canvas'),width=canvas.clientWidth,height=canvas.clientHeight;
    if(!width||!height)return;
    const scale=Math.min(window.devicePixelRatio||1,2);
    if(canvas.width!==Math.round(width*scale))canvas.width=Math.round(width*scale);
    if(canvas.height!==Math.round(height*scale))canvas.height=Math.round(height*scale);
    const ctx=canvas.getContext('2d');
    ctx.setTransform(scale,0,0,scale,0,0);
    ctx.clearRect(0,0,width,height);
    const light=document.documentElement.dataset.theme==='light';
    ctx.font='11px -apple-system, sans-serif';
    ctx.fillStyle=light?'#394763':'#b1bed5';
    if(!closes.length){
      ctx.textAlign='center';
      ctx.fillText('Waiting for saved or downloaded prices',width/2,height/2);
      return;
    }
    const lastClose=closes.at(-1).t;
    const live=livePoints.filter(point=>point.t>lastClose&&point.t>=chart.end&&point.t<=Date.now()+5000);
    const points=[...closes,...live];
    const prices=points.map(point=>point.p);
    const low=Math.min(...prices),high=Math.max(...prices),padding=Math.max((high-low)*.08,high*.0005);
    const from=chart.start,to=Math.max(chart.end,points.at(-1).t);
    const usableWidth=Math.max(1,width-83),plotHeight=height-45;
    const x=t=>10+(t-from)/Math.max(1,to-from)*usableWidth;
    const y=p=>14+(high+padding-p)/(high-low+2*padding)*plotHeight;
    ctx.textAlign='right';
    for(const p of [high,(high+low)/2,low]){
      const level=y(p);
      ctx.strokeStyle=light?'#d9e0eb':'#26344c';
      ctx.beginPath();ctx.moveTo(10,level);ctx.lineTo(width-74,level);ctx.stroke();
      ctx.fillText(money.format(p),width-5,level+3);
    }
    function line(rows,gap,colour){
      ctx.lineWidth=2;ctx.strokeStyle=colour;ctx.beginPath();
      let previous=null;
      for(const row of rows){
        if(previous===null||row.t-previous>gap)ctx.moveTo(x(row.t),y(row.p));
        else ctx.lineTo(x(row.t),y(row.p));
        previous=row.t;
      }
      ctx.stroke();
      for(let i=0;i<rows.length;i++){
        const row=rows[i],before=rows[i-1],after=rows[i+1];
        if((!before||row.t-before.t>gap)&&(!after||after.t-row.t>gap)){
          ctx.fillStyle=colour;ctx.beginPath();ctx.arc(x(row.t),y(row.p),2,0,Math.PI*2);ctx.fill();
        }
      }
    }
    line(closes,chart.interval*1.05,light?'#2756a8':'#83a6ff');
    line(live,15000,light?'#087c66':'#59dfb6');
    const axis=range==='1H'||range==='1D'?shortTime:shortDate;
    ctx.fillStyle=light?'#394763':'#b1bed5';
    for(const [stamp,align] of [[from,'left'],[(from+to)/2,'center'],[to,'right']]){
      ctx.textAlign=align;
      ctx.fillText(axis.format(stamp),x(stamp),height-9);
    }
  }

  async function loadChart(){
    const id=++chartRequest,expectedProduct=product,expectedRange=range;
    try{
      const response=await api('/api/v3/crypto-chart?product='+product+'&range='+range);
      if(id!==chartRequest||!visible()||product!==expectedProduct||range!==expectedRange)return;
      chart=response.points?.length?response:null;
      const coverageText=chart?.coverage&&typeof ChartResearch!=='undefined'?ChartResearch.describeCoverage(chart.coverage):'';
      byId('crypto38-status').textContent=chart
        ?chart.points.length+' of '+chart.expected+' completed candles · '+(response.status==='saved'?'Saved copy · checked ':'Checked ')+date.format(chart.fetchedAt)+' UTC'+(coverageText?' · '+coverageText:'')
        :'Coinbase history is temporarily unavailable. Try again when connected.';
    }catch{
      if(id!==chartRequest||!visible())return;
      byId('crypto38-status').textContent='History could not be updated. Check the local server and connection.';
    }
    scheduleDraw();
  }

  async function loadQuote(){
    const id=++quoteRequest,expected=product;
    try{
      const response=await api('/api/v3/crypto-quote?product='+expected);
      if(id!==quoteRequest||!visible()||expected!==product)return;
      if(usablePrice(response.price)&&Number.isFinite(response.time)&&(!quote||response.time>=quote.time)){
        quote={price:response.price,time:response.time,kind:response.status==='saved'?'saved':'snapshot'};
      }
    }catch{/* Keep the last dated observation visible. */}
    scheduleDraw();
  }

  function disconnect(){
    clearTimeout(retryTimer);
    const old=stream;stream=null;streamHasTrade=false;
    if(old)old.close();
  }

  function connect(){
    if(!visible()||typeof WebSocket==='undefined')return;
    const expected=product;
    let socket;
    try{socket=new WebSocket('wss://ws-feed.exchange.coinbase.com');}
    catch{return;}
    stream=socket;streamHasTrade=false;
    socket.addEventListener('open',()=>{
      if(socket===stream)socket.send(JSON.stringify({type:'subscribe',product_ids:[expected],channels:['ticker']}));
    });
    socket.addEventListener('message',event=>{
      if(socket!==stream||!visible())return;
      let message;
      try{message=JSON.parse(event.data);}catch{return;}
      const tick=acceptTick(message,expected,Date.now());
      if(!tick)return;
      const last=livePoints.at(-1);
      if(last&&tick.time<last.t)return;
      const point={t:tick.time,p:tick.price};
      if(last&&Math.floor(last.t/1000)===Math.floor(point.t/1000))livePoints[livePoints.length-1]=point;
      else livePoints.push(point);
      if(livePoints.length>400)livePoints.shift();
      streamHasTrade=true;attempt=0;
      scheduleDraw();
    });
    socket.addEventListener('close',()=>{
      if(socket!==stream)return;
      stream=null;scheduleDraw();
      if(visible())retryTimer=setTimeout(connect,Math.min(45000,2000*2**Math.min(attempt++,5)));
    });
  }

  function stop(){
    active=false;chartRequest++;quoteRequest++;
    clearInterval(quoteTimer);clearInterval(chartTimer);disconnect();
  }

  function start(){
    stop();active=true;attempt=0;
    if(!visible())return;
    loadChart();loadQuote();loadBoard();connect();
    quoteTimer=setInterval(loadQuote,12000);
    chartTimer=setInterval(loadChart,120000);
  }

  function choose(next){
    if(!names[next]||next===product)return;
    product=next;chart=null;quote=null;livePoints=[];
    byId('crypto38-name').textContent=names[product];
    byId('crypto38-pair').textContent=product+' · USD spot';
    byId('crypto38-status').textContent='Reading prices…';
    document.querySelectorAll('[data-crypto-pair]').forEach(button=>{
      button.setAttribute('aria-pressed',String(button.dataset.cryptoPair===product));
    });
    start();paintBoard();scheduleDraw();
  }

  function selectRange(next){
    if(!labels[next]||range===next)return;
    range=next;chart=null;
    document.querySelectorAll('[data-crypto-range]').forEach(button=>{
      button.setAttribute('aria-pressed',String(button.dataset.cryptoRange===range));
    });
    byId('crypto38-period').textContent=labels[range];
    byId('crypto38-status').textContent='Reading '+labels[range]+' history…';
    loadChart();scheduleDraw();
  }

  function favourites(){
    try{return JSON.parse(localStorage.getItem('md-crypto-favourites')||'[]').filter(item=>names[item]);}
    catch{return [];}
  }
  function paintBoard(){
    const box=byId('crypto38-assets'),heat=byId('crypto38-heat');
    if(!box)return;
    const query=(byId('crypto38-search')?.value||'').trim().toLowerCase();
    const onlyFav=byId('crypto38-favourites')?.getAttribute('aria-pressed')==='true';
    const sort=byId('crypto38-sort')?.value||'name';
    const rows=(board?.rows||Object.keys(names).map(id=>({product:id,name:names[id]}))).filter(row=>{
      const text=(row.name+' '+row.product).toLowerCase();
      return text.includes(query)&&(!onlyFav||favourites().includes(row.product));
    });
    const value=row=>sort==='24h'?row.change24h:sort==='7d'?row.change7d:row.name;
    rows.sort((a,b)=>{
      const left=value(a),right=value(b);
      if(left==null)return 1;if(right==null)return -1;
      return sort==='name'?String(left).localeCompare(String(right)):right-left;
    });
    const pct=n=>n==null?'Not saved':(n>0?'+':'')+n.toFixed(2)+'%';
    box.innerHTML=rows.map(row=>'<button class="ghost-btn" type="button" data-crypto-pair="'+row.product+'" aria-pressed="'+(row.product===product)+'">'+row.name+' · '+row.product.split('-')[0]+'</button>').join('')||'<p class="crypto38-foot">No matching market.</p>';
    if(heat)heat.innerHTML=rows.map(row=>'<button type="button" data-crypto-tile="'+row.product+'"><strong>'+row.name+'</strong><span>'+pct(sort==='7d'?row.change7d:row.change24h)+'</span></button>').join('');
    box.querySelectorAll('[data-crypto-pair]').forEach(button=>button.addEventListener('click',()=>choose(button.dataset.cryptoPair)));
    heat?.querySelectorAll('[data-crypto-tile]').forEach(button=>button.addEventListener('click',()=>{choose(button.dataset.cryptoTile);selectRange(sort==='7d'?'1W':'1D');}));
    const gaps=(board?.rows||[]).reduce((sum,row)=>sum+(row.coverage?.tradingGapCount||0),0);
    const note=byId('crypto38-coverage');
    if(note)note.textContent='Coinbase Exchange · USD · UTC · 24 hours, seven days'+(gaps?' · '+gaps+' saved gap'+(gaps===1?'':'s')+' still visible':'');
    const follow=byId('crypto38-follow');
    if(follow)follow.textContent=(board?.followed||[]).includes(product)?'Remove from followed':'Follow this market';
    const star=byId('crypto38-star');
    if(star)star.textContent=favourites().includes(product)?'Remove favourite':'Add favourite';
  }
  async function loadBoard(){
    try{board=await api('/api/v3/crypto-board');}catch{board=board||{rows:[]};}
    paintBoard();
  }
  async function toggleFollow(){
    const current=new Set(board?.followed||[]);
    if(current.has(product))current.delete(product);else current.add(product);
    await fetch('/api/v3/crypto-follow',{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify({products:[...current]})});
    await loadBoard();
  }
  async function saveAlert(){
    const target=Number(byId('crypto38-target').value);
    const note=byId('crypto38-alert-note');
    if(!(target>0)){note.textContent='Enter a USD price above zero.';return;}
    const response=await fetch('/api/alerts',{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify({action:'create',symbol:product,direction:byId('crypto38-direction').value,target,unit:'USD',kind:'level'})});
    const body=await response.json();
    note.textContent=body.error||('Saved a '+product+' alert at '+target+' USD. Evidence stays with the alert record.');
  }
  function setup(){
    paintBoard();
    document.querySelectorAll('[data-crypto-range]').forEach(button=>button.addEventListener('click',()=>selectRange(button.dataset.cryptoRange)));
    byId('crypto38-refresh').addEventListener('click',()=>{loadChart();loadQuote();loadBoard();});
    byId('crypto38-search')?.addEventListener('input',paintBoard);
    byId('crypto38-sort')?.addEventListener('change',paintBoard);
    byId('crypto38-favourites')?.addEventListener('click',()=>{
      const button=byId('crypto38-favourites');
      button.setAttribute('aria-pressed',String(button.getAttribute('aria-pressed')!=='true'));
      paintBoard();
    });
    byId('crypto38-star')?.addEventListener('click',()=>{
      const next=favourites().filter(item=>item!==product);
      if(!favourites().includes(product))next.push(product);
      localStorage.setItem('md-crypto-favourites',JSON.stringify(next));
      paintBoard();
    });
    byId('crypto38-follow')?.addEventListener('click',()=>{toggleFollow().catch(()=>{});});
    byId('crypto38-alert')?.addEventListener('click',()=>{saveAlert().catch(()=>{byId('crypto38-alert-note').textContent='The alert was not saved.';});});
    document.addEventListener('visibilitychange',()=>{if(E.view==='crypto'){if(document.hidden)stop();else start();}});
    window.addEventListener('resize',scheduleDraw);
    byId('theme-toggle')?.addEventListener('click',scheduleDraw);
  }

  if(typeof document!=='undefined')document.addEventListener('DOMContentLoaded',setup);
  return {open:start,close:stop,acceptTick};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=Crypto38;
