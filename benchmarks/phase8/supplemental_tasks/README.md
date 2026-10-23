# Phase 8 supplemental novelty-qualified evaluation

These six original, owned Python fixtures supplement the frozen Phase8 catalog.
They were authored after the repair-session implementation froze at
`48ce3f15a134ba06846d7eda8fe4ac2e594e7563`. No core, prompts or primary
catalog fixtures changed during this work. Each task has one approved
`subject.py`, a stdlib unittest contract, pinned source/test hashes, at most
eight direct-call regression methods and a target body within 30 lines.
There are no reference repairs or generated candidate patches.

The original twenty-case catalog remains unchanged. The semantic audit in
`novelty_review.json` compares every primary case against Phase5 development,
Phase5 structural development, Phase6 evaluation, Phase7 public calibration,
the fixed Phase7 arithmetic rehearsal and all six concurrently authored Phase8
development cases. It compares the intended behavior and defect rather than
relying on different names or hashes. The review records exact comparison
file hashes and rationale for every primary and supplemental case.

`middle_observation` repeats the exposed even-length median repair problem.
`weighted_measurement` repeats the weighted-mean repair problem exposed by
Phase8 DEV `weighted_samples`, despite differences in input shape and the
defective expressions. Both are excluded from claims of fresh evaluation.
Four additional primary cases share broad themes with earlier fixtures;
their contracts and defects differ, and the audit identifies them explicitly.

The pinned `selection.json` takes a conservative approach: it selects fourteen
primary cases after all six exclusions and all six supplemental cases, for
twenty reviewed distinct repair problems. The complete catalogs contain
twenty-four problems after the two semantic duplicates are excluded; this
larger number is not the conservative evaluation denominator. The selection
references both exact manifest hashes and explicit case IDs, and its own hash
is pinned in the static tests. This qualification does not establish broad
real-world novelty or commercial accuracy.

No fixture source or regression method was executed during authoring or review.
All baseline-defect assertions remain static expectations pending admitted,
isolated execution. Static checks only parse syntax, verify identity and inspect
tree shape. Keep supplemental details sealed until this catalog's freeze commit;
retain exact files and expectations thereafter. The separately frozen core must
not be tuned on these cases. Baseline admission and any authorized model
evaluation are separate steps, and runtime or admission blocks must remain
infrastructure outcomes. This work used no inference, internet, paid resources,
customer code, filesystem operations from fixtures, publication or delivery.
