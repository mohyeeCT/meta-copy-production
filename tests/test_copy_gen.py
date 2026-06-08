import unittest

from utils import copy_gen


class MetaCopyGenTests(unittest.TestCase):
    def test_ecommerce_prompt_blocks_unsupported_claims(self):
        prompt = copy_gen._build_prompt(
            copy_gen.COPY_PROMPT,
            url="https://example.com/shoes",
            keyword="running shoes",
            page_type="category",
            brand_name="Acme",
            forbidden_phrases="",
            context="",
            business_type="ecommerce",
            h1="Running Shoes",
        )

        self.assertIn("UNSUPPORTED CLAIM RULES", prompt)
        self.assertIn("Do not state return", prompt)
        self.assertIn("shipping", prompt)
        self.assertIn("warranty", prompt)
        self.assertIn("unless explicitly present", prompt)
        self.assertNotIn("Free shipping", prompt)

    def test_parse_copy_json_strips_fences_and_requires_object(self):
        parsed = copy_gen._parse_copy_json(
            '```json\n{"title":"A","description":"B","h1_optimised":"C"}\n```'
        )

        self.assertEqual(parsed["title"], "A")
        self.assertEqual(parsed["description"], "B")
        self.assertEqual(parsed["h1_optimised"], "C")

    def test_normalise_copy_result_enforces_seo_lengths(self):
        result = copy_gen._normalise_copy_result(
            {
                "title": "This is a very long SEO title that should be shortened before sheet writeback",
                "description": " ".join(["description"] * 30),
                "h1_optimised": "Optimised H1",
            },
            brand_name="Acme",
        )

        self.assertLessEqual(len(result["title"]), 80)
        self.assertLessEqual(len(result["description"]), 180)
        self.assertEqual(result["h1_optimised"], "Optimised H1")


if __name__ == "__main__":
    unittest.main()
