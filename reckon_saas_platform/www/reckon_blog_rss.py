from reckon_saas_platform import blog, marketing


def get_context(context):
    context.no_cache = 1
    context.body = blog.rss_xml(marketing.site_base(), blog.get_articles())
