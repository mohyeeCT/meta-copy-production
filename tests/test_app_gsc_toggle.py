import unittest
from pathlib import Path


class MetaGscToggleTests(unittest.TestCase):
    def test_app_exposes_gsc_toggle_and_guards_gsc_client(self):
        source = Path("app.py").read_text(encoding="utf-8")

        self.assertIn("Use GSC for keyword selection", source)
        self.assertIn("if use_gsc:", source)
        self.assertIn("detect_ready = (\n        use_gsc and", source)
        self.assertIn("gsc_client = get_gsc_client(sa_info) if use_gsc else None", source)


if __name__ == "__main__":
    unittest.main()
