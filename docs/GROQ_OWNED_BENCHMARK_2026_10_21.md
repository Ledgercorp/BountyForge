# BountyForge authenticated Groq 120B owned benchmark, October 21 2026

## The connection and request issue

The owner demonstrated `openai/gpt-oss-120b` working in Groq Playground
under **Personal / Default Project**, using a benign Hello interaction.
The existing GitHub Actions secret was never retrieved or disclosed.

Read-only authenticated [GitHub API GET metadata diagnostic 39676916597](https://github.com/Ledgercorp/BountyForge/actions/runs/39676916597)
returned **HTTP 200** and listed `openai/gpt-oss-120b`.
The first minimal authenticated Chat Completions probe
[39677106215](https://github.com/Ledgercorp/BountyForge/actions/runs/39677106215)
returned **HTTP 200 and a valid model response**. Both used a fixed
non-default `User-Agent`.

Prior Groq adapter attempts had returned 403 while not setting the
same explicit client header. A regression test first failed:
[39677414824](https://github.com/Ledgercorp/BountyForge/actions/runs/39677414824).
The adapter was changed to send `User-Agent: BountyForge-Owned-Canary/1`
without changing authorization, quota limits, model ID, fixed endpoint or
strict JSON schema.
[Hosted regression 39677463529](https://github.com/Ledgercorp/BountyForge/actions/runs/39677463529)
then passed **297 tests, seven existing namespace-rootfs skips**.

The observations identify the adapter/request-shape difference; they do
**not** independently prove which Groq edge security rule returned 403.
Do not claim the provider explicitly blocked Python's default User-Agent.

## The first completed and independently verified GPT-OSS benchmark

- Run: [GitHub Actions 39677572877](https://github.com/Ledgercorp/BountyForge/actions/runs/39677572877).
- Workflow head / report revision: `2d7d389f86d52e75554466be1df020b567eddb6c`
- Provider/model: Groq `openai/gpt-oss-120b`
- Scope: unchanged **structural** four-task owned development set,
  `ast_contract_v5`, pinned public Python image by SHA-256,
  no outside/third-party/customer code.
- **Model-reported and independently replayed results: 2 of 4 passed**
  using **six Groq model calls** (cap eight; minimum 60 seconds apart).
- Qwen2.5-Coder-1.5B frozen structural v5 baseline was 0/4 with eight calls;
  diagnosis-first Qwen v6 baseline was 0/4 with sixteen calls.
- Each owned baseline failure reproduced before generation, and the existing
  stage-lines AST/source SHA validators remained active.
- An independent replay step ran **with zero model calls and no Groq key**,
  reapplying the two reported successful patches and validating
  exactly the two corresponding owned Docker regression suites. Replay
  status: `completed`; verified successes count **2**, IDs exactly
  `optional_banner`, `setting_precedence`.
- GitHub artifact ID `12382877414`, ZIP digest
  `sha256:82ce41a04bb7ddeecccc69caf7075c0c8b7d3c08eab7af859a8d3dfac0956dca`.
  Artifact expires under the current two-day retention policy.

### Task-level findings

| Fixture | Calls | Result | Failure type |
| --- | ---: | --- | --- |
| optional_banner | 1 | **PASS**, independently replayed | none |
| reference_code | 2 | FAIL | two proposals rejected by source validator |
| setting_precedence | 1 | **PASS**, independently replayed | none |
| empty_summary | 2 | FAIL | two changed proposals failed regression tests |

This is a real, narrow controlled improvement over Qwen on four *owned*
structural fixtures, **not** a commercial, arbitrary-code, real-world or
statistically representative success rate. It does not prove the model is
ready for paying customer tasks.

### Safety boundaries

- No customer information, third-party code, private files, secrets or payment
  details were sent in prompts.
- No GitHub write credential reached the model. No external issue claim, code
  submission, customer communication, contract or production deployment.
- The owner attested Groq Free Plan and model quotas in the existing protected
  repository variable, but **actual billing/account entitlement has not been
  independently read**, so no claim of independently verified zero charge.
- The worker remains on GitHub standard hosted Ubuntu, with an immutable
  Docker image. Existing seven namespace-rootfs isolation tests remain skipped
  in the ordinary full CI regression.
- The one-shot branch-only gate was removed in commit
  `26ea8cf77cf7bb7b696e02ab7c9f7ceb177fd567`.
  The final workflow remains **manual-only**, draft PR #2 remains unmerged,
  and no recurring external inference is enabled.

## Next measured engineering work

1. Perform a source/diagnostic review of the two failed tasks. Improve the
   patch-generation interface or diagnostics only if the source/test contracts
   and security restrictions remain intact. Avoid training on held-out answers
   and then claiming independent evaluation.
2. Run a separate frozen, genuinely independent historical benchmark after
   explicit authorization and quota review, not repetitive synthetic tests.
3. Require independently reviewed hostile-code isolation and private customer
   intake before admitting real paid jobs.
4. Preserve the 2/4 result and replay evidence as baseline. No false
   'production ready' or revenue claims. Customer payment and delivery
   permissions are separate from model output.
