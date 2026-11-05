import re

import frappe
from frappe.model.document import Document

from reckon_saas_platform.blog import CACHE_KEY, SLUG


class SEOArticle(Document):
    def validate(self):
        self.slug = re.sub(r"[^a-z0-9-]+", "-", (self.slug or "").lower()).strip("-")
        if not SLUG.fullmatch(self.slug or ""):
            frappe.throw("The URL slug must be 3-79 characters: lowercase letters, numbers and dashes.")
        if self.status == "Published":
            self.check_publishable()
            if not self.published_on:
                self.published_on = frappe.utils.nowdate()

    def check_publishable(self):
        from reckon_saas_platform.blog_agent import FORBIDDEN_ARTICLE, MAX_WORDS, word_count

        if not 70 <= len(self.summary or "") <= 160:
            frappe.throw("The summary must be 70-160 characters before publishing.")
        if not 20 <= len(self.title or "") <= 58:
            frappe.throw("The title must be 20-58 characters before publishing.")
        if not 150 <= word_count(self.body) <= MAX_WORDS:
            frappe.throw("The body must be 150-2200 words before publishing.")
        if FORBIDDEN_ARTICLE.search((self.title or "") + " " + (self.summary or "") + " " + (self.body or "")):
            frappe.throw("Remove unverifiable claims (the best, number one, guaranteed, cheapest), scripts and the framework name.")
        if re.search(r"\]\(http://", self.body or ""):
            frappe.throw("Links must be https or site-relative.")

    def on_update(self):
        frappe.cache.delete_value(CACHE_KEY)
        frappe.enqueue("reckon_saas_platform.seo.refresh_seo", trigger="article", queue="short", enqueue_after_commit=True)

    def on_trash(self):
        frappe.cache.delete_value(CACHE_KEY)
