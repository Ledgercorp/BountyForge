# BountyForge controlled Qwen acceptance

Local Linux Qwen2.5-Coder 1.5B inference with line-edit validation passed three small owned synthetic defect tests on the first attempt: addition, multiplication and increment. The original source remained unchanged and the patched disposable copies passed each targeted test. These are manually orchestrated controlled trials, not a complete BountyForge worker or GitHub Actions acceptance run.

The old prompt returned repeated nested function declarations for addition, which the hardened validator rejected. A general example illustrating single-line JSON replacements improved the three synthetic cases. Model hash was checked. No paid inference, external submission or bounty revenue occurred.

Remaining gates: complete repository regression, five historical Boltons model benchmark, safe third-party execution verification and confirmed zero-overage GitHub Actions billing. Keep scheduled work disabled.

## Follow-up reproduction

A subsequent independent local addition replay on the same small synthetic fixture required two model requests: the first failed syntax validation and was rejected, and the second passed the targeted test. This demonstrates that the model's first-attempt success is not stable even on curated examples. The observed two-attempt cap remained intact. The 3/3 initial first-attempt observation is one specific run, not a general reliability statistic.

The full 5-issue historical real-model benchmark, repository-wide regression, full worker integration, and GitHub-hosted CPU acceptance remain unverified in this continuation.
