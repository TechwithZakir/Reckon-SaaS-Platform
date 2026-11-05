from reckon_saas_platform import marketing


def get_context(context):
    context.no_cache = 1
    context.body = marketing.robots_txt(marketing.site_base())
