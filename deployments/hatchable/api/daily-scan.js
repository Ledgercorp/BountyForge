import { discover } from 'lib/discovery.js';
import { saveScan } from 'lib/scan-store.js';

// Hatchable Free tier: one scheduled scan per day, no AI calls and no paid runners.
// Scheduler-only route; never accepts an external request.
export const access='scheduler';
export const schedule='0 12 * * *';

export default async function(req,res) {
  try {
    const report=await discover();
    await saveScan(report);
    return res.json({state:'saved',scanned_at:report.scanned_at,candidate_count:report.candidates.length,paid_work_claimed:0});
  } catch(error) {
    // Report failure without replacing the last known good scan.
    return res.status(503).json({state:'scan_failed',candidate_count:0,paid_work_claimed:0,error:'GitHub or storage temporarily unavailable.'});
  }
}