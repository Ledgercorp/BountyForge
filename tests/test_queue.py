import tempfile,time,unittest
from pathlib import Path
from bountyforge.queue import Queue
class QueueTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.q=Queue(Path(self.tmp.name)/'queue.sqlite');self.addCleanup(self.q.close)
 def test_idempotent_enqueue(self):
  self.assertTrue(self.q.enqueue('a',{'task':1}));self.assertFalse(self.q.enqueue('a',{'task':2}))
 def test_claim_and_finish(self):
  self.q.enqueue('a',{'task':1});j=self.q.claim();self.assertEqual(j['id'],'a')
  self.assertTrue(self.q.finish('a',{'status':'failed'},lease_token=j['lease_token']));self.assertIsNone(self.q.claim())
 def test_does_not_fabricate_success(self):
  self.q.enqueue('a',{});self.q.claim()
  with self.assertRaises(ValueError):self.q.finish('a',{'status':'success'},lease_token='invalid')
 def test_lease_recovery(self):
  self.q.enqueue('a',{});self.q.claim()
  self.q.conn.execute('UPDATE jobs SET lease_until=0 WHERE id=?',('a',))
  self.assertEqual(self.q.claim()['attempts'],2)
  self.q.conn.execute('UPDATE jobs SET lease_until=0 WHERE id=?',('a',))
  self.assertIsNone(self.q.claim())
  self.assertEqual(self.q.get('a')['state'],'failed')
  self.assertEqual(self.q.get('a')['result']['error'],'lease_exhausted')
 def test_bad_ids(self):
  with self.assertRaises(ValueError):self.q.enqueue('../../../passwd',{})
 def test_only_one_global_active_claim(self):
  self.q.enqueue('a',{});self.q.enqueue('b',{})
  self.q.claim()
  self.assertIsNone(self.q.claim())
 def test_stale_worker_cannot_finish_recovered_claim(self):
  self.q.enqueue('a',{});first=self.q.claim()
  self.q.conn.execute('UPDATE jobs SET lease_until=0 WHERE id=?',('a',))
  second=self.q.claim()
  self.assertFalse(self.q.finish('a',{'status':'failed'},lease_token=first['lease_token']))
  self.assertTrue(self.q.finish('a',{'status':'failed'},lease_token=second['lease_token']))
 def test_success_requires_worker_evidence(self):
  self.q.enqueue('a',{});claim=self.q.claim()
  with self.assertRaises(ValueError):
   self.q.finish('a',{'status':'review_ready'},lease_token=claim['lease_token'])
if __name__=='__main__':unittest.main()
