import unittest

from frappe_stub import REPO_ROOT

PKG = REPO_ROOT / "reckon_saas_platform"


class AuraAiBrandTests(unittest.TestCase):
    def test_the_old_name_is_gone_from_the_site_text(self):
        for path in list(PKG.glob("*.py")) + list((PKG / "www").glob("*.html")) + list((PKG / "templates").rglob("*.html")):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("Reckon AI", text, path.name)
            self.assertNotIn("AuraAI", text, path.name)  # spelled with a space: Aura AI

    def test_fill_with_ai_is_described_on_the_one_assistant_page(self):
        text = (PKG / "marketing.py").read_text(encoding="utf-8")
        self.assertNotIn('"slug": "ask-ai"', text)
        self.assertNotIn('"slug": "reckon-ai-assistant"', text)
        ask = text[text.index('"slug": "aura-ai-assistant"'):text.index('"slug": "field-sales-and-visits"')]
        for marker in ("Fill with AI", "photo or PDF", "customer, supplier or item", "limited by plan"):
            self.assertIn(marker, ask, marker)
        bn = (PKG / "marketing_bn_pages.py").read_text(encoding="utf-8")
        self.assertIn("Fill with AI কী এবং কোন কোন ফর্মে কাজ করে?", bn)

    def test_the_old_ask_ai_and_assistant_addresses_redirect_to_the_one_page(self):
        hooks = (PKG / "hooks.py").read_text(encoding="utf-8")
        for old in ("/features/ask-ai", "/features/reckon-ai-assistant", "/bn/features/ask-ai", "/bn/features/reckon-ai-assistant"):
            self.assertIn(f'"source": "{old}"', hooks)
        self.assertIn("merge_ai_pages_links", (PKG / "patches.txt").read_text(encoding="utf-8"))

    def test_a_patch_renames_published_articles(self):
        self.assertIn("rename_reckon_ai_to_auraai", (PKG / "patches.txt").read_text(encoding="utf-8"))
        self.assertIn("Aura AI", (PKG / "patches" / "rename_reckon_ai_to_auraai.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
