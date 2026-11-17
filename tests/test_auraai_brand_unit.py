import unittest

from frappe_stub import REPO_ROOT

PKG = REPO_ROOT / "reckon_saas_platform"


class AuraAiBrandTests(unittest.TestCase):
    def test_the_old_name_is_gone_from_the_site_text(self):
        for path in list(PKG.glob("*.py")) + list((PKG / "www").glob("*.html")) + list((PKG / "templates").rglob("*.html")):
            self.assertNotIn("Reckon AI", path.read_text(encoding="utf-8"), path.name)

    def test_fill_with_ai_is_described_under_ask_ai(self):
        text = (PKG / "marketing.py").read_text(encoding="utf-8")
        ask = text[text.index('"slug": "ask-ai"'):text.index('"slug": "reckon-ai-assistant"')]
        for marker in ("Fill with AI", "photo or PDF", "customer, supplier or item", "limited by plan"):
            self.assertIn(marker, ask, marker)
        bn = (PKG / "marketing_bn_pages.py").read_text(encoding="utf-8")
        self.assertIn("Fill with AI কী এবং কোন কোন ফর্মে কাজ করে?", bn)

    def test_a_patch_renames_published_articles(self):
        self.assertIn("rename_reckon_ai_to_auraai", (PKG / "patches.txt").read_text(encoding="utf-8"))
        self.assertIn("AuraAI", (PKG / "patches" / "rename_reckon_ai_to_auraai.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
