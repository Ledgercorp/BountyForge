"""Deterministic, local-only Python context projection for bounded minimal edits.

Only existing allowlisted file contents may be projected. This does not
execute, import or evaluate the provided source.
"""
from __future__ import annotations
import ast
import re
from bountyforge.drafts import DraftRejected

_SYMBOL = re.compile(r'[A-Za-z_][A-Za-z0-9_]{0,79}\Z')


def select_python_context(source: str, symbols: list[str], *, budget: int = 3200) -> str:
    """Reduce long files to exact function bodies and required top-level assignments.

    The excerpts are for *reading* by the local model only. Patches are always
    validated against the untouched complete file and unique literal old text.
    """
    if not isinstance(source, str) or not isinstance(symbols, list) or not 1 <= len(symbols) <= 3:
        raise DraftRejected('Explicit one-to-three target symbols required')
    if any(not isinstance(n, str) or not _SYMBOL.fullmatch(n) for n in symbols) or len(set(symbols)) != len(symbols):
        raise DraftRejected('Invalid or duplicate Python target symbols')
    if not 200 <= budget <= 4000:
        raise DraftRejected('Context budget out of bounds')
    try:
        parsed = ast.parse(source)
    except SyntaxError as exc:
        raise DraftRejected('Invalid source Python syntax') from exc
    lines = source.splitlines(keepends=True)
    functions = [node for node in ast.walk(parsed) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    selected = []
    needed_globals = set()
    for name in symbols:
        matches = [node for node in functions if node.name == name]
        if len(matches) != 1:
            raise DraftRejected('Requested target function missing or ambiguous')
        node = matches[0]
        # Remove a large docstring ONLY from model context; not from the source file.
        excluded = set()
        if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
            excluded.update(range(node.body[0].lineno, node.body[0].end_lineno + 1))
        start = node.lineno
        if node.decorator_list:
            start = min(start, *(d.lineno for d in node.decorator_list))
        content = ''.join(lines[n - 1] for n in range(start, node.end_lineno + 1) if n not in excluded)
        selected.append((start, content))
        needed_globals.update(child.id for child in ast.walk(node) if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load))
    # Include only referenced, simple top-level assignments, expanding dependencies
    # within a fixed four-hop bound. Never evaluate the expressions.
    assignments = []
    candidates = []
    for node in parsed.body:
        if isinstance(node, ast.Assign) and all(isinstance(t, ast.Name) for t in node.targets):
            names = {t.id for t in node.targets}
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = {node.target.id}
        else:
            continue
        text = ''.join(lines[node.lineno - 1:node.end_lineno])
        if len(text.encode('utf-8')) <= 500:
            dependencies = {child.id for child in ast.walk(node) if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)}
            candidates.append((node.lineno, text, names, dependencies))
    for _ in range(4):
        before = set(needed_globals)
        for _, _, names, dependencies in candidates:
            if names.intersection(needed_globals):
                needed_globals.update(dependencies)
        if before == needed_globals:
            break
    for position, text, names, _ in candidates:
        if names.intersection(needed_globals):
            assignments.append((position, text))
    fragments = sorted(assignments + selected, key=lambda p: p[0])
    result = '\n\n'.join(text.rstrip() for _, text in fragments) + '\n'
    if len(result.encode('utf-8')) > budget:
        raise DraftRejected('Selected function context exceeds budget, narrow scope')
    return result