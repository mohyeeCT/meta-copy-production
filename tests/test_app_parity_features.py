from pathlib import Path
import unittest


APP_SOURCE = Path(__file__).resolve().parents[1] / "app.py"


class AppParityFeatureTests(unittest.TestCase):
    def setUp(self):
        self.source = APP_SOURCE.read_text(encoding="utf-8")

    def test_app_exposes_jina_scraping_controls_and_passes_context(self):
        self.assertIn("from utils.scraper import scrape_page_context", self.source)
        self.assertIn('"Jina Reader"', self.source)
        self.assertIn('"Enable page scraping"', self.source)
        self.assertIn("scrape_page_context(jina_key, url", self.source)
        self.assertIn("PAGE CONTENT EXCERPT", self.source)
        self.assertIn("context=_effective_context", self.source)

    def test_app_exposes_partial_results_and_auto_write_controls(self):
        self.assertIn("RESULT_COL_MAP", self.source)
        self.assertIn('"Auto-write completed rows to Google Sheet"', self.source)
        self.assertIn('st.session_state["partial_results"]', self.source)
        self.assertIn("partial_results_placeholder", self.source)
        self.assertIn("write_results_to_sheet(ws, pd.DataFrame(results), RESULT_COL_MAP)", self.source)

    def test_app_adds_review_flags_and_scrape_status_to_output(self):
        self.assertIn("def _build_review_flags", self.source)
        self.assertIn('"review_flags"', self.source)
        self.assertIn('"scrape_status"', self.source)
        self.assertIn('"Review Flags"', self.source)
        self.assertIn('"Page Scrape Status"', self.source)


if __name__ == "__main__":
    unittest.main()
