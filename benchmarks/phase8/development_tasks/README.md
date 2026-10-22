# Phase 8 owned development fixtures

These six original, owned maintenance examples are **development material**.
They are not held-out evaluation cases, commercial work or evidence of model
repair accuracy. The sealed evaluation set is outside this catalog and was not
read or changed while authoring these fixtures.

`manifest.json` pins each baseline source and acceptance test by SHA-256.
`reference_changes` are manually authored **DEV_ONLY** statement proposals.
They may validate the development harness, but must never be supplied as model
answers, counted as autonomous successes or included in an evaluation prompt.
Production prompts may select the description, original source and tests;
reference fields stay in the development plane.

| Case | Maintenance behavior | Development purpose |
| --- | --- | --- |
| `configuration_values` | Colons inside setting values, comments, whitespace and overrides | Distinguish an unpacking error from syntax or infrastructure failure |
| `stable_partition` | Preserve membership, duplicates and both output orders | Protect behavior outside the failing branch and preserve inputs |
| `weighted_samples` | Nonnegative weighted aggregation and zero-weight handling | Correct two related accumulator statements in one bounded proposal |
| `discount_continuation` | Percentage reduction, range checks and rounding | Replace a complete multiline assignment through its AST anchor |
| `canonical_headers` | Empty component handling and normalized header text | Replace a multiline return while preserving ordinary inputs |
| `status_priority` | Success, unknown-status and transient retry precedence | Edit an expression inside a multiline condition without changing branches |

All source is one approved `subject.py` per case. Tests use only Python's
standard library. Every reference uses the unchanged `stage_statements`
validator, deterministic `editable_scope` anchors, at most three changes and
at most three replacement physical lines per change. No reference requests a
path, command, import, credential or new execution capability.

Offline catalog and admission checks:

```sh
python -m unittest discover -s tests -p test_phase8_development.py -v
```

Explicit owned-only Docker reference validation:

```sh
BOUNTYFORGE_PHASE8_DEV_DOCKER=1 python -m unittest discover -s tests -p test_phase8_development.py -v
```

The optional integration check first proves the existing pinned Docker runtime
boundary with trusted probes. Only a fixed catalog ID and a baseline/reference
flag can select fixture execution. Exact source/test bytes, marker, file tree,
hardlinks and symlinks are checked before the unchanged hardened Docker command
runs. There is no host execution fallback or caller-supplied candidate executor.

Set `BOUNTYFORGE_PHASE8_DEV_EVIDENCE` to an explicit output file to retain the
bounded validation report. Its labels keep model calls and model-generated
repairs at zero, regardless of whether the manual development references pass.
