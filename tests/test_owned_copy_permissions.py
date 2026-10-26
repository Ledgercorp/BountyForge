"""Regression for the real opt-in Docker fixture import failure in private checkouts."""
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import test_phase8_development as owned


class OwnedCopyPermissionsTests(unittest.TestCase):
    def test_only_validated_disposable_copy_becomes_guest_readable(self):
        original=owned.TASKS/'configuration_values'/'subject.py';old_mode=original.stat().st_mode
        def observe(root,command,timeout):
            for p in (root,*root.rglob('*')):
                if p.is_dir():self.assertEqual(p.stat().st_mode&0o777,0o755)
                else:self.assertEqual(p.stat().st_mode&0o777,0o644)
            return {'passed':False,'output':'Ran 1 test\nFAILED (failures=1)'}
        mask=os.umask(0o077)
        try:
            with patch.object(owned,'_execute',side_effect=observe):owned.run_owned_fixture('configuration_values')
        finally:os.umask(mask)
        self.assertEqual(original.stat().st_mode,old_mode)
