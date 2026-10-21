// Pure read-only projection. Remote data never chooses commands or URLs.
export function projectState(ledger, now = Date.now()/1000) {
  if (!ledger || ledger.version !== 1 || !Array.isArray(ledger.jobs) || ledger.jobs.length > 100 ||
      !Array.isArray(ledger.discoveries) || ledger.discoveries.length > 1000) throw Error('Invalid ledger');
  const jobs = ledger.jobs.map(job => {
    const input = JSON.parse(job.input_json);
    const result = job.result_json ? JSON.parse(job.result_json) : null;
    if (input.kind !== 'synthetic' || input.fixture_id !== 'addition' || !/^[a-f0-9]{40}$/.test(input.revision) ||
        !['queued','running','failed','review_ready'].includes(job.state) || !Number.isFinite(job.updated)) throw Error('Invalid job');
    if (result && result.status === 'synthetic_review_ready' &&
        (result.commercial_review_ready !== false || result.external_submission !== false ||
         !/^[a-f0-9]{64}$/.test(result.evidence_sha256) ||
         !/^https:\/\/github.com\/Ledgercorp\/BountyForge\/actions\/runs\/[1-9][0-9]*$/.test(result.run_url))) throw Error('Untrusted result');
    if (job.state === 'review_ready' && result?.status !== 'synthetic_review_ready') throw Error('Unproven ready state');
    return { ...job, input, result };
  });
  const complete = jobs.filter(j => j.state === 'review_ready' && j.result?.status === 'synthetic_review_ready');
  const latest = complete.sort((a,b) => b.updated-a.updated)[0];
  return {
    readiness: latest ? 'DRY_RUN_READY' : 'NOT_READY',
    execution_scope: 'owned_synthetic_only',
    active_leases: jobs.filter(j => j.state === 'running' && j.lease_until > now).length,
    expired_leases: jobs.filter(j => j.state === 'running' && j.lease_until <= now).length,
    synthetic_cycles_completed: complete.length,
    failed_internal_jobs: jobs.filter(j => j.state === 'failed').length,
    unverified_discoveries: ledger.discoveries.length,
    latest_revision: latest?.input.revision || null,
    latest_run: latest?.result.run_url || null,
    latest_evidence_sha256: latest?.result.evidence_sha256 || null,
    recurring_repair_schedule_active: false,
    real_review_ready: 0,
    revenue_usd_confirmed: 0,
    external_submissions: 0,
    paid_inference: false,
  };
}
