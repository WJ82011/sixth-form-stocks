/* No packages or provider calls. Node.js optional; Python app does not need it. */
const fs=require('node:fs'),path=require('node:path');
async function main(){
 const files=fs.readdirSync(__dirname).filter(n=>/^test_.*\.cjs$/.test(n)).sort();
 for(const file of files){
  const before=new Map(Object.entries(globalThis));
  require(path.join(__dirname,file));
  const jobs=Object.entries(globalThis).filter(([k,v])=>v&&typeof v.then==='function'&&before.get(k)!==v).map(([,v])=>v);
  await Promise.all(jobs);
  console.log('PASS '+file);
 }
 console.log(files.length+' JavaScript test files passed.');
}
module.exports=main();
module.exports.catch(error=>{console.error(error);process.exitCode=1});
