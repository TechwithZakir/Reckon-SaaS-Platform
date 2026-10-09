from __future__ import annotations

from unittest.mock import patch

from reckon_saas_platform import hooks
from reckon_saas_platform.api import check_app_permission
from reckon_saas_platform.install import _workspace_doc


def test_saas_app_has_a_real_desk_route():
    item = hooks.add_to_apps_screen[0]
    assert item["route"] == "/desk/reckon-saas-admin"
    assert item["desk_route"] == "/desk/reckon-saas-admin"


def test_saas_app_is_hidden_from_tenant_users():
    with patch("reckon_saas_platform.api.frappe.session", frappe_session("tenant@example.com")):
        with patch(
            "reckon_saas_platform.api.frappe.get_roles",
            return_value=["Reckon Distribution User"],
        ):
            assert check_app_permission() is False


def test_saas_app_is_visible_to_vendor_users():
    with patch("reckon_saas_platform.api.frappe.session", frappe_session("vendor@example.com")):
        with patch(
            "reckon_saas_platform.api.frappe.get_roles",
            return_value=["Reckon Vendor Superuser"],
        ):
            assert check_app_permission() is True


def test_saas_workspace_uses_url_field_for_public_pages():
    workspace = _workspace_doc()
    public_links = [link for link in workspace["shortcuts"] if link["type"] == "URL"]
    assert len(public_links) == 3
    assert all(link.get("url") for link in public_links)
    assert workspace["links"] == []


def frappe_session(user: str):
    class Session:
        pass

    session = Session()
    session.user = user
    return session
