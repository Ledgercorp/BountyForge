"""Trusted metadata and replay validation for the five frozen historical excerpts.

Never imports or executes task source. All model changes use the existing line
validator, with statement locations chosen by AST and pinned target symbols.
"""
from __future__ import annotations
import ast
import hashlib
import json
import tempfile
from pathlib import Path
from bountyforge.drafts import DraftRejected
from bountyforge.lineedit import stage_lines

TASKS = Path(__file__).resolve().parents[1] / 'benchmarks/phase4/tasks'
MANIFEST = json.loads((TASKS / 'manifest.json').read_text())
RECEIPT = '.bountyforge-curated-proposal.json'


def task_spec(task_id: str) -> dict:
    matches = [t for t in MANIFEST['tasks'] if t['id'] == task_id]
    if len(matches) != 1:
        raise DraftRejected('Unknown curated task')
    return matches[0]


def editable_scope(source: str, symbol: str) -> list[int]:
    """Allow statement starts, excluding headers/docstrings, plus global data dependencies."""
    tree = ast.parse(source)
    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == symbol]
    if len(functions) != 1:
        raise DraftRejected('Target symbol missing or multiply defined')
    target = functions[0]
    lines = {n.lineno for n in ast.walk(target) if isinstance(n, ast.stmt)
             and not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
             and not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                      and isinstance(n.value.value, str))}
    names = {n.id for n in ast.walk(target) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    assignments = [n for n in tree.body if isinstance(n, (ast.Assign, ast.AnnAssign))]
    pending = True
    while pending:
        pending = False
        for node in assignments:
            defined = {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
            if defined & names and node.lineno not in lines:
                lines.add(node.lineno)
                names.update(n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load))
                pending = True
    if not 1 <= len(lines) <= 30:
        raise DraftRejected('Curated target exceeds line scope budget')
    return sorted(lines)


def replay(task_id: str, proposals: list[dict]) -> str:
    """Reconstruct exactly the staged candidate; receipts confer no extra authority."""
    task = task_spec(task_id)
    source = (TASKS / task_id / task['file']).read_text()
    if not isinstance(proposals, list) or not 1 <= len(proposals) <= len(task['symbols']):
        raise DraftRejected('Invalid curated proposal count')
    seen = set()
    with tempfile.TemporaryDirectory(prefix='bf-validate-') as directory:
        root = Path(directory)
        path = root / task['file']
        for entry in proposals:
            if (not isinstance(entry, dict) or set(entry) != {'symbol', 'response'}
                    or entry['symbol'] not in task['symbols'] or entry['symbol'] in seen):
                raise DraftRejected('Unexpected curated proposal target')
            seen.add(entry['symbol'])
            path.write_text(source)
            staged = stage_lines(entry['response'], root, task['file'],
                                 editable_scope(source, entry['symbol']),
                                 hashlib.sha256(source.encode()).hexdigest())
            source = staged['files'][0]['content']
    return source
