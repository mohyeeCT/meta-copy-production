import unittest
from unittest.mock import patch

from utils import dfs


class MetaDfsTests(unittest.TestCase):
    def test_keyword_overview_surfaces_api_error(self):
        with patch("utils.dfs._post_json", side_effect=RuntimeError("bad auth")):
            result = dfs.get_keyword_overview("login", "password", ["alpha"])

        self.assertIn("_error", result)
        self.assertIn("bad auth", result["_error"])

    def test_keyword_difficulty_surfaces_api_error(self):
        with patch("utils.dfs._post_json", side_effect=RuntimeError("bad auth")):
            result = dfs.get_keyword_difficulty("login", "password", ["alpha"])

        self.assertIn("_error", result)
        self.assertIn("bad auth", result["_error"])


if __name__ == "__main__":
    unittest.main()
