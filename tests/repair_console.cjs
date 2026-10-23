const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {spawnSync}=require('node:child_process');
const path=require('node:path');
const root=path.resolve(__dirname,'..');

test('owner selection exports the exact backend configuration consumed by the CLI',()=>{
  const file=path.join(root,'dashboard/repair-console.js');
  assert.ok(fs.existsSync(file),'The working owner repair selector is missing');
  const ui=require(file);
  const config=ui.buildConfig('CODEX_AGENT','weighted-mix');
  assert.deepEqual(config,{engine:'CODEX_AGENT',case_id:'weighted-mix'});
  const tmp=require('node:os').tmpdir();
  const dir=fs.mkdtempSync(path.join(tmp,'bountyforge-console-'));
  try{
    const target=path.join(dir,'engine.json');fs.writeFileSync(target,JSON.stringify(config));
    const p=spawnSync('python3',['-m','scripts.repair_engine','--config',target],{cwd:root,encoding:'utf8'});
    assert.equal(p.status,2,p.stderr);
    const response=JSON.parse(p.stdout);
    assert.equal(response.engine,'CODEX_AGENT');
    assert.equal(response.outcome,'CODEX_SESSION_REQUIRED');
    assert.equal(response.additional_model_calls,0);
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
  assert.equal(ui.buildConfig('QWEN_LOCAL','sparse-average').engine,'QWEN_LOCAL');
  assert.throws(()=>ui.buildConfig('PAID_API','sparse-average'));
  assert.throws(()=>ui.buildConfig('CODEX_AGENT','../../private'));
  const experimental=ui.buildConfig('QWEN_LOCAL','weighted-window','QWEN_7B');
  assert.equal(experimental.model_profile,'QWEN_7B');
  assert.throws(()=>ui.buildConfig('CODEX_AGENT','weighted-mix','QWEN_7B'));
  assert.throws(()=>ui.buildConfig('QWEN_LOCAL','weighted-mix','PAID'));
});

test('experimental console configuration selects exact profile in the real CLI',()=>{
  const ui=require(path.join(root,'dashboard/repair-console.js'));
  const dir=fs.mkdtempSync(path.join(require('node:os').tmpdir(),'bf15-console-'));
  try{
    const target=path.join(dir,'engine.json');
    fs.writeFileSync(target,JSON.stringify(ui.buildConfig('QWEN_LOCAL','weighted-window','QWEN_7B')));
    const p=spawnSync('python3',['-m','scripts.repair_engine','--config',target],{cwd:root,encoding:'utf8'});
    assert.equal(p.status,2,p.stderr);const response=JSON.parse(p.stdout);
    assert.equal(response.outcome,'QWEN_UNAVAILABLE');assert.equal(response.model_profile,'QWEN_7B');
    assert.equal(response.additional_model_calls,0);
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
});

test('owner console verifies hash-bound real receipts and rejects tampered outcomes',async()=>{
  const file=path.join(root,'dashboard/repair-console.js');
  assert.ok(fs.existsSync(file),'The owner receipt verifier is missing');
  const ui=require(file);
  const recording=JSON.parse(fs.readFileSync(path.join(root,'evidence/phase12/codex_live_repairs.json')));
  const receipt=recording.calls.map(c=>c.response.result)
    .filter(r=>r && !r.isError).map(r=>JSON.parse(r.content[0].text)).find(r=>r.outcome==='VERIFIED');
  const verified=await ui.verifyReceipt(receipt);
  assert.equal(verified.independently_verified,true);
  assert.equal(verified.engine,'CODEX_AGENT');
  assert.equal(verified.independent_evaluation,false);
  await assert.rejects(ui.verifyReceipt({...receipt,delivery_authorized:true}));
  await assert.rejects(ui.verifyReceipt({...receipt,state:'DELIVERED'}));
});

test('the same owner interface verifies the actual failed Qwen receipt without promoting it',async()=>{
  const ui=require(path.join(root,'dashboard/repair-console.js'));
  const recording=JSON.parse(fs.readFileSync(path.join(root,'evidence/phase12/qwen_canary_39943137925.json')));
  const result=await ui.verifyReceipt(recording);
  assert.equal(result.engine,'QWEN_LOCAL');
  assert.equal(result.state,'EXHAUSTED');
  assert.equal(result.independently_verified,false);
  assert.equal(result.outcome,'REPEATED_PROPOSAL');
});
