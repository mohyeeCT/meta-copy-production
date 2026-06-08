import unittest

from utils.keyword import select_keyword


class KeywordSelectionTests(unittest.TestCase):
    def test_ctr_cap_prevents_outlier_from_winning(self):
        """A keyword with 80% CTR must not beat a stronger keyword due to uncapped CTR."""
        queries = [
            {"query": "buy widgets online", "impressions": 500, "clicks": 50,  "ctr": 0.10, "position": 5.0},
            {"query": "widget store",       "impressions": 100, "clicks": 80,  "ctr": 0.80, "position": 5.0},
        ]
        dfs_data = {
            "buy widgets online": {"volume": 1000, "difficulty": 20},
            "widget store":       {"volume": 200,  "difficulty": 20},
        }

        result = select_keyword(gsc_queries=queries, dfs_data=dfs_data, branded_terms=[])

        self.assertEqual(result["selected_keyword"], "buy widgets online",
                         "High-volume keyword should win; outlier CTR must not override it")

    def test_normal_ctr_unaffected_by_cap(self):
        """CTR values below 0.15 must pass through the cap unchanged."""
        queries = [
            {"query": "red widgets", "impressions": 200, "clicks": 20, "ctr": 0.10, "position": 3.0},
        ]
        dfs_data = {"red widgets": {"volume": 300, "difficulty": 30}}

        result = select_keyword(gsc_queries=queries, dfs_data=dfs_data, branded_terms=[])

        self.assertIsNotNone(result["selected_keyword"])
        self.assertEqual(result["selected_keyword"], "red widgets")


if __name__ == "__main__":
    unittest.main()
