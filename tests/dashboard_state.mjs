import test from 'node:test';
import assert from 'node:assert/strict';
import {projectState} from '../dashboard/operations-state.mjs';
const ready = () => ({version:1,discoveries:[],jobs:[{
  state:'review_ready',updated:100,input_json:JSON.stringify({kind:'synthetic',fixture_id:'addition',revision:'a'.repeat(40)}),
  result_json:JSON.stringify({status:'synthetic_review_ready',commercial_review_ready:false,external_submission:false,
    evidence_sha256:'b'.repeat(64),run_url:'https://github.com/Ledgercorp/BountyForge/actions/runs/123'})}]});
test('only synthetic readiness and exact evidence link are exposed', () => {
  const r=projectState(ready());assert.equal(r.readiness,'DRY_RUN_READY');assert.equal(r.real_review_ready,0);
  assert.equal(r.recurring_repair_schedule_active,false);assert.equal(r.synthetic_cycles_completed,1);
});
test('arbitrary run URLs or commercial promotion fail closed', () => {
  const r=ready();r.jobs[0].result_json=JSON.stringify({status:'review_ready',commercial_review_ready:true});
  assert.throws(()=>projectState(r));
});
test('unknown or unavailable ledger does not invent healthy state', () => {
  assert.throws(()=>projectState(null));assert.equal(projectState({version:1,jobs:[],discoveries:[]}).readiness,'NOT_READY');
});
test('expired leases are separated from active worker claims', () => {
  const r=ready();r.jobs[0].state='running';r.jobs[0].lease_until=10;r.jobs[0].result_json=null;
  const x=projectState(r,20);assert.equal(x.active_leases,0);assert.equal(x.expired_leases,1);assert.equal(x.readiness,'NOT_READY');
});
