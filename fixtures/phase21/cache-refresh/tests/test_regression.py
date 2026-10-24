import unittest
from subject import refresh_cache

class CacheTests(unittest.TestCase):
    def test_not_modified(self):
        self.assertEqual(refresh_cache({'value': 'old', 'etag': 'a', 'attempts': 2}, {'status': 304}), {'value': 'old', 'etag': 'a', 'attempts': 0})
    def test_retry_count(self):
        self.assertEqual(refresh_cache({'value': 7, 'etag': 'a', 'attempts': 2}, {'status': 503}), {'value': 7, 'etag': 'a', 'attempts': 3})
    def test_repeated_failure(self):
        a=refresh_cache({'value': 7, 'etag': 'a', 'attempts': 0}, {'status': 500})
        self.assertEqual(refresh_cache(a, {'status': 500}), {'value': 7, 'etag': 'a', 'attempts': 2})
    def test_fresh_value(self):
        self.assertEqual(refresh_cache({'value': 'old', 'etag': 'a', 'attempts': 3}, {'status': 200, 'value': 8, 'etag': 'b'}), {'value': 8, 'etag': 'b', 'attempts': 0})
    def test_false_new_value(self):
        self.assertEqual(refresh_cache({'value': 8, 'etag': 'a', 'attempts': 3}, {'status': 200, 'value': False}), {'value': False, 'etag': 'a', 'attempts': 0})
    def test_zero_cached_value(self):
        self.assertEqual(refresh_cache({'value': 0, 'etag': '', 'attempts': 2}, {'status': 304}), {'value': 0, 'etag': '', 'attempts': 0})
    def test_missing_new_value(self):
        self.assertEqual(refresh_cache({'value': 8, 'etag': 'a', 'attempts': 3}, {'status': 200}), {'value': None, 'etag': 'a', 'attempts': 0})
    def test_preserves_inputs(self):
        cache={'value': [], 'etag': 'a', 'attempts': 2};response={'status': 503}
        result=refresh_cache(cache,response)
        self.assertIsNot(result, cache)
        self.assertEqual(cache, {'value': [], 'etag': 'a', 'attempts': 2})
        self.assertEqual(response, {'status': 503})
