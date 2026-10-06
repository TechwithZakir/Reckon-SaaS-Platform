# Reckon SaaS Platform

Reusable parent SaaS platform for Reckon ERP apps on Frappe/ERPNext v15 and v16+.

This app owns tenant identity, subscription plans, registration, payment
verification, provisioning jobs, tenant assignment, route gates, and public SaaS
pages. Business modules such as `reckon_distribution` plug into it through the
`reckon_saas_modules` hook.

Install before product modules:

```bash
bench get-app reckon_saas_platform <platform-repo-url>
bench --site distribution.reckon.tech install-app reckon_saas_platform
```

Then install a product module such as `reckon_distribution`.
