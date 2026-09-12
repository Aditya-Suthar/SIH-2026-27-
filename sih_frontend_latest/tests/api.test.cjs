const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

// Execute the actual request/hook module with deterministic browser and hook
// scheduling. Network responses vary while the protected resource stays fixed.
function harness() {
  const states=[], effects=[], storage=new Map([['access_token','test-token'],['role','authority']]);
  let redirect=null, reply={status:200,body:{items:[{id:7}]}}, fail=false;
  const events=new EventTarget();
  const window={dispatchEvent:e=>events.dispatchEvent(e),addEventListener:(...x)=>events.addEventListener(...x),
    removeEventListener:(...x)=>events.removeEventListener(...x),setInterval:()=>1,location:{replace:path=>redirect=path}};
  const hooks={useState:value=>{const i=states.length;states.push(value);return [value,v=>states[i]=v];},
    useRef:value=>({current:value}),useCallback:fn=>fn,useEffect:fn=>effects.push(fn)};
  const exports={};
  const source=ts.transpileModule(fs.readFileSync('src/lib/api.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  vm.runInNewContext(source,{exports,require:name=>name==='react'?hooks:{API_BASE_URL:'https://backend.example'},
    localStorage:{getItem:k=>storage.get(k)||null,removeItem:k=>storage.delete(k)},window,document:{hidden:false},
    Event,AbortController,Error,clearInterval:()=>{},fetch:async()=>{if(fail)throw Error('Network unavailable');return {ok:reply.status===200,status:reply.status,json:async()=>reply.body};}});
  return {module:exports,states,effects,storage,redirect:()=>redirect,
    response:(status,body={})=>{reply={status,body};fail=false;},networkFailure:()=>fail=true};
}
test('polling permission failure clears previously loaded protected data',async()=>{
  const h=harness(),remote=h.module.useRemote('/api/monitoring/indicators');
  await remote.refresh();assert.equal(h.states[0].items[0].id,7);
  h.response(403);await remote.refresh();
  assert.equal(h.states[0],null);assert.match(h.states[1],/^Refresh failed/);
  assert.equal(h.redirect(),null);
});
test('network refresh failure is local, keeps last data, and retry recovers',async()=>{
  const h=harness(),remote=h.module.useRemote('/api/support-requests');
  await remote.refresh();h.networkFailure();await remote.refresh();
  assert.equal(h.states[0].items[0].id,7);assert.match(h.states[1],/^Refresh failed/);
  h.response(200,{items:[]});await remote.refresh();assert.equal(h.states[1],'');
});
test('expired authentication clears session and every mounted resource',async()=>{
  const h=harness();h.module.useRemote('/api/support-requests');h.module.useRemote('/api/monitoring/indicators');
  h.effects.forEach(fn=>fn());await new Promise(resolve=>setImmediate(resolve));
  h.response(401);await assert.rejects(()=>h.module.api('/api/monitoring/indicators'),/expired/);
  assert.equal(h.states[0],null);assert.equal(h.states[3],null);
  assert.equal(h.storage.size,0);assert.equal(h.redirect(),'/login');
});

test('graph keeps the two sources distinct, sorts time, and excludes missing attempts',()=>{
  const exports={};
  const source=ts.transpileModule(fs.readFileSync('src/lib/monitoring.ts','utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  vm.runInNewContext(source,{exports,Date,Intl});
  const points=exports.observationPoints([
    {status:'completed',distress_score:0,created_at:'2026-09-12T20:00:00Z'},
    {status:'failed',distress_score:null,created_at:'2026-09-12T21:00:00Z'},
    {status:'pending',distress_score:null,created_at:'2026-09-12T22:00:00Z'},
  ],[{score:66,observed_at:'2026-09-12T19:03:08Z'},{score:null,observed_at:'2026-09-12T19:04:00Z'}]);
  assert.equal(points.length,2);assert.equal(points[0].questionnaire,66);assert.equal(points[0].text_ai,null);
  assert.equal(points[1].text_ai,0);assert.equal(points[1].questionnaire,null);
  assert.equal(exports.observationPoints([],[{score:48,observed_at:'2026-09-12T20:03:18Z'}]).length,1);
  const ist=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Kolkata',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
  assert.equal(ist.format(points[0].time),'00:33');
});
