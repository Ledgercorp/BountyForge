import io
import json
import unittest
from unittest.mock import patch

from bountyforge.model import LocalModel, ensure_loopback


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class ModelTests(unittest.TestCase):
    def test_blocks_remote_inference(self):
        bad = [
            "https://api.openai.com/v1/chat/completions",
            "http://127.0.0.2:8080/v1/chat/completions",
            "http://localhost:9999/v1/chat/completions",
            "http://127.0.0.1:8080/private",
            "http://user:password@localhost:8080/v1/chat/completions",
        ]
        for endpoint in bad:
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(ValueError):
                    ensure_loopback(endpoint)

    def test_accepts_local_endpoint(self):
        ensure_loopback("http://127.0.0.1:8080/v1/chat/completions")

    def test_response_shape(self):
        fake = FakeResponse(json.dumps({"choices": [{"message": {"content": "Write tests first."}}]}).encode())
        with patch("urllib.request.urlopen", return_value=fake) as requester:
            result = LocalModel().analyze({"title": "sample", "url": "https://github.com/a/b/issues/1"})
        self.assertEqual(result, "Write tests first.")
        req = requester.call_args.args[0]
        self.assertEqual(req.full_url, "http://127.0.0.1:8080/v1/chat/completions")
        payload = json.loads(req.data)
        self.assertEqual(payload["model"], "local")
        self.assertNotIn("api_key", json.dumps(payload).lower())


if __name__ == "__main__":
    unittest.main()
