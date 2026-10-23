import json
import unittest


class RecordedModelReplayTests(unittest.TestCase):
    def test_default_does_not_execute(self):
        from phase19_qwen_replay import replay
        with self.assertRaisesRegex(ValueError,'EXPLICIT_RECORDED_OWNED_REPLAY_REQUIRED'):replay()

    def test_only_exact_recorded_model_response_can_be_replayed(self):
        from phase19_qwen_replay import validate_origin,ORIGIN
        from bountyforge.repair_engines import receipt_hash
        record=json.loads(ORIGIN.read_text());validate_origin(record)
        record['calls'][0]['effective_proposal']='{"changes":[]}'
        record['receipt_sha256']=receipt_hash(record)
        with self.assertRaisesRegex(ValueError,'RECORDED_MODEL_ORIGIN_REJECTED'):validate_origin(record)
