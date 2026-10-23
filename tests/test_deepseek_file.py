"""Owner-side, local-only file bridge negative tests (no Docker, no SDK)."""
from pathlib import Path
import os
import stat
import tempfile
import types
import sys
import unittest
from unittest.mock import patch

from deepseek_harness_handoff import HarnessHandoffRejected
from scripts.deepseek_owned_file import main, read_candidate_file, verify_owned_file

GOOD = b'{"changes":[{"line":4,"new":"denominator = 123"}]}'


class CandidateFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.file = self.root / "candidate.json"
        self.file.write_bytes(GOOD)
        self.file.chmod(0o600)

    def rejected(self, path, code=None):
        with self.assertRaises(HarnessHandoffRejected) as result:
            read_candidate_file(path)
        if code:
            self.assertEqual(str(result.exception), code)

    def test_read_private_regular_utf8(self):
        self.assertEqual(read_candidate_file(self.file), GOOD.decode())

    def test_deny_relative_path(self):
        self.rejected(Path("candidate.json"), "ABSOLUTE_CANDIDATE_FILE_REQUIRED")

    def test_deny_symlink(self):
        link=self.root / "link.json";link.symlink_to(self.file)
        self.rejected(link,"CANDIDATE_FILE_UNAVAILABLE")

    def test_deny_hardlink(self):
        link=self.root / "hardlink.json";os.link(self.file,link)
        self.rejected(self.file,"CANDIDATE_FILE_SCOPE_REJECTED")

    def test_deny_fifo_without_blocking(self):
        pipe=self.root / "pipe.json";os.mkfifo(pipe,mode=0o600)
        self.rejected(pipe,"CANDIDATE_FILE_SCOPE_REJECTED")

    def test_deny_directory(self):
        self.rejected(self.root,"CANDIDATE_FILE_SCOPE_REJECTED")

    def test_deny_world_readable(self):
        self.file.chmod(0o644)
        self.rejected(self.file,"CANDIDATE_FILE_SCOPE_REJECTED")

    def test_deny_empty_and_oversize(self):
        self.file.write_bytes(b'')
        self.rejected(self.file,"CANDIDATE_FILE_SCOPE_REJECTED")
        self.file.write_bytes(b'x'*3001)
        self.rejected(self.file,"CANDIDATE_FILE_SCOPE_REJECTED")

    def test_deny_invalid_utf8(self):
        self.file.write_bytes(b'\xff')
        self.rejected(self.file,"CANDIDATE_NOT_UTF8")

    def test_deny_missing_file(self):
        self.rejected(self.root/"missing","CANDIDATE_FILE_UNAVAILABLE")

    def test_deny_when_not_explicitly_enabled(self):
        with self.assertRaisesRegex(HarnessHandoffRejected,"EXPLICIT_OWNED_VERIFICATION_REQUIRED"):
            verify_owned_file("weighted-mix",self.file)
        self.assertEqual(main(["--case-id","weighted-mix","--candidate-file",str(self.file)]),2)

    def test_deny_invalid_case_without_loading_service(self):
        with self.assertRaisesRegex(HarnessHandoffRejected,"OWNED_CASE_REQUIRED"):
            verify_owned_file("",self.file,allow_owned_verification=True)

    def test_owner_file_path_uses_existing_service_only(self):
        class FakeService:
            def prepare(self,case_id,engine):
                self_id=case_id
                assert engine=="CODEX_AGENT"
                return {"case_id":self_id,"source_sha256":"a"*64,"tests_sha256":"b"*64}
        module=types.ModuleType("bountyforge.repair_engines")
        module.RepairService=FakeService
        def bridge(service, prepared, candidate, *, allow_owned_verification=False):
            self.assertTrue(allow_owned_verification)
            self.assertIsInstance(service,FakeService)
            self.assertEqual(candidate,GOOD.decode())
            return {
                "handoff":{"proposal_sha256":"c"*64},
                "owned_verifier_receipt":{
                    "outcome":"TEST_FAILED","state":"REVISION_REQUIRED",
                    "receipt_sha256":"d"*64,"independently_verified":False},
            }
        with patch.dict(sys.modules,{"bountyforge.repair_engines":module}),patch(
                "deepseek_owned_bridge.verify_owned_harness_response",side_effect=bridge):
            out=verify_owned_file("weighted-mix",self.file,allow_owned_verification=True)
        self.assertEqual(out["outcome"],"TEST_FAILED")
        self.assertEqual(out["commercial_admission"],"NOT_ADMITTED")
        self.assertFalse(out["model_identity_attested"])
        self.assertFalse(out["verified_owned_development"])


if __name__ == "__main__":
    unittest.main()
