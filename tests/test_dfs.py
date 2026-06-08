import unittest
from unittest.mock import patch

from utils import dfs


class MetaDfsTests(unittest.TestCase):
    def test_keyword_overview_raises_on_api_error(self):
        with patch("utils.dfs._post_json", side_effect=RuntimeError("bad auth")):
            with self.assertRaises(RuntimeError) as ctx:
                dfs.get_keyword_overview("login", "password", ["alpha"])
        self.assertIn("bad auth", str(ctx.exception))

    def test_keyword_difficulty_raises_on_api_error(self):
        with patch("utils.dfs._post_json", side_effect=RuntimeError("bad auth")):
            with self.assertRaises(RuntimeError) as ctx:
                dfs.get_keyword_difficulty("login", "password", ["alpha"])
        self.assertIn("bad auth", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
