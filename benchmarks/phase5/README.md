These four owned Python fixtures form the Phase 5 development set. They are
separate from the unchanged five historical Boltons evaluation cases. Fixture
source and acceptance tests are pinned by SHA-256 in `tasks/manifest.json`.
Never count their results as historical repairs or commercial bounty work.

`python -m benchmarks.phase5.development_runner --output evidence-run/phase5-development.json`
uses the existing numeric-loopback model, shared line validator and unchanged
hardened Docker command. It first runs the existing independent runtime
admission probes on an exact trusted historical baseline without executing its
source. Development execution then admits only this fixed owned catalog, exact
tests and source reconstructed from validated proposal receipts. No network or
dependency installation is provided. At most eight calls run, in one stream.

The report records raw bounded prompts/responses and call latency even when
staging rejects a candidate. Prompts contain owned fixture source and tests only.
The next call may include its previous proposal and failure. These are retry
data, never permission to widen the editable scope.

`--suite structural` selects a second, separately pinned four-task catalog.
It exercises optional text formatting, ASCII reference validation through a
global dependency, dictionary override precedence, and branch-local state for
empty inputs. Neither catalog changes the historical evaluation tasks.

Use `--protocol ast_contract_v5` or `--protocol ast_contract_v6` for the
structural comparison. V6 makes a bounded diagnosis call before its patch call;
each call is recorded with `kind` and latency, including rejected diagnoses and
endpoint errors. Each run selects exactly four tasks. V5/legacy run at most
eight calls; V6 runs at most sixteen. A failed diagnosis never reaches patch
inference. All patch candidates retain the original admission and validators.
