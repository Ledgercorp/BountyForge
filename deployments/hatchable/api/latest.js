import { getLatestScan } from 'lib/scan-store.js';

export const access='admin';
export const methods=['GET'];
export default async function(req,res) {
  res.setHeader('Cache-Control','no-store');
  try {
    return res.json(await getLatestScan());
  } catch(error) {
    return res.status(503).json({state:'storage_unavailable',error:'Unable to read the saved scan.'});
  }
}