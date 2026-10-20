import {db} from 'hatchable';
export const access='admin';
export const methods=['GET'];
export default async function(req,res) {
  res.setHeader('Cache-Control','no-store');
  try {
    const r=await db.query('SELECT COUNT(*) AS scans_saved, MAX(scanned_at) AS last_scan_at FROM bounty_scan_history');
    const count=Number(r.rows?.[0]?.scans_saved||0);
    const recent=await db.query('SELECT report FROM bounty_scan_history ORDER BY scanned_at DESC, id DESC LIMIT 1');
    const raw=recent.rows?.[0]?.report;
    const report=typeof raw==='string'?JSON.parse(raw):(raw||{});
    return res.json({
      state:'ok',data_source:'Hatchable private Postgres and independently committed engineering evidence',
      hosted_worker:'not_deployed',cpu_model_on_hatchable:'not_available',
      active_hosted_jobs:0,completed_hosted_jobs:0,failed_hosted_jobs:0,
      saved_discovery_scans:count,last_scan_at:r.rows?.[0]?.last_scan_at||null,
      discovered_candidates:Array.isArray(report.candidates)?report.candidates.length:0,
      verified_funded:0,third_party_repair_attempts:0,pending_external_submissions:0,
      confirmed_earnings_usd:0,paid_ai_calls:0,
      actual_hatchable_bill_usd:null,
      note:'Real Linux CPU repair acceptance exists, but is a separate temporary workspace. Runtime status is not live-linked to this hosting tier. Billing not independently retrieved.'
    });
  } catch(e) {
    return res.status(503).json({state:'data_unavailable',error:'Operational status cannot be read; live metrics not fabricated.'});
  }
}