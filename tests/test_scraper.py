import unittest
from unittest.mock import patch

from utils import scraper


class MetaScraperTests(unittest.TestCase):
    def test_scraper_retries_without_selector_when_filtered_body_is_empty(self):
        class FakeResponse:
            def __init__(self, text):
                self.text = text
                self.status_code = 200

            def raise_for_status(self):
                return None

        with patch.object(
            scraper.requests,
            "get",
            side_effect=[
                FakeResponse("Menu\nAdd to cart"),
                FakeResponse(
                    "This service helps growing teams plan implementation, "
                    "coordinate delivery, and support customers after launch."
                ),
            ],
        ) as request:
            result = scraper.scrape_page_context(
                "test-key",
                "https://example.com/services",
            )

        self.assertTrue(result["success"])
        self.assertIn("plan implementation", result["content"])
        self.assertEqual(request.call_count, 2)
        self.assertNotIn(
            "X-Remove-Selector",
            request.call_args_list[1].kwargs["headers"],
        )

    def test_clean_reader_text_scores_linked_paragraphs_independently(self):
        content, _ = scraper._clean_reader_text(
            """
Customers can review the [service options](https://example.com/services) before choosing support for their team.

The [implementation process](https://example.com/process) includes practical planning for each stage of the project.

Ongoing [customer support](https://example.com/support) helps teams resolve questions after the initial launch.
""",
            max_chars=1000,
        )

        self.assertIn("service options", content)
        self.assertIn("implementation process", content)
        self.assertIn("customer support", content)

    def test_clean_reader_text_filters_noise_and_keeps_substantive_copy(self):
        content, title = scraper._clean_reader_text(
            """
Title: Example Product

Menu

This product is designed for everyday training with lightweight support and breathable materials.

Add to cart

Customers can use it for short runs, gym sessions, and casual walks.
""",
            max_chars=500,
        )

        self.assertEqual(title, "Example Product")
        self.assertIn("lightweight support", content)
        self.assertIn("casual walks", content)
        self.assertNotIn("Add to cart", content)
        self.assertNotIn("Menu", content)


if __name__ == "__main__":
    unittest.main()
