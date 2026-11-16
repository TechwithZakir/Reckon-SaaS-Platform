from reckon_saas_platform import marketing


def get_context(context):
    # One page per policy: a shared route would be cached once and show the same policy everywhere.
    marketing.apply_context(context, marketing.legal_page(marketing.site_base(), "privacy-policy"), marketing.get_modules())
