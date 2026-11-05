from reckon_saas_platform import marketing


def get_context(context):
    context.no_cache = 1
    context.body = marketing.llms_txt(
        marketing.site_base(), marketing.get_modules(), marketing.get_integrations()
    )
