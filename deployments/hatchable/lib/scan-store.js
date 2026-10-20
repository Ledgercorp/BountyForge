import { db } from 'hatchable';

export async function saveScan(report) {
  // Store only candidate summaries from public GitHub issues, never tokens or private credentials.
  await db.query('INSERT INTO bounty_scan_history (source, candidate_count, report) VALUES ($1, $2, $3::jsonb)', [
    'github_public', report.candidates.length, JSON.stringify(report)
  ]);
}
export async function getLatestScan() {
  const result=await db.query('SELECT report, scanned_at FROM bounty_scan_history ORDER BY scanned_at DESC, id DESC LIMIT 1');
  const entry=result.rows[0];
  if (!entry) return {state:'empty',candidates:[],message:'No successful scan has run yet.'};
  const report=typeof entry.report==='string'?JSON.parse(entry.report):entry.report;
  if (!report || !Array.isArray(report.candidates)) throw Error('Invalid stored scan');
  return {...report, source:'Saved scan · '+report.source};
}