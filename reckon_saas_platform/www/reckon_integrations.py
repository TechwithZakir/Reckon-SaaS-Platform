from reckon_saas_platform import marketing


def get_context(context):
    modules = marketing.get_modules()
    marketing.apply_context(context, marketing.integrations_page(marketing.site_base()), modules)
