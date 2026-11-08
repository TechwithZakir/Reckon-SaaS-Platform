import frappe

from reckon_saas_platform import invoices, marketing


def get_context(context):
    # The link key is the only credential: nothing else on the page is shared across invoices.
    context.no_cache = 1
    invoice = invoices.get_invoice_by_key(marketing.requested("key"))
    if not invoice:
        raise frappe.DoesNotExistError
    context.update(invoices.invoice_context(invoice))
    context.title = f"Invoice {invoice.name}"
