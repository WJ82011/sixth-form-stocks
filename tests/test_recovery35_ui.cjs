/* Recovery failures must not silently replace a newer or damaged browser draft. */
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
const values=new Map(),nodes=new Map();const node=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',classList:{add(){},remove(){},toggle(){}}});return nodes.get(id)};
const ctx=vm.createContext({document:{readyState:'loading',getElementById:node,addEventListener(){},querySelectorAll(){return []}},localStorage:{getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)},URL,console,setTimeout:()=>1,clearTimeout(){},window:{dispatchEvent(){}},Event});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../site/app.js'),'utf8'),ctx);const run=x=>vm.runInContext(x,ctx);ctx.mergeReportArchives=(a,b)=>a||b||[];ctx.normaliseWatchlist=x=>x;
globalThis.recovery35UiTestResult=(async()=>{
 values.set('md-analyst-drafts-v35','damaged unfinished JSON');values.set('md-reborn-watch','["AAPL"]');
 ctx.api=async()=>({snapshot:{watch:['AAPL'],names:{},notes:[],reports:[],portfolio:{capital:10000,trades:[]},v3:{},design:{},preferences:{},tapeSymbol:'AAPL',analystDrafts:{version:1,records:[]}},updated_at:123});
 await run('restoreWorkspace()');assert.equal(values.get('md-analyst-drafts-v35'),'damaged unfinished JSON','Automatic startup must retain damaged recovery evidence');assert.throws(()=>run('snapshotWorkspace()'),/Draft recovery data needs checking/,'No backup may silently replace damaged drafts with an empty array');
 values.set('md-analyst-drafts-v35',JSON.stringify({version:1,records:[{symbol:'AAA',revision:'new-local'}]}));await run('restoreWorkspace()');assert(values.get('md-analyst-drafts-v35').includes('new-local'),'A remote older backup must not overwrite local unfinished work');
 assert.equal(JSON.parse(JSON.stringify(run('snapshotWorkspace()'))).analystDrafts.records[0].revision,'new-local','Full research exports include recovery copies');
})();
