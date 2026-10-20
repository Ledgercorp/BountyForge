import { discover } from 'lib/discovery.js';
import { saveScan } from 'lib/scan-store.js';

export const access = 'admin';
export const methods = ['GET'];

export default async function(req,res) {
  res.setHeader('Cache-Control','no-store');
  try {
    const report=await discover();
    try {
      await saveScan(report);
    } catch (error) {
      return res.status(503).json({state:'storage_unavailable',error:'GitHub responded, but the report could not be saved; no stale data was substituted.'});
    }
    return res.json(report);
  } catch(error) {
    return res.status(error?.status===503?503:500).json({state:'unavailable',error:'Bounty search unavailable. No results were fabricated.'});
  }
}