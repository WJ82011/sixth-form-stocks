const assert=require('node:assert/strict');
const v=require('../site/v3.js');
assert.equal(v.finite(null),false);assert.equal(v.finite(Infinity),false);assert.equal(v.finite(0),true);
assert.equal(v.url('javascript:alert(1)'),'');assert.equal(v.url('https://user:password@example.com'),'');assert.equal(v.url('https://www.sec.gov/'),'https://www.sec.gov/');
const boxes=v.treemap([{symbol:'A',value:6},{symbol:'B',value:3},{symbol:'C',value:1},{symbol:'bad',value:NaN}],1000,360);
assert.equal(boxes.length,3);
for(const b of boxes){assert.ok(Math.abs(b.w*b.h/360000-b.value/10)<1e-10);assert.ok(b.x>=0&&b.y>=0&&b.x+b.w<=1000.000001&&b.y+b.h<=360.000001)}
for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){const a=boxes[i],b=boxes[j];assert.ok(Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x)<1e-8||Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y)<1e-8)}
assert.deepEqual(v.treemap([]),[]);
assert.equal(v.path([]),'');
const line=v.path([{date:'2025-01-01',index:100},{date:'2025-01-02',index:101},{date:'2025-01-10',index:102}]);
assert.equal((line.match(/M/g)||[]).length,2);assert.equal((line.match(/L/g)||[]).length,1);assert.ok(!line.includes('NaN'));
console.log('V3 proportional areas, safe links and dated chart gaps passed');
