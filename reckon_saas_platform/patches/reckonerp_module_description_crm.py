"""Refresh the ReckonERP suite's stored description again: Reckon CRM is included, assets and projects on request."""

from reckon_saas_platform.patches.reckonerp_module_description import execute as refresh


def execute():
    refresh()
