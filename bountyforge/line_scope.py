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
    if not 1 <= len(failing) <= 8:
        raise DraftRejected("Failure count outside bounded scope")
    # Multiple failures are accepted only if each independently resolves
    # to exactly the same one top-level source function.
    direct_functions = {
        node.name: node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.end_lineno is not None
    }
    declared = [node.name for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if len(declared) != len(set(declared)):
        raise DraftRejected("Multiply defined source function")
    found: dict[str, list[str]] = {name: [] for name in failing}
    for test_file in sorted(tests_dir.glob("test_*.py")):
        if test_file.is_symlink() or test_file.stat().st_size > 100000:
            raise DraftRejected("Invalid controlled test")
        for node in ast.walk(ast.parse(test_file.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in failing:
                called = {call.func.id for call in ast.walk(node)
                          if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)}
                candidates = set(direct_functions).intersection(called)
                if len(candidates) != 1:
                    raise DraftRejected("Failing test does not identify one unique source function")
                found[node.name].append(next(iter(candidates)))
    if any(len(matches) != 1 for matches in found.values()):
        raise DraftRejected("Failing test missing or multiply defined")
    implicated = {matches[0] for matches in found.values()}
    if len(implicated) != 1:
        raise DraftRejected("Failing tests implicate distinct source functions")
    target = direct_functions[next(iter(implicated))]
    lines = list(range(target.lineno + 1, target.end_lineno + 1))
    if not 1 <= len(lines) <= 30:
        raise DraftRejected("Function outside bounded editable scope")
    return lines
