"""CLI. No PR creation, bidding, external file execution, or payouts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from bountyforge.model import LocalModel
from bountyforge.scanner import DiscoveryError, make_report, normalize_issue, scan_github

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "dashboard" / "data" / "results.json"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict:
    content = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(content, dict) or not isinstance(content.get("candidates"), list):
        raise ValueError("Expected a BountyForge candidates report")
    return content


def do_scan(args: argparse.Namespace) -> None:
    if args.offline:
        demo = json.loads((ROOT / "fixtures" / "demo_issues.json").read_text(encoding="utf-8"))
        candidates = [c for raw in demo for c in [normalize_issue(raw)] if c]
        source = "FICTIONAL DEMO. No real payout opportunities."
    else:
        candidates = scan_github(per_query=args.limit)
        source = "GitHub public issues (unverified, read only)"
    candidates.sort(key=lambda c: (-c["score"], c["url"]))
    report = make_report(candidates, source)
    output = Path(args.output)
    write_json(output, report)
    print(f"Saved {len(candidates)} unverified candidates to {output}")
    for candidate in candidates[:8]:
        print(f"  {candidate['score']:02d}  {candidate['repo']}#{candidate['number']}: {candidate['title'][:90]}")
    if args.summary:
        lines = [
            "# BountyForge candidate scan", "",
            "**No payout is verified. No submissions were made.**", "",
        ]
        for c in candidates[:12]:
            safe_title = c["title"].replace("\\", "").replace("[", "").replace("]", "").replace("|", " ")[:90]
            lines.append(f"- [{safe_title}]({c['url']}) · score {c['score']} · funding unverified")
        Path(args.summary).write_text("\n".join(lines) + "\n", encoding="utf-8")


def do_analyze(args: argparse.Namespace) -> None:
    report = load_json(Path(args.input))
    candidates = report["candidates"][:args.top]
    if not candidates:
        print("No candidates to analyze. Scan first.", file=sys.stderr)
        return
    model = LocalModel()
    output: list[dict] = []
    for issue in candidates:
        output.append({
            "url": issue["url"],
            "title": issue["title"],
            "verified_payout": False,
            "analysis": model.analyze(issue),
            "requires_human_review": True,
        })
        print(f"Analyzed {issue['url']} using the loopback model")
    write_json(Path(args.output), {
        "status": "draft_plans_only",
        "model_endpoint": "loopback",
        "results": output,
    })


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BountyForge, zero paid AI API usage")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="read-only candidate discovery")
    scan.add_argument("--offline", action="store_true", help="fictional offline demo")
    scan.add_argument("--limit", type=int, default=12, help="results per GitHub query, max 30")
    scan.add_argument("--output", default=str(DEFAULT_REPORT))
    scan.add_argument("--summary", help="optional GitHub step summary file")
    analyze = sub.add_parser("analyze", help="local-model draft plans, no code execution")
    analyze.add_argument("--input", default=str(DEFAULT_REPORT))
    analyze.add_argument("--top", type=int, default=2)
    analyze.add_argument("--output", default=str(ROOT / "reports" / "plans.json"))
    args = parser.parse_args(argv)
    if args.command == "scan":
        if not 1 <= args.limit <= 30:
            parser.error("--limit must be between 1 and 30")
        do_scan(args)
    else:
        if not 1 <= args.top <= 5:
            parser.error("--top must be between 1 and 5")
        do_analyze(args)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (DiscoveryError, RuntimeError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"BountyForge: {exc}", file=sys.stderr)
        raise SystemExit(2)
