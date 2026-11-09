/* Behaviour checks: invalid settings, interrupted navigation and accessibility overrides. */
const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert/strict');
const code=fs.readFileSync(path.join(__dirname,'../site/design.js'),'utf8');
const nodes=new Map(),animations=[],events={},saved={},frames=[];
function node(id){if(nodes.has(id))return nodes.get(id);const n={id,dataset:{},style:{setProperty(){},removeProperty(){}},classList:{contains(){return false}},value:'',textContent:'',checked:false,open:false,addEventListener(){},setAttribute(){},prepend(){},querySelector(){return null},getBoundingClientRect(){return {width:800,height:500,left:0,top:0}},getContext(){return null},animate(k,o){const a={k,o,cancel(){this.oncancel?.()}};animations.push(a);return a}};nodes.set(id,n);return n}
const reduced={matches:false,addEventListener(k,f){this.change=f}},scheme={matches:false,addEventListener(){}},coarse={matches:false,addEventListener(){}};
const document={documentElement:node('html'),body:node('body'),hidden:false,getElementById:node,querySelector:s=>s==='.focus-nav'?node('nav'):null,querySelectorAll:()=>[],createElement:()=>node('created'),addEventListener(){}};
const context={document,window:{matchMedia:q=>q.includes('reduced')?reduced:q.includes('scheme')?scheme:coarse,addEventListener(k,f){events[k]=f},dispatchEvent(){}},localStorage:{getItem:k=>saved[k]||null,setItem(k,v){saved[k]=v}},requestAnimationFrame:f=>(frames.push(f),frames.length),cancelAnimationFrame(){},innerWidth:1280,innerHeight:900,devicePixelRatio:1,Event:class{},console};
vm.createContext(context);vm.runInContext(code,context);const design=vm.runInContext('AppDesign',context);
let p=design.normalise({theme:'bad',enabled:'yes',intensity:200,accent:'cyan',shell:'sidebar',unknown:'ignored'});assert.equal(p.theme,'dark');assert.equal(p.enabled,true);assert.equal(p.intensity,100);assert.equal(p.accent,'cyan');assert.equal(p.shell,'sidebar');assert(!('unknown' in p));assert.equal(design.normalise({intensity:-30}).intensity,0);assert.equal(design.normalise({intensity:NaN}).intensity,35);
design.setup();
const commits=[];
const result=(async()=>{
 const first=design.page('markets',()=>commits.push('markets'));
 const second=design.page('news',()=>commits.push('news'));
 animations.at(-1).onfinish();await Promise.resolve();await Promise.resolve();
 animations.at(-1).onfinish?.();await first;await second;assert.deepEqual(commits,['news'],'A cancelled destination must never commit');
 const third=design.page('research',()=>commits.push('research'));reduced.matches=true;reduced.change();await third;assert.deepEqual(commits,['news','research'],'Reduce Motion settles the latest destination');
 const count=animations.length;await design.page('overview',()=>commits.push('overview'));assert.equal(animations.length,count,'OS Reduce Motion bypasses animation');assert.equal(document.body.dataset.motion,'off');
 assert.equal(node('html').dataset.motion,'off');assert(!saved['marketdesk-motion-preview-v1']);
 console.log('Design: validated settings, latest navigation wins, cancellation settles, OS Reduce Motion and production storage PASS');return true;
})();
globalThis.designTestResult=result;
