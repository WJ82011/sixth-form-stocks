const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert/strict');
const observers=[];const groups=[],buttons=[];
function classes(initial=[]){const set=new Set(initial);return {contains:x=>set.has(x),toggle(x,on){if(on)set.add(x);else set.delete(x)}}}
function node(){return {events:{},attrs:{},classList:classes(),addEventListener(k,f){this.events[k]=f},setAttribute(k,v){this.attrs[k]=v},removeAttribute(k){delete this.attrs[k]},focus(){this.focused=true}}}
function group(id){const g=node(),summary=node();g.id=id;g.open=false;g.querySelector=()=>summary;g.summary=summary;groups.push(g);return g}
const markets=group('markets'),research=group('research'),workspace=group('workspace');
function button(view,parent=null){const b=node();b.dataset={view};b.closest=()=>parent;buttons.push(b);return b}
const overview=button('overview'),intel=button('intelligence'),settings=button('settings'),stock=button('markets',markets),chart=button('indicators',research),alerts=button('alerts',workspace);
overview.classList.toggle('active',true);
const source={textContent:'0'},badge=node();const sidebar={querySelectorAll:s=>s==='.sidebar-group'?groups:buttons};
const context={document:{readyState:'complete',getElementById:id=>({'sidebar':sidebar,'alerts-nav-count':source,'nav-workspace-alerts':badge}[id])},MutationObserver:class{constructor(f){this.f=f;observers.push(this)}observe(){}},Number,Math,Array};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/navigation.js'),'utf8'),context);const sync=observers[0].f,syncAlerts=observers[1].f;
function visit(target){for(const b of buttons)b.classList.toggle('active',b===target);sync()}
assert(groups.every(g=>!g.open),'Overview initially keeps every group condensed');assert.equal(overview.attrs['aria-current'],'page');
markets.open=true;markets.events.toggle();research.open=true;research.events.toggle();assert(!markets.open&&research.open,'Only one group stays expanded');
visit(alerts);assert(workspace.open&&!research.open);assert(workspace.classList.contains('is-current'));assert.equal(alerts.attrs['aria-current'],'page');assert(!overview.attrs['aria-current']);
workspace.open=false;sync();assert(!workspace.open,'An unrelated mutation cannot undo manual collapse');assert(workspace.classList.contains('is-current'),'Collapsed current section stays identifiable');
visit(chart);assert(research.open&&!workspace.open,'Deep link reveals its actual group');visit(intel);assert(groups.every(g=>!g.open),'Direct destination condenses groups');
source.textContent='3';syncAlerts();assert.equal(badge.hidden,false);assert.equal(badge.textContent,'3');assert.equal(badge.attrs['aria-label'],'3 triggered price alerts');source.textContent='0';syncAlerts();assert.equal(badge.hidden,true);
visit(stock);let prevented=false;markets.events.keydown({key:'Escape',preventDefault(){prevented=true}});assert(!markets.open&&markets.summary.focused&&prevented,'Escape returns focus to the group summary');
console.log('Compact navigation: disclosure accordion, deep links, current page, manual collapse, alert badge and keyboard focus PASS');
// Animated disclosures remain reversible and settle when reduced motion is chosen.
function animatedNavigation(){
 const obs=[],gs=[],bs=[],animations=[];const body={dataset:{motion:'on'}};
 function g(id){const item=node(),summary=node(),content={inert:false};item.id=id;item.open=false;item.style={removeProperty(k){delete this[k]}};item.querySelector=s=>s==='summary'?summary:content;item.summary=summary;item.content=content;item.getBoundingClientRect=()=>({height:item.open?240:42});summary.getBoundingClientRect=()=>({height:42});item.animate=(frames,options)=>{const a={frames,options,cancel(){this.cancelled=true}};animations.push(a);return a};gs.push(item);return item}
 const a=g('a'),b=g('b');const page=node();page.dataset={view:'overview'};page.classList.toggle('active',true);page.closest=()=>null;bs.push(page);const side={querySelectorAll:s=>s==='.sidebar-group'?gs:bs};const media={matches:false,addEventListener(k,f){this.change=f}};
 const c={document:{readyState:'complete',body,getElementById:id=>id==='sidebar'?side:null},window:{matchMedia:()=>media},MutationObserver:class{constructor(f){this.f=f;obs.push(this)}observe(){}},Number,Math,Array};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../site/navigation.js'),'utf8'),c);const click=x=>x.summary.events.click({button:0,preventDefault(){}});
 click(a);assert(a.open&&animations.length===1);assert.equal(animations[0].options.duration,220);const stale=animations[0].onfinish;click(a);assert(a.open&&a.content.inert,'Closing stays open only until its animation finishes');assert(animations[0].cancelled);stale();assert(a.open,'Stale completion cannot close the new state');animations[1].onfinish();assert(!a.open);
 click(a);click(b);assert(b.open);body.dataset.motion='off';obs[obs.length-1].f();assert(!a.open&&b.open,'Switching motion off settles both targets');const n=animations.length;click(b);assert(!b.open&&animations.length===n,'Saved motion preference bypasses animations');body.dataset.motion='on';media.matches=true;click(a);assert(a.open&&animations.length===n,'OS reduced motion also bypasses animations');
}
animatedNavigation();console.log('Navigation motion: interruption, stale callbacks, focus inertness and reduced-motion settlement PASS');
