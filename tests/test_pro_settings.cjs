'use strict';
const assert=require('assert');
const fs=require('fs');
const vm=require('vm');
const path=require('path');
const js=fs.readFileSync(path.join(__dirname,'..','site','pro.js'),'utf8');
const handlers={};
const sandbox={
  window:{},
  document:{readyState:'loading',addEventListener:(type,fn)=>{handlers[type]=fn}},
  localStorage:{},
  console,
  setInterval:()=>{},
};
vm.runInNewContext(js,sandbox,{filename:'pro.js'});
const api=sandbox.window.MarketDeskPreferences;
assert(api,'Exposes a preferences-only testing interface');
function plain(o){return JSON.parse(JSON.stringify(o));}
const defaults=plain(api.defaults());
assert.deepStrictEqual(defaults,{edition:'signal',density:'balanced',colour:'blue',chartHeight:'standard',contrast:'normal',ticker:true,motion:true});
assert.deepStrictEqual(plain(api.normalise(null)),defaults);
assert.deepStrictEqual(plain(api.normalise('malicious')),defaults);
assert.deepStrictEqual(plain(api.normalise({edition:'invalid',density:'wide',colour:'javascript:alert(1)',ticker:'false',motion:0})),defaults);
assert.deepStrictEqual(plain(api.normalise({edition:'professional',density:'terminal',colour:'cyan',chartHeight:'xl',contrast:'high',ticker:false,motion:false})),{edition:'professional',density:'terminal',colour:'cyan',chartHeight:'xl',contrast:'high',ticker:false,motion:false});
assert.strictEqual(api.normalise({extra:'bad'}).extra,undefined);
assert.strictEqual(api.current().edition,'signal');
console.log('Professional Edition preference normalisation, defaults and allowlist: PASS');
// Existing workspace choices survive the one-time switch to the new blue theme.
const stored=new Map([['md-reborn-workstation-v1',JSON.stringify({edition:'professional',density:'compact',colour:'brass',chartHeight:'xl',contrast:'high',ticker:false,motion:false})]]);
function bootTheme(){
 const elements=new Map(),listeners={};const element=id=>{if(!elements.has(id))elements.set(id,{dataset:{},events:{},addEventListener(k,f){this.events[k]=f},setAttribute(){},querySelector(){return {textContent:''}}});return elements.get(id)};
 const choices=['blue','brass','cyan','mint','violet'].map(c=>{const n=element('colour-'+c);n.dataset.colour=c;return n});
 const context={window:{addEventListener(){},dispatchEvent(){}},document:{readyState:'loading',body:{dataset:{}},getElementById:element,querySelectorAll:s=>s==='.colour-choice'?choices:[],addEventListener:(k,f)=>listeners[k]=f},localStorage:{getItem:k=>stored.get(k)||null,setItem:(k,v)=>stored.set(k,v)},Event:function(){},CustomEvent:function(){},MutationObserver:class{observe(){}},setInterval(){}};
 vm.runInNewContext(js,context);listeners.DOMContentLoaded();return {api:context.window.MarketDeskPreferences,element};
}
let themed=bootTheme();assert.deepStrictEqual(plain(themed.api.current()),{edition:'professional',density:'compact',colour:'blue',chartHeight:'xl',contrast:'high',ticker:false,motion:false});themed.element('colour-brass').events.click();assert.equal(themed.api.current().colour,'brass');assert.equal(bootTheme().api.current().colour,'brass','Choosing Brass explicitly after migration persists');
console.log('Rounded theme migration preserves edition, layout and accessibility choices; all accent choices remain available: PASS');
