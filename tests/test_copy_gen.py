import unittest

from utils import copy_gen


class MetaCopyGenTests(unittest.TestCase):
    def test_provider_fallback_models_match_sidebar_defaults(self):
        self.assertEqual(
            copy_gen.DEFAULT_MODELS,
            {
                "Claude": "claude-sonnet-5",
                "OpenAI": "gpt-5.5",
                "Gemini (free)": "gemini-3.5-flash",
            },
        )

    def test_sonnet_5_request_leaves_thinking_unset(self):
        options = copy_gen._anthropic_request_options("claude-sonnet-5", 512)

        self.assertEqual(options, {"model": "claude-sonnet-5", "max_tokens": 512})
        self.assertNotIn("thinking", options)
        self.assertNotIn("extra_body", options)

    def test_anthropic_text_extractor_skips_non_text_blocks(self):
        class Block:
            def __init__(self, type_, text=None):
                self.type = type_
                self.text = text

        self.assertEqual(
            copy_gen._extract_anthropic_text([
                Block("thinking"),
                Block("text", '{"title":"A","description":"B","h1_optimised":"C"}'),
            ]),
            '{"title":"A","description":"B","h1_optimised":"C"}',
        )

    def test_openai_gpt5_models_use_completion_token_parameter(self):
        self.assertEqual(
            copy_gen._openai_token_limit("gpt-5.5", 512),
            {"max_completion_tokens": 512},
        )
        self.assertEqual(
            copy_gen._openai_token_limit("gpt-5.4", 512),
            {"max_completion_tokens": 512},
        )

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

        self.assertIn("aim for about 80 to 100 characters", prompt)
        self.assertIn("aim for about 140 to 180 characters", prompt)
        self.assertNotIn("This is a strict limit", prompt)

    def test_normalise_copy_result_uses_relaxed_title_safety_cap(self):
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
        self.assertLessEqual(len(result["title"]), 120)
        self.assertLessEqual(len(result["description"]), 180)
        self.assertEqual(result["h1_optimised"], "Optimised H1")

    def test_normalise_copy_result_caps_extreme_titles_at_120(self):
        result = copy_gen._normalise_copy_result(
            {
                "title": " ".join(["descriptive"] * 30),
                "description": "Description",
                "h1_optimised": "Optimised H1",
            }
        )

        self.assertLessEqual(len(result["title"]), 120)


if __name__ == "__main__":
    unittest.main()
