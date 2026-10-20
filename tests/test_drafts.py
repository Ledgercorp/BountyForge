import json
import tempfile
import unittest
from pathlib import Path

from bountyforge.drafts import DraftRejected, safe_path, stage_draft


class DraftTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "src").mkdir()
        (self.root / "src" / "parser.py").write_text("def parse(x):\n    return x\n", encoding="utf-8")

    def stage(self, files, approved=None):
        return stage_draft(json.dumps({"files": files}), self.root, approved or ["src/parser.py"])

    def test_valid_draft_never_executes(self):
        original = (self.root / "src" / "parser.py").read_text()
        result = self.stage([{"path": "src/parser.py", "content": "def parse(x):\n    return str(x)\n"}])
        self.assertEqual(result["state"], "review_required")
        self.assertFalse(result["execution_performed"])
        self.assertFalse(result["external_submission_performed"])
        self.assertFalse(result["payout_verified"])
        self.assertIn("+    return str(x)", result["files"][0]["diff"])
        self.assertEqual((self.root / "src" / "parser.py").read_text(), original)

    def test_no_code_fences(self):
        with self.assertRaises(DraftRejected):
            stage_draft('```json\n{"files": []}\n```', self.root, ["src/parser.py"])

    def test_requires_allowlist(self):
        with self.assertRaises(DraftRejected):
            stage_draft(json.dumps({"files": [{"path": "src/parser.py", "content": "pass\n"}]}), self.root, [])
        with self.assertRaises(DraftRejected):
            self.stage([{"path": "src/parser.py", "content": "pass\n"}], ["src/other.py"])

    def test_rejects_traversal(self):
        for path in ("../../etc/passwd", "src/../secret.py", "/tmp/x.py", ".github/workflows/x.yml", "src/x.py/../file.py", "src\\parser.py", "src/.env", "src/sub\x00.py"):
            with self.subTest(path=path):
                with self.assertRaises(DraftRejected):
                    safe_path(path)

    def test_rejects_duplicate_targets(self):
        entries = [{"path": "src/parser.py", "content": "def a(): pass"}] * 2
        with self.assertRaises(DraftRejected):
            self.stage(entries)

    def test_syntax_gate(self):
        with self.assertRaises(DraftRejected):
            self.stage([{"path": "src/parser.py", "content": "def broken(:\n"}])

    def test_schema_gate(self):
        for bad in ('{"files":[],"shell":"rm -rf /"}', '{"files": {}}', '[]', '{"files":[{"path":"src/parser.py","content":"pass","command":"whoami"}]}'):
            with self.subTest(bad=bad):
                with self.assertRaises(DraftRejected):
                    stage_draft(bad, self.root, ["src/parser.py"])

    def test_noop_rejected(self):
        with self.assertRaises(DraftRejected):
            self.stage([{"path": "src/parser.py", "content": (self.root / "src" / "parser.py").read_text()}])

    def test_link_escape_rejected(self):
        (self.root / "src" / "outside.py").symlink_to("/etc/passwd")
        with self.assertRaises(DraftRejected):
            self.stage([{"path": "src/outside.py", "content": "x=1\n"}], ["src/outside.py"])

    def test_no_new_files(self):
        with self.assertRaises(DraftRejected):
            self.stage([{"path": "src/new.py", "content": "x=1\n"}], ["src/new.py"])

    def test_file_size_gate(self):
        with self.assertRaises(DraftRejected):
            self.stage([{"path": "src/parser.py", "content": "#" * 12001}])

    def test_json_format_checked(self):
        (self.root / "src" / "config.json").write_text('{"a": 1}')
        with self.assertRaises(DraftRejected):
            self.stage([{"path": "src/config.json", "content": "{bad json}"}], ["src/config.json"])


if __name__ == "__main__":
    unittest.main()
