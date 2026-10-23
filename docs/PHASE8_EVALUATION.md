# Phase8 owned preparation and recorded replay

The repair core is frozen at `48ce3f15a134ba06846d7eda8fe4ac2e594e7563`.
The default selection pins the original twenty-case primary manifest from
`f55ad34`. Its novelty audit remains pending: prior-task overlap can limit any
future generalization claim. Preparation measures Docker baseline reproduction
and whether the frozen session can construct bounded context. It does not
measure repair accuracy.

Run from the repository root:

```sh
python -m scripts.phase8_evaluate --prepare --output /tmp/phase8-prepare.json
```

The coordinator never constructs or invokes a provider. Live inference remains
disabled because FreePlan and budget authority are unverified. Reports contain
`accuracy: null`, `inference_calls: 0` and `inference_seconds: 0`. No argument or
caller boolean can authorize paid inference. A future inference API needs
independently established financial authority, at most four selected cases,
eight requests across one fresh model instance, and no fallback or reset of the
provider's request counter. The existing `repair_session.repair_owned` must
remain unchanged.

Each preparation invocation rechecks literal frozen-core hashes and selected
manifest/source/test pins, then runs fresh fixed controls through
`curated_docker.verify_runtime_boundary` on its admitted owned control fixture.
All twenty proof fields, the pinned image digest and the explicit absence of
arbitrary-source certification are required. The existing Docker primitive uses
`--pull never`, no network, read-only mounts, no credentials, an unprivileged
UID and bounded resources. No image download or host subject execution occurs.

Each selected original is copied once and gets an exact `owned-phase8-<id>`
marker. Admission checks the exact source/test/marker tree, exact directories,
hashes, file sizes, hardlinks, symlinks and special objects before and after
every test invocation. Extra files and empty directories are rejected. A strict
unittest receipt must complete; only assertion-failure baselines count as
reproduced defects. The coordinator uses the same deterministic localization
and `make_prompt` as the frozen session, retaining context failures as per-case
blocked reasons. Counts record actual baseline invocations and receipts.
`baseline_invocations` counts calls dispatched to the Docker primitive;
`baseline_receipts` counts valid completed receipts. A launch failure can leave
these counts different. The CLI atomically checkpoints the bounded JSON report
before each dispatch and after every case, keeping `baseline_pending` and
`preparing` labels if interrupted. API callers can request the same durable
checkpoints with `report_path=`. The CLI always writes a checkpoint file;
`--output` defaults to `evidence/phase8/prepare.json`.

The prepared prompt is the session middleware's provider context. It differs
from the frozen worker's internal prepared context. Preparation establishes
that the session prompt fits; the frozen worker can still reject its own
earlier preparation before reaching middleware. No inference success is
inferred from context readiness.

## Explicit catalog selections

Use an independently reviewed selection file and its exact digest to select
primary cases or a later supplemental manifest without changing the engine:

```json
{
  "schema": 1,
  "novelty": "Describe the reviewed overlap and novelty qualification here.",
  "manifests": [
    {
      "path": "benchmarks/phase8/evaluation_tasks/manifest.json",
      "sha256": "6c01abe0e35fafbb7aee4de108b512ff53c2f9b0150e3191c3c57b04ae771687",
      "case_ids": ["stock_admission"]
    }
  ]
}
```

```sh
python -m scripts.phase8_evaluate --prepare \
  --selection /tmp/reviewed-selection.json \
  --selection-sha256 <independently-reviewed-digest>
```

The caller-selected digest is a trust input. It does not establish originality
or financial authority. Manifest paths must stay under this repository's
`benchmarks/phase8` directory; each manifest must use the owned sealed catalog
schema and pin each source/test pair. Selected IDs must be unique across all
catalogs. Config bytes, manifests, core and selected trees are rechecked before
each test admission. Keep the reviewed selection and its pin with evidence.

## Independent recorded-candidate replay

`bountyforge.phase8_evaluation.replay(record, selection_file=...,
selection_sha256=...)` accepts one object shaped as:

```json
{"case_id": "selected_case_id", "session": "the full recorded repair_owned result object"}
```

The session must report `review_ready` and contain exact source/test pins,
deterministic scope, baseline receipt, top-level actual requests and responses,
worker attempts, exact patch and candidate digest. Replay validates response
hashes and retry linkage, rebuilds provider context from pinned source and
contracts, runs the unchanged stricter binding guard and `stage_statements`,
and compares the exact diff. Invalid records are blocked before Docker.
Admission then requires a fresh twenty-control preflight and credential-free
Docker verification of the bound candidate in a disposable copy.

`replay_passed` establishes that the recorded candidate passed this fresh
owned regression run. It does not authenticate who generated the transcript,
reproduce live inference, or certify a legitimate real-world fix. Replay keeps
`accuracy: null` and makes zero inference requests. No reference repairs are
used as model scores.

Tests use mock Docker/preflight results to check coordinator behavior and truth
labels. They never import evaluation subjects or run their source on the host.
