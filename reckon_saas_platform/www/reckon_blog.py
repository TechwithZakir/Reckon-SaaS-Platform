import frappe

from reckon_saas_platform import blog, marketing


def get_context(context):
    base = marketing.site_base()
    modules = marketing.get_modules()
    articles = blog.get_articles()
    slug = marketing.requested("slug")
    if not slug:
        page = blog.blog_page(base, articles)
    else:
        article = blog.get_article(slug)
        if not article:
            raise frappe.DoesNotExistError
        page = blog.article_page(base, article, articles)
    marketing.apply_context(context, page, modules)
