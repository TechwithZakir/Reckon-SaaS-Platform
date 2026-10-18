from __future__ import annotations

from dataclasses import dataclass

SAAS_PLATFORM_WORKSPACE = "Reckon SaaS Admin"


@dataclass(frozen=True)
class PlatformRole:
    name: str
    purpose: str


PLATFORM_ROLES = (
    PlatformRole("Reckon Vendor Superuser", "Vendor SaaS plan and tenant support control"),
)

TENANT_BYPASS_ROLES = frozenset({"Administrator", "System Manager", "Reckon Vendor Superuser"})
# Platform-wide roles a tenant login must never hold. Either one would let a
# tenant user step outside the tenant query conditions.
TENANT_FORBIDDEN_ROLES = frozenset({"System Manager", "Reckon Vendor Superuser"})

SAAS_ACTIVE_STATUSES = frozenset({"Active", "Trial", "Grace"})
SAAS_BLOCKED_STATUSES = frozenset({"Pending", "Due", "Expired", "Suspended", "Cancelled"})
CURRENT_SEED_VERSION = "2026.10.06"

REGISTRATION_VERIFICATION_TTL_HOURS = 48
SIGNUP_RATE_LIMIT_PER_HOUR = 5
VERIFY_RATE_LIMIT_PER_HOUR = 20
OPERATIONAL_ACCESS_CACHE_TTL_SECONDS = 300
