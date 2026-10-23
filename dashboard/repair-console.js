(function (root) {
  'use strict';
  const engines = ['QWEN_LOCAL', 'CODEX_AGENT'];
  const cases = ['sparse-average', 'label-order', 'weighted-mix', 'optional-setting', 'chunk-count', 'inclusive-window',
    'invoice-summary','event-reducer','cursor-adapter','reading-groups','retry-policy','stock-allocation',
    'reserve-release','response-normalize','weighted-window'];
  const profiles = ['QWEN_1_5B', 'QWEN_7B'];
  function buildConfig(engine, caseId, profile) {
    if (!engines.includes(engine) || !cases.includes(caseId)) throw Error('Unsupported owned selection');
    if (profile !== undefined && (engine !== 'QWEN_LOCAL' || !profiles.includes(profile))) throw Error('Unsupported local model profile');
    return {engine, case_id: caseId, ...(profile === undefined ? {} : {model_profile:profile})};
  }
  function canonical(value) {
    if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
    if (value && typeof value === 'object') return '{' + Object.keys(value).sort()
      .map(key => canonical(key) + ':' + canonical(value[key])).join(',') + '}';
    return JSON.stringify(value).replace(/[\u007f-\uffff]/g, char => '\\u' + char.charCodeAt(0).toString(16).padStart(4, '0'));
  }
  async function verifyReceipt(input) {
    const receipt = input?.verification_receipt || input?.result?.verification_receipt || input;
    if (!receipt || receipt.kind !== 'owned_dual_engine_verification' || !engines.includes(receipt.engine) ||
        !cases.includes(receipt.case_id) || receipt.delivery_authorized !== false ||
        receipt.customer_execution_authorized !== false || receipt.independent_evaluation !== false ||
        typeof receipt.independently_verified !== 'boolean' ||
        !['VERIFIED','SOURCE_REJECTED','REPEATED_PROPOSAL','TEST_FAILED','INDEPENDENT_VERIFICATION_FAILED','SANDBOX_UNAVAILABLE'].includes(receipt.outcome) ||
        !['REVISION_REQUIRED','EXHAUSTED','BLOCKED','AWAITING_OWNER_APPROVAL'].includes(receipt.state) ||
        !/^[a-f0-9]{64}$/.test(receipt.receipt_sha256)) throw Error('Unsupported or unauthorized receipt');
    if ((receipt.outcome === 'VERIFIED') !== receipt.independently_verified ||
        (receipt.state === 'AWAITING_OWNER_APPROVAL') !== receipt.independently_verified) throw Error('Contradictory repair state');
    if (receipt.model_profile !== undefined && (receipt.engine !== 'QWEN_LOCAL' || !profiles.includes(receipt.model_profile))) throw Error('Unsupported local model identity');
    if (receipt.independently_verified && (receipt.outcome !== 'VERIFIED' ||
        receipt.state !== 'AWAITING_OWNER_APPROVAL' || receipt.targeted?.passed !== true ||
        receipt.independent?.passed !== true)) throw Error('Contradictory verification outcome');
    const unsigned = {...receipt}; delete unsigned.receipt_sha256;
    const crypto = root.crypto || (typeof require === 'function' ? require('node:crypto').webcrypto : null);
    if (!crypto?.subtle) throw Error('Browser cryptographic hashing is unavailable');
    const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(canonical(unsigned)));
    const actual = Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join('');
    if (actual !== receipt.receipt_sha256) throw Error('Receipt hash mismatch');
    return {engine:receipt.engine,case_id:receipt.case_id,state:receipt.state,outcome:receipt.outcome,
      model_profile:receipt.model_profile || (receipt.engine === 'QWEN_LOCAL' ? 'QWEN_1_5B' : null),
      independently_verified:receipt.independently_verified,independent_evaluation:false,
      hash_valid:true,signature_verified:false,delivery_authorized:false,
      tests_run:receipt.independent?.tests_run || receipt.targeted?.tests_run || 0};
  }
  const api = {buildConfig, verifyReceipt};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.BountyForgeRepairConsole = api;
  if (typeof document === 'undefined') return;
  document.addEventListener('DOMContentLoaded', () => {
    const engine = document.getElementById('engine'), task = document.getElementById('case'), profile = document.getElementById('model-profile');
    const selected = () => buildConfig(engine.value, task.value, engine.value === 'QWEN_LOCAL' ? profile.value : undefined);
    function update() {
      profile.disabled = engine.value !== 'QWEN_LOCAL';
      const config = selected();
      document.getElementById('configuration').textContent = JSON.stringify(config, null, 2);
      document.getElementById('availability').textContent = engine.value === 'CODEX_AGENT'
        ? 'Requires an active Codex session through MCP. Separate unattended Codex inference is unavailable.'
        : 'Selected: ' + profile.value + '. Linux checks this exact model, runtime and required limits. No model fallback. Browser availability is unmeasured; 7B is experimental and rejects rendered prompts above 700 tokens.';
      document.getElementById('command').textContent = 'python -m scripts.repair_engine --config bountyforge-owned-engine.json';
    }
    engine.addEventListener('change', update);task.addEventListener('change', update);profile.addEventListener('change', update);update();
    document.getElementById('download').addEventListener('click', () => {
      const data = JSON.stringify(selected(), null, 2) + '\n';
      const url = URL.createObjectURL(new Blob([data], {type:'application/json'}));
      const a = document.createElement('a');a.href = url;a.download = 'bountyforge-owned-engine.json';
      a.click();setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    document.getElementById('receipt-file').addEventListener('change', async event => {
      const output = document.getElementById('verification');
      try {
        const file = event.target.files[0];
        if (!file || file.size > 100000) throw Error('Select a bounded owned receipt');
        output.textContent = JSON.stringify(await verifyReceipt(JSON.parse(await file.text())), null, 2);
      } catch (_) { output.textContent = 'UNVERIFIED — the local receipt is unsupported, inconsistent or tampered.'; }
    });
  });
})(globalThis);
