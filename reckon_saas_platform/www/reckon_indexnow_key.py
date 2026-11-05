import frappe

from reckon_saas_platform import marketing, seo


def get_context(context):
    # Serves the IndexNow key file at /<key>.txt, and only for the real key.
    context.no_cache = 1
    requested = (marketing.requested_path_stem() or "").lower()
    key = str(frappe.db.get_single_value(seo.SETTINGS, "indexnow_key") or "")
    if not key or requested != key:
        raise frappe.DoesNotExistError
    context.body = key
