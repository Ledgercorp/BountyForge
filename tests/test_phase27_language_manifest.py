import hashlib
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class Phase27LanguageManifestTests(unittest.TestCase):
    def test_owned_fixture_manifest_is_exposed_hashed_and_has_no_model_claim(self):
        manifest=json.loads((ROOT/'evidence/phase27/language_fixture_manifest.json').read_text())
        self.assertEqual(manifest['kind'],'BOUNTYFORGE_PHASE27_OWNED_LANGUAGE_FIXTURES')
        self.assertEqual(manifest['classification'],'DEVELOPMENTAL_EXPOSED')
        self.assertEqual(manifest['model_calls'],0)
        self.assertIs(manifest['reference_repairs_model_generated'],False)
        self.assertEqual(set(manifest['cases']),{'JAVASCRIPT','TYPESCRIPT'})
        for relative,digest in manifest['files'].items():
            path=ROOT/relative
            self.assertFalse(path.is_symlink())
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),digest)

    def test_language_smoke_runner_has_no_user_supplied_source_or_command_arguments(self):
        source=(ROOT/'scripts/phase27_language_smoke.py').read_text()
        self.assertIn("CASES=(",source)
        self.assertIn("EXPECTED_FILES=frozenset",source)
        self.assertNotIn("argparse",source)
        self.assertIn("timeout=15",source)
        self.assertIn("third_party_execution_authorized':False",source)


if __name__=='__main__':unittest.main()
