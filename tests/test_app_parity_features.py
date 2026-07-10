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

    def test_app_exposes_only_approved_provider_model_set(self):
        self.assertIn('"Claude"', self.source)
        self.assertIn('"OpenAI"', self.source)
        self.assertIn('"Gemini (free)"', self.source)
        self.assertIn("Claude Sonnet 5", self.source)
        self.assertIn("claude-sonnet-5", self.source)
        self.assertIn("claude-sonnet-4-6", self.source)
        self.assertIn("claude-haiku-4-5-20251001", self.source)
        self.assertIn("gpt-5.5", self.source)
        self.assertIn("gpt-5.4", self.source)
        self.assertIn("gemini-3.5-flash", self.source)
        self.assertNotIn("Mistral", self.source)
        self.assertNotIn("Groq", self.source)
        self.assertNotIn("gemini-2.0-flash", self.source)
        self.assertNotIn("gpt-5.4-mini", self.source)
        self.assertNotIn("gpt-5.4-nano", self.source)
        self.assertNotIn("gpt-4o", self.source)


if __name__ == "__main__":
    unittest.main()
