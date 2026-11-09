/* Exercises the production V3 save function with isolated transport/storage fixtures. */
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');const source=fs.readFileSync(path.join(__dirname,'../site/v3.js'),'utf8');const a=source.indexOf(' async function action('),b=source.indexOf(' function mount()',a);let stored=JSON.stringify({research:{projects:[{id:'newer-other-window'}]}}),accepted=null,messages=[];
const ctx=vm.createContext({busy:false,state:{research:{projects:[]}},KEY:'synthetic-key',localStorage:{getItem:()=>stored},document:{querySelectorAll:()=>[]},E:{view:'research'},message:(id,t)=>messages.push(t),accept:d=>{accepted=d;},renderPortfolio(){},renderLayout(){},loadState:async()=>{},window:{dispatchEvent(){}},Event:class{},JSON,Error});vm.runInContext(source.slice(a,b),ctx);
globalThis.projectSaveRaceTestResult=(async()=>{
 ctx.request=async(path,body)=>({state:body.state});assert.equal(await vm.runInContext("action('research.project.save',{})",ctx),true);assert.equal(accepted.state.research.projects[0].id,'newer-other-window','save must read latest stored research before mutation');
 accepted=null;ctx.request=async(path,body)=>{stored=JSON.stringify({research:{projects:[{id:'changed-during-request'}]}});return {state:body.state}};assert.equal(await vm.runInContext("action('research.project.save',{})",ctx),false);assert.equal(accepted,null);assert.ok(messages.some(t=>t.includes('another window')));
 console.log('V3 project saves: latest local state and in-flight conflict protection PASS');
})();
