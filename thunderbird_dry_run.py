#!/usr/bin/env python3
"""
Safe dry-run inspector for local Mozilla Thunderbird profiles on Windows.

This script only reads Thunderbird configuration files and lists accounts and
local mail folders. It does not modify, delete, move, or send anything.
"""

from __future__ import annotations

import argparse
import configparser
import json
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

DRY_RUN = True


@dataclass
class ProfileInfo:
    name: str
    path: str
    is_default: bool
    exists: bool


@dataclass
class AccountInfo:
    account_key: str
    identity_key: str | None
    email: str | None
    server_key: str | None
    server_name: str | None
    hostname: str | None
    server_type: str | None


@dataclass
class FolderInfo:
    area: str
    relative_path: str
    size_bytes: int
    size_mb: float
    likely_mbox: bool


def thunderbird_base() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not set. This script is intended for Windows.")
    return Path(appdata) / "Thunderbird"


def read_profiles(base: Path) -> list[ProfileInfo]:
    profiles_ini = base / "profiles.ini"
    if not profiles_ini.exists():
        return []

    config = configparser.RawConfigParser()
    config.read(profiles_ini, encoding="utf-8")

    profiles: list[ProfileInfo] = []
    for section in config.sections():
        if not section.lower().startswith("profile"):
            continue
        name = config.get(section, "Name", fallback=section)
        raw_path = config.get(section, "Path", fallback="")
        is_relative = config.getint(section, "IsRelative", fallback=1) == 1
        is_default = config.getint(section, "Default", fallback=0) == 1
        profile_path = (base / raw_path) if is_relative else Path(raw_path)
        profiles.append(
            ProfileInfo(
                name=name,
                path=str(profile_path),
                is_default=is_default,
                exists=profile_path.exists(),
            )
        )
    return profiles


def select_profile(base: Path, explicit_profile: str | None) -> Path:
    if explicit_profile:
        profile = Path(explicit_profile).expanduser()
        if not profile.exists():
            raise FileNotFoundError(f"Profile path does not exist: {profile}")
        return profile

    profiles = read_profiles(base)
    existing = [Path(p.path) for p in profiles if p.exists]
    default_profiles = [Path(p.path) for p in profiles if p.is_default and p.exists]

    if default_profiles:
        return default_profiles[0]
    if existing:
        return existing[0]

    profiles_dir = base / "Profiles"
    if profiles_dir.exists():
        candidates = [p for p in profiles_dir.iterdir() if p.is_dir()]
        if candidates:
            return candidates[0]

    raise FileNotFoundError("No Thunderbird profile found.")


def parse_prefs(profile: Path) -> dict[str, str]:
    prefs = profile / "prefs.js"
    if not prefs.exists():
        return {}

    pattern = re.compile(r'^user_pref\("(?P<key>.+?)",\s*(?P<value>.+?)\);$')
    values: dict[str, str] = {}

    with prefs.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = pattern.match(line.strip())
            if not match:
                continue
            key = match.group("key")
            raw_value = match.group("value").strip()
            if raw_value.startswith('"') and raw_value.endswith('"'):
                value = raw_value[1:-1].encode("utf-8", errors="ignore").decode("unicode_escape", errors="ignore")
            else:
                value = raw_value
            values[key] = value
    return values


def account_infos(prefs: dict[str, str]) -> list[AccountInfo]:
    account_list = prefs.get("mail.accountmanager.accounts", "")
    account_keys = [item.strip() for item in account_list.split(",") if item.strip()]

    if not account_keys:
        account_keys = sorted(
            {key.split(".")[2] for key in prefs if key.startswith("mail.account.") and len(key.split(".")) > 2}
        )

    accounts: list[AccountInfo] = []
    for account_key in account_keys:
        identity_keys = prefs.get(f"mail.account.{account_key}.identities", "")
        identity_key = identity_keys.split(",")[0].strip() if identity_keys else None
        server_key = prefs.get(f"mail.account.{account_key}.server")

        email = prefs.get(f"mail.identity.{identity_key}.useremail") if identity_key else None
        server_name = prefs.get(f"mail.server.{server_key}.name") if server_key else None
        hostname = prefs.get(f"mail.server.{server_key}.hostname") if server_key else None
        server_type = prefs.get(f"mail.server.{server_key}.type") if server_key else None

        accounts.append(
            AccountInfo(
                account_key=account_key,
                identity_key=identity_key,
                email=email,
                server_key=server_key,
                server_name=server_name,
                hostname=hostname,
                server_type=server_type,
            )
        )
    return accounts


def is_likely_mbox(path: Path) -> bool:
    if path.suffix.lower() == ".msf":
        return False
    if path.is_dir():
        return False
    if path.name.endswith(".dat") or path.name.endswith(".json") or path.name.endswith(".sqlite"):
        return False
    return True


def folder_infos(profile: Path) -> list[FolderInfo]:
    folders: list[FolderInfo] = []
    for area in ("Mail", "ImapMail"):
        root = profile / area
        if not root.exists():
            continue
        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue
            try:
                size = file_path.stat().st_size
            except OSError:
                continue
            relative = file_path.relative_to(profile)
            folders.append(
                FolderInfo(
                    area=area,
                    relative_path=str(relative),
                    size_bytes=size,
                    size_mb=round(size / (1024 * 1024), 2),
                    likely_mbox=is_likely_mbox(file_path),
                )
            )
    return sorted(folders, key=lambda item: (item.area, item.relative_path.lower()))


def build_report(profile_arg: str | None) -> dict[str, Any]:
    base = thunderbird_base()
    profile = select_profile(base, profile_arg)
    prefs = parse_prefs(profile)

    return {
        "dry_run": DRY_RUN,
        "thunderbird_base": str(base),
        "selected_profile": str(profile),
        "profiles": [asdict(profile_info) for profile_info in read_profiles(base)],
        "accounts": [asdict(account) for account in account_infos(prefs)],
        "folders": [asdict(folder) for folder in folder_infos(profile)],
    }


def print_text_report(report: dict[str, Any]) -> None:
    print(f"DRY RUN: {'enabled' if report['dry_run'] else 'disabled'}")
    print(f"Thunderbird base: {report['thunderbird_base']}")
    print(f"Selected profile: {report['selected_profile']}")
    print()

    print("Profiles:")
    if report["profiles"]:
        for profile in report["profiles"]:
            marker = "default" if profile["is_default"] else "profile"
            status = "exists" if profile["exists"] else "missing"
            print(f"- {profile['name']} ({marker}, {status}): {profile['path']}")
    else:
        print("- No profiles listed in profiles.ini")
    print()

    print("Accounts:")
    if report["accounts"]:
        for account in report["accounts"]:
            email = account["email"] or "no email identity"
            hostname = account["hostname"] or "no hostname"
            server_type = account["server_type"] or "unknown type"
            print(f"- {account['account_key']}: {email}, {hostname}, {server_type}")
    else:
        print("- No accounts found in prefs.js")
    print()

    print("Folders:")
    if report["folders"]:
        for folder in report["folders"]:
            kind = "mbox" if folder["likely_mbox"] else "index/metadata"
            print(f"- {folder['relative_path']}  {folder['size_mb']} MB  {kind}")
    else:
        print("- No local Mail or ImapMail files found")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safely inspect local Mozilla Thunderbird accounts and folders in dry-run mode."
    )
    parser.add_argument("--profile", help="Optional explicit Thunderbird profile path.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text output.")
    args = parser.parse_args()

    report = build_report(args.profile)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_text_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
