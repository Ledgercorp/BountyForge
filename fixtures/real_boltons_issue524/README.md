# Real upstream issue reproduction, excerpt only

Issue: https://github.com/mahmoud/boltons/issues/524 (open when reviewed October 20, 2026)
Source: https://github.com/mahmoud/boltons/blob/master/boltons/strutils.py
Upstream blob: `74441c7e39dc5a666d76ca559f2ea6b80b3372c6`

`strutils.py` is an isolated reproduction comprising the exact upstream constants and `bytes2human` function with a BountyForge provenance comment. **This is not a full GitHub checkout of Boltons.**

The BSD-3-Clause license of boltons applies to the copied excerpt. See https://github.com/mahmoud/boltons/blob/master/LICENSE. No public contribution has been made.

The added tests reproduce the three exact GitHub issue examples and two existing documented behaviors. Baseline: 3 failures and 2 passes. The assistant-authored patch in `evidence/issue524_assistant_draft.diff` produced 5/5 passes within the isolated runner. The actual Qwen model failed two bounded proposals (unauthorized path, then malformed Python), so **Qwen did not repair this issue.**