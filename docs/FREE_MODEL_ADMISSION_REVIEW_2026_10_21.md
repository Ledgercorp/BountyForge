# Free hosted model admission review — October 21, 2026

Groq and Gemini document usable free API offers; OpenRouter's current public
catalog also contains zero-token-price endpoints. **No owner's account, remaining
quota or billing protection has been verified, and no hosted model is admitted
by this review.** No inference occurred. There is no measured quality ranking.

The review covers the existing Groq integration and two alternatives only. It
supports a small owned-fixture experiment after admission, not further bounty
searching or unattended customer-code processing. Public free availability does
not establish permission to send private customer source.

Engineering baseline inspected:
`1f2833581ca6f9d96a0406c7c0a40dc9320cb3ba`. The
[policy evidence](../evidence/revenue/model-provider-policy-review.json) records
official URLs, retrieval timestamps, short excerpts, public-catalog digest and
the facts that remain unverified. Public documents were read as data; downloaded
code was not executed.

| Provider and exact model | Current public evidence | Structured output and reasoning | Admission limit |
|---|---|---|---|
| Groq `openai/gpt-oss-120b` | Free Plan table lists 30 requests/minute, 1,000/day, 8,000 tokens/minute and 200,000/day; organization exceptions apply. | Strict JSON Schema documented. Reasoning supports low/medium/high; medium is the API default. | Existing adapter, but owner Free Plan, remaining limits, key scope and settings remain unverified. |
| Gemini Developer API `gemini-3.8-flash` | Current stable model and Standard pricing list free input/output, including thinking. | JSON Schema subset; low/medium/high thinking, default medium. Minimal is unsupported. | New adapter needed; actual project/model quota and absence of paid billing must be confirmed. Unpaid data use excludes confidential source. |
| OpenRouter `nvidia/nemotron-3.5-super-vl:free` | Live unauthenticated catalog lists prompt/completion prices of zero and `structured_outputs`. | Support must also be confirmed for the exact provider endpoint; parameters can otherwise be ignored. | Catalog example, not an endpoint/account admission. Pin provider and model; no random router or paid fallback. |

Provider sources: [Groq rate limits](https://console.groq.com/docs/rate-limits),
[Groq schema support](https://console.groq.com/docs/structured-outputs),
[Groq API parameters](https://console.groq.com/docs/api-reference),
[Gemini model](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash),
[Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing),
[OpenRouter public catalog](https://openrouter.ai/api/v1/models).

## The existing Groq token cap needs review before an accuracy comparison

`HostedGroqModel` currently sends 125 completion tokens by default, permits at
most 150, and omits reasoning controls. Groq documents a medium default for
GPT-OSS and explains that reasoning consumes generated output. Its Chat API
describes the cap as generated tokens; its Responses API explicitly describes
the combined visible/reasoning cap. Treat 125–150 as a total generation budget,
not an allowance reserved for final JSON. The exact Chat usage split has not
been measured here. A truncated or empty answer would not establish the model's
ability to repair a task. [API reference](https://console.groq.com/docs/api-reference),
[reasoning guide](https://console.groq.com/docs/reasoning).

Setting `include_reasoning=false` suppresses reasoning in the returned message;
it does not turn the reasoning computation off. GPT-OSS does not document `none`
as an accepted effort value. Preserve the independent patch and test validators
even when the provider advertises strict schema decoding. The exact existing
diagnosis schema has not been tested against the service.

Recommend Groq first because the adapter already exists, without claiming that
it outperforms Gemini, OpenRouter models or Qwen. After the owner independently
verifies an existing Free Plan, model access, sufficient remaining quota and no
paid activation, review this separate canary configuration:

- Fixed current Chat endpoint and `openai/gpt-oss-120b`; no model/provider fallback.
- `reasoning_effort=low`, `include_reasoning=false`, `max_completion_tokens=1024`,
  `temperature=0`, non-streaming strict JSON Schema, no tools.
- At most eight attempted requests, one concurrent stream, at most one request
  per minute; stop on quota/provider errors. No automatic retries or account
  rotation. Eight requests reserve at most 8,192 generated tokens; prompt usage
  also consumes quota, so confirm the actual account TPM before admission.
- Keep the existing input, response-byte and final-JSON/source-change limits,
  line enums, syntax/scope checks, Docker admission and independent tests.
- Record request count, elapsed time, returned model/backend identity if
  available, finish reason and provider usage counters. Record reasoning usage
  as unknown when absent. Record schema rejection, truncation and test failure
  separately; do not publish raw reasoning or credentials.

This is a proposed configuration, not a code change, dispatch or activation.
The existing 150-token check must not be silently bypassed. A reviewed adapter
change and negative tests must separate the total generation allowance from the
unchanged retained patch limits. A Free Plan attestation variable is a human
assertion, not a billing kill switch. Groq's
[billing documentation](https://console.groq.com/docs/billing-faqs) distinguishes
the paid Developer upgrade from the Free tier; public pricing cannot certify
the owner's current account.

## Alternative admission details

Gemini's exact `gemini-3.8-flash` ID is documented as stable, with JSON and
thinking support. Its current [quota page](https://ai.google.dev/gemini-api/docs/rate-limits)
directs users to their active project limits rather than guaranteeing one
universal numeric free allowance. Do not substitute a latest/preview alias or
the current paid-only Gemini 4 Argon. Current
[thinking documentation](https://ai.google.dev/gemini-api/docs/thinking) includes
thought tokens in the output cap; changing providers does not remove the token
budget problem. [Structured-output documentation](https://ai.google.dev/gemini-api/docs/structured-output)
says string-length and object-property-count constraints may be ignored
server-side. Retain local checks. A separate reviewed adapter would be required;
none was built or called.

OpenRouter's catalog returned **468 models, including 20 with zero prompt and
completion prices**, at `2026-10-21T16:51:05.810606+00:00`; its response SHA-256 is
`988f659f60d3876ea1e36a580e8733441d89cb306df805bff1b8194cc607d0ef`.
Neither `openai/gpt-oss-120b:free` nor `openai/gpt-oss-20b:free` was listed, so old
indexed model pages do not establish their current availability. This is an
observation of the returned catalog, not proof that an account can invoke every
listed model. Official [pricing](https://openrouter.ai/pricing) describes 20
requests/minute and 50/day without a credit purchase; buying credits to raise
the allowance is outside the $0 scope.

Do not use [`openrouter/free`](https://openrouter.ai/docs/guides/routing/routers/free-router)
for a controlled comparison: it randomly selects among available models.
For a future approved fixed free model, confirm the exact zero-price endpoint,
then restrict the provider and set `allow_fallbacks=false` and
`require_parameters=true`. Defaults permit provider fallback and unsupported
parameters may be ignored. See [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection)
and [structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs).
No authenticated quota endpoint was accessed, no key was read and no provider
was selected or activated.

## Data handling and the remaining boundary

Groq documents default non-retention for ordinary inference, with usage metadata
and reliability/abuse exceptions that can retain customer content for up to 30
days. Account-specific controls and ZDR are unverified.
[Groq data policy](https://console.groq.com/docs/your-data).

Google's unpaid-service terms allow product improvement using inputs/outputs
and human review, and warn against sensitive, confidential or personal inputs.
[Gemini terms](https://ai.google.dev/gemini-api/terms).

OpenRouter adds both its own and the selected provider's policies. Free-route
training permissions and retention can differ; a free label is not a promise
of confidential processing. [Provider data policies](https://openrouter.ai/docs/guides/privacy/provider-logging).

For all three, restrict any later canary to existing public owned fixtures with
recorded hashes. Exclude customer source, intake details, payment information,
secrets and unpublished vulnerabilities. Model IDs are provider identifiers,
not immutable weight/runtime checksums equivalent to the local pinned Qwen
assets. Record model identity and observation time and preserve those limits in
the comparison.

No account was created, terms accepted, billing setting changed, credential
accessed or inference made. Additional spending, new provider charges and
confirmed revenue from this work are $0. Account eligibility and remaining
quota are the concrete access boundary; repair quality remains unmeasured.
