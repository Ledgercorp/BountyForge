"""Coordination tests use a fake repair service, never AI accuracy evidence."""
import tempfile
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import unittest
from unittest.mock import patch


class QueueTests(unittest.TestCase):
    def setUp(self):
        from bountyforge.owned_repair_queue import OwnedRepairQueue
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.clock = [1000.0]
        self.path = Path(self.temp.name)/'private'/'queue.sqlite3'
        class Service:
            def prepare(_, case_id, engine):
                return {'task_id':'a'*32, 'case_id':case_id, 'engine':engine, 'revision':0}
            def submit(_, task_id, revision, proposal):
                from bountyforge.repair_engines import receipt_hash
                value = {'state':'EXHAUSTED' if revision else 'REVISION_REQUIRED',
                         'outcome':'TEST_FAILED', 'independently_verified':False,
                         'task_id':task_id, 'engine':'CODEX_AGENT', 'revision':revision+1}
                value['receipt_sha256'] = receipt_hash(value)
                return value
        self.factory = lambda: OwnedRepairQueue(self.path, service_factory=Service,
                                               clock=lambda:self.clock[0])
        self.q = self.factory()
        self.q.create('trial', 'CODEX_AGENT', ['weighted-mix','label-order'])

    def claim(self):
        return self.q.claim('trial')

    def submit(self, claim, revision=0, proposal=None):
        return self.q.submit('trial', claim['job_id'], claim['lease_token'], revision,
                             proposal or {'changes':[{'line':4,'new':'denominator = 123'}]})

    def test_idempotent_enqueue_and_single_active_worker_across_connections(self):
        self.assertFalse(self.q.create('trial','CODEX_AGENT',['weighted-mix','label-order'])['created'])
        first=self.claim()
        self.assertEqual(first['task']['engine'],'CODEX_AGENT')
        self.assertEqual(self.factory().claim('trial')['outcome'],'WORKER_BUSY')
        with self.assertRaises(ValueError):self.q.create('trial','QWEN_LOCAL',['weighted-mix'])

    def test_simultaneous_claims_have_one_winner(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:self.factory().claim('trial'),range(2)))
        self.assertEqual(sum('lease_token' in value for value in results),1)
        self.assertEqual(sum(value.get('outcome')=='WORKER_BUSY' for value in results),1)

    def test_expired_lease_recovery_rejects_stale_writer_and_is_bounded(self):
        first=self.claim();self.clock[0]+=181
        second=self.factory().claim('trial')
        self.assertNotEqual(first['lease_token'],second['lease_token'])
        with self.assertRaises(ValueError):self.submit(first)
        self.clock[0]+=181
        third=self.factory().claim('trial')
        self.assertNotEqual(third['job_id'],first['job_id'])
        self.assertEqual(self.q.status('trial')['jobs'][0]['state'],'FAILED')

    def test_attempt_reservation_survives_crash_and_does_not_reverify_same_proposal(self):
        first=self.claim()
        with patch.object(self.q.sessions[first['job_id']]['service'],'submit',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):self.submit(first)
        self.clock[0]+=181
        recovered=self.factory();second=recovered.claim('trial')
        self.assertEqual(second['attempts_used'],1)
        with self.assertRaisesRegex(ValueError,'REPEATED_PROPOSAL'):
            recovered.submit('trial',second['job_id'],second['lease_token'],0,
                             {'changes':[{'line':4,'new':'denominator = 123'}]})
        result=recovered.submit('trial',second['job_id'],second['lease_token'],0,
                                {'changes':[{'line':4,'new':'denominator = 124'}]})
        self.assertEqual(result['state'],'FAILED')
        self.assertFalse(result['receipt']['independently_verified'])

    def test_stop_revokes_leases_and_cannot_resume_batch(self):
        first=self.claim();self.q.stop('trial')
        with self.assertRaises(ValueError):self.submit(first)
        self.assertEqual(self.factory().claim('trial')['outcome'],'STOPPED')
        self.assertEqual(self.q.status('trial')['jobs'][0]['state'],'STOPPED')

    def test_stop_during_verification_discards_result(self):
        first=self.claim();service=self.q.sessions[first['job_id']]['service']
        original=service.submit
        def stopping(*args):
            self.factory().stop('trial')
            return original(*args)
        with patch.object(service,'submit',side_effect=stopping):result=self.submit(first)
        self.assertEqual(result['outcome'],'LEASE_REVOKED_RESULT_DISCARDED')
        self.assertNotIn('receipt',result)

    def test_unexpected_worker_error_is_sanitized_and_never_verified(self):
        first=self.claim()
        with patch.object(self.q.sessions[first['job_id']]['service'],'submit',
                          side_effect=RuntimeError('sensitive details')):
            result=self.submit(first)
        self.assertEqual(result['receipt']['outcome'],'WORKER_ERROR')
        self.assertEqual(result['state'],'BLOCKED')
        self.assertNotIn('sensitive',str(result))

    def test_a_verified_flag_without_matching_verification_receipt_is_blocked(self):
        first=self.claim()
        from bountyforge.repair_engines import receipt_hash
        forged={'state':'AWAITING_OWNER_APPROVAL','outcome':'VERIFIED','independently_verified':True}
        forged['receipt_sha256']=receipt_hash(forged)
        with patch.object(self.q.sessions[first['job_id']]['service'],'submit',return_value=forged):
            result=self.submit(first)
        self.assertEqual(result['state'],'BLOCKED')
        self.assertEqual(result['receipt']['outcome'],'VERIFICATION_RECEIPT_INVALID')

    def test_corrupted_durable_success_cannot_be_reported_as_verified(self):
        first=self.claim()
        with self.q._db() as db:
            db.execute("UPDATE owned_jobs SET state='VERIFIED',receipt=? WHERE id=?",
                       ('{"outcome":"VERIFIED","independently_verified":true}',first['job_id']))
        with self.assertRaisesRegex(ValueError,'QUEUE_RECEIPT_CORRUPT'):
            self.q.status('trial')

    def test_failed_attempt_receipts_survive_later_attempts_and_restart(self):
        first=self.claim();one=self.submit(first)
        two=self.submit(first,1,{'changes':[{'line':4,'new':'denominator = 124'}]})
        history=self.factory().status('trial')['jobs'][0]['attempt_history']
        self.assertEqual([entry['receipt_sha256'] for entry in history],
                         [one['receipt']['receipt_sha256'],two['receipt']['receipt_sha256']])
        self.assertEqual([entry['outcome'] for entry in history],['TEST_FAILED','TEST_FAILED'])

    def test_corrupted_attempt_history_is_refused(self):
        first=self.claim();self.submit(first)
        with self.q._db() as db:
            db.execute('UPDATE owned_attempt_receipts SET result=? WHERE job_id=?',('{}',first['job_id']))
        with self.assertRaisesRegex(ValueError,'QUEUE_HISTORY_CORRUPT'):self.factory().status('trial')

    def test_restart_requires_new_preparation_not_caller_supplied_completion(self):
        first=self.claim();restarted=self.factory()
        with self.assertRaisesRegex(ValueError,'SESSION_CAPABILITY_LOST'):
            restarted.submit('trial',first['job_id'],first['lease_token'],0,{'changes':[]})
        restarted.release('trial',first['job_id'],first['lease_token'])
        self.assertNotEqual(restarted.claim('trial')['lease_token'],first['lease_token'])

    def test_heartbeat_is_fenced_and_has_absolute_job_deadline(self):
        first=self.claim();self.clock[0]+=100
        self.q.heartbeat('trial',first['job_id'],first['lease_token'])
        self.clock[0]+=81
        self.assertEqual(self.factory().claim('trial')['outcome'],'WORKER_BUSY')
        self.clock[0]+=1000
        with self.assertRaises(ValueError):self.q.heartbeat('trial',first['job_id'],first['lease_token'])

    def test_symlink_hardlink_and_nonprivate_store_are_rejected(self):
        from bountyforge.owned_repair_queue import OwnedRepairQueue
        self.path.chmod(0o644)
        with self.assertRaises(ValueError):OwnedRepairQueue(self.path)
        self.path.chmod(0o600)
        alias=self.path.parent/'alias';alias.symlink_to(self.path)
        with self.assertRaises(ValueError):OwnedRepairQueue(alias)
        hard=self.path.parent/'hard';os.link(self.path,hard)
        with self.assertRaises(ValueError):OwnedRepairQueue(hard)

    def test_unknown_source_engine_scope_and_excessive_batch_are_rejected(self):
        for engine,cases in [('PAID',['weighted-mix']),('CODEX_AGENT',['../../secret']),
                             ('CODEX_AGENT',['weighted-mix']*6)]:
            with self.assertRaises(ValueError):self.q.create('bad',engine,cases)
        self.assertNotIn('lease_token',str(self.q.status('trial')))

