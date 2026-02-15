#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_VERSION_PATH = os.path.join(ROOT, "app_version.py")
VERSION_INFO_PATH = os.path.join(ROOT, "packaging", "pyinstaller", "version_info.txt")


def _read_git_tag() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", "ignore").strip()
        return out or None
    except Exception:
        return None


def _normalize_tag(tag: str | None) -> str | None:
    if not tag:
        return None
    tag = tag.strip()
    if tag.startswith(("v", "V")):
        tag = tag[1:]
    # Remove build metadata / pre-release suffix
    tag = re.split(r"[-+]", tag, maxsplit=1)[0]
    if not re.match(r"^\d+(\.\d+){0,3}$", tag):
        return None
    return tag


def _read_existing_version() -> str | None:
    if not os.path.exists(APP_VERSION_PATH):
        return None
    try:
        content = open(APP_VERSION_PATH, "r", encoding="utf-8").read()
        m = re.search(r'APP_VERSION\s*=\s*[\'"]([^\'"]+)[\'"]', content)
        return m.group(1) if m else None
    except Exception:
        return None


def _parse_version_tuple(version: str) -> tuple[int, int, int, int]:
    base = re.split(r"[-+]", version, maxsplit=1)[0]
    parts = [p for p in base.split(".") if p.isdigit()]
    nums = [int(p) for p in parts][:4]
    while len(nums) < 4:
        nums.append(0)
    return tuple(nums)  # type: ignore[return-value]


def _write_app_version(version: str) -> None:
    with open(APP_VERSION_PATH, "w", encoding="utf-8") as f:
        f.write(f'APP_VERSION = "{version}"\n')


def _write_version_info(version: str) -> None:
    vtuple = _parse_version_tuple(version)
    content = f"""# UTF-8
#
# Windows version info for PyInstaller
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={vtuple},
    prodvers={vtuple},
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'Timothee Grollier'),
          StringStruct('FileDescription', 'BPM-detector'),
          StringStruct('FileVersion', '{version}'),
          StringStruct('InternalName', 'BPM-detector'),
          StringStruct('LegalCopyright', 'Copyright (c) 2026'),
          StringStruct('OriginalFilename', 'BPM-detector.exe'),
          StringStruct('ProductName', 'BPM-detector'),
          StringStruct('ProductVersion', '{version}'),
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    os.makedirs(os.path.dirname(VERSION_INFO_PATH), exist_ok=True)
    with open(VERSION_INFO_PATH, "w", encoding="utf-8") as f:
        f.write(content)


def main() -> int:
    env_version = os.environ.get("APP_VERSION")
    tag_version = _normalize_tag(_read_git_tag())
    existing = _read_existing_version()

    version = env_version or tag_version or existing or "0.0.0"
    _write_app_version(version)
    _write_version_info(version)
    print(f"Version set to {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
