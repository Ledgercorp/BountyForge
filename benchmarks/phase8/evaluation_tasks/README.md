# Phase 8 sealed owned maintenance evaluation

This catalog contains 20 original Python maintenance fixtures authored separately
from the Phase 8 repair-session implementation. Each directory contains one
approved `subject.py` and a fixed `tests/test_regression.py` contract. There are no
reference repairs, generated candidate patches, external dependencies, downloads,
network operations or customer material. Copyright and licensing follow this
repository's MIT license.

The tasks cover distinct maintenance categories and include scalar, branching,
loop-state, binding, ordering and multiline-expression defects. They deliberately
fit the existing bounded one-function Python profile: at most 30 body lines,
direct target calls from each regression method, and at most eight methods per
case. Existing source capabilities suffice for intended behavior; no import or
new callable capability is required. Unsupported model edits must still fail the
existing validators. These owned fixtures do not establish real-world accuracy,
private-code safety or commercial readiness.

The manifest records the exact source and test SHA-256 values, original
provenance, base revision and requirements. The catalog was authored without
using historical upstream fixes or solutions from the earlier exposed benchmarks.
Static inspection identified intended assertion failures and guarded invalid
inputs. That inspection is not an executed baseline measurement: **no subject or
regression test has been executed before security admission**. The separate
`tests/test_phase8_catalog.py` checks only file hashes and parsed syntax/tree shape.

Keep this catalog sealed from the implementation agent until its new session
architecture is frozen at an exact commit. Pin the resulting manifest hash in the
admitted evaluator, reproduce every baseline in the approved isolated environment,
and reject runtime errors or admission failures as infrastructure blocks rather
than model failures. Preserve the fixtures and acceptance tests unchanged during
evaluation. Record exposure after unsealing; subsequent tuning on these tasks
cannot be represented as fresh independent evaluation. Do not add manual fixes
or count them as autonomous successes.
