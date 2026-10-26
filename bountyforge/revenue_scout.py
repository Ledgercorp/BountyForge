"""Fail-closed read-only bounty prospect discovery for GitHub-hosted Linux."""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from bountyforge.language_profiles import SUPPORTED_LANGUAGE_PROFILES, from_repository_language

SEARCH_QUERIES = (
    'is:issue is:open label:bounty',
    'is:issue is:open "bounty" in:title',
    'is:issue is:open "reward" in:title',
)
SEARCH_LIMIT = 20
PROSPECT_LIMIT = 12
MAX_REPO_LOOKUPS = 20
MAX_ADVERTISED_REWARD_USD = 100_000
BLOCKED_MIRROR_REPOS = frozenset({'zhangjiayang6835-cyber/bounty-plaza'})
MIRROR_METADATA = re.compile(
    r'\b(aggregat(?:or|ion|ed)|mirror(?:s|ed)?|scrap(?:er|ed|ing)|bounty directory|bounty index)\b|聚合', re.I)
MAX_RESPONSE_BYTES = 256_000
ISSUE = re.compile(r'https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/issues/([1-9][0-9]*)\Z')
DOLLAR = re.compile(r'\$\s*([1-9]\d{0,2}(?:,\d{3})+|[1-9]\d{0,5})(?:\.(\d{1,2}))?\s*([kK])?\b(?![\d,]|\.\d)')
# A dollar sign alone is the existing USD advertisement convention. Explicit
# other-dollar currencies must never be relabeled USD or silently converted.
NON_USD_PREFIX = re.compile(
    r'\b(?:CAD|AUD|NZD|HKD|SGD|TWD|MXN|ARS|CLP|COP|BRL|CA|AU|NZ|HK|SG|NT|C|A|S|R)\s*\Z', re.I)
NON_USD_SUFFIX = re.compile(
    r'\s*(?:CAD|AUD|NZD|HKD|SGD|TWD|MXN|ARS|CLP|COP|BRL)\b', re.I)
REWARD = re.compile(r'\b(bounty|reward|paid issue|compensation|payment for fix)\b', re.I)
CONTROL = re.compile(r'[\x00-\x1f\x7f]')

class ScoutError(RuntimeError):
    """Failed observation, not evidence of zero available work."""

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, url):
        raise ScoutError('GitHub API redirects are not approved')

class GitHubReadOnly:
    """Fixed-origin GET-only API reader; cannot claim, comment, or push."""
    def __init__(self, token: str | None = None):
        self.token = token or ''
        # Honor the execution environment's standard HTTPS proxy. Some hosted
        # runners require it for all egress. Requests still use only the
        # hard-coded api.github.com origin, certificate validation stays on,
        # and cross-origin redirects are rejected below.
        self.opener = urllib.request.build_opener(_NoRedirect())

    def get(self, path: str, params: dict | None = None) -> dict:
        if not (path == '/search/issues' or re.fullmatch(
                r'/repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', path)):
            raise ScoutError('Only read-only GitHub search/repository endpoints permitted')
        url = 'https://api.github.com' + path
        if params:
            url += '?' + urllib.parse.urlencode(params)
        headers = {'Accept': 'application/vnd.github+json',
                   'X-GitHub-Api-Version': '2022-11-28',
                   'User-Agent': 'BountyForge-ReadOnly-Revenue-Scout'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        request = urllib.request.Request(url, headers=headers, method='GET')
        try:
            with self.opener.open(request, timeout=12) as response:
                data = response.read(MAX_RESPONSE_BYTES + 1)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise ScoutError('GitHub API unavailable: ' + type(exc).__name__) from exc
        if len(data) > MAX_RESPONSE_BYTES:
            raise ScoutError('GitHub API response exceeds bounded size')
        try:
            result = json.loads(data)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ScoutError('Invalid GitHub response') from exc
        if not isinstance(result, dict):
            raise ScoutError('Unexpected GitHub API response')
        return result

def _title(value) -> str:
    if not isinstance(value, str):
        return 'Untitled issue'
    value = CONTROL.sub(' ', value)[:160]
    return re.sub(r'\s+', ' ', value).strip() or 'Untitled issue'

def _reward_amount(text: str) -> int | None:
    """Untrusted advertised amount, never verified escrow or expected revenue."""
    amounts = []
    for match in DOLLAR.finditer(text[:7500]):
        if (NON_USD_PREFIX.search(text[:match.start()])
                or NON_USD_SUFFIX.match(text[match.end():])):
            continue
        surrounding = text[max(0, match.start() - 120):match.end() + 120]
        if REWARD.search(surrounding):
            digits = match.group(1).replace(',', '')
            if len(digits) > 6:
                return -1  # Implausible spam; avoid unbounded integer conversion.
            whole = int(digits)
            decimal = int((match.group(2) or '').ljust(2, '0'))
            amount = (whole * 100 + decimal) * (1000 if match.group(3) else 1) // 100
            if amount > MAX_ADVERTISED_REWARD_USD:
                return -1
            amounts.append(amount)
    return max(amounts) if amounts else None

def _parse_issue(item: dict, now: datetime) -> dict | None:
    url = item.get('html_url')
    if not isinstance(url, str) or ISSUE.fullmatch(url) is None:
        return None
    if item.get('state') != 'open' or 'pull_request' in item:
        return None
    body = item.get('body') if isinstance(item.get('body'), str) else ''
    title = _title(item.get('title'))
    raw_labels = item.get('labels', [])
    labels = [x.get('name', '') for x in raw_labels[:30]
              if isinstance(x, dict) and isinstance(x.get('name'), str)] if isinstance(raw_labels, list) else []
    amount = _reward_amount(title + '\n' + body[:7500])
    if amount == -1:
        return None
    named = any('bounty' in x.lower() or 'reward' in x.lower() for x in labels)
    if amount is None:
        return None  # An unpriced bounty label is not a monetary lead.
    try:
        checked = datetime.fromisoformat(item['updated_at'].replace('Z', '+00:00'))
        days = max(0, (now - checked).days)
        if checked.tzinfo is None or checked > now or days > 365:
            return None
    except (KeyError, ValueError, TypeError, AttributeError):
        return None
    match = ISSUE.fullmatch(url)
    assert match is not None
    score = min(100, 10 + (25 if named else 0)
                + (20 if amount is not None else 0)
                + (15 if amount is not None and amount >= 100 else 0)
                + (15 if days <= 14 else 8 if days <= 60 else 0))
    return {
        'issue_url': url, 'repository': match.group(1) + '/' + match.group(2),
        'title': title, 'advertised_reward_usd': amount,
        'rank_for_research': score, 'updated_at': checked.isoformat(),
        'qualification': 'unverified_research_only', 'payout_verified': False,
        'eligibility_verified': False, 'ai_allowed_verified': False,
        'execution_authorized': False, 'external_submission_authorized': False,
        'reasons': ['GitHub text is not sponsor-funding proof',
                    'Payout, availability, AI policy and eligibility require independent evidence'],
    }

def run(client: GitHubReadOnly, *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Timestamp must include timezone')
    found: dict[str, dict] = {}
    for query in SEARCH_QUERIES:
        response = client.get('/search/issues', {'q': query, 'per_page': SEARCH_LIMIT, 'page': 1})
        if not isinstance(response.get('items'), list):
            raise ScoutError('Search response missing issues')
        if response.get('incomplete_results') is not False:
            raise ScoutError('Search observation incomplete or completeness unavailable')
        for issue in response['items'][:SEARCH_LIMIT]:
            if not isinstance(issue, dict):
                continue
            candidate = _parse_issue(issue, now)
            if candidate:
                found[candidate['issue_url'].lower()] = candidate
    ordered = sorted(found.values(), key=lambda c: (-c['rank_for_research'], c['issue_url']))
    prospects = []
    cached_sources: dict[str, tuple[str, bool]] = {}
    repo_lookups = 0
    mirror_rejections = 0
    metadata_budget_exhausted = False
    unexamined_candidate_count = 0
    for index, candidate in enumerate(ordered):
        if len(prospects) >= PROSPECT_LIMIT:
            break
        repo = candidate['repository']
        if repo.lower() in BLOCKED_MIRROR_REPOS:
            mirror_rejections += 1
            continue
        if repo not in cached_sources:
            if repo_lookups >= MAX_REPO_LOOKUPS:
                metadata_budget_exhausted = True
                unexamined_candidate_count = len(ordered) - index
                break
            metadata = client.get('/repos/' + repo)
            repo_lookups += 1
            language = metadata.get('language')
            description = metadata.get('description')
            source_text = repo + ' ' + (description if isinstance(description, str) else '')
            profile=from_repository_language(language)
            cached_sources[repo] = (profile, profile in SUPPORTED_LANGUAGE_PROFILES
                                    and not MIRROR_METADATA.search(source_text))
        profile, allowed=cached_sources[repo]
        if not allowed:
            mirror_rejections += 1
            continue
        candidate['technical_profile']=profile
        candidate['language_evidence']='GITHUB_REPOSITORY_PRIMARY_LANGUAGE'
        prospects.append(candidate)
    return {
        'schema': 1, 'kind': 'read_only_revenue_prospect_scan',
        'generated_at': now.astimezone(timezone.utc).isoformat(),
        'source': 'GitHub public issue metadata', 'source_queries': list(SEARCH_QUERIES),
        'prospects': prospects, 'prospect_count': len(prospects),
        'excluded_mirror_or_unsupported_language_count': mirror_rejections,
        # Retained as a compatibility alias for existing dashboard consumers.
        'excluded_mirror_or_non_python_count': mirror_rejections,
        'supported_language_profiles': list(SUPPORTED_LANGUAGE_PROFILES),
        'metadata_lookup_count': repo_lookups,
        'observation_status': ('incomplete_metadata_budget' if metadata_budget_exhausted
                               else 'bounded_sample_complete'),
        'metadata_budget_exhausted': metadata_budget_exhausted,
        'unexamined_candidate_count': unexamined_candidate_count,
        'commercial_review_ready': 0, 'jobs_executed': 0,
        'model_calls': 0, 'paid_inference': False, 'external_submissions': 0,
        'funds_verified_usd': 0, 'revenue_received_usd': 0,
        'notes': 'Research only: no payout, escrow, policy, eligibility or execution claims.'
    }

def _markdown_title(value: str) -> str:
    return re.sub(r'([\\*_\[\]()<>|])', r'\\\1', value)

def summary(report: dict) -> str:
    lines = ['## BountyForge revenue scouting', '',
             '**Research leads: %s. Verified payable opportunities: 0.**' % report['prospect_count'],
             '', 'All amounts are unverified issue advertisements, not expected earnings.', '']
    if report.get('metadata_budget_exhausted'):
        lines.extend(['**Incomplete observation: metadata lookup budget exhausted; '
                      '%s unexamined candidates.**' % report['unexamined_candidate_count'],
                      'The observed lead count does not establish that no opportunities exist.', ''])
    for candidate in report['prospects']:
        label = ('$' + str(candidate['advertised_reward_usd'])
                 if candidate['advertised_reward_usd'] is not None else 'no confirmed amount')
        lines.append('- [%s](%s) · %s (unverified)' % (
            _markdown_title(candidate['title']), candidate['issue_url'], label))
    return '\n'.join(lines) + '\n'

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Read-only Linux bounty scout')
    parser.add_argument('--mode', choices=('live', 'offline'), default='offline')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--summary', type=Path)
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.mode == 'offline':
        report = {'schema': 1, 'kind': 'offline_test_not_live_discovery',
                  'generated_at': datetime.now(timezone.utc).isoformat(),
                  'prospects': [], 'prospect_count': 0, 'commercial_review_ready': 0,
                  'jobs_executed': 0, 'model_calls': 0, 'paid_inference': False,
                  'external_submissions': 0, 'funds_verified_usd': 0,
                  'revenue_received_usd': 0,
                  'notes': 'Offline means no live discovery was attempted.'}
    else:
        report = run(GitHubReadOnly(os.environ.get('GITHUB_TOKEN')))
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if args.summary is not None:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(summary(report), encoding='utf-8')
    print('Research prospects:', report['prospect_count'], 'verified payable: 0, model calls: 0')
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ScoutError, ValueError) as exc:
        print('BountyForge scouting failed closed: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
