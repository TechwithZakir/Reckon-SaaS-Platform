"""scripts/reckon_bench.py: safe get-app/update and the apps.txt doctor (no bench needed)."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reckon_bench.py"
spec = importlib.util.spec_from_file_location("reckon_bench", SCRIPT)
rb = importlib.util.module_from_spec(spec)
sys.modules["reckon_bench"] = rb  # dataclasses on Python < 3.12 look the module up here
spec.loader.exec_module(rb)

ALWAYS = lambda name: True  # noqa: E731 - import checker stub


class Bench:
    """A throwaway bench directory."""

    def __init__(self, root: Path):
        self.root = root
        (root / "apps").mkdir()
        (root / "sites").mkdir()

    def app(self, folder: str, app_name: str | None = None) -> Path:
        package = self.root / "apps" / folder / (app_name or folder)
        package.mkdir(parents=True)
        (package / "hooks.py").write_text(f'app_name = "{app_name or folder}"\n', encoding="utf-8")
        return self.root / "apps" / folder

    def registry(self, *names: str) -> None:
        (self.root / "sites" / "apps.txt").write_text("\n".join(names) + "\n", encoding="utf-8")

    def registered(self) -> list[str]:
        return (self.root / "sites" / "apps.txt").read_text(encoding="utf-8").split()


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.bench = Bench(Path(self._tmp.name))
        for name in ("frappe", "erpnext", "reckon_saas_platform", "reckon_accounts"):
            self.bench.app(name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_healthy_registry_is_left_alone(self):
        self.bench.registry("frappe", "erpnext", "reckon_saas_platform")
        diagnosis = rb.diagnose(self.bench.root, ALWAYS)
        self.assertTrue(diagnosis.healthy)
        self.assertIsNone(rb.repair(self.bench.root, diagnosis))

    def test_the_failure_seen_on_the_server_is_repaired(self):
        # apps.txt from the broken bench, plus the leftover folder of a failed re-clone.
        self.bench.app("Reckon-SaaS-Platform", "reckon_saas_platform")
        self.bench.registry(
            "frappe", "erpnext", "Reckon-SaaS-Platform", "Reckon-Accounts", "Reckon-Constructions", "reckon_accounts"
        )
        diagnosis = rb.diagnose(self.bench.root, ALWAYS)
        self.assertFalse(diagnosis.healthy)
        self.assertEqual(diagnosis.renamed, {"Reckon-SaaS-Platform": "reckon_saas_platform"})
        self.assertEqual(set(diagnosis.dropped), {"Reckon-Accounts", "Reckon-Constructions"})
        self.assertEqual(diagnosis.leftover_folders, ["Reckon-SaaS-Platform"])

        backup = rb.repair(self.bench.root, diagnosis, stamp="20261018")
        self.assertEqual(self.bench.registered(), ["frappe", "erpnext", "reckon_saas_platform", "reckon_accounts"])
        self.assertFalse((self.bench.root / "apps" / "Reckon-SaaS-Platform").exists())
        self.assertTrue((self.bench.root / "archived" / "apps" / "Reckon-SaaS-Platform-20261018").is_dir())
        self.assertIn("Reckon-Constructions", (backup / "apps.txt").read_text(encoding="utf-8"))
        self.assertTrue(rb.diagnose(self.bench.root, ALWAYS).healthy)

    def test_names_python_cannot_import_are_removed(self):
        self.bench.registry("frappe", "erpnext", "reckon_accounts")
        diagnosis = rb.diagnose(self.bench.root, lambda name: name != "reckon_accounts")
        self.assertIn("cannot be imported", diagnosis.dropped["reckon_accounts"])
        self.assertEqual(diagnosis.corrected, ["frappe", "erpnext"])

    def test_duplicates_collapse_and_frappe_is_restored(self):
        self.bench.app("Reckon-Accounts", "reckon_accounts").rename(self.bench.root / "apps" / "Reckon-Accounts")
        self.bench.registry("erpnext", "reckon_accounts", "Reckon-Accounts")
        diagnosis = rb.diagnose(self.bench.root, ALWAYS)
        self.assertEqual(diagnosis.corrected, ["frappe", "erpnext", "reckon_accounts"])
        self.assertEqual(diagnosis.added, ["frappe"])

    def test_never_renamed_folder_is_explained_not_guessed(self):
        self.bench.app("Reckon-Accounts-SaaS", "reckon_accounts_saas")
        self.bench.registry("frappe", "Reckon-Accounts-SaaS")
        diagnosis = rb.diagnose(self.bench.root, ALWAYS)
        self.assertIn("never renamed", diagnosis.dropped["Reckon-Accounts-SaaS"])
        self.assertEqual(diagnosis.misnamed_folders, {"Reckon-Accounts-SaaS": "reckon_accounts_saas"})
        self.assertIn("mv apps/Reckon-Accounts-SaaS apps/reckon_accounts_saas", rb.report(diagnosis))
        rb.repair(self.bench.root, diagnosis, stamp="x")
        # The folder is kept: only its app owner can decide to rename and reinstall it.
        self.assertTrue((self.bench.root / "apps" / "Reckon-Accounts-SaaS").is_dir())

    def test_doctor_command_dry_run_then_apply(self):
        self.bench.registry("frappe", "Reckon-Constructions")
        with patch.object(rb, "import_checker", return_value=ALWAYS):
            self.assertEqual(rb.cmd_doctor(self.bench.root, apply=False), 1)
            self.assertEqual(self.bench.registered(), ["frappe", "Reckon-Constructions"])
            self.assertEqual(rb.cmd_doctor(self.bench.root, apply=True), 0)
            self.assertEqual(self.bench.registered(), ["frappe"])


class GetAppTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.bench = Bench(Path(self._tmp.name))
        self.bench.app("frappe")
        self.bench.app("reckon_saas_platform")
        self.bench.registry("frappe", "reckon_saas_platform")

    def tearDown(self):
        self._tmp.cleanup()

    def test_installed_app_is_updated_not_recloned(self):
        url = "https://github.com/TechwithZakir/Reckon-SaaS-Platform"
        remotes = {
            "frappe": "https://github.com/frappe/frappe",
            "reckon_saas_platform": url + ".git",
        }
        with patch.object(rb, "import_checker", return_value=ALWAYS), patch.object(
            rb, "remote_url", side_effect=lambda folder: rb.normalise_url(remotes[folder.name])
        ), patch.object(rb, "cmd_update", return_value=0) as update, patch.object(rb, "run") as run:
            self.assertEqual(rb.cmd_get_app(self.bench.root, url, None), 0)
        update.assert_called_once_with(self.bench.root, ["reckon_saas_platform"], None)
        run.assert_not_called()

    def test_new_app_goes_through_bench_and_registry_is_repaired_after(self):
        def fake_bench(command, cwd):
            # Simulate bench failing half way: repo-named folder and entry left behind.
            self.bench.app("Reckon-Accounts-SaaS", "reckon_accounts_saas")
            (self.bench.root / "sites" / "apps.txt").write_text("frappe\nreckon_saas_platform\nReckon-Accounts-SaaS\n")
            return 1

        with patch.object(rb, "import_checker", return_value=ALWAYS), patch.object(
            rb, "remote_url", return_value=None
        ), patch.object(rb, "run", side_effect=fake_bench) as run:
            status = rb.cmd_get_app(self.bench.root, "https://github.com/TechwithZakir/Reckon-Accounts-SaaS", "main")
        self.assertEqual(status, 1)
        self.assertEqual(run.call_args.args[0], [
            "bench", "get-app", "https://github.com/TechwithZakir/Reckon-Accounts-SaaS", "--branch", "main"])
        self.assertEqual(self.bench.registered(), ["frappe", "reckon_saas_platform"])

    def test_broken_registry_is_fixed_before_bench_runs(self):
        self.bench.registry("frappe", "reckon_saas_platform", "Reckon-Constructions")
        seen = []
        with patch.object(rb, "import_checker", return_value=ALWAYS), patch.object(
            rb, "remote_url", return_value=None
        ), patch.object(rb, "run", side_effect=lambda command, cwd: seen.append(self.bench.registered()) or 0):
            rb.cmd_get_app(self.bench.root, "https://github.com/TechwithZakir/Reckon-Accounts", None)
        self.assertEqual(seen, [["frappe", "reckon_saas_platform"]])


class HelperTests(unittest.TestCase):
    def test_remote_urls_compare_equal_across_forms(self):
        forms = (
            "https://github.com/TechwithZakir/Reckon-SaaS-Platform",
            "https://github.com/TechwithZakir/Reckon-SaaS-Platform.git",
            "git@github.com:TechwithZakir/Reckon-SaaS-Platform.git",
            "https://token123@github.com/TechwithZakir/reckon-saas-platform/",
        )
        self.assertEqual(len({rb.normalise_url(form) for form in forms}), 1)

    def test_main_refuses_a_non_bench_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(rb.main(["--bench", tmp, "doctor"]), 2)


if __name__ == "__main__":
    unittest.main()
