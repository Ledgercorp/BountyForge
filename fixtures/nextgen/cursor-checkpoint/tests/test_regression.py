import unittest
from subject import consume_page


def row(seq, name='item', generation='g'):
    return {'sequence':seq,'id':name,'generation':generation}


class CheckpointTests(unittest.TestCase):
    def test_empty_page_keeps_checkpoint(self):
        self.assertEqual(consume_page([],4,'g'),{'ids':[],'checkpoint':4})
    def test_replayed_checkpoint_is_excluded(self):
        self.assertEqual(consume_page([row(4)],4,'g'),{'ids':[],'checkpoint':4})
    def test_all_fresh_ids_are_retained(self):
        self.assertEqual(consume_page([row(5,'a'),row(6,'b')],4,'g'),{'ids':['a','b'],'checkpoint':6})
    def test_duplicate_sequence_is_excluded(self):
        self.assertEqual(consume_page([row(5,'a'),row(5,'b')],4,'g')['ids'],['a'])
    def test_invalid_row_cannot_advance_checkpoint(self):
        self.assertEqual(consume_page([row(100,generation='other'),row(5)],4,'g')['checkpoint'],5)
    def test_missing_identity_cannot_advance_checkpoint(self):
        self.assertEqual(consume_page([row(100,None)],4,'g'),{'ids':[],'checkpoint':4})
    def test_old_out_of_order_row_is_ignored(self):
        self.assertEqual(consume_page([row(8,'a'),row(7,'b')],4,'g')['ids'],['a'])
    def test_source_rows_unchanged(self):
        rows=[row(5)];before=[dict(x) for x in rows]
        consume_page(rows,4,'g');self.assertEqual(rows,before)
