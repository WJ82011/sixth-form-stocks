const AppDesign=(()=>{
 'use strict';
 const KEY='md-reborn-design-v28',el=id=>document.getElementById(id),root=document.documentElement;
 const defaults={theme:'dark',accent:'blue',roundness:'soft',density:'airy',enabled:true,style:'soft',speed:'balanced',atmosphere:'glass',intensity:35,pointer:true,hover:true,reveal:true,chart:true,shell:'focus'};
 const enums={theme:['dark','light','system'],accent:['blue','cyan','violet','mint','brass'],roundness:['soft','extra','compact'],density:['airy','compact','terminal'],shell:['focus','sidebar'],style:['soft','glide','depth'],speed:['relaxed','balanced','snappy'],atmosphere:['glow','glass','none']};
 const presets={quiet:{enabled:true,style:'glide',speed:'snappy',atmosphere:'none',intensity:10,pointer:false,hover:true,reveal:false,chart:true},balanced:{enabled:true,style:'soft',speed:'balanced',atmosphere:'glass',intensity:35,pointer:true,hover:true,reveal:true,chart:true},cinematic:{enabled:true,style:'depth',speed:'relaxed',atmosphere:'glass',intensity:75,pointer:true,hover:true,reveal:true,chart:true},off:{enabled:false}};
 const reduce=window.matchMedia('(prefers-reduced-motion: reduce)'),light=window.matchMedia('(prefers-color-scheme: light)'),coarse=window.matchMedia('(pointer: coarse)');
 let prefs={...defaults},ready=false,saving=true,active='overview',epoch=0,pending=null,opener=null,closing=false,raf=0,lastDraw=0,canvas=null,ctx=null,w=0,h=0,observer=null,seen=new WeakSet(),tilted=null,scrollDepth=0,scrollTarget=0;
 const animations=new Set(),pointer={x:0,y:0,tx:0,ty:0},ease='cubic-bezier(.16,1,.3,1)';
 function normalise(value){const p={...defaults};if(!value||typeof value!=='object'||Array.isArray(value))return p;for(const key of Object.keys(enums))if(enums[key].includes(value[key]))p[key]=value[key];for(const key of ['enabled','pointer','hover','reveal','chart'])if(typeof value[key]==='boolean')p[key]=value[key];if(typeof value.intensity==='number'&&Number.isFinite(value.intensity))p.intensity=Math.max(0,Math.min(100,Math.round(value.intensity/5)*5));return p;}
 function enabled(){return ready&&prefs.enabled&&!reduce.matches;}
 function duration(){return {relaxed:620,balanced:420,snappy:260}[prefs.speed];}
 function cancel(group){for(const item of [...animations])if(!group||item.group===group)item.animation.cancel();}
 function animate(node,frames,options={},group='page'){
  if(!node||!enabled()||typeof node.animate!=='function')return Promise.resolve();
  return new Promise(resolve=>{let animation;try{animation=node.animate(frames,{duration:duration(),easing:ease,fill:'both',...options})}catch{resolve();return}
   const item={animation,group};animations.add(item);let settled=false;
   function finish(){if(settled)return;settled=true;animations.delete(item);animation.onfinish=null;animation.oncancel=null;animation.cancel();resolve();}
   animation.onfinish=finish;animation.oncancel=finish;
  });
 }
 function frames(enter){
  const strength=prefs.intensity/100;
  if(prefs.style==='glide')return enter?[{opacity:0,transform:'translateY(18px)'},{opacity:1,transform:'translateY(0)'}]:[{opacity:1,transform:'translateY(0)'},{opacity:0,transform:'translateY(-7px)'}];
  if(prefs.style==='depth')return enter?[{opacity:0,transform:`perspective(1200px) translateY(${18+strength*10}px) scale(.976) rotateX(1.2deg)`,filter:'blur(3px)'},{opacity:1,transform:'perspective(1200px) translateY(0) scale(1) rotateX(0)',filter:'blur(0)'}]:[{opacity:1,transform:'scale(1)',filter:'blur(0)'},{opacity:0,transform:'scale(.992)',filter:'blur(2px)'}];
  return enter?[{opacity:0,transform:'translateY(11px)',filter:'blur(4px)'},{opacity:1,transform:'translateY(0)',filter:'blur(0)'}]:[{opacity:1,filter:'blur(0)'},{opacity:0,filter:'blur(2px)'}];
 }
 function indicator(){const nav=document.querySelector('.focus-nav'),pill=el('nav-indicator');const selected=document.querySelector('#nav .nav-btn.active')?.dataset.view;document.querySelectorAll('[data-focus-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.focusView===selected)));const button=nav?.querySelector('[aria-pressed=true]');if(!pill)return;if(!button){pill.style.opacity='0';return}const box=button.getBoundingClientRect(),parent=nav.getBoundingClientRect();pill.style.width=box.width+'px';pill.style.transform='translateX('+(box.left-parent.left)+'px)';pill.style.opacity='1';}
 function clearMotion(node){if(!node)return;node.getAnimations?.().forEach(animation=>animation.cancel());node.style.removeProperty('opacity');node.style.removeProperty('transform');node.style.removeProperty('filter');}
 function flush(){epoch++;cancel('page');if(pending){const job=pending;pending=null;job.commit();active=job.name;document.querySelectorAll('.view').forEach(clearMotion);}indicator();}
 async function page(name,commit){
  if(!ready){commit();active=name;document.querySelectorAll('.view').forEach(clearMotion);return}
  const id=++epoch;cancel('page');pending=null;
  if(el('main-chart-panel')?.classList.contains('is-expanded'))toggleExpandedChart(false);
  commit();active=name;document.querySelectorAll('.view').forEach(clearMotion);indicator();watch();
  if(!enabled())return;
  await animate(el('view-'+name),frames(true),{duration:duration()},'page');
  if(id!==epoch)return;
 }
 function chart(){if(!ready||!enabled()||!prefs.chart)return;const node=el('overview-chart');cancel('chart');if(node&&node.getBoundingClientRect().width)animate(node,[{opacity:.08},{opacity:1}],{duration:Math.min(320,duration()*.65)},'chart');}
 function company(){if(!enabled())return;cancel('company');animate(el('desk-company-about'),[{opacity:0,transform:'translateY(5px)'},{opacity:1,transform:'translateY(0)'}],{duration:duration()*.65},'company');}
 function watch(){
  observer?.disconnect();observer=null;if(!enabled()||!prefs.reveal||typeof IntersectionObserver==='undefined')return;
  observer=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting&&!seen.has(entry.target)){seen.add(entry.target);animate(entry.target,[{opacity:0,transform:'translateY(15px)'},{opacity:1,transform:'translateY(0)'}],{duration:duration()*.9},'reveal');observer.unobserve(entry.target)}},{threshold:.12});
  document.querySelectorAll('#view-'+active+' .desk-company,#view-'+active+' .focus-entry').forEach(node=>{if(!seen.has(node))observer.observe(node)});
 }
 function presetName(){if(!prefs.enabled)return 'off';return Object.keys(presets).find(name=>name!=='off'&&Object.entries(presets[name]).every(([key,value])=>prefs[key]===value))||'custom';}
 function controls(){
  for(const key of Object.keys(enums))el('motion-'+key).value=prefs[key];
  for(const key of ['enabled','pointer','hover','reveal','chart'])el('motion-'+key).checked=prefs[key];
  el('motion-intensity').value=prefs.intensity;el('motion-intensity-value').textContent=prefs.intensity+'%';
  const preset=presetName();document.querySelectorAll('[data-motion-preset]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.motionPreset===preset)));
  el('motion-preset-note').textContent=({quiet:'Quiet: quick transitions, a steady background and minimal movement.',balanced:'Balanced: fluid transitions, gentle depth and a little atmosphere.',cinematic:'Cinematic: slower depth transitions and stronger floating-glass atmosphere.',off:'Off: instant navigation and a steady interface.',custom:'Custom: your own mix of appearance and motion.'})[preset];
  el('motion-system-note').textContent=reduce.matches?'Your system’s Reduce Motion setting is on. All motion is currently disabled; your choices are saved for when it is off.':'Your system’s Reduce Motion setting is always respected. Background animation pauses when this tab is hidden.';
 }
 function save(){try{localStorage.setItem(KEY,JSON.stringify(prefs));window.dispatchEvent(new Event('marketdesk:design-saved'));saving=true;el('motion-settings-feedback').textContent='Saved on this Mac. Included in your workspace backup.'}catch{saving=false;el('motion-settings-feedback').textContent='Applied for this session. This browser could not save the settings.'}}
 function apply(persist=true){
  flush();cancel();
  const on=enabled();document.body.dataset.motion=on?'on':'off';document.body.dataset.focusShell=prefs.shell;root.dataset.motion=on?'on':'off';root.dataset.accent=prefs.accent;root.dataset.roundness=prefs.roundness;root.dataset.density=prefs.density;root.dataset.pointer=on&&prefs.pointer&&!coarse.matches?'on':'off';root.dataset.hover=on&&prefs.hover?'on':'off';root.dataset.theme=prefs.theme==='system'?(light.matches?'light':'dark'):prefs.theme;
  root.style.setProperty('--motion-duration',duration()+'ms');const isLight=root.dataset.theme==='light';el('theme-toggle').textContent=isLight?'☾':'☼';el('theme-toggle').setAttribute('aria-pressed',String(isLight));el('theme-toggle').setAttribute('aria-label','Switch to '+(isLight?'dark':'light')+' appearance');
  syncLegacy();clearTilt();controls();watch();stopLoop();if(on&&ctx&&prefs.intensity>0&&prefs.atmosphere!=='none'&&!document.hidden)startLoop();else ctx?.clearRect(0,0,w,h);if(persist)save();requestAnimationFrame(()=>{indicator();if(typeof drawChart==='function')drawChart()});
 }
 function set(key,value){prefs=normalise({...prefs,[key]:value});apply();}
 function toggleTheme(){set('theme',root.dataset.theme==='light'?'dark':'light');}
 function openSettings(){opener=document.activeElement;closing=false;const panel=el('motion-settings');if(panel.open)return;controls();panel.showModal();el('motion-settings-title').focus();animate(panel,[{opacity:0,transform:'translateX(30px) scale(.985)'},{opacity:1,transform:'translateX(0) scale(1)'}],{duration:duration()*.8},'settings');}
 async function closeSettings(replay=false){
  const panel=el('motion-settings');if(!panel.open||closing)return;closing=true;cancel('settings');await animate(panel,[{opacity:1,transform:'translateX(0)'},{opacity:0,transform:'translateX(22px)'}],{duration:Math.min(210,duration()*.45)},'settings');
  if(panel.open)panel.close();closing=false;opener?.focus({preventScroll:true});if(replay&&enabled()){flush();animate(el('view-'+active),frames(true),{duration:duration()},'page');}
 }
 function detailOpen(node){cancel('detail');animate(node,[{opacity:0,transform:'translateY(14px) scale(.975)',filter:'blur(3px)'},{opacity:1,transform:'translateY(0) scale(1)',filter:'blur(0)'}],{duration:duration()*.8},'detail');}
 function detailClose(node,done){cancel('detail');animate(node,[{opacity:1,transform:'translateY(0)'},{opacity:0,transform:'translateY(8px)'}],{duration:Math.min(170,duration()*.4)},'detail').then(done);}
 function clearTilt(){if(tilted){tilted.style.removeProperty('--tilt-x');tilted.style.removeProperty('--tilt-y');tilted=null}}
 function resize(){if(!canvas)return;w=innerWidth;h=innerHeight;const dpr=Math.min(devicePixelRatio||1,1.5);canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);canvas.style.width=w+'px';canvas.style.height=h+'px';ctx?.setTransform(dpr,0,0,dpr,0,0);indicator();if(enabled()&&prefs.atmosphere!=='none')startLoop();}
 function stopLoop(){if(raf)cancelAnimationFrame(raf);raf=0;lastDraw=0;}
 function startLoop(){if(!raf&&!document.hidden&&enabled())raf=requestAnimationFrame(tick);}
 function tick(now){
  raf=0;if(document.hidden||!enabled())return;
  const bg=Boolean(ctx)&&prefs.atmosphere!=='none'&&prefs.intensity>0;
  if(coarse.matches&&now-lastDraw<1000/30){raf=requestAnimationFrame(tick);return}lastDraw=now;
  pointer.x+=(pointer.tx-pointer.x)*.065;pointer.y+=(pointer.ty-pointer.y)*.065;scrollDepth+=(scrollTarget-scrollDepth)*.055;
  if(bg&&ctx){
   ctx.clearRect(0,0,w,h);const strength=prefs.intensity/100,time=now*.00012,blue=({blue:'120,169,255',cyan:'100,210,222',violet:'167,141,255',mint:'100,210,170',brass:'210,180,120'})[prefs.accent],isLight=root.dataset.theme==='light';
   const px=prefs.pointer&&!coarse.matches?pointer.x*24*strength:0,py=prefs.pointer&&!coarse.matches?pointer.y*18*strength:0;
   const cx=w*.77+Math.sin(time*.8)*30+px,cy=h*.15+Math.cos(time)*20+py-scrollDepth*60*strength,radius=Math.max(w*.32,240);
   const glow=ctx.createRadialGradient(cx,cy,0,cx,cy,radius);glow.addColorStop(0,`rgba(${blue},${(isLight?.09:.13)*strength})`);glow.addColorStop(1,`rgba(${blue},0)`);ctx.fillStyle=glow;ctx.fillRect(0,0,w,h);
   if(prefs.atmosphere==='glass'){
    const shapes=[{x:.88,y:.16,s:125,a:.3},{x:.12,y:.59,s:90,a:-.25},{x:.67,y:.86,s:75,a:.1}];
    for(let i=0;i<shapes.length;i++){const shape=shapes[i],x=w*shape.x+Math.sin(time+i)*21+px*(i%2?-.5:1),y=h*shape.y+Math.cos(time*.7+i)*17+py-scrollDepth*(i+1)*20*strength,s=Math.min(shape.s,w*.22),angle=shape.a+Math.sin(time*.5+i)*.08;
     ctx.save();ctx.translate(x,y);ctx.rotate(angle);const fill=ctx.createLinearGradient(-s,-s,s,s);fill.addColorStop(0,`rgba(${blue},${.13*strength})`);fill.addColorStop(.5,`rgba(${blue},${.025*strength})`);fill.addColorStop(1,`rgba(${blue},${.075*strength})`);ctx.fillStyle=fill;ctx.strokeStyle=`rgba(${blue},${.19*strength})`;ctx.lineWidth=1;
     ctx.beginPath();ctx.moveTo(-s*.75,-s*.55);ctx.bezierCurveTo(-s*.1,-s*.95,s*.95,-s*.65,s*.8,-s*.1);ctx.lineTo(s*.52,s*.55);ctx.bezierCurveTo(s*.1,s*.92,-s*.8,s*.65,-s*.75,s*.05);ctx.closePath();ctx.fill();ctx.stroke();ctx.beginPath();ctx.moveTo(-s*.6,-s*.44);ctx.bezierCurveTo(0,-s*.72,s*.62,-s*.5,s*.64,-s*.08);ctx.strokeStyle=`rgba(${blue},${.21*strength})`;ctx.stroke();ctx.restore();
    }
    ctx.fillStyle=`rgba(${blue},${.25*strength})`;for(let i=0;i<14;i++){const x=((i*173.3+w*.1+Math.sin(time+i)*14)%w+w)%w,y=((i*91.7+time*13)%h+h)%h;ctx.beginPath();ctx.arc(x,y,i%3===0?1.25:.7,0,Math.PI*2);ctx.fill();}
   }
  }
  if(bg||Math.abs(pointer.tx-pointer.x)+Math.abs(pointer.ty-pointer.y)>.001)raf=requestAnimationFrame(tick);
 }
let syncing=false;
 function syncLegacy(){if(!window.MarketDeskPreferences?.patch)return;const old=MarketDeskPreferences.current(),patch={colour:prefs.accent,density:prefs.density==='airy'?'balanced':prefs.density,motion:prefs.enabled};if(Object.keys(patch).some(k=>patch[k]!==old[k])){syncing=true;try{MarketDeskPreferences.patch(patch)}finally{syncing=false}}document.body.dataset.motion=enabled()?'on':'off';}
 function migrate(){let raw;try{raw=JSON.parse(localStorage.getItem(KEY))}catch{}if(raw&&Object.keys(raw).length)return normalise(raw);const old=window.MarketDeskPreferences?.current?.()||{};return normalise({...defaults,accent:old.colour||'blue',density:old.density==='balanced'?'airy':old.density,enabled:typeof old.motion==='boolean'?old.motion:true});}
 function setup(){
  if(ready)return;prefs=migrate();
  ready=true;canvas=el('atmosphere');try{ctx=canvas.getContext('2d')}catch{ctx=null}
  const pill=document.createElement('span');pill.id='nav-indicator';pill.className='nav-indicator';pill.setAttribute('aria-hidden','true');document.querySelector('.focus-nav').prepend(pill);
  el('theme-toggle').addEventListener('click',toggleTheme);el('motion-settings-open').addEventListener('click',openSettings);el('motion-settings-close').addEventListener('click',()=>closeSettings());el('motion-done').addEventListener('click',()=>closeSettings());el('motion-replay').addEventListener('click',()=>closeSettings(true));el('motion-settings').addEventListener('cancel',event=>{event.preventDefault();closeSettings()});el('motion-settings').addEventListener('click',event=>{if(event.target===el('motion-settings'))closeSettings()});
  for(const key of Object.keys(enums))el('motion-'+key).addEventListener('change',event=>set(key,event.target.value));
  for(const key of ['enabled','pointer','hover','reveal','chart'])el('motion-'+key).addEventListener('change',event=>set(key,event.target.checked));
  el('motion-intensity').addEventListener('input',event=>set('intensity',Number(event.target.value)));
  document.querySelectorAll('[data-motion-preset]').forEach(button=>button.addEventListener('click',()=>{prefs=normalise({...prefs,...presets[button.dataset.motionPreset]});apply()}));
  el('motion-reset').addEventListener('click',()=>{prefs={...defaults};apply()});
  window.addEventListener('resize',resize);window.addEventListener('scroll',()=>{scrollTarget=Math.max(0,Math.min(1,scrollY/Math.max(1,document.documentElement.scrollHeight-innerHeight)));if(prefs.atmosphere!=='none')startLoop()},{passive:true});window.addEventListener('pointermove',event=>{
   if(!enabled()||!prefs.pointer||coarse.matches||event.pointerType==='touch')return;
   pointer.tx=event.clientX/innerWidth*2-1;pointer.ty=event.clientY/innerHeight*2-1;
   const card=prefs.hover?event.target.closest('.context-card,.story,.company-tile'):null;if(card!==tilted)clearTilt();tilted=card;
   if(card){const r=card.getBoundingClientRect(),strength=prefs.intensity/100;card.style.setProperty('--tilt-x',((.5-(event.clientY-r.top)/r.height)*3*strength).toFixed(2)+'deg');card.style.setProperty('--tilt-y',(((event.clientX-r.left)/r.width-.5)*3*strength).toFixed(2)+'deg');}
   startLoop();
  },{passive:true});document.addEventListener('pointerleave',()=>{pointer.tx=pointer.ty=0;clearTilt();startLoop()});
  document.addEventListener('visibilitychange',()=>{if(document.hidden){flush();cancel();stopLoop()}else apply(false)});
  for(const query of [reduce,light,coarse]){if(query.addEventListener)query.addEventListener('change',()=>apply(false));else query.addListener?.(()=>apply(false))}
  window.addEventListener('marketdesk:workspace-restored',()=>{prefs=migrate();apply(false)});window.addEventListener('marketdesk:preference-saved',()=>{if(syncing)return;const old=MarketDeskPreferences.current();prefs=normalise({...prefs,enabled:old.motion,accent:old.colour,density:old.density==='balanced'?'airy':old.density});apply()});apply(false);resize();animate(el('view-overview'),frames(true),{duration:duration()},'page');
 }
 return {setup,page,chart,company,toggleTheme,detailOpen,detailClose,normalise,flush,current:()=>({...prefs})};
})();

 const boot=()=>{
  AppDesign.setup();
  window.Desk68?.regroup();
  const tools=document.getElementById('focus-tools-dialog'),grid=document.getElementById('focus-tools-grid');let opener;
  function close(){tools.close();opener?.focus({preventScroll:true})}
  document.querySelectorAll('#sidebar .nav-btn[data-view]').forEach(source=>{const b=document.createElement('button');b.type='button';const name=source.dataset.navLabel||source.querySelector('span:nth-child(2)')?.textContent||source.textContent.trim();b.textContent=name;b.dataset.area=source.dataset.area||'';b.title=source.title||name;b.addEventListener('click',()=>{close();changeView(source.dataset.view)});grid.append(b)});
  const search=document.getElementById('focus-tools-search');
  search?.addEventListener('input',()=>{const query=search.value.trim().toLowerCase();grid.querySelectorAll('button').forEach(button=>{button.hidden=Boolean(query)&&!button.textContent.toLowerCase().includes(query)&&!button.title.toLowerCase().includes(query)});});
  document.getElementById('focus-tools').addEventListener('click',()=>{opener=document.activeElement;tools.showModal();document.getElementById('focus-tools-close').focus();AppDesign.detailOpen(tools)});
  document.getElementById('focus-tools-close').addEventListener('click',close);
  tools.addEventListener('click',e=>{if(e.target===tools)close()});
  document.querySelectorAll('[data-focus-view]').forEach(b=>b.addEventListener('click',()=>changeView(b.dataset.focusView)));
  document.getElementById('focus-home').addEventListener('click',e=>{e.preventDefault();changeView('home')});
  const stock=document.getElementById('desk-stock'),company=stock.querySelector('.desk-company'),mount=document.getElementById('desk-chart-mount');
  const layout=document.createElement('div');layout.className='focus-chart-layout';mount.before(layout);layout.append(mount);
  const chart=document.getElementById('main-chart-panel'),plot=chart.querySelector('.chart-wrap');if(plot)plot.after(chart.querySelector('.chart-research-toolbar'),document.getElementById('desk-range-hint'));
  const context=document.createElement('aside');context.className='focus-context';layout.append(context);context.append(company);
  const ai=document.createElement('article');ai.className='focus-intelligence';ai.innerHTML='<p class="desk-eyebrow">MARKET DESK INTELLIGENCE</p><h2>A clearer view of your company.</h2><p>Explore recorded price moves, ask about a company or read the evidence behind an answer.</p><button type="button" class="primary-btn">Ask Intelligence ↗</button><small>Answers depend on available sources. Forecasts can be wrong.</small>';ai.querySelector('button').addEventListener('click',()=>changeView('intelligence'));context.append(ai);const healthButton=document.createElement('button');healthButton.type='button';healthButton.className='ghost-btn focus-health-link';healthButton.textContent='Explore financial health ↗';healthButton.addEventListener('click',()=>{openStockResearch('company')});ai.append(healthButton);
  const entries=document.createElement('div');entries.className='focus-entries';
  for(const [view,title,desc] of [['news','The latest context','Read publisher headlines and their dates.'],['heatmap','Your market, in colour','Explore the moves across your watchlist.'],['research','Make it your own','Keep your notes and build your research.']]){const b=document.createElement('button');b.type='button';b.className='focus-entry';const h=document.createElement('strong');h.textContent=title;const p=document.createElement('span');p.textContent=desc;b.append(h,p);b.addEventListener('click',()=>changeView(view));entries.append(b)}
  stock.append(entries);
  const sync=()=>document.querySelectorAll('[data-focus-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.focusView===E.view)));
  new MutationObserver(sync).observe(document.getElementById('nav'),{subtree:true,attributes:true,attributeFilter:['class']});sync();
  document.getElementById('overview-ranges')?.addEventListener('click',()=>AppDesign.chart());
 };
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
