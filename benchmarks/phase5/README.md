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
