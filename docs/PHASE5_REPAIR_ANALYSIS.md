# Phase 5 repair analysis

Starting revision: `773b2b0499117956b4c138696c78c1f5d6f834c7`.
The fixed evaluation remains the original five curated excerpts and their tests.
No upstream fixes or manually authored repairs enter model context.

`evidence/phase5/historical-call-audit.json` enumerates all 24 calls from hosted
runs 39590337663 (v3) and 39592095298 (v4), including artifact hashes, exact source
revisions, response hashes where retained, timings and evidence limitations.
Regenerate with `python scripts/audit_historical_calls.py`.

| Case | v3 observed failure | v4 observed failure |
| --- | --- | --- |
| 454 | Both rounds staged args2sh then rejected args2cmd: syntax error; no-op. No candidate test executed. | Both candidates failed separator/default contracts; args2cmd concatenated without the required separator. |
| 459 | No-op then unsafe replacement text, before tests. | Both candidates used hnbytes before assignment; identical response hashes. |
| 460 | Omitted n still returned []; retry returned a boolean for zero and compared None with an integer. | Both candidates produced [()] instead of expected pairs/empty list; identical response hashes. |
| 475 | Both changed control flow to read end before its assignment. | Unsafe text rejected first; retry again read end before assignment. |
| 524 | Both candidates broke unit formatting, e.g. 0.0Z instead of 1.0K. | Same incorrect unit output first; unsafe replacement text rejected on retry. |

Every baseline reproduced. Neither experiment passed any case: **0/5, 12 calls
each**. These were model/validation failures after successful isolation admission.
The earlier namespace-blocked run is excluded from these counts.

The original harness saved raw responses only in temporary replay receipts,
then deleted them. Rejected-call latency was not recorded; v3 lacks token/finish
metadata entirely. Consequently exact invalid JSON versus oversized/multiline
text cannot be reconstructed, nor can every statement choice be identified.
The combined 454 test outcome cannot prove each individual symbol was wrong.
All retained v4 finish reasons are `stop`; the evidence does not establish
truncation, timeout, server unavailability or insufficient model size as causes.
Full upstream regression was never executed, so none is labeled its failure.

Protocol weaknesses supported by source inspection: only the trailing 400 failure
characters were supplied; passing contracts and earlier failures were absent;
retries reset source without showing the prior proposal; v3 included an unrelated
boolean-inversion example. These plausibly contribute but do not prove causality.

Opt-in `ast_contract_v5` uses the existing proposer and unchanged stage validator.
It supplies complete function flow and multiline global data dependencies, removes
docstrings/comments, includes acceptance contracts and prior failed proposals,
and removes the unrelated example. It remains within the existing 3600-byte input,
150-token generation, 30-line scope and 3-change/400-byte validators. An oversized
context fails closed. Physical source line splitting now follows Python AST LF
positions, preserving Unicode separators inside literals. Model call metadata is
cleared before requests to prevent stale attribution after a failed call.

Development fixtures live separately from the frozen historical evaluation.
Future experiment transcripts must record raw bounded prompt/response, validation
outcome, timing including rejection, source hash and finish metadata. Historical
scores are updated only by a clean hosted run after development protocol freeze.
