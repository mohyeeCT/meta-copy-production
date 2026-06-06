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

    def test_prompt_uses_length_guidance_not_strict_limits(self):
        prompt = copy_gen._build_prompt(
            copy_gen.COPY_PROMPT,
            url="https://example.com/services",
            keyword="commercial roofing services",
            page_type="service",
            brand_name="Acme",
            forbidden_phrases="",
            context="",
            business_type="service",
            h1="Commercial Roofing Services",
        )

        self.assertIn("Title should usually land around 50 to 65 characters", prompt)
        self.assertIn("Meta description should usually land around 140 to 165 characters", prompt)
        self.assertNotIn("This is a strict limit", prompt)

    def test_normalise_copy_result_preserves_longer_copy(self):
        long_title = "This is a very long SEO title that should stay intact for review instead of being shortened automatically"
        long_description = " ".join(["description"] * 30)
        result = copy_gen._normalise_copy_result(
            {
                "title": long_title,
                "description": long_description,
                "h1_optimised": "Optimised H1",
            },
            brand_name="Acme",
        )

        self.assertEqual(result["title"], long_title)
        self.assertEqual(result["description"], long_description)
        self.assertEqual(result["h1_optimised"], "Optimised H1")


if __name__ == "__main__":
    unittest.main()
