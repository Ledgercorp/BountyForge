# Phase 4 | Targeted reliability continuation

**Date:** 2026-10-20. **Scope:** inspected Boltons historical function excerpts, not a complete upstream checkout.

## Measured outcome

The original five-issue historical benchmark remains **0/5 complete issue repairs across eight local Qwen calls**. These new focused, manually localized subfunction probes are a different protocol and MUST NOT be compared as a new five-issue success rate.

* Boltons PR #460: three new Qwen calls, zero passing repairs. The model repeated an invalid source line, then generated an invalid boolean expression.
* Boltons PR #475: two new Qwen calls, zero passing repairs. The outputs lacked valid complete Python source.
* Boltons PR #454, args2sh: one real Qwen call generated `sep.join(ret_list)`. The initial raw response had incorrect indentation and was rejected. After developing an explicit, deterministic original-indent-preserving formatter, its unchanged generated expression passed **4/4 targeted tests**.
* Boltons PR #454, args2cmd: one real Qwen call hardcoded `|`, fixing the custom case but breaking the default. One bounded retry using the failing default test's output generated `result.append(sep)` and passed **5/5 targeted tests**.

These eight new model calls provide **two narrow successful historical subfunction repairs** after trusted manual location selection. They do not demonstrate independently solved full GitHub issues or production-readiness. The model was not given reference patches.

## Implemented changes and validation

* `bountyforge/lineedit.py` ties generated changes to a trusted path, source SHA-256 and exact approved line numbers. The model does not supply a path. Unsafe JSON, duplicate/unapproved lines, stale sources and invalid Python are refused.
* The system prompt is smaller and no longer contains a sample replacement that could be echoed as code.
* The context includes the enclosing function signature, preserving parameters such as `sep` or `n=None` even when distant from the target line.
* The validator preserves original base indentation and relative multiline indentation. It labels this deterministic formatting change explicitly in the result; it does not change model-authored expression bytes beyond indentation.
* Root-level test files and tab-indented edits are explicitly denied.
* **16/16 focused tests passed** in Linux, using byte-for-byte matching GitHub source and Git blob verification for lineedit.py, test_lineedit.py and drafts.py. This is not the complete BountyForge suite.
* The legacy five-issue benchmark now saves results to the correct top-level `evidence` folder and rejects HTTP redirects from its loopback model endpoint. The historical baseline receipts were not regenerated.

## Boundaries

Original historical source excerpts were manually inspected and isolated in disposable Linux directories with unprivileged namespace tests. The model did not get a real third-party code execution permit. No full upstream repository suite was run, no external issue was modified, no PR was opened and no payment was claimed. The rootless sandbox is not certified for hostile code and lacks per-job cgroups. No unattended free CPU inference server was deployed; the measured server was temporary.

**New paid AI calls:** 0. **Confirmed earnings:** $0. **Additional billable compute provisioned:** none. Provider billing totals were not independently audited.

Historical issues: https://github.com/mahmoud/boltons/pull/454, https://github.com/mahmoud/boltons/pull/460, https://github.com/mahmoud/boltons/pull/475.
Machine-readable results: `evidence/phase4_targeted_repair_2026_10_20.json`.

## Next gate

Add this strategy to the **synthetic-only** queued worker behind an opt-in switch, run the entire repository regression suite and evaluate an independent holdout before sending tasks to the paid-opportunity queue. Do not equate assistant-located target lines with autonomous fault localization.
