// Shared, read-only GitHub Search adapter. No tokens, paid models or writes.
const searchURL = 'https://api.github.com/search/issues?q=' + encodeURIComponent('is:issue is:open bounty in:title') + '&sort=updated&order=desc&per_page=25';
const amounts = [/(?<!\w)\$\s*([1-9][\d,]{0,8}(?:\.\d{1,2})?)\s*([kKmM])?(?!\w)/g, /\bUSD\s+([1-9][\d,]{0,8}(?:\.\d{1,2})?)\s*([kKmM])?(?!\w)/gi];

function clean(issue) {
  if (!issue || issue.pull_request || typeof issue.title !== 'string') return null;
  const url = String(issue.html_url || '');
  // Fixed GitHub issue paths only. No redirects, embed or HTML rendering in UI.
  const match = /^https:\/\/github\.com\/([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+)\/issues\/(\d+)$/.exec(url);
  if (!match) return null;
  const title = issue.title.slice(0, 220);
  const body = String(issue.body || '').slice(0, 5500);
  const combined = (title + '\n' + body).toLowerCase();
  const amountsUSD = new Set();
  for (const re of amounts) {
    re.lastIndex = 0;
    for (const m of (title + '\n' + body).matchAll(re)) {
      const multiplier = m[2] ? ({k:1000,m:1000000}[m[2].toLowerCase()] || 1) : 1;
      const n = Number(m[1].replace(/,/g, '')) * multiplier;
      if (Number.isSafeInteger(n) && n > 0 && n <= 100000) amountsUSD.add(n);
    }
  }
  let score = 0;
  const reasons = [];
  const name = title.toLowerCase();
  if (name.includes('bounty')) {score += 25; reasons.push('Bounty mentioned in title')}
  if (name.includes('reward')) {score += 18; reasons.push('Reward mentioned in title')}
  if (amountsUSD.size) {score += 20; reasons.push('Amount mentioned, not verified')}
  if (combined.includes('acceptance criteria') || combined.includes('steps to reproduce')) {score += 12;reasons.push('Acceptance details found')}
  if (body.length >= 200) score += 8;
  if (['proposal','radar','alert','bounty board','discovery'].some(x => name.includes(x))) {score -= 40;reasons.push('Likely proposal or aggregator')}
  if (name.startsWith('application:') || combined.includes('i would like to apply for')) {score -= 50;reasons.push('Applicant post, not an available task')}
  if (!amountsUSD.size && ['bounty on you','bounty hunter','player bounty','nation\'s bounty','wanted bounty'].some(x => combined.includes(x))) {score -= 55;reasons.push('Game mechanic, not paid development work')}
  if (['claude api','openai api','paid subscription','gpu required','hardware required'].some(x => combined.includes(x))) {score -= 25;reasons.push('Potential paid dependency')}
  if (['already claimed','closed bounty','first come first served'].some(x => combined.includes(x))) {score -= 35;reasons.push('Possible competition/unavailability')}
  return {
    url, title, repository: match[1] + '/' + match[2], number:Number(match[3]),
    score:Math.max(0,Math.min(score,100)), amounts_usd:[...amountsUSD].sort((a,b)=>a-b),
    label:'UNVERIFIED', reasons, excerpt:body.slice(0,560),
    updated_at:typeof issue.updated_at==='string'?issue.updated_at:''
  };
}

export async function discover() {
  let response;
  try {
    response = await fetch(searchURL, {headers:{Accept:'application/vnd.github+json', 'User-Agent':'LeftSock-BountyForge/0.3', 'X-GitHub-Api-Version':'2022-11-28'}});
  } catch (e) {
    const problem=new Error('External GitHub request failed');problem.status=503;throw problem;
  }
  if (response.status===403 || response.status===429) {
    const problem=new Error('GitHub Search is rate-limited. Retry later.');problem.status=503;throw problem;
  }
  if (!response.ok) {
    const problem=new Error('GitHub Search unavailable.');problem.status=503;throw problem;
  }
  let raw;
  try {raw=await response.json()} catch { const problem=new Error('Invalid upstream JSON');problem.status=503;throw problem; }
  if (!raw || !Array.isArray(raw.items)) {
    const problem=new Error('Unexpected GitHub Search response');problem.status=503;throw problem;
  }
  const candidates=raw.items.map(clean).filter(Boolean).sort((a,b)=>b.score-a.score || a.url.localeCompare(b.url));
  return {state:'ok',source:'GitHub public issue search',scanned_at:new Date().toISOString(),candidates,earning_usd:0,verified_count:0,disclaimer:'Discovery only: payouts, availability and eligibility are unverified. No submissions were made.'};
}