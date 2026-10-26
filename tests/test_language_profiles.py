import unittest
from bountyforge.language_profiles import (
    SUPPORTED_LANGUAGE_PROFILES, classify_task_language,
    from_file_paths, from_repository_language, from_skills, toolchain_requirements,
)


class LanguageProfileTests(unittest.TestCase):
    def test_repository_metadata_separates_python_typescript_and_javascript(self):
        self.assertEqual(from_repository_language('Python'),'PYTHON')
        self.assertEqual(from_repository_language('TypeScript'),'TYPESCRIPT')
        self.assertEqual(from_repository_language('JavaScript'),'JAVASCRIPT')
        self.assertEqual(from_repository_language('Rust'),'OTHER')
        self.assertEqual(from_repository_language(None),'UNKNOWN')

    def test_file_extensions_and_skills_are_bounded_metadata_hints(self):
        self.assertEqual(from_file_paths(['src/app.ts','src/types.d.ts']),'TYPESCRIPT')
        self.assertEqual(from_file_paths(['src/app.mjs']),'JAVASCRIPT')
        self.assertEqual(from_file_paths(['src/app.ts','src/app.mjs']),'MULTI_LANGUAGE')
        self.assertEqual(from_skills(['TypeScript programming']),'TYPESCRIPT')
        self.assertEqual(from_skills(['Python','JavaScript']),'MULTI_LANGUAGE')
        self.assertEqual(from_file_paths(['../outside.ts']),'UNKNOWN')

    def test_conflicting_authoritative_and_skill_evidence_is_not_guessed(self):
        self.assertEqual(classify_task_language(repository_language='TypeScript',skills=['JavaScript']),'MULTI_LANGUAGE')
        self.assertEqual(classify_task_language(repository_language='JavaScript'), 'JAVASCRIPT')
        self.assertIn('TYPESCRIPT',SUPPORTED_LANGUAGE_PROFILES)

    def test_typescript_policy_discloses_missing_full_compiler_and_denies_untrusted_execution(self):
        policy=toolchain_requirements('TYPESCRIPT')
        self.assertIn('tsc is not installed',policy['tools']['typecheck'])
        self.assertEqual(policy['third_party_execution'],'NOT_ADMITTED')
        self.assertEqual(policy['dependency_installation'],'DENIED')
        self.assertEqual(policy['network_access'],'DENIED')

    def test_javascript_uses_built_in_node_test_without_claiming_external_admission(self):
        policy=toolchain_requirements('JAVASCRIPT')
        self.assertEqual(policy['tools']['test_runner'],'built-in node:test')
        self.assertEqual(policy['third_party_execution'],'NOT_ADMITTED')
        with self.assertRaises(ValueError):toolchain_requirements('UNKNOWN')


if __name__=='__main__':unittest.main()
