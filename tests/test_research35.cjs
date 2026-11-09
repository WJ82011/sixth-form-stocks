const assert=require('node:assert/strict'),R=require('../site/research35.js');
class Storage{constructor(){this.data=new Map();this.fail=false;}getItem(k){return this.data.get(k)??null;}setItem(k,v){if(this.fail)throw Error('Synthetic storage failure');this.data.set(k,v);}}
const s=new Storage(),messages=[],store=new R.DraftStore(s,(t,e)=>messages.push({t,e}));store.init({records:[]});
const draft={symbol:'AAA',book:{bookIndex:0},config:{scenarios:[]},forms:{shared:{rationale:'unfinished'}},caseIndex:1};
assert(store.save(draft));assert(store.protected(draft));assert.equal(store.read().records.length,1);
const reload=new R.DraftStore(s);reload.init(reload.read());assert(reload.protected(draft),'Restart retains incomplete form');
assert(reload.save({...draft,symbol:'BBB'}));assert.equal(reload.read().records.length,2,'Company drafts stay separate');
assert(!store.save({...draft,symbol:'BBB'}),'Another window must not overwrite a recovery draft it has not reviewed');
assert(store.save({...draft,forms:{shared:{rationale:'more typing'}}}));assert(!reload.save(draft),'Stale tab cannot overwrite a newer company draft');
const before=s.getItem(R.key);s.fail=true;assert(!store.save({...draft,forms:{shared:{rationale:'unsaved'}}}));assert.equal(s.getItem(R.key),before,'Storage failure preserves last good copy');s.fail=false;
assert(store.remove('AAA'));assert.equal(store.read().records.length,1);assert.equal(store.read().records[0].symbol,'BBB');
s.setItem(R.key,'broken JSON');assert(!store.save(draft));assert.equal(s.getItem(R.key),'broken JSON','Damaged recovery data is retained');
const bridge=R.waterfall([{value:-20,total:true},{value:10,total:false},{value:-5,total:false},{value:-15,total:true}]);assert.deepEqual(bridge.map(x=>[x.start,x.end]),[[0,-20],[-20,-10],[-10,-15],[0,-15]]);
assert.equal(R.esc('<img onerror="x">'),'&lt;img onerror=&quot;x&quot;&gt;');
const source=require('node:fs').readFileSync(require('node:path').join(__dirname,'../site/research35.js'),'utf8');assert(!source.includes('data-action='),'New controls must not collide with the retained navigation delegate');

const bounded=new Storage(),limitStore=new R.DraftStore(bounded);limitStore.init({records:[]});assert(!limitStore.save({...draft,forms:{shared:{rationale:"x".repeat(400001)}}}));assert.equal(bounded.getItem(R.key),null,"Oversized recovery data must not replace a valid store");
