"""Unit tests for the pure Desk path rules of the module desk guard."""

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reckon_saas_platform"))

from desk_paths import classify, is_allowed, slugify  # noqa: E402

DOCTYPES = ["Employee", "Leave Application"]
WORKSPACES = ["Reckon HRMS"]


class DeskPathTests(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Leave Application"), "leave-application")

    def test_classify_desk_routes(self):
        self.assertEqual(classify("/app/employee/EMP-0001"), ("desk", "employee"))
        self.assertEqual(classify("/app/leave-application?x=1"), ("desk", "leave-application"))
        self.assertEqual(classify("/app"), ("desk", ""))

    def test_classify_resource_and_other(self):
        self.assertEqual(classify("/api/resource/Leave%20Application/LA-1"), ("resource", "Leave Application"))
        self.assertEqual(classify("/api/method/ping"), ("other", None))
        self.assertEqual(classify("/assets/x.js"), ("other", None))

    def test_allowed_desk_doctype_and_workspace(self):
        self.assertTrue(is_allowed("desk", "employee", DOCTYPES, WORKSPACES))
        self.assertTrue(is_allowed("desk", "reckon-hrms", DOCTYPES, WORKSPACES))
        self.assertTrue(is_allowed("desk", "home", DOCTYPES, WORKSPACES))

    def test_blocked_desk_doctype(self):
        self.assertFalse(is_allowed("desk", "sales-invoice", DOCTYPES, WORKSPACES))
        self.assertFalse(is_allowed("desk", "accounts-home", DOCTYPES, WORKSPACES))

    def test_resource_api(self):
        self.assertTrue(is_allowed("resource", "Employee", DOCTYPES, WORKSPACES))
        self.assertFalse(is_allowed("resource", "Sales Invoice", DOCTYPES, WORKSPACES))

    def test_other_requests_never_blocked(self):
        self.assertTrue(is_allowed("other", None, [], []))


if __name__ == "__main__":
    unittest.main()
