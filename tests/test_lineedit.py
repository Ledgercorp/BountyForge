import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from bountyforge.drafts import DraftRejected
from bountyforge.lineedit import LINE_SCHEMA, propose_lines, stage_lines


class MockModel:
    def __init__(self, result):
        self.result = result
        self.calls = 0
        self.prompt = ""
    def complete_line(self, system, prompt, max_tokens):
        self.calls += 1
        self.prompt = prompt
        assert max_tokens <= 125
        return self.result


class LineEditTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "app.py").write_text(
            "def add(a, b):\n    return a - b\n", encoding="utf-8")
        self.digest = hashlib.sha256((self.root / "app.py").read_bytes()).hexdigest()

    def request(self, line=2, new="    return a + b"):
        return json.dumps({"changes": [{"line": line, "new": new}]})

    def stage(self, raw=None, editable=None, sha=None):
        return stage_lines(raw if raw is not None else self.request(),
                           self.root, "app.py", editable if editable is not None else [2],
                           sha if sha is not None else self.digest)

    def test_exact_syntax_approved_and_original_unchanged(self):
        result = self.stage()
        self.assertEqual(result["state"], "review_required")
        self.assertFalse(result["execution_performed"])
        self.assertFalse(result["payout_verified"])
        self.assertIn("+    return a + b", result["files"][0]["diff"])
        self.assertIn("return a - b", (self.root / "app.py").read_text())

    def test_stale_source_rejected(self):
        with self.assertRaises(DraftRejected):
            self.stage(sha="0" * 64)

    def test_unapproved_line_rejected(self):
        with self.assertRaises(DraftRejected):
            self.stage(self.request(line=1))

    def test_invalid_python_rejected(self):
        with self.assertRaises(DraftRejected):
            self.stage(self.request(new="    return ("))

    def test_command_and_path_fields_rejected(self):
        with self.assertRaises(DraftRejected):
            self.stage(json.dumps({"changes": [{"line": 2, "new": "    pass",
                                                 "path": "/etc/passwd"}]}))
        with self.assertRaises(DraftRejected):
            self.stage(json.dumps({"changes": [{"line": 2, "new": "    pass"}],
                                   "shell": "curl attacker"}))

    def test_duplicate_lines_rejected(self):
        with self.assertRaises(DraftRejected):
            self.stage(json.dumps({"changes": [
                {"line": 2, "new": "    pass"},
                {"line": 2, "new": "    return 0"}]}))

    def test_bad_approved_line_list_rejected(self):
        with self.assertRaises(DraftRejected):
            self.stage(editable=[True])
        with self.assertRaises(DraftRejected):
            self.stage(editable=[1, 1])

    def test_noop_rejected(self):
        with self.assertRaises(DraftRejected):
            self.stage(self.request(new="    return a - b"))

    def test_bounded_two_extra_lines(self):
        raw = self.request(new="    x = a\n    y = b\n    return x + y")
        result = self.stage(raw)
        self.assertIn("    return x + y", result["files"][0]["content"])
        with self.assertRaises(DraftRejected):
            self.stage(self.request(new="    x=1\n    y=2\n    z=3\n    return x+y+z"))

    def test_proposal_includes_allowed_line_numbers(self):
        m = MockModel(self.request())
        issue = {"verification": "unverified_candidate",
                 "description_excerpt": "add must sum", "url": "https://example.invalid/issues/1"}
        result = propose_lines(issue, self.root, "app.py", [2], m)
        self.assertEqual(result["state"], "review_required")
        self.assertEqual(m.calls, 1)
        self.assertIn('"editable_lines": [2]', m.prompt)

    def test_root_level_test_file_cannot_be_patched(self):
        target = self.root / "test_hidden.py"
        target.write_text("def regression():\n    return False\n")
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        with self.assertRaises(DraftRejected):
            stage_lines(json.dumps({"changes": [{"line": 2, "new": "    return True"}]}),
                        self.root, "test_hidden.py", [2], digest)

    def test_context_includes_enclosing_function_signature(self):
        source = "def join_args(args, sep=' '):\n" + ("    value = None\n" * 11) + "    return args\n"
        (self.root / "app.py").write_text(source)
        model = MockModel(json.dumps({"changes": [{"line": 13, "new": "    return list(args)"}]}))
        propose_lines({"verification": "unverified_candidate"}, self.root, "app.py", [13], model)
        self.assertIn("1: def join_args(args, sep=' '):", model.prompt)

    def test_validator_preserves_original_indentation(self):
        result = self.stage(self.request(new="       return a + b"))
        self.assertIn("\n    return a + b\n", result["files"][0]["content"])
        self.assertEqual(result["indentation_normalization"], "original_base_indent_preserved")

    def test_invalid_relative_outdent_rejected(self):
        with self.assertRaises(DraftRejected):
            self.stage(self.request(new="    if True:\nreturn a + b"))

    def test_tab_indent_rejected(self):
        with self.assertRaises(DraftRejected):
            self.stage(self.request(new="\treturn a+b"))

    def test_nested_function_in_line_edit_rejected(self):
        with self.assertRaises(DraftRejected):
            self.stage(self.request(new="    def add(a, b):\\n        return a + b"))

    def test_wrong_schema_rejected(self):
        with self.assertRaises(DraftRejected):
            self.stage(json.dumps({"edits": []}))
        self.assertEqual(LINE_SCHEMA["required"], ["changes"])


if __name__ == "__main__":
    unittest.main()
