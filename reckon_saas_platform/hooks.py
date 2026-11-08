app_name = "reckon_saas_platform"
app_title = "Reckon SaaS Platform"
app_publisher = "Reckon Technologies Ltd."
app_description = "Reusable SaaS tenant, plan, subscription, payment, and provisioning platform"
app_email = "support@reckon.tech"
app_license = "MIT"
app_logo_url = "/assets/reckon_saas_platform/images/reckon-saas-platform-icon.svg"
app_icon_url = app_logo_url
app_icon_title = app_title
app_icon_route = "/desk/reckon-saas-admin"

add_to_apps_screen = [
    {
        "name": app_name,
        "logo": app_logo_url,
        "title": app_title,
        "route": app_icon_route,
        "desk_route": app_icon_route,
        "has_permission": "reckon_saas_platform.api.check_app_permission",
        "sequence_id": 20,
    },
]

required_apps = ["frappe", "erpnext"]

after_install = "reckon_saas_platform.install.after_install"
after_migrate = "reckon_saas_platform.install.after_migrate"
# Register a product app's SaaS module as soon as that app is installed.
after_app_install = "reckon_saas_platform.install.after_app_install"

# Tenant users may use Desk and the API only while their company is provisioned
# and subscribed. See reckon_saas_platform.saas_gate.
before_request = [
    "reckon_saas_platform.saas_gate.enforce_operational_access",
    "reckon_saas_platform.desk_module_guard.enforce_module_desk_access",
]
after_request = [
    "reckon_saas_platform.saas_gate.redirect_blocked_response",
    "reckon_saas_platform.marketing.redirect_signed_in_home",
]

# Signed-in users go to their module, not the marketing home page; /login carries
# the same name, logo and "powered by" as the landing page.
get_website_user_home_page = "reckon_saas_platform.marketing.website_user_home_page"
web_include_css = ["/assets/reckon_saas_platform/css/reckon_login.css"]
web_include_js = ["/assets/reckon_saas_platform/js/reckon_login.js"]

# Keep subscription statuses in step with trial, paid-period and grace dates.
# Access itself is decided from the dates, so the gate never waits for this job.
scheduler_events = {
    "weekly": ["reckon_saas_platform.seo_agent.run_agent_weekly"],
    "daily": [
        "reckon_saas_platform.saas.refresh_subscription_statuses",
        "reckon_saas_platform.seo.refresh_seo_daily",
        "reckon_saas_platform.invoices.create_renewal_invoices",
        "reckon_saas_platform.invoices.send_payment_reminders",
    ],
}

doc_events = {
    "User": {
        "validate": "reckon_saas_platform.tenant_security.validate_user_tenant_roles",
    },
    # Team and module access follow every assignment, for every tenant module.
    "Tenant User Assignment": {
        "after_insert": "reckon_saas_platform.team.sync_tenant_user_access",
        "on_update": "reckon_saas_platform.team.sync_tenant_user_access",
    },
}

# Google reCAPTCHA and BulkSMSBD are configured in SaaS Platform Settings. Other
# apps may add captcha verifiers here, e.g.:
# reckon_saas_signup_captcha_verifier = ["my_app.captcha.verify"]

# The site root is the public marketing website (www/index). Signup and login stay
# on /reckonerp-signup and /login; see reckon_saas_platform.marketing.
home_page = "index"

website_route_rules = [
    {"from_route": "/features", "to_route": "reckon_features"},
    {"from_route": "/features/<slug>", "to_route": "reckon_features"},
    {"from_route": "/industries", "to_route": "reckon_industries"},
    {"from_route": "/industries/<slug>", "to_route": "reckon_industries"},
    {"from_route": "/modules", "to_route": "reckon_modules"},
    {"from_route": "/modules/<slug>", "to_route": "reckon_modules"},
    {"from_route": "/integrations", "to_route": "reckon_integrations"},
    {"from_route": "/pricing", "to_route": "reckon_pricing"},
    {"from_route": "/sitemap.xml", "to_route": "reckon_sitemap.xml"},
    {"from_route": "/robots.txt", "to_route": "reckon_robots.txt"},
    {"from_route": "/llms.txt", "to_route": "reckon_llms.txt"},
    {"from_route": "/llms-full.txt", "to_route": "reckon_llms_full.txt"},
    {"from_route": "/faq", "to_route": "reckon_faq"},
    {"from_route": "/invoice/<key>", "to_route": "reckon_invoice"},
    {"from_route": "/blog", "to_route": "reckon_blog"},
    {"from_route": "/blog/rss.xml", "to_route": "reckon_blog_rss.xml"},
    {"from_route": "/blog/<slug>", "to_route": "reckon_blog"},
    {"from_route": "/<key>.txt", "to_route": "reckon_indexnow_key.txt"},
    {"from_route": "/reckonerp-signup", "to_route": "reckonerp_signup"},
    {"from_route": "/reckon-saas-admin", "to_route": "reckon_saas_admin"},
    {"from_route": "/reckonerp-subscription", "to_route": "reckonerp_subscription"},
]

permission_query_conditions = {
    "SaaS Payment": "reckon_saas_platform.saas_security.get_vendor_only_query",
    "SaaS Invoice": "reckon_saas_platform.saas_security.get_vendor_only_query",
    "SEO Article": "reckon_saas_platform.saas_security.get_vendor_only_query",
    "SEO Suggestion": "reckon_saas_platform.saas_security.get_vendor_only_query",
    "SaaS Plan": "reckon_saas_platform.saas_security.get_vendor_only_query",
    "SaaS Registration": "reckon_saas_platform.saas_security.get_vendor_only_query",
    "SaaS Subscription": "reckon_saas_platform.saas_security.get_vendor_only_query",
    "Tenant Provisioning Job": "reckon_saas_platform.saas_security.get_vendor_only_query",
    "Tenant User Assignment": "reckon_saas_platform.tenant_security.get_tenant_user_assignment_query",
}

has_permission = {
    "SaaS Payment": "reckon_saas_platform.saas_security.has_vendor_only_permission",
    "SaaS Invoice": "reckon_saas_platform.saas_security.has_vendor_only_permission",
    "SEO Article": "reckon_saas_platform.saas_security.has_vendor_only_permission",
    "SEO Suggestion": "reckon_saas_platform.saas_security.has_vendor_only_permission",
    "SaaS Plan": "reckon_saas_platform.saas_security.has_vendor_only_permission",
    "SaaS Platform Settings": "reckon_saas_platform.saas_security.has_vendor_only_permission",
    "SaaS Registration": "reckon_saas_platform.saas_security.has_vendor_only_permission",
    "SaaS Subscription": "reckon_saas_platform.saas_security.has_vendor_only_permission",
    "Tenant Provisioning Job": "reckon_saas_platform.saas_security.has_vendor_only_permission",
    "Tenant User Assignment": "reckon_saas_platform.tenant_security.has_tenant_user_assignment_permission",
}

fixtures = [
    {
        "dt": "Role",
        "filters": [["name", "in", ["Reckon Vendor Superuser"]]],
    },
    {
        "dt": "Workspace",
        "filters": [["name", "=", "Reckon SaaS Admin"]],
    },
]
