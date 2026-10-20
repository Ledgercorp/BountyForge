"""Fail-closed, execution-free patch staging for a local coding model.

This stage does NOT evaluate the correctness of the proposal. It never
executes generated source, installs packages, or touches external repositories.
The caller supplies the exact paths the model may propose changes to.
"""

from __future__ import annotations

import ast
import difflib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

MAX_FILE_COUNT = 5
MAX_FILE_BYTES = 12_000
MAX_RESPONSE_BYTES = 65_536
_ALLOWED_SUFFIXES = frozenset({".py", ".js", ".ts", ".json", ".md", ".txt"})
_BLOCKED_PARTS = frozenset({".git", ".github", "node_modules", "__pycache__", ".venv", "dist", "build"})


class DraftRejected(ValueError):
    """The proposed patch cannot be safely staged."""


@dataclass(frozen=True)
class ProposedFile:
    path: str
    content: str
    syntax_checked: bool
    diff: str


def safe_path(raw: str) -> str:
    if not isinstance(raw, str) or not raw or len(raw) > 180 or "\\" in raw or "\x00" in raw:
        raise DraftRejected("Unsafe file path")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in raw.split("/")):
        raise DraftRejected("Absolute and traversing paths are forbidden")
    if any(part in _BLOCKED_PARTS or part.startswith(".") for part in path.parts):
        raise DraftRejected("Hidden, environment and build paths are forbidden")
    if path.suffix.lower() not in _ALLOWED_SUFFIXES:
        raise DraftRejected("Executable, config and unsupported file extensions are forbidden")
    if not re.fullmatch(r"[A-Za-z0-9_./-]+", raw):
        raise DraftRejected("Only portable path characters are permitted")
    return str(path)


def _verify_existing(workspace: Path, relative: str) -> str:
    root = workspace.resolve(strict=True)
    path = root / relative
    # No symlink in any ancestor; weak isolation can otherwise escape the checkout.
    cursor = root
    for component in PurePosixPath(relative).parts:
        cursor = cursor / component
        if cursor.is_symlink():
            raise DraftRejected("Symlinks are not accepted")
    if not path.is_file():
        raise DraftRejected("Only existing, explicitly approved source files may be changed")
    if not path.resolve(strict=True).is_relative_to(root):
        raise DraftRejected("File escapes workspace")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise DraftRejected("Existing source exceeds review size limit")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise DraftRejected("Existing file is not UTF-8 text") from exc


def stage_draft(response: str, workspace: Path, approved_paths: list[str]) -> dict:
    """Purely parse and diff a model response; no file writes and no execution.

    The result includes a ready-to-save JSON-serializable manifest. Clients should
    commit or submit nothing unless a human independently approves the diff.
    """
    if not isinstance(response, str) or len(response.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise DraftRejected("Model response exceeded maximum size")
    try:
        proposal = json.loads(response)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise DraftRejected("Model must return one JSON object, without markdown fences") from exc
    if not isinstance(proposal, dict) or set(proposal) != {"files"}:
        raise DraftRejected("Model must return exactly the files key")
    files = proposal["files"]
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILE_COUNT:
        raise DraftRejected("Expected between one and five proposed files")
    allow = {safe_path(x) for x in approved_paths}
    if not allow or len(allow) != len(approved_paths):
        raise DraftRejected("Approved file list is missing or duplicated")
    staged: list[ProposedFile] = []
    visited: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"path", "content"}:
            raise DraftRejected("Each proposed file must have only path and content")
        name = safe_path(entry["path"])
        if name not in allow or name in visited:
            raise DraftRejected("Unapproved or duplicated patch target")
        visited.add(name)
        content = entry["content"]
        if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_FILE_BYTES:
            raise DraftRejected("Proposed source is not text or exceeds size limit")
        previous = _verify_existing(Path(workspace), name)
        syntax_ok = False
        if name.endswith(".py"):
            try:
                ast.parse(content, filename=name)
            except SyntaxError as exc:
                raise DraftRejected("Python proposal did not pass syntax validation") from exc
            syntax_ok = True
        elif name.endswith(".json"):
            try:
                json.loads(content)
            except json.JSONDecodeError as exc:
                raise DraftRejected("JSON proposal did not parse") from exc
            syntax_ok = True
        diff = "".join(difflib.unified_diff(
            previous.splitlines(keepends=True), content.splitlines(keepends=True),
            fromfile=f"a/{name}", tofile=f"b/{name}", n=3,
        ))
        if not diff:
            raise DraftRejected("Proposed file has no changes")
        staged.append(ProposedFile(name, content, syntax_ok, diff))
    return {
        "state": "review_required",
        "execution_performed": False,
        "external_submission_performed": False,
        "payout_verified": False,
        "files": [dict(path=x.path, content=x.content, syntax_checked=x.syntax_checked, diff=x.diff) for x in staged],
    }
