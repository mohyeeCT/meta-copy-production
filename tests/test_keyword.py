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


    def test_restricted_industry_scores_zero_volume_keywords(self):
        """In restricted mode, keywords with no DFS volume must still be scored."""
        queries = [
            {"query": "cbd tinctures", "impressions": 400, "clicks": 40, "ctr": 0.10, "position": 4.0},
        ]
        # No DFS data for this keyword (volume suppressed)
        dfs_data = {}

        result = select_keyword(
            gsc_queries=queries,
            dfs_data=dfs_data,
            branded_terms=[],
            restricted_industry=True,
        )

        self.assertIsNotNone(result["selected_keyword"],
                             "Restricted mode must select a keyword even with no DFS volume")
        self.assertEqual(result["selected_keyword"], "cbd tinctures")

    def test_standard_mode_drops_zero_volume_keywords(self):
        """In standard mode, keywords with no DFS data must be skipped."""
        queries = [
            {"query": "cbd tinctures", "impressions": 400, "clicks": 40, "ctr": 0.10, "position": 4.0},
        ]
        dfs_data = {}

        result = select_keyword(
            gsc_queries=queries,
            dfs_data=dfs_data,
            branded_terms=[],
            restricted_industry=False,
        )

        self.assertIsNone(result["selected_keyword"],
                          "Standard mode must not select a keyword when DFS data is absent")
        self.assertTrue(result["fallback_triggered"])

    def test_restricted_industry_ignores_min_volume_filter(self):
        """In restricted mode, keywords below min_volume must still compete."""
        queries = [
            {"query": "artisan hemp extract", "impressions": 200, "clicks": 10, "ctr": 0.05, "position": 5.0},
        ]
        dfs_data = {"artisan hemp extract": {"volume": 5, "difficulty": 30}}

        result = select_keyword(
            gsc_queries=queries,
            dfs_data=dfs_data,
            branded_terms=[],
            min_volume=50,
            restricted_industry=True,
        )

        self.assertEqual(result["selected_keyword"], "artisan hemp extract",
                         "Restricted mode must not apply min_volume filter")


if __name__ == "__main__":
    unittest.main()
