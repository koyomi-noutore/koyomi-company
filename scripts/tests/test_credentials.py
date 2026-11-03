"""python3 -m unittest discover -s scripts/tests"""
import json, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import credentials as c

GOOD = {"installed": {"client_id": "id", "client_secret": "sec", "token_uri": "t", "auth_uri": "a", "redirect_uris": ["http://localhost"]}}


class T(unittest.TestCase):
    def run_with(self, raw):
        os.environ["YOUTUBE_CLIENT_SECRET_JSON"] = raw
        return c.youtube_client()

    def test_correct_json(self):
        self.assertEqual(self.run_with(json.dumps(GOOD))["client_id"], "id")

    def test_missing_inner_brace(self):
        broken = json.dumps(GOOD).replace('{"installed": {', '{"installed":', 1)
        self.assertEqual(self.run_with(broken)["client_secret"], "sec")

    def test_missing_inner_brace_web(self):
        broken = '{"web":' + json.dumps(GOOD["installed"])[1:] + "}"
        self.assertEqual(self.run_with(broken)["client_id"], "id")

    def test_other_breakage_rejected(self):
        with self.assertRaises(SystemExit):
            self.run_with('{"installed": {"client_id": "id",')

    def test_missing_fields_rejected(self):
        with self.assertRaises(SystemExit):
            self.run_with('{"installed":{"client_id":"id"}}')


if __name__ == "__main__":
    unittest.main()
