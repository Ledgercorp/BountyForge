"""Conservative, deterministic editable-line selection for controlled fixtures.

No model-selected paths. If a failing test cannot identify exactly one source
function, stop rather than guess. This is NOT safe for arbitrary repositories.
"""
from __future__ import annotations
import ast
import re
from pathlib import Path
from bountyforge.drafts import DraftRejected, _verify_existing, safe_path

def infer_editable_lines(root: Path, source_path: str, test_output: str) -> list[int]:
    source_path = safe_path(source_path)
    if not source_path.endswith(".py") or source_path.startswith("tests/"):
        raise DraftRejected("Automatic scope supports only one Python source")
    if not isinstance(test_output, str) or "FAIL:" not in test_output:
        raise DraftRejected("No reproducible unittest assertion failure")
    source = _verify_existing(root, source_path)
    tree = ast.parse(source, filename=source_path)
    tests_dir = Path(root) / "tests"
    if not tests_dir.is_dir() or tests_dir.is_symlink():
        raise DraftRejected("Missing controlled tests")
    failing = set(re.findall(r"FAIL:\s+(test_\w+)\s*\(", test_output))
    if len(failing) != 1:
        raise DraftRejected("Failure location ambiguous")
    test_name = next(iter(failing))
    names = set()
    for test_file in sorted(tests_dir.glob("test_*.py")):
        if test_file.is_symlink() or test_file.stat().st_size > 100000:
            raise DraftRejected("Invalid controlled test")
        for node in ast.walk(ast.parse(test_file.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == test_name:
                for call in ast.walk(node):
                    if isinstance(call, ast.Call) and isinstance(call.func, ast.Name):
                        names.add(call.func.id)
    matches = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
               and n.name in names and n.end_lineno is not None]
    if len(matches) != 1:
        raise DraftRejected("No unique tested top-level function")
    target = matches[0]
    lines = list(range(target.lineno + 1, target.end_lineno + 1))
    if not 1 <= len(lines) <= 30:
        raise DraftRejected("Function outside bounded editable scope")
    return lines
