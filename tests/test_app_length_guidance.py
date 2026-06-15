from pathlib import Path
import unittest


APP_SOURCE = Path(__file__).resolve().parents[1] / "app.py"
README = Path(__file__).resolve().parents[1] / "README.md"


class AppLengthGuidanceTests(unittest.TestCase):
    def test_title_length_warning_uses_relaxed_guidance(self):
        source = APP_SOURCE.read_text(encoding="utf-8")
        readme = README.read_text(encoding="utf-8")

        self.assertIn('int(row["title_length"]) > 100', source)
        self.assertIn("flagged if > 100", readme)
        self.assertNotIn("flagged red if > 60", readme)


if __name__ == "__main__":
    unittest.main()
