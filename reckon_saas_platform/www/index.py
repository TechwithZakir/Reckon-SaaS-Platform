from reckon_saas_platform import marketing


def get_context(context):
    modules = marketing.get_modules()
    marketing.apply_context(context, marketing.home_page(marketing.site_base(), modules, marketing.get_integrations()), modules)
