"""Conservative read-only GitHub bounty candidate discovery."""

from __future__ import annotations

import json
import os
import re
from decimal import Decimal
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

GITHUB_API = "https://api.github.com/search/issues"
SEARCH_QUERIES = (
    "is:issue is:open bounty in:title",
    "is:issue is:open reward in:title",
    "is:issue is:open paid in:title",
)
_AMOUNTS = (
    re.compile(r"(?<!\w)\$\s*([1-9][\d,]{0,8}(?:\.\d{1,2})?)\s*([kKmM])?(?!\w)"),
    re.compile(r"\bUSD\s+([1-9][\d,]{0,8}(?:\.\d{1,2})?)\s*([kKmM])?(?!\w)", re.I),
)


class DiscoveryError(RuntimeError):
    """GitHub discovery failed; do not silently manufacture fresh findings."""


def payout_mentions(text: str) -> list[int]:
    amounts: set[int] = set()
    for expression in _AMOUNTS:
        for match in expression.finditer(text[:16000]):
            try:
                multiplier = {"k": 1000, "m": 1000000}.get((match.group(2) or "").lower(), 1)
                amount = Decimal(match.group(1).replace(",", "")) * multiplier
            except (ValueError, ArithmeticError):
                continue
            if amount == int(amount) and 1 <= amount <= 100000:
                amounts.add(int(amount))
    return sorted(amounts)


def normalize_issue(item: dict) -> dict | None:
    """Treat third-party issue contents as unverified untrusted text."""
    if not isinstance(item, dict) or item.get("pull_request"):
        return None
    url = str(item.get("html_url") or "")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
        return None
    if not re.fullmatch(r"/[^/]+/[^/]+/issues/\d+", parsed.path):
        return None
    title = str(item.get("title") or "").strip()[:240]
    body = str(item.get("body") or "")[:6000]
    if not title:
        return None
    text = title + "\n" + body
    amounts = payout_mentions(text)
    lower = text.lower()
    reasons: list[str] = []
    score = 0
    title_lower = title.lower()
    for keyword, points in (("bounty", 25), ("reward", 18), ("paid", 12)):
        if keyword in title_lower:
            score += points
            reasons.append(f"Title contains '{keyword}'")
    if amounts:
        score += 20
        reasons.append("An amount is mentioned, not verified")
    if "acceptance criteria" in lower or "steps to reproduce" in lower:
        score += 12
        reasons.append("Issue has structured acceptance information")
    if len(body.strip()) >= 200:
        score += 8
        reasons.append("Issue includes details")
    if any(x in lower for x in ("first come first served", "already claimed", "closed bounty")):
        score -= 35
        reasons.append("Potential competition or unavailable reward")
    if any(x in title_lower for x in ("proposal", "alert", "radar", "bounty board", "discovery")):
        score -= 40
        reasons.append("May be a proposal or aggregator, not claimable paid work")
    if title_lower.startswith("application:") or "i would like to apply for" in lower:
        score -= 50
        reasons.append("Applicant post, not an available task")
    if not amounts and any(x in lower for x in (
        "bounty on you", "bounty hunter", "player bounty", "nation's bounty", "wanted bounty"
    )):
        score -= 55
        reasons.append("Game mechanic, not paid development work")
    if any(x in lower for x in ("claude api", "openai api", "paid subscription", "gpu required", "hardware required")):
        score -= 25
        reasons.append("May require paid APIs or special compute; reject for $0 budget")
    score = max(0, min(score, 100))
    return {
        "id": str(item.get("id") or url),
        "url": url,
        "title": title,
        "repo": "/".join(parsed.path.strip("/").split("/")[:2]),
        "number": int(parsed.path.rsplit("/", 1)[-1]),
        "created_at": str(item.get("created_at") or ""),
        "updated_at": str(item.get("updated_at") or ""),
        "score": score,
        "mentioned_amounts_usd": amounts,
        "reasons": reasons,
        "verification": "unverified_candidate",
        "description_excerpt": body[:1000],
    }


def scan_github(per_query: int = 15, token: str | None = None) -> list[dict]:
    """No issue writes. Any external result is advisory only."""
    if not (1 <= per_query <= 30):
        raise ValueError("per_query must be between 1 and 30")
    token = token if token is not None else os.environ.get("GITHUB_TOKEN", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "LeftSock-BountyForge/0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    dedup: dict[str, dict] = {}
    for query in SEARCH_QUERIES:
        url = GITHUB_API + "?" + urllib.parse.urlencode(
            {"q": query, "per_page": per_query, "sort": "updated", "order": "desc"}
        )
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=18) as response:
                payload = json.load(response)
        except (urllib.error.URLError, ValueError, TimeoutError) as exc:
            raise DiscoveryError(
                "GitHub Search unavailable or rate-limited. Retry later; no fabricated results."
            ) from exc
        items = payload.get("items") if isinstance(payload, dict) else None
        if not isinstance(items, list):
            raise DiscoveryError("GitHub Search returned an unexpected response")
        for item in items:
            normalized = normalize_issue(item)
            if normalized is not None:
                dedup[normalized["url"]] = normalized
    return sorted(dedup.values(), key=lambda c: (-c["score"], c["url"]))


def make_report(candidates: list[dict], source: str) -> dict:
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "disclaimer": "Candidate discovery only. Payouts and eligibility are unverified; revenue is zero until actually received.",
        "candidates": candidates,
    }
