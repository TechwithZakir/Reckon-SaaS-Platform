#!/usr/bin/env python3
"""Safe app install and update for a Frappe bench, plus a registry doctor.

Why: ``bench get-app <url>`` clones into a folder named after the repository
(``Reckon-SaaS-Platform``) and then renames it to the app name
(``reckon_saas_platform``). If that rename fails, because the app is already
installed or a leftover folder is in the way, the bench keeps a repo-named
folder and ``sites/apps.txt`` can end up listing a name Python cannot import.
Every later ``bench build`` / ``migrate`` then crashes.

This tool (standard library only, runs even when bench cannot boot):

    python apps/reckon_saas_platform/scripts/reckon_bench.py doctor          # report
    python apps/reckon_saas_platform/scripts/reckon_bench.py doctor --apply  # repair
    python apps/reckon_saas_platform/scripts/reckon_bench.py get-app <git-url> [--branch main]
    python apps/reckon_saas_platform/scripts/reckon_bench.py update <app> [<app> ...] [--branch main]

``get-app`` updates an app that is already installed instead of re-cloning it,
repairs the registry before and after running bench, and never leaves a
repo-named entry behind. ``doctor --apply`` keeps a timestamped backup of
``sites/apps.txt`` and moves leftover repo-named folders to ``archived/apps``.
It never touches site databases.
"""

from __future__ import annotations

import argparse
import ast
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

APP_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


# ---------------------------------------------------------------------------
# Inspection


def app_name_of(folder: Path) -> str | None:
    """The ``app_name`` declared in ``<folder>/<package>/hooks.py``, if any."""
    for hooks in sorted(folder.glob("*/hooks.py")):
        try:
            module = ast.parse(hooks.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        for node in module.body:
            if (
                isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "app_name" for t in node.targets)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                return node.value.value
    return None


def remote_url(folder: Path) -> str | None:
    """First git remote URL of an app folder, normalised for comparison."""
    try:
        output = subprocess.run(
            ["git", "-C", str(folder), "remote", "-v"], capture_output=True, text=True, check=False
        ).stdout
    except OSError:
        return None
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            return normalise_url(parts[1])
    return None


def normalise_url(url: str) -> str:
    url = url.strip().rstrip("/")
    url = re.sub(r"\.git$", "", url)
    url = re.sub(r"^git@([^:]+):", r"https://\1/", url)
    url = re.sub(r"^https?://[^@/]+@", "https://", url)  # drop embedded credentials
    return url.lower()


def remote_name(folder: Path) -> str:
    output = subprocess.run(
        ["git", "-C", str(folder), "remote"], capture_output=True, text=True, check=False
    ).stdout.split()
    if "upstream" in output:
        return "upstream"
    return output[0] if output else "origin"


@dataclass
class Diagnosis:
    """What is wrong with the bench app registry, and the corrected version."""

    registered: list[str]
    folders: dict[str, str]  # folder name -> declared app_name
    corrected: list[str] = field(default_factory=list)
    renamed: dict[str, str] = field(default_factory=dict)  # bad entry -> app name
    dropped: dict[str, str] = field(default_factory=dict)  # entry -> reason
    added: list[str] = field(default_factory=list)
    leftover_folders: list[str] = field(default_factory=list)
    misnamed_folders: dict[str, str] = field(default_factory=dict)  # folder -> app name, rename never done

    @property
    def healthy(self) -> bool:
        return not (self.renamed or self.dropped or self.leftover_folders) and self.corrected == self.registered


def bench_python(bench: Path) -> Path | None:
    for candidate in (bench / "env" / "bin" / "python", bench / "env" / "Scripts" / "python.exe"):
        if candidate.is_file():
            return candidate
    return None


def import_checker(bench: Path):
    """``name -> bool`` using the bench's own Python; without an env, assume importable."""
    python = bench_python(bench)
    if python is None:
        return lambda name: True

    def can_import(name: str) -> bool:
        result = subprocess.run(
            [str(python), "-c", f"import importlib; importlib.import_module({name!r})"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    return can_import


def diagnose(bench: Path, can_import=None) -> Diagnosis:
    can_import = can_import or import_checker(bench)
    apps_dir = bench / "apps"
    apps_txt = bench / "sites" / "apps.txt"
    registered = (
        [line.strip() for line in apps_txt.read_text(encoding="utf-8").splitlines() if line.strip()]
        if apps_txt.exists()
        else []
    )
    folders = {
        folder.name: name
        for folder in sorted(apps_dir.iterdir())
        if folder.is_dir() and (name := app_name_of(folder))
    }
    proper = {name for folder, name in folders.items() if folder == name}
    result = Diagnosis(registered=registered, folders=folders)
    result.misnamed_folders = {
        folder: name for folder, name in folders.items() if folder != name and name not in proper
    }

    seen: set[str] = set()
    for entry in registered:
        name = entry
        if entry not in proper:
            declared = folders.get(entry)
            if declared and declared in proper:
                result.renamed[entry] = declared  # repo-named entry for an installed app
                name = declared
            elif entry in result.misnamed_folders:
                result.dropped[entry] = (
                    f"folder apps/{entry} declares app {result.misnamed_folders[entry]!r} but was never renamed"
                )
                continue
            else:
                result.dropped[entry] = "no app folder declares this name"
                continue
        if not APP_NAME.fullmatch(name) or not can_import(name):
            result.dropped[entry] = f"{name!r} cannot be imported by the bench Python"
            continue
        if name not in seen:
            seen.add(name)
            result.corrected.append(name)
    if "frappe" in proper and "frappe" not in seen:
        result.corrected.insert(0, "frappe")
        result.added.append("frappe")

    result.leftover_folders = sorted(
        folder for folder, name in folders.items() if folder != name and name in proper
    )
    return result


# ---------------------------------------------------------------------------
# Repair


def repair(bench: Path, diagnosis: Diagnosis, stamp: str | None = None) -> Path | None:
    """Write the corrected apps.txt and archive leftover folders. Returns the backup dir."""
    if diagnosis.healthy:
        return None
    stamp = stamp or datetime.now().strftime("%Y%m%d%H%M%S")
    backup = bench / "sites" / ".app-registry-backups" / stamp
    backup.mkdir(parents=True, exist_ok=True)
    apps_txt = bench / "sites" / "apps.txt"
    if apps_txt.exists():
        shutil.copy2(apps_txt, backup / "apps.txt")
    apps_txt.write_text("\n".join(diagnosis.corrected) + "\n", encoding="utf-8")

    archive = bench / "archived" / "apps"
    archive.mkdir(parents=True, exist_ok=True)
    for folder in diagnosis.leftover_folders:
        target = archive / f"{folder}-{stamp}"
        shutil.move(str(bench / "apps" / folder), str(target))
    return backup


def report(diagnosis: Diagnosis) -> str:
    lines = []
    if diagnosis.healthy:
        return "App registry is healthy: " + ", ".join(diagnosis.registered)
    for bad, good in diagnosis.renamed.items():
        lines.append(f"  apps.txt lists repo name {bad!r}; the app is {good!r}")
    for bad, reason in diagnosis.dropped.items():
        lines.append(f"  apps.txt lists {bad!r}: {reason}; it will be removed")
    for name in diagnosis.added:
        lines.append(f"  apps.txt is missing {name!r}; it will be added")
    for folder in diagnosis.leftover_folders:
        lines.append(f"  apps/{folder} is a leftover copy of {diagnosis.folders[folder]!r}; it will be archived")
    for folder, name in diagnosis.misnamed_folders.items():
        lines.append(
            f"  apps/{folder} declares {name!r} but was never renamed. To keep it: "
            f"mv apps/{folder} apps/{name} && bench pip install -e apps/{name}, "
            f"then add {name} to sites/apps.txt"
        )
    lines.append("Corrected apps.txt: " + ", ".join(diagnosis.corrected))
    return "Problems found:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Commands


def run(command: list[str], cwd: Path) -> int:
    print("$ " + " ".join(command), flush=True)
    return subprocess.run(command, cwd=str(cwd), check=False).returncode


def cmd_doctor(bench: Path, apply: bool) -> int:
    diagnosis = diagnose(bench)
    print(report(diagnosis))
    if diagnosis.healthy:
        return 0
    if not apply:
        print("\nDry run. Re-run with --apply to repair (apps.txt is backed up first).")
        return 1
    backup = repair(bench, diagnosis)
    print(f"\nRepaired. Backup: {backup}")
    return 0


def installed_folder_for(bench: Path, url: str) -> Path | None:
    """The installed app folder whose git remote is ``url`` (matching repo-named folders too)."""
    wanted = normalise_url(url)
    repo = wanted.rsplit("/", 1)[-1]
    for folder in sorted((bench / "apps").iterdir()):
        if not folder.is_dir() or not app_name_of(folder):
            continue
        if remote_url(folder) == wanted or folder.name.lower() == repo:
            name = app_name_of(folder)
            proper = bench / "apps" / name
            return proper if proper.is_dir() else folder
    return None


def cmd_update(bench: Path, apps: list[str], branch: str | None) -> int:
    status = 0
    for app in apps:
        folder = bench / "apps" / app
        if not folder.is_dir():
            print(f"apps/{app} does not exist; install it with get-app.", file=sys.stderr)
            status = 1
            continue
        remote = remote_name(folder)
        target = branch or subprocess.run(
            ["git", "-C", str(folder), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=False
        ).stdout.strip() or "main"
        status |= run(["git", "-C", str(folder), "pull", "--ff-only", remote, target], bench)
    if status == 0:
        print("\nNext: bench --site <site> migrate && bench build && bench restart")
    return status


def cmd_get_app(bench: Path, url: str, branch: str | None) -> int:
    before = diagnose(bench)
    if not before.healthy:
        print(report(before))
        repair(bench, before)
        print("Registry repaired before installing.\n")

    existing = installed_folder_for(bench, url)
    if existing is not None:
        print(f"{url} is already installed as apps/{existing.name}; updating it instead of re-cloning.")
        status = cmd_update(bench, [existing.name], branch)
    else:
        command = ["bench", "get-app", url] + (["--branch", branch] if branch else [])
        status = run(command, bench)

    after = diagnose(bench)
    if not after.healthy:
        print("\n" + report(after))
        repair(bench, after)
        print("Registry repaired after bench get-app.")
    if status:
        print(
            "\nbench reported an error above. The app registry has been repaired, so "
            "bench build/migrate keep working; fix the reported cause and re-run this command.",
            file=sys.stderr,
        )
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--bench", type=Path, default=Path.cwd(), help="bench directory (default: current directory)")
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="check sites/apps.txt and app folders")
    doctor.add_argument("--apply", action="store_true", help="repair what doctor reports")
    get_app = sub.add_parser("get-app", help="install an app safely, or update it if already installed")
    get_app.add_argument("url")
    get_app.add_argument("--branch")
    update = sub.add_parser("update", help="git pull installed apps")
    update.add_argument("apps", nargs="+")
    update.add_argument("--branch")
    args = parser.parse_args(argv)

    bench = args.bench.resolve()
    if not (bench / "apps").is_dir() or not (bench / "sites").is_dir():
        print(f"{bench} is not a bench directory (needs apps/ and sites/).", file=sys.stderr)
        return 2
    if args.command == "doctor":
        return cmd_doctor(bench, args.apply)
    if args.command == "get-app":
        return cmd_get_app(bench, args.url, args.branch)
    return cmd_update(bench, args.apps, args.branch)


if __name__ == "__main__":
    raise SystemExit(main())
