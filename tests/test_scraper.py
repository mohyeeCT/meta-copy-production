import unittest

from utils import scraper


class MetaScraperTests(unittest.TestCase):
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
