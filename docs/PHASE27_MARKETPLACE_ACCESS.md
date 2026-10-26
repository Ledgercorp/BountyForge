# Phase 27 marketplace access and language support

Observation date: 2026-10-26 UTC
Branch: `engineering/phase27-agent-marketplace-20261026`
Commercial admission: `NOT_ADMITTED`

## Result

The work found no assignment that currently satisfies BountyForge's funding,
AI eligibility, U.S. participation, rights, technical-scope, and payout gates.
No pilot is admitted. The first payment remains $0. This report distinguishes
an open issue or advertised amount from a funded, payable assignment.

The strongest market-side next step is to obtain owner approval for creating a
Superteam agent identity. Its live agent-only listing endpoint requires an
agent API key; this session intentionally did not create an identity or key.
Registration is an external account-creation action, and the current official
skill does not state whether registration is free or creates other obligations.

## Superteam Earn access

The official agent skill was fetched from
<https://superteam.fun/skill.md> on 2026-10-26. It identified itself as version
`0.5.1`, SHA-256
`f18e68b29d87adb287cd24ad274ba5c43ab68d3708182a4bbb6cb58052cb3f7d`.
The public agent page is <https://superteam.fun/earn/agents>.

The documented registration request is `POST https://superteam.fun/api/agents`
with JSON `{"name":"<chosen-agent-name>"}`. The documented response includes
an API key, claim code, agent ID, and public username. Subsequent agent listing
requests use `GET /api/agents/listings/live?take=20` with `Authorization:
Bearer <api-key>`. A no-key read of that documented endpoint returned HTTP 401;
the adapter records this as `BLOCKED_AUTHENTICATION`, never as an empty feed.
Registration itself was not attempted. No credentials were created or
retrieved. The documented agent `POST` has no human-authentication step; the
instructions do not say whether a separate pre-existing human login is needed
for registration. They do require a human sign-in later to claim an award and
complete a profile. The fee is not stated, so registration cost and obligations
remain unknown rather than assumed to be zero.

The agent endpoint defaults to bounty, project, and hackathon listings that
permit agents. The skill says submissions are allowed only when a listing has
`agentAccess=AGENT_ALLOWED` or `AGENT_ONLY`; agent-only listings are hidden
from the normal feed. Agents do not perform OAuth, wallet signing, or KYC. If an
agent wins, a human must use its claim code, sign in, complete a talent profile,
review the identity, and confirm the claim before payout eligibility. The
skill documents submission/update endpoints, but Phase 27 does not call them.

The documentation lists a registration rate limit but no registration fee.
That is not proof that registration is free or obligation-free. U.S. eligibility,
tax treatment, reward escrow, payout asset/network, fees, and collection remain
listing/account-specific and unknown until verified. No listing was claimed,
submitted, or contacted.

### Owner action to unlock agent listing discovery

1. Decide whether to authorize creation of one public Superteam agent identity
   and choose its unique public name. Review the current Superteam terms and
   account requirements first; this session did not accept terms or create an
   identity.
2. If approved, use the official registration request above in an
   owner-controlled environment. Keep the returned API key and claim code out
   of GitHub issues, prompts, artifacts, and source control.
3. On an approved Linux host, store the API key in a private directory in a
   single-link regular file owned by that user with mode `0600`. The read-only
   scan accepts that format through `--superteam-key-file`; the output records
   only whether a credential was configured, never its value. Do not store it
   in this ephemeral workspace or a public Actions artifact.
4. Review the agent feed and each primary listing. A discovered listing does
   not authorize a claim, submission, customer contact, or paid inference.
5. If work is later awarded, the owner must complete the human claim flow and
   the listing's payout requirements. Those are separate owner-controlled
   actions.

## Read-only discovery and findings

The Phase 27 scan at `evidence/phase27/crypto_scan_live_2026-10-26.json` made
nine GET requests at 2026-10-26 11:34 UTC: one Superteam agent-list request,
six fixed public GitHub queries across Python, TypeScript, and JavaScript,
and two public exchange ticker requests. It returned 18 deduplicated GitHub
search groups, all still unverified leads; the feed was blocked with HTTP 401.
GitHub search returned 9 broad-query and 9 Algora-bot-comment query matches
across the three language profiles. The queries are bounded samples, not
exhaustive discovery. None of those advertisements independently established
funding, AI permission, U.S. eligibility, source rights, or payout collection.
No model call, external write, submission, or payment occurred.

The existing revenue scout initially failed in this environment because it
disabled the runner's required HTTPS proxy. Its fixed-origin, GET-only reader
now honors the standard proxy while retaining TLS validation, the hard-coded
`api.github.com` host allowlist, response bounds, and cross-origin redirect
rejection. A follow-up unauthenticated scan made three bounded issue searches
and four repository-metadata reads, yielding three priced-looking leads. They
were not accepted as bounty offers; all three fail the commercial gates.

The captured assessment is in
`evidence/phase27/opportunity_shortlist.json`. The closest leads were:

1. [Claude Code destructive-command hook, $100 advertised](https://github.com/claude-builders-bounty/claude-builders-bounty/issues/3).
   The issue remained open in the captured view and describes a Python/Bash
   task. The page shows an existing open PR and numerous attempts/submissions,
   including activity through 2026-10-25. An agent commented that its work was
   AI-generated, but that is not explicit permission from the bounty owner.
   The issue states payment is through Opire; Opire's official docs say a
   bounty is not an automatic payment and each bounty creator arranges payment
   directly after reviewing a PR. No funded/escrow receipt or owner-confirmed
   remaining award was found. The task is a security hook and presents
   substantial competition. It is not a pilot candidate.
2. [Open Innovation Track: Build Anything on Solana](https://superteam.fun/earn/listing/open-innovation-track-agents/).
   It explicitly targeted autonomous AI agents and advertised 5,000 USDG,
   global eligibility, and open-source work. The captured page states a
   2026-03-09 winner announcement, winners announced, and 122 submissions.
   It is closed, open-ended product development, and outside this repair pilot.
3. [go-redis retry issue #1](https://github.com/Kristywvs22/go-redis/issues/1).
   It is open and advertises $10, but the official Opire bot said the reward
   cannot be created below the documented $20 minimum. Several attempts are
   visible; the repo's primary language is Go, outside current profiles.
4. [Kickama deterministic-data issue #2](https://github.com/lb1192176991-lab/zeroeye/issues/2).
   The issue advertises $50 and a USDC-on-Base route, but the primary thread
   contains conflicting funding and claim status, numerous competing PRs and
   attempts, and no current owner confirmation that an award remains payable.
   Its apparent open issue state is not proof that the reward remains
   available. It is excluded.
5. [BasedHardware Omi Dzongkha quickstart proposal #15496](https://github.com/BasedHardware/omi/issues/15496).
   The issue proposed a $25 Algora bounty but was closed after a maintainer
   said the file was already on `main`. No funding was established, and the
   work required translation quality rather than a demonstrated repair skill.
   It is unavailable.

The live scan also returned [bounty-bot issue #27](https://github.com/alfrexo95/bounty-bot/issues/27)
and [issue #28](https://github.com/alfrexo95/bounty-bot/issues/28), each claiming
$100 and “escrow.” They are quarantined, not ranked as opportunities: the
primary issue body says to verify escrow, does not provide independently
verifiable escrow evidence, contains an apparent placeholder code proposal
that sets verification to true, includes inconsistent payout assertions, and
already has competing proposed solutions. No repository source or scripts
were downloaded or executed.

OnlyDust's current official vision page says it helps actual humans, “not bots,”
while describing future AI-assisted collaboration as human-controlled. That
does not provide current explicit authorization for BountyForge's autonomous
participation, so OnlyDust work remains ineligible pending a specific program's
rules.

Algora's browsed organization bounty pages showed no open bounties for the
sampled organizations. The official API documentation endpoint was unavailable
to this session; no undocumented API or scraping was used. Algora's published
terms prohibit automated access to the Algora service, so the GitHub reader
does not scrape Algora pages. It searches GitHub's public issue API only.

Opire's current official pricing and lifecycle documentation says only code
owners may create a bounty on their own issue; the minimum bounty is $20; a PR
must be reviewed by each creator; and payment is arranged directly rather than
automatically by Opire. The retrieved public docs do not establish an
agent-eligibility rule or a public listing API for the candidates reviewed.

## TypeScript and JavaScript profile

Discovery and qualification now classify Python, TypeScript, and JavaScript
separately using exact GitHub repository-language metadata, Superteam skill
metadata, or bounded file extensions. Conflicting file evidence is reported as
multi-language. Classification is metadata only; it does not enable repair
generation, third-party execution, dependency installation, or a submission.

The owned fixture manifest is `evidence/phase27/language_fixture_manifest.json`.
It freezes one JavaScript Retry-After zero-value defect and one TypeScript
reservation-state defect, with baseline and reference tests. The direct smoke
runner is fixed-input, hash-checks the eight owned files, copies them read-only
to a private temporary workspace, and runs Node's built-in `node:test`. It
records that network isolation is not enforced and is not a model evaluation.

On the current Node `v24.19.0` runtime, both baseline suites reproduced their
documented defects (2/2 tests each), while both preauthored reference suites
passed (2/2 each). No model generated either patch. Node's built-in TypeScript
stripping supports only erasable TypeScript syntax; `tsc` and ESLint are not
installed. No dependencies were installed. JavaScript/TypeScript commercial
repair remains disabled until a separately admitted toolchain and sandbox
profile exist.

## DeepSeek and commercial pilot

The Phase 22 DeepSeek evidence remains historical: six owned developmental
repairs passed at the time, with an estimated maximum of $0.048742, and must not
be generalized to real issues. Its spend authorization and STOP marker remain
closed. Phase 27 made zero DeepSeek requests and did not read the credential.

There is no qualifying pilot to scope. No source revision or tests were
authorized, no third-party code was fetched or run, and no DeepSeek token or
cost envelope is proposed against an unverified listing. New owner approval
would be needed to create the Superteam agent identity, and a separate approval
would still be required for any paid DeepSeek experiment, task claim, external
submission, account or payout setup, or commercial execution.

## Verification

The focused Phase 27 adapter/language/scout suite passed 62 tests. The complete
Python regression passed 947 tests with no failures; eight namespace/rootfs
checks ran against the existing Linux rootfs and passed. The historical
development registry check passed for six repositories and 30 tasks. The
Phase 27 Node smoke used four fixed subprocesses, with two checks in each
baseline/reference suite; all passed. The Node dashboard/console suite passed
eight tests. The existing owned Docker reference replay also passed its six
cases and cleanup checks; that is historical owned-fixture evidence, not
third-party isolation admission. Machine-readable run outputs and discovery
receipts are in `evidence/phase27/`.

No production deployment, merge, external submission, agent registration,
customer operation, payment, DeepSeek request, or paid API call occurred.
Confirmed revenue remains $0. The new Phase 27 GitHub Actions acceptance is
model-free and runs only for this same-repository draft PR. Its hosted result
is recorded after the PR is opened; it is distinct from the local regression
above.
