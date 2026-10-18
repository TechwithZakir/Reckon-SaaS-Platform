"""A minimal in-memory ``frappe`` stand-in for database-free unit tests."""

from __future__ import annotations

import importlib
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

REPO_ROOT = Path(__file__).resolve().parents[1]


class _Dict(dict):
    __getattr__ = dict.get

    def __setattr__(self, key, value):
        self[key] = value


class FakeCache:
    def __init__(self):
        self.store: dict[str, object] = {}

    def get_value(self, key):
        return self.store.get(key)

    def set_value(self, key, value, expires_in_sec=None):
        self.store[key] = value

    def delete_value(self, key):
        self.store.pop(key, None)


class FakeSettings(_Dict):
    """SaaS Platform Settings with phone verification and captcha switched off."""

    def __init__(self, **values):
        super().__init__(
            require_phone_verification=0,
            require_captcha=0,
            bulksmsbd_sender_id="",
            recaptcha_site_key="",
            otp_validity_minutes=10,
            otp_max_attempts=5,
            otp_resend_cooldown_seconds=60,
            passwords={},
        )
        self.update(values)

    def get_password(self, fieldname, raise_exception=True):
        return self["passwords"].get(fieldname)


def plan_lookup(enabled=1, saas_module="distribution", module_enabled=1):
    """``frappe.db.get_value`` side effect for SaaS Plan / SaaS Module lookups."""

    def get_value(doctype, *args, **kwargs):
        if doctype == "SaaS Plan":
            return _Dict(enabled=enabled, saas_module=saas_module)
        if doctype == "SaaS Module":
            return module_enabled
        return None

    return get_value


def build_requests() -> ModuleType:
    requests = ModuleType("requests")

    class RequestException(Exception):
        pass

    requests.RequestException = RequestException
    requests.post = Mock()
    return requests


def build_frappe() -> ModuleType:
    frappe = ModuleType("frappe")

    class ValidationError(Exception):
        http_status_code = 417

    class PermissionError(Exception):  # noqa: A001 - mirrors frappe.PermissionError
        http_status_code = 403

    class DuplicateEntryError(Exception):
        http_status_code = 409

    def throw(msg, exc=ValidationError, *args, **kwargs):
        raise exc(msg)

    frappe.ValidationError = ValidationError
    frappe.PermissionError = PermissionError
    frappe.DuplicateEntryError = DuplicateEntryError
    frappe.DoesNotExistError = type("DoesNotExistError", (ValidationError,), {})
    frappe._ = lambda text: text
    frappe._dict = _Dict
    frappe.throw = Mock(side_effect=throw)
    frappe.whitelist = lambda *args, **kwargs: (lambda fn: fn)
    frappe.get_roles = Mock(return_value=[])
    frappe.get_all = Mock(return_value=[])
    frappe.get_doc = Mock()
    frappe.get_hooks = Mock(return_value=[])
    frappe.get_attr = Mock()
    frappe.log_error = Mock()
    frappe.get_traceback = Mock(return_value="traceback")
    frappe.enqueue = Mock()
    frappe.sendmail = Mock()
    frappe.set_user = Mock()
    frappe.clear_cache = Mock()
    frappe.generate_hash = Mock(return_value="token")
    frappe.settings = FakeSettings()
    frappe.get_cached_doc = Mock(side_effect=lambda doctype: frappe.settings)
    frappe.conf = _Dict()
    frappe.flags = _Dict()
    frappe.session = _Dict(user="Administrator")
    frappe.local = _Dict(form_dict=_Dict())
    frappe.cache = FakeCache()
    frappe.db = Mock()
    frappe.db.exists = Mock(return_value=None)
    frappe.db.get_value = Mock(return_value=None)
    frappe.db.after_commit = Mock()

    utils = ModuleType("frappe.utils")
    for name in (
        "add_days",
        "add_to_date",
        "get_datetime",
        "get_url",
        "getdate",
        "now_datetime",
        "nowdate",
    ):
        setattr(utils, name, Mock(name=name))
    utils.cint = lambda value: int(value or 0)
    utils.flt = lambda value: float(value or 0)
    utils.strip_html = lambda value: value
    utils.escape_html = lambda value: value
    utils.validate_email_address = lambda value, throw=False: value if "@" in value else ""
    frappe.utils = utils

    rate_limiter = ModuleType("frappe.rate_limiter")
    rate_limiter.rate_limit = lambda **kwargs: (lambda fn: fn)
    frappe.rate_limiter = rate_limiter

    model = ModuleType("frappe.model")
    document = ModuleType("frappe.model.document")
    document.Document = object
    model.document = document
    frappe.model = model
    return frappe


@contextmanager
def platform_modules(*names: str):
    """Import ``reckon_saas_platform`` modules against a fresh frappe stub."""
    frappe = build_frappe()
    frappe.requests = build_requests()
    stubs = {
        "requests": frappe.requests,
        "frappe": frappe,
        "frappe.utils": frappe.utils,
        "frappe.rate_limiter": frappe.rate_limiter,
        "frappe.model": frappe.model,
        "frappe.model.document": frappe.model.document,
    }
    saved_path = list(sys.path)
    sys.path.insert(0, str(REPO_ROOT))
    saved = {key: mod for key, mod in sys.modules.items() if key.startswith("reckon_saas_platform")}
    for key in saved:
        del sys.modules[key]
    try:
        with patch.dict(sys.modules, stubs):
            modules = [importlib.import_module(f"reckon_saas_platform.{name}") for name in names]
            yield frappe, modules
    finally:
        for key in [key for key in sys.modules if key.startswith("reckon_saas_platform")]:
            del sys.modules[key]
        sys.modules.update(saved)
        sys.path[:] = saved_path
