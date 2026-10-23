import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from bountyforge import phase8_live_qwen as live
from bountyforge.phase8_evaluation import Catalog,materialize,EvaluationRejected
from bountyforge.statements import stage_statements

class LegacyBindingRegression(unittest.TestCase):
    def test_validated_recorded_candidate_is_bound_explicitly_and_other_bytes_are_denied(self):
        self.assertTrue(hasattr(live,'candidate_bound_observer'),
                        'The old live adapter still verifies changed copies as original bytes')
        catalog=Catalog(live.SELECTION,live.SELECTION_SHA256)
        spec=next(s for s in catalog.tasks() if s['id']=='shipping_cartons')
        report=json.loads((live.ROOT/'evidence/phase11/final_qwen_39935810157.json').read_bytes())
        recorded=next(c for c in report['cases'] if c['case_id']==spec['id'])['session']
        response=recorded['calls'][0]['response']
        with tempfile.TemporaryDirectory() as d:
            original=Path(d)/'original';materialize(catalog,spec,original)
            work=Path(d)/'candidate';materialize(catalog,spec,work)
            candidate=stage_statements(response,original,'subject.py',recorded['editable_lines'],spec['sha256']['subject.py'])['files'][0]['content']
            (work/'subject.py').write_text(candidate)
            runner=live.candidate_bound_observer(catalog,spec,original,SimpleNamespace(last_response=response))
            with patch.object(live,'observe',return_value={'passed':False}) as observe:
                runner(work)
                self.assertEqual(observe.call_args.kwargs['candidate'],candidate)
                (work/'subject.py').write_text(candidate+'\n# unbound bytes\n')
                with self.assertRaises(EvaluationRejected):runner(work)
                self.assertEqual(observe.call_count,1)

if __name__=='__main__':unittest.main()
