"""Render the reviewed, read-only Phase 5 commercial audit; never enqueue work.

Primary snapshots are data, never commands. No network or target-code execution.
The reviewed findings below are not a funding or contributor-identity adapter.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "evidence/phase5"

# Frozen ledger order. Reasons are individually reviewed against current issues,
# comments, repository languages/tree, and the policies cited in the snapshots.
FINDINGS = [
    ("rejected", "Reward means protocol interest, not a developer reward offer.", "Solidity contract guards across multiple facets; outside Python Profile A."),
    ("unknown", "Maintainer confirms low-severity reward eligibility, but requires reservation and identity; no issue-specific committed funds verified.", "TypeScript SDK exception handling, not Python."),
    ("unknown", "Aggregator advertises $105 and coin redemption; upstream issue #4 returns 404, so availability and sponsor commitment are unknown.", "Advertised target is src/chains/stellar.ts; TypeScript, not Python."),
    ("rejected", "Paid Club Base is a statistics denominator, not a bounty offer.", "Repository has no Python files; TypeScript ranking rules also need an external domain decision."),
    ("rejected", "Paid refers to an invoice, not payment for fixing the issue.", "TypeScript financial matching application; no Python files."),
    ("rejected", "Reward means reinforcement-learning shaping, not a developer bounty; blocked by issue #36.", "Python feature redesign spanning configurable outcomes and shaping; no reproduced single-function defect."),
    ("rejected", "Mirrored posting says all 40 slots filled; no available claim verified. Funding receipt endpoint is inaccessible.", "Write a MAP description using an external package, not a Python defect repair."),
    ("rejected", "Rewarded means advertising product behavior, not a developer bounty.", "TypeScript telemetry diagnosis requires production GA4 evidence and possible UI changes."),
    ("rejected", "Sparse paid-help solicitation with no terms, funded amount, acceptance criteria or safe reproducible defect.", "C++ browser-reversal repository; no Python files or approved source scope."),
    ("rejected", "Reward refers to game content research, not a developer bounty.", "Sample-bound proprietary-executable research, not a unique reproducible Python repair."),
    ("rejected", "Paid means swap consideration in accounting, not developer compensation.", "TypeScript/Vue accounting read model with several consumers and no Python files."),
    ("rejected", "Paid refers to a vendor LLM reviewer, not developer compensation.", "TypeScript pipeline feature using external model vendors; outside offline Python-only scope."),
    ("unknown", "Stellar Wave applications exist; contributor policy requires maintainer assignment. No LeftSock assignment or issue-specific reward funds verified.", "Rust Soroban contract recipient validation; no Python files."),
    ("unknown", "Aggregator advertises $105; upstream issue #1 returns 404. Coin policy is a claim, not independent sponsor or cash-reserve verification.", "Advertised target is Stellar TypeScript polling, not Python."),
    ("rejected", "Closed and Wave completion credited to another contributor; unavailable as new work.", "Rust contract funding handshake, outside Python scope."),
    ("rejected", "Wave bot records another contributor's accepted application and October 22 due date; unavailable to LeftSock without reassignment.", "Rust escrow lifecycle feature with multiple entry points and treasury interaction."),
    ("rejected", "Paid means provider requests billed to the application, not a developer reward.", "Rust delivery/provider contracts; no Python files."),
    ("unknown", "Maintainer confirms low-severity reward eligibility but insists on on-chain identity; no LeftSock reservation or independent funds verified.", "TypeScript Acala swap arithmetic, not Python."),
    ("unknown", "Issue and README advertise $50 automatic-on-merge; current Opire site describes arranged payment after approval. No issue funding confirmation or payout record verified.", "Creation of a new changelog skill/script, not repair of an existing uniquely scoped Python function; repository contains no Python code."),
    ("rejected", "Paid means a network credential, not developer compensation.", "Rust backend plus TypeScript UI disclosed-contract integration; no Python files."),
    ("unknown", "Stellar Wave applications and assignment prerequisite exist, but no LeftSock assignment, fixed payout or independently verified issue funding.", "New TypeScript/Next.js multi-module discovery, parsing and UI feature; not Python repair."),
    ("unknown", "Mirrored $1 agent onboarding posting claims slots and funding; primary bounty/receipt pages inaccessible; identity eligibility unknown.", "Account onboarding and sending email through an external MCP server are not Python defect repair."),
    ("rejected", "Radar aggregates nominal amounts and discovery links; this is not a sponsor's scoped payable task.", "An opportunity-discovery report, not a reproduced source defect."),
    ("rejected", "Closed and explicitly superseded pilot backlog; paid refers to product questions, not developer compensation.", "Superseded TypeScript product feature; no Python files."),
    ("rejected", "Paid means mentor-session payouts, not developer compensation.", "TypeScript Stripe Connect feature, multiple entities and financial integration; no Python files."),
    ("unknown", "Existing multi-vulnerability report with companion fix PR; bounty policy rewards first valid findings, not an independently guaranteed second repair award.", "Target is TypeScript wallet across note storage, swaps and event parsing; not Python."),
    ("unknown", "Mirrored $1 email task claims available slots and funding; primary bounty and receipt pages inaccessible, so funds and account eligibility unverified.", "External CLI onboarding and sending email, not a Python defect repair."),
    ("rejected", "Owner-needed business-rule choice; job price refers to the product's users, not developer compensation.", "Requires owner policy choice, not a deterministic Python bug; TypeScript repository."),
    ("unknown", "Reporter asserts up to $150 USDC under a finite first-report bounty pool; several competing fixes already posted. Remaining funds, triage and any fix reward unknown.", "Four Rust privacy/coordinator modules; not a single Python function; some compute paths excluded by bounty policy."),
    ("rejected", "Paid means a customer's Checkout, not developer compensation.", "TypeScript/Stripe/Postgres order feature with webhook and UI; no Python files."),
    ("rejected", "Automated digest explicitly reports paymentMode=disabled and committed=0 for every pool; no independently payable task here.", "Digest of other projects, not an approved source defect."),
    ("unknown", "Maintainer says reporting reward paid to the original reporter and links an extrinsic; reporter asks to reserve the fix. Not revenue for LeftSock; fix availability and funds unknown.", "TypeScript Hydration fee estimation; not Python."),
    ("rejected", "Force-paid describes mint-quote accounting, not a developer bounty offer.", "Rust mint RPC accounting; outside Python safe profile."),
]


def fact(status, reason, urls):
    return {"status": status, "reason": reason, "evidence_urls": urls}


def render():
    source = json.loads((DIR / "opportunity-primary-issues.json").read_text())
    comments = json.loads((DIR / "opportunity-primary-comments.json").read_text())
    repos = json.loads((DIR / "opportunity-repositories.json").read_text())
    repositories = {r["repository_full_name"]: r for r in repos["repositories"]}
    assert len(source["issues"]) == len(FINDINGS) == 33
    assert len({x["url"] for x in source["issues"]}) == 33
    rows = []
    for n, (entry, finding) in enumerate(zip(source["issues"], FINDINGS), 1):
        issue = entry["issue"]
        url = entry["url"]
        repo = "/".join(url.split("/")[3:5])
        r = repositories[repo]
        c = comments["issues"][n - 1]
        assert c["url"] == url
        commercial, commercial_reason, profile_reason = finding
        issue_evidence = [url]
        comment_evidence = [x["url"] for x in c["selected_comments"] if x.get("url")]
        evidence = issue_evidence + comment_evidence
        funding_status = "rejected" if n == 31 else "unknown"
        funding_reason = ("Digest explicitly says payments disabled and committed=0; nominal caps are not funding."
                          if n == 31 else "No independently verified remaining escrow or binding, issue-specific commitment to pay LeftSock. Advertised amounts and other contributors' payments do not establish this.")
        eligibility_reason = "No verified LeftSock identity, location/payment eligibility or accepted assignment; no account registration or terms accepted."
        eligibility_urls = evidence
        ai_status, ai_reason = "unknown", "No explicit contribution policy granting AI-generated submissions verified. Generated-by notices, third-party submissions and ready-for-agent labels are not blanket authorization."
        policy_urls = []
        if repo == "paraspell/xcm-tools":
            policy_urls = ["https://paraspell.github.io/docs/contribution-guidelines.html"]
            ai_status, ai_reason = "verified", "Disclosed AI assistance permitted only with human understanding/review; autonomous submissions without it excluded. Six-month history, identity judgement, signatures, reservation and review-response duties apply."
            eligibility_reason = "LeftSock's required six-month commit history, on-chain identity judgement and reservation not verified; no exception inferred. Owner action and review required."
        elif repo == "auscaster/frantic-board":
            policy_urls = ["https://github.com/auscaster/frantic-board/blob/main/CONTRIBUTING.md", "https://gofrantic.com/wtf", "https://gofrantic.com/charter"]
            ai_status, ai_reason = "verified", "Official contribution page and venue explicitly invite agent participation. This does not authorize account onboarding, external email, claims or terms for this owner."
            eligibility_reason = "Venue requires verified identity for paid tasks; LeftSock registration, current paid-access status and accepted terms not verified. No account created."
        elif n in (13, 15, 16, 21):
            policy_urls = ["https://docs.drips.network/wave/contributors/solving-issues-and-earning-rewards/", "https://www.drips.network/wave"]
            eligibility_reason = "Wave requires KYC before applying and maintainer assignment before work; neither verified for LeftSock. Points are a variable share of a pool, not a guaranteed dollar bounty."
        elif n in (26, 29):
            policy_urls = ["https://github.com/paraloom-labs/paraloom-core/blob/main/docs/bug-bounty.md"]
            eligibility_reason = "Finite $3,000 pool and first-valid-unique-finding rules; these findings already publicly reported. LeftSock has no verified eligible original report or separate paid-fix agreement."
        elif n in (3, 14):
            policy_urls = ["https://github.com/zhangjiayang6835-cyber/bounty-plaza/blob/main/REWARD_POLICY.en.md"]
            eligibility_reason = "Aggregator coin/redemption rules do not prove upstream sponsor agreement, withdrawal eligibility or payout reserve. Upstream issue inaccessible (404)."
        elif n == 19:
            policy_urls = ["https://opire.dev/home", "https://app.opire.dev/home", "https://docs.opire.dev/faq"]
            eligibility_reason = "No issue-specific Opire fund record or authenticated payout/eligibility evidence; latest comments request funding and AI-policy clarification without a verified maintainer answer."
        all_evidence = list(dict.fromkeys(evidence + policy_urls))
        dependency_reason = "Execution not admitted: target does not satisfy current Python repair profile. No upstream install, package script, test or source execution performed. Reproducibility is unverified."
        if n == 6:
            dependency_reason = "Static pyproject review finds unpinned-range NumPy, Gymnasium, PyTorch, stable-baselines3 and pytest dependencies. No audited/pinned offline dependency closure or admitted test image. Nothing installed or executed."
        elif n == 10:
            dependency_reason = "Toolkit declares no runtime dependencies, but this task requires exact proprietary game-sample provenance; no sample acquired or executed. Unique repair/test acceptance scope unverified."
        elif n == 19:
            dependency_reason = "Repository tree contains README and license, no source/test harness for a baseline defect. A new Git-reading utility can be Python, but arbitrary git/subprocess use is outside current patch capabilities and sandbox admission. No execution."
        payout_reason = "No enforceable issue-specific payout mechanism verified; product financial terminology is not a developer payment promise."
        if commercial == "unknown" or n in (7, 15, 16):
            payout_reason = commercial_reason + " Documented payout claims remain distinct from independently verified funds and LeftSock eligibility."
        rows.append({"ordinal": n, "issue_url": url, "title": issue["title"],
                     "issue_updated_at": issue.get("updated_at"), "observed_at": source["retrieved_at"],
                     "repository_tree_sha": r.get("head_tree_sha"), "repository_languages": r["languages"],
                     "commercial_classification": commercial, "commercial_reason": commercial_reason,
                     "qualification_classification": "rejected", "execution_authorized": False,
                     "commercial_review_ready": False, "owner_review_candidate": False,
                     "dimensions": {
                         "issue_open": fact("verified" if issue["state"] == "open" else "rejected", "GitHub issue state is " + issue["state"] + "; open state alone does not imply available work.", issue_evidence),
                         "funding": fact(funding_status, funding_reason, all_evidence),
                         "payout_mechanism_legitimate": fact("unknown", payout_reason, all_evidence),
                         "leftsock_eligibility": fact("rejected" if n in (7, 15, 16, 24) else "unknown", eligibility_reason if n not in (7, 15, 16, 24) else commercial_reason, all_evidence),
                         "ai_contributions_permitted": fact(ai_status, ai_reason, policy_urls or issue_evidence),
                         "python_safe_profile": fact("rejected", profile_reason, issue_evidence + [f"https://github.com/{repo}/tree/{r['head_tree_sha']}"]),
                         "safe_test_dependency_reproduction": fact("unknown", dependency_reason, all_evidence),
                     }, "evidence_urls": all_evidence})
    count = Counter(x["commercial_classification"] for x in rows)
    report = {"schema_version": 1, "kind": "phase5_read_only_opportunity_audit",
              "frozen_pool_source_blob": "803ba112e7d3568180e1e2038763eba8f528ad13",
              "observed_at": source["retrieved_at"], "engineering_baseline_revision": "773b2b0499117956b4c138696c78c1f5d6f834c7",
              "classification_rule": "Commercial triage separates unsupported/nonavailable postings (rejected) from plausible reward claims lacking proof (unknown). Final qualification rejects any current Python Profile A mismatch even when commercial facts remain unknown.",
              "counts": {"total": 33, "open": sum(x["dimensions"]["issue_open"]["status"] == "verified" for x in rows),
                         "closed": sum(x["dimensions"]["issue_open"]["status"] == "rejected" for x in rows),
                         "commercial_verified": count["verified"], "commercial_rejected": count["rejected"], "commercial_unknown": count["unknown"],
                         "qualification_verified": 0, "qualification_rejected": 33, "qualification_unknown": 0,
                         "owner_review_candidates": 0, "execution_authorized": 0},
              "external_actions": [], "additional_spending_usd": 0, "confirmed_revenue_usd": 0,
              "limitations": ["Funding reserves/escrow, payment finality and LeftSock identity/location eligibility not independently attested.",
                              "Primary Frantic bounty and receipt URLs inaccessible through web retrieval; mirror statements are not verified funds.",
                              "Both referenced Parabola upstream issues return 404; repository package metadata accessible but issue availability unknown.",
                              "Third-party dependencies were statically inspected only where relevant; no target code/tests/packages executed.",
                              "All 33 issue bodies and returned comment collections inspected; bounded selected excerpts retained, not every claim or linked PR verified.",
                              "No inference of AI permission from absence of a prohibition, issue labels or other people's submissions."],
              "snapshot_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DIR.glob("opportunity-primary-*.json"))},
              "repository_snapshot_sha256": hashlib.sha256((DIR / "opportunity-repositories.json").read_bytes()).hexdigest(),
              "candidates": rows}
    (DIR / "opportunity-audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n")
    lines = [
        "# Phase 5 commercial audit — 2026-10-21", "",
        "All 33 frozen discoveries were checked against current issue state, comments and repository metadata. "
        "31 issues are open and 2 closed. Commercial triage: **0 verified, 21 rejected, 12 unknown**. "
        "Final qualification: **33 rejected for the current Python repair profile; 0 eligible owner-review candidates**. "
        "An unknown commercial claim stays unknown even when its technical scope is definitively rejected.", "",
        "The pool is fixed to ledger blob `803ba112e7d3568180e1e2038763eba8f528ad13`. "
        "Audit source baseline: `773b2b0499117956b4c138696c78c1f5d6f834c7`. "
        "The machine-readable [audit](../evidence/phase5/opportunity-audit.json) records seven dimensions per candidate, "
        "individual reasons, current timestamps, exact repository tree SHAs, evidence URLs and snapshot checksums. "
        "[Renderer](../scripts/phase5_audit_opportunities.py) is offline and cannot enqueue, execute targets or publish.", "",
        "| # | Candidate | Commercial triage | Current finding | Profile A rejection |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        repo_number = row["issue_url"].removeprefix("https://github.com/").replace("/issues/", " #")
        lines.append(f"| {row['ordinal']} | [{repo_number}]({row['issue_url']}) | {row['commercial_classification']} | "
                     f"{row['commercial_reason']} | {row['dimensions']['python_safe_profile']['reason']} |")
    lines.extend([
        "", "## Evidence that changes the commercial assessment", "",
        "ParaSpell has a documented reward program, and maintainers confirm low-severity eligibility for #2153 and #2155. "
        "Its [current policy](https://paraspell.github.io/docs/contribution-guidelines.html) permits disclosed AI assistance "
        "with human understanding and review, excludes autonomous submissions without that review, and requires account history, "
        "on-chain identity judgement, signed commits, reservation and timely responses. Those LeftSock prerequisites are unverified. "
        "#2174 has a maintainer statement that its original reporter was rewarded; that is not a LeftSock payment or proof that a separate fix award is available. All three targets are TypeScript.", "",
        "Frantic's [venue explanation](https://gofrantic.com/wtf) explicitly invites agents and requires verified identity for paid tasks. "
        "The three issue mirrors are onboarding/documentation/email work, not Python repair. #143 says its slots are filled. "
        "The primary bounty URLs and funding receipts were inaccessible through the web tool; mirrored funded/paid labels and receipt links are insufficient to verify remaining funds.", "",
        "The [Drips contributor documentation](https://docs.drips.network/wave/contributors/solving-issues-and-earning-rewards/) "
        "requires KYC and maintainer assignment. Rewards depend on the Wave pool and confirmed Points, with adjustments reserved by the program. "
        "StellarSwipe #1323 is completed; Refract #313 has another accepted contributor. LeftSock KYC and assignments are unverified. "
        "SoroWill and Golden Raccoon require assignment before work; their targets are Rust or TypeScript.", "",
        "Claude Builders #1 is the only advertised task that expressly permits a Python implementation, but it creates a new utility "
        "rather than repairing an existing uniquely scoped function. Its repository has only README/license files. "
        "The issue's automatic-on-merge payment claim differs from the [current Opire site](https://opire.dev/home), which describes arranging payment after approval. "
        "All 2,376 returned comments were searched; there is no OpireBot author in that collection and no independently verified issue funding record. "
        "A visible app summary containing zero counters alongside sample bounties is not proof of funding or non-funding. "
        "AI contribution permission, LeftSock payout eligibility and issue-specific funds remain unknown.", "",
        "Bounty Plaza's two $105 posts are mirrors of Parabola issues that currently return 404. "
        "Its coin redemption formula is a platform assertion, not proof of upstream sponsor authorization or cash reserves. "
        "Accessible Parabola package metadata identifies TypeScript and a build command that invokes `node api.js`; it was read only and never run.", "",
        "Paraloom's [bounty policy](https://github.com/paraloom-labs/paraloom-core/blob/main/docs/bug-bounty.md) describes a finite $3,000 USDC pool, "
        "first valid unique reports and excluded compute paths. Both discoveries are already-existing reports with competing fixes; "
        "no guaranteed second repair payment or remaining pool funds were verified. The scope spans Rust or TypeScript modules.", "",
        "## Safety, uncertainty and operational effect", "",
        "No target source, test suite, install hook, third-party dependency, CLI or MCP server was executed. "
        "Repository trees/languages and selected manifests were inspected as data. The Python RL candidate declares broad dependency ranges "
        "including NumPy, PyTorch and stable-baselines3; there is no audited offline dependency closure. "
        "The Python reverse-engineering candidate requires exact proprietary samples and research conclusions rather than a reproduced scoped bug. "
        "A default-branch tree SHA records the snapshot; it does not attest deployed code or test success.", "",
        "No candidate has independently verified funding plus payment eligibility, AI permission, admitted Python scope and safe reproducible tests. "
        "No maintainer was contacted, no claim/PR/account/contract was created, no terms accepted, and no payment made or received. "
        "Additional spending and confirmed revenue are $0. Existing dashboard v11, durable coordination and discovery records remain unchanged; "
        "recurring repair execution remains disabled. No real opportunity is marked review-ready.", "",
        "Before paid operations: obtain issue-specific primary funding/payout evidence, verify owner identity/location and policy prerequisites, "
        "find an actually available narrow Python defect, attest its exact revision and dependency closure, and reproduce/tests within an admitted boundary. "
        "Any account/KYC/terms, maintainer communication or external submission remains an owner action requiring its specific authorization.", "",
    ])
    (ROOT / "docs/PHASE5_COMMERCIAL_AUDIT.md").write_text("\n".join(lines))
    return report


if __name__ == "__main__":
    print(json.dumps(render()["counts"], sort_keys=True))
