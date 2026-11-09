/* Server-owned alert state. This module never polls a market-data provider. */
const PriceAlerts=(()=>{
'use strict';
let data=null,pending=null,ready=false,editing='',known=null,listKey='',historyKey='',pickerKey='',saving=false,historyPage=0;
const $=id=>document.getElementById(id),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const stamp=t=>Number.isFinite(t)?new Date(t).toLocaleString('en-GB',{timeZoneName:'short'}):'Not yet';
const number=v=>Number(v).toLocaleString('en-GB',{maximumSignificantDigits:12});
const label=a=>`${a.direction==='above'?'At or above':'At or below'} ${number(a.target)} ${a.unit}`;
const unit=sym=>typeof DIRECTORY_BY_SYMBOL!=='undefined'&&DIRECTORY_BY_SYMBOL[sym]?.currency==='USD'?'USD':'provider units';
async function request(body){const options=body?{method:'POST',headers:{'Content-Type':'application/json','X-MD-Request':'1'},body:JSON.stringify(body)}:{};const r=await fetch('/api/alerts',{...options,cache:'no-store'});let d;try{d=await r.json()}catch{throw Error('The local alerts service did not return a valid response.')}if(!r.ok||d.error)throw Error(d.error||'Could not load alerts.');return d;}
function feedback(message){$('alerts-feedback').textContent=message;}
function populate(){
 const key=JSON.stringify([E.watch,editing]);if(key===pickerKey)return;pickerKey=key;
 const box=$('alerts-symbol'),current=box.value,edit=data?.alerts.find(a=>a.id===editing),symbols=[...new Set([...E.watch,...(edit?[edit.symbol]:[])])];
 box.innerHTML=symbols.length?symbols.map(s=>`<option value="${esc(s)}">${esc(s)} · ${esc(safeName(s))}${E.watch.includes(s)?'':' (not watched)'}</option>`).join(''):'<option value="">Add a stock to your watchlist first</option>';
 box.value=symbols.includes(current)?current:edit?.symbol||symbols[0]||'';$('alerts-submit').disabled=!symbols.length;showUnit();
}
function showUnit(){const s=$('alerts-symbol').value;$('alerts-unit').textContent=s?'Target in '+unit(s)+'. Use the same units as the stock’s quoted price. No currency conversion.':'Add a stock in Stock Browser to create an alert.';}
function monitoring(){
 if(!data)return;
 const armed=data.alerts.filter(a=>a.status==='armed'),watched=armed.filter(a=>E.watch.includes(a.symbol)),stocks=new Set(watched.map(a=>a.symbol)),recent=new Set(watched.filter(a=>a.last_received&&Date.now()-a.last_received<300000).map(a=>a.symbol));let title;
 if(!armed.length)title='No armed alerts · add or re-arm a target to begin';
 else if(!stocks.size)title='Regular checks are off · your armed stocks are not on the watchlist';
 else if(!E.configured&&!E.wsOpen)title='Waiting for a data connection · no new prices are being checked here';
 else if(typeof navigator!=='undefined'&&navigator.onLine===false)title='Browser offline · monitoring is waiting for new data';
 else if(E.lastQuoteError&&!E.wsOpen&&!recent.size)title='Price checks are failing · waiting for a working connection';
 else title=recent.size?'Recent prices received for '+recent.size+' of '+stocks.size+' watched alert stocks':'Waiting for a new, recent price after arming';
 $('alerts-monitor-title').textContent=title;
 $('alerts-monitor-detail').textContent='Keep Market Desk open and connected. Only newly received prices no more than five minutes old can trigger. During sleep, closure or a disconnect, missed moves are not recorded or checked later.';
 document.querySelectorAll('[data-alert-monitor]').forEach(node=>{const a=data.alerts.find(x=>x.id===node.dataset.alertMonitor);if(!a)return;node.textContent=a.status==='paused'?'Paused by you. Re-arm to start a new check.':a.status==='triggered'?'Triggered once. Re-arm when you want to monitor this target again.':!E.watch.includes(a.symbol)?'Not on your watchlist · regular price checks are off.':a.last_received?'Last qualifying price: '+number(a.last_price)+' '+a.unit+' · recorded '+stamp(a.last_ts)+' · received '+stamp(a.last_received):'Waiting for a new price dated after '+stamp(a.armed_at)+'.';});
}
function render(){
 if(!data)return;populate();
 const counts={armed:0,paused:0,triggered:0};data.alerts.forEach(a=>counts[a.status]++);
 $('alerts-summary').innerHTML=[['Armed targets',counts.armed],['Paused targets',counts.paused],['Triggered targets',counts.triggered],['Saved history records',data.events.length]].map(([name,count])=>`<article><span>${esc(name)}</span><strong>${count}</strong></article>`).join('');
 const badge=$('alerts-nav-count');badge.textContent=String(counts.triggered);badge.hidden=counts.triggered===0;badge.setAttribute('aria-label',counts.triggered+' triggered alerts');
 const filter=$('alerts-filter').value||'all',key=JSON.stringify([data.alerts.map(a=>[a.id,a.symbol,a.direction,a.target,a.unit,a.status,a.arm]),filter,E.watch]);
 if(key!==listKey){listKey=key;const rows=data.alerts.filter(a=>filter==='all'||a.status===filter);$('alerts-list').innerHTML=rows.length?rows.map(a=>`<article class="alert-card"><div class="alert-card-head"><div><strong>${esc(a.symbol)} · ${esc(safeName(a.symbol))}</strong><h3>${esc(label(a))}</h3></div><span class="alert-state alert-state-${esc(a.status)}">${esc(a.status==='armed'?'Armed':a.status==='paused'?'Paused':'Triggered')}</span></div><p data-alert-monitor="${esc(a.id)}"></p><div class="alert-card-actions">${a.status==='armed'?`<button class="ghost-btn" type="button" data-alert-action="pause" data-alert-id="${esc(a.id)}">Pause</button>`:`<button class="ghost-btn" type="button" data-alert-action="rearm" data-alert-id="${esc(a.id)}">Re-arm</button>`}<button class="ghost-btn" type="button" data-alert-action="edit" data-alert-id="${esc(a.id)}">Edit target</button><button class="ghost-btn" type="button" data-alert-action="delete" data-alert-id="${esc(a.id)}">Delete alert</button>${!E.watch.includes(a.symbol)?`<button class="ghost-btn" type="button" data-add="${esc(a.symbol)}" data-name="${esc(safeName(a.symbol))}">Add to watchlist</button>`:''}</div></article>`).join(''):'<div class="alerts-empty"><h3>No '+(filter==='all'?'saved':esc(filter))+' alerts yet</h3><p>Choose a watched stock and set a target. Alerts trigger once, then wait for you to re-arm them.</p><button type="button" class="ghost-btn" data-market-tab-link="explore">Explore stocks ↗</button></div>';}
 const pages=Math.max(1,Math.ceil(data.events.length/25));historyPage=Math.max(0,Math.min(historyPage,pages-1));$('alerts-history-page').textContent='Page '+(historyPage+1)+' of '+pages+' · '+data.events.length+' saved records';$('alerts-history-prev').disabled=historyPage===0;$('alerts-history-next').disabled=historyPage+1>=pages;
 const hkey=JSON.stringify([historyPage,data.events]);if(hkey!==historyKey){historyKey=hkey;$('alerts-history').innerHTML=data.events.length?data.events.slice(historyPage*25,(historyPage+1)*25).map(e=>`<article class="alert-event"><div><strong>${esc(e.symbol)} · ${esc(label(e))}</strong><h3>Observed ${esc(number(e.price))} ${esc(e.unit)}</h3><span>${esc(e.source==='finnhub_quote'?'Finnhub price quote':'Finnhub trade with a reported size above zero')}</span></div><div><p>Price recorded: ${esc(stamp(e.price_ts))}</p><p>Received by this app: ${esc(stamp(e.received_at))}</p><small>Trigger #${e.id} · arming ${e.arm}. This is an observed match, not the exact time a target was crossed.</small></div></article>`).join(''):'<div class="alerts-empty">No alerts have triggered. When one does, its actual price and times will appear here.</div>';}
 monitoring();
}
function apply(d){
 if(!d||!Number.isInteger(d.revision)||!Array.isArray(d.alerts)||!Array.isArray(d.events))throw Error('The local alerts response is incomplete.');
 if(data&&d.revision<data.revision)return;
 if(known===null)known=new Set(d.events.map(e=>e.id));else{const fresh=d.events.filter(e=>!known.has(e.id));if(fresh.length){const latest=fresh[0];toast(fresh.length===1?'Price alert: '+latest.symbol+' observed '+number(latest.price)+' '+latest.unit: fresh.length+' price alerts triggered. Open Price Alerts to see the records.');}known=new Set(d.events.map(e=>e.id));}
 data=d;render();
}
async function refresh(){if(pending)return pending;pending=(async()=>{try{apply(await request());}catch(e){$('alerts-monitor-title').textContent='Alerts service unavailable · status cannot be confirmed';$('alerts-monitor-detail').textContent=e.message+' Showing the last saved results, if any.';}finally{pending=null;}})();return pending;}
function cancel(){editing='';pickerKey='';$('alerts-form-title').textContent='Create an alert';$('alerts-submit').textContent='Save and arm alert';$('alerts-cancel').hidden=true;$('alerts-target').value='';$('alerts-direction').value='above';populate();}
async function submit(e){
 e.preventDefault();if(saving)return;const symbol=$('alerts-symbol').value,target=Number($('alerts-target').value),direction=$('alerts-direction').value;
 if(!symbol||(!editing&&!E.watch.includes(symbol))){feedback('Add this stock to your watchlist first.');return;}
 if(!Number.isFinite(target)||target<=0||target>1e9){feedback('Enter a target price above zero and no more than 1 billion.');return;}
 const button=$('alerts-submit');saving=true;button.disabled=true;
 try{const result=await request({action:editing?'update':'create',...(editing?{id:editing}:{}),symbol,target,direction,unit:unit(symbol)});apply(result);cancel();feedback('Alert saved. New qualifying prices can trigger it; check its current status below.');}
 catch(error){feedback(error.message);}finally{saving=false;button.disabled=!$('alerts-symbol').value;}
}
async function action(e){const button=e.target.closest('[data-alert-action]');if(!button)return;const id=button.dataset.alertId,a=data?.alerts.find(x=>x.id===id);if(!a)return;const name=button.dataset.alertAction;
 if(name==='edit'){editing=id;pickerKey='';populate();$('alerts-symbol').value=a.symbol;$('alerts-direction').value=a.direction;$('alerts-target').value=String(a.target);showUnit();$('alerts-form-title').textContent='Edit and re-arm target';$('alerts-submit').textContent='Save changes and re-arm';$('alerts-cancel').hidden=false;$('alerts-target').focus();feedback('Saving changes starts a new arming. Existing trigger history is kept.');return;}
 if(name==='delete'&&!window.confirm('Delete this alert? Its trigger history will stay saved.'))return;
 button.disabled=true;try{apply(await request({action:name,id}));if(editing===id)cancel();feedback(name==='delete'?'Alert deleted. Its trigger history is kept.':name==='pause'?(data.alerts.find(x=>x.id===id)?.status==='paused'?'Alert paused.':'This alert has already triggered. Re-arm it to start again.'):'Alert re-armed. Check its current status below.');}catch(error){feedback(error.message);button.disabled=false;}
}
function download(){if(!data){feedback('Load your alerts first.');return;}const b=new Blob([JSON.stringify({format:'MarketDesk-Alert-Records',version:1,exportedAt:new Date().toISOString(),...data},null,2)],{type:'application/json'}),url=URL.createObjectURL(b),a=document.createElement('a');a.href=url;a.download='MarketDesk-Alert-Records-'+new Date().toISOString().slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);}
function setup(){if(ready)return;ready=true;$('alerts-form').addEventListener('submit',submit);$('alerts-symbol').addEventListener('change',showUnit);$('alerts-filter').addEventListener('change',render);$('alerts-list').addEventListener('click',action);$('alerts-refresh').addEventListener('click',refresh);$('alerts-cancel').addEventListener('click',()=>{cancel();feedback('Edit cancelled.');});$('alerts-export').addEventListener('click',download);$('alerts-history-prev').addEventListener('click',()=>{historyPage--;render();});$('alerts-history-next').addEventListener('click',()=>{historyPage++;render();});populate();refresh();setInterval(()=>{if(!editing)populate();refresh();},5000);}
function open(){setup();populate();render();return refresh();}
return {setup,open,refresh};
})();
