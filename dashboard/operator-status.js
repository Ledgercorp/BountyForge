import {db} from 'hatchable';
import {projectState} from '../lib/operations-state.js';
export const access='admin';
export const methods=['GET'];

export default async function(req,res) {
  res.setHeader('Cache-Control','no-store');
  try {
    const saved=await db.query('SELECT COUNT(*) AS scans_saved, MAX(scanned_at) AS last_scan_at FROM bounty_scan_history');
    const recent=await db.query('SELECT report FROM bounty_scan_history ORDER BY scanned_at DESC, id DESC LIMIT 1');
    const raw=recent.rows?.[0]?.report;
    const report=typeof raw==='string'?JSON.parse(raw):(raw||{});
    let operations=null;
    try {
      const response=await fetch('https://raw.githubusercontent.com/Ledgercorp/BountyForge/state/bountyforge-ledger-v1/state/ledger.json?observed='+Math.floor(Date.now()/30000),
                                 {signal:AbortSignal.timeout(5000),headers:{'Accept':'application/json'}});
      if(!response.ok)throw Error('Ledger unavailable');
      const text=await response.text();
      if(text.length>512000)throw Error('Ledger too large');
      operations=projectState(JSON.parse(text));
    } catch(e) { /* Keep unknown status unknown; never infer model health. */ }
    return res.json({
      state:'ok',data_source:'Private discovery history and public GitHub durable coordination ledger',
      hosted_worker:operations?.synthetic_cycles_completed>0?'github_actions_internal_cycles_verified':'status_unavailable',
      cpu_model_on_hatchable:'not_running_here',operations,
      saved_discovery_scans:Number(saved.rows?.[0]?.scans_saved||0),
      last_scan_at:saved.rows?.[0]?.last_scan_at||null,
      discovered_candidates:Array.isArray(report.candidates)?report.candidates.length:0,
      verified_funded:0,third_party_repair_attempts:0,pending_external_submissions:0,
      confirmed_earnings_usd:0,paid_ai_calls:0,actual_hatchable_bill_usd:null,
      historical_benchmark:{attempted:5,passed:0,model_calls:12,
        run_url:'https://github.com/Ledgercorp/BountyForge/actions/runs/39592095298',
        scope:'curated_excerpts_only_no_full_upstream_suite'},
      note:'Bounded internal Qwen cycles run on standard GitHub-hosted Linux runners. No recurring repair schedule or approved real opportunity. Model health between runs and provider bills are not inferred.'
    });
  } catch(e) {
    return res.status(503).json({state:'data_unavailable',error:'Operational status cannot be read; live metrics not fabricated.'});
  }
}
