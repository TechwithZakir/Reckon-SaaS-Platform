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

## Signup verification

Public signup creates no Company or User until the owner has verified both the
email link and, by default, an SMS one-time code. Configure it in
**SaaS Platform Settings** (`/app/saas-platform-settings`, vendor only):

- **BulkSMSBD API Key / Sender ID**: from your bulksmsbd.net account. Codes are
  sent in English, so use a non-masking sender ID (BulkSMSBD requires Bengali
  text for masking senders).
- **reCAPTCHA Site Key / Secret Key**: create a reCAPTCHA **v2 "I'm not a
  robot"** key at https://www.google.com/recaptcha/admin and restrict it to the
  signup domain.
- **Require Phone Verification / Require Captcha** are on by default. While
  either is on without credentials, signup answers 503 "temporarily
  unavailable", so configure the keys right after deploying.

Failed provisioning jobs show on `/reckon-saas-admin` with a **Retry
Provisioning** button.

## Modules and plans

Each product app declares its module in the `reckon_saas_modules` hook. On
install and on every migrate the platform creates a **SaaS Module** record for
it (`/app/saas-module`). Every **SaaS Plan** belongs to one module, and
registrations and subscriptions record the module they were bought for.

- Untick **Available for Sale** on a module to stop new signups for its plans.
- `/reckonerp-signup?module=<key>` shows only that module's plans; without the
  parameter, plans are grouped by module.
- A company keeps Desk access while any of its module subscriptions is active.
  `is_subscription_active(company, saas_module=...)` checks a single module.

The vendor **Dashboard** (`/app/saas-dashboard`) is the first item in the SaaS
Platform sidebar.
