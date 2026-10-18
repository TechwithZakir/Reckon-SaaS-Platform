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
    }
]

required_apps = ["frappe", "erpnext"]

after_install = "reckon_saas_platform.install.after_install"
after_migrate = "reckon_saas_platform.install.after_migrate"

# Tenant users may use Desk and the API only while their company is provisioned
# and subscribed. See reckon_saas_platform.saas_gate.
before_request = ["reckon_saas_platform.saas_gate.enforce_operational_access"]
after_request = ["reckon_saas_platform.saas_gate.redirect_blocked_response"]

doc_events = {
    "User": {
        "validate": "reckon_saas_platform.tenant_security.validate_user_tenant_roles",
    },
}

# Google reCAPTCHA and BulkSMSBD are configured in SaaS Platform Settings. Other
# apps may add captcha verifiers here, e.g.:
# reckon_saas_signup_captcha_verifier = ["my_app.captcha.verify"]

website_route_rules = [
    {"from_route": "/reckonerp-signup", "to_route": "reckonerp_signup"},
    {"from_route": "/reckon-saas-admin", "to_route": "reckon_saas_admin"},
    {"from_route": "/reckonerp-subscription", "to_route": "reckonerp_subscription"},
]

permission_query_conditions = {
    "SaaS Payment": "reckon_saas_platform.saas_security.get_vendor_only_query",
    "SaaS Plan": "reckon_saas_platform.saas_security.get_vendor_only_query",
    "SaaS Registration": "reckon_saas_platform.saas_security.get_vendor_only_query",
    "SaaS Subscription": "reckon_saas_platform.saas_security.get_vendor_only_query",
    "Tenant Provisioning Job": "reckon_saas_platform.saas_security.get_vendor_only_query",
    "Tenant User Assignment": "reckon_saas_platform.tenant_security.get_tenant_user_assignment_query",
}

has_permission = {
    "SaaS Payment": "reckon_saas_platform.saas_security.has_vendor_only_permission",
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
