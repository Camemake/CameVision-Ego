#!/usr/bin/env python3
"""Portable CameVision Ego paths for the repo and the offline installer."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

def _looks_like_root(p: Path) -> bool:
    return (p / "tools" / "ego_stereo.py").is_file() and (
        (p / "docs" / "index.html").is_file() or (p / "restore").is_dir()
    )


def repo_root() -> Path:
    env = os.environ.get("CAMEVISION_EGO_ROOT")
    if env:
        cand = Path(env).expanduser().resolve()
        if not _looks_like_root(cand):
            raise SystemExit(f"CAMEVISION_EGO_ROOT is not a CameVision Ego tree: {cand}")
        return cand
    here = Path(__file__).resolve().parent
    for cand in (here.parent, here):
        if _looks_like_root(cand):
            return cand
    return here.parent


def host_dir() -> Path:
    return repo_root() / "host"


def is_windows() -> bool:
    return os.name == "nt"


def driver_assistant_dir() -> Path | None:
    host = host_dir()
    for cand in (
        host / "DriverAssitant_v5.14" / "DriverAssitant_v5.14",
        host / "DriverAssitant" / "DriverAssitant_v5.14",
        host / "DriverAssistant_v5.14" / "DriverAssistant_v5.14",
        host / "DriverAssitant_v5.14",
    ):
        if (cand / "DriverInstall.exe").is_file():
            return cand
    return None


def udev_rules_file() -> Path:
    return host_dir() / "linux" / "99-camevision-rockusb.rules"


def bundled_python() -> Path | None:
    host = host_dir()
    env = os.environ.get("CAMEVISION_PYTHON")
    if env and Path(env).is_file():
        return Path(env)
    if is_windows():
        return first_file(host / "python" / "python.exe", host / "python" / "pythonw.exe")
    machine = os.uname().machine.lower() if hasattr(os, "uname") else ""
    linux = host / "linux"
    if machine in ("aarch64", "arm64"):
        found = first_file(
            linux / "python-aarch64" / "bin" / "python3",
            linux / "python" / "bin" / "python3",
            host / "python" / "bin" / "python3",
        )
    else:
        found = first_file(
            linux / "python" / "bin" / "python3",
            linux / "python-aarch64" / "bin" / "python3",
            host / "python" / "bin" / "python3",
        )
    return found


def first_file(*cands: Path) -> Path | None:
    for p in cands:
        if p.is_file() and p.stat().st_size > 0:
            return p
    return None


def adb_exe() -> str:
    env = os.environ.get("CAMEVISION_ADB")
    if env and Path(env).is_file():
        return env
    if is_windows():
        found = first_file(
            host_dir() / "adb.exe",
            host_dir() / "adb" / "adb.exe",
        )
    else:
        found = first_file(
            host_dir() / "linux" / "adb",
            host_dir() / "adb",
            host_dir() / "platform-tools" / "adb",
        )
    if found is not None:
        return str(found)
    which = shutil.which("adb")
    if which:
        return which
    return "adb"


def upgrade_tool() -> str:
    env = os.environ.get("CAMEVISION_UPGRADE_TOOL")
    if env and Path(env).is_file():
        return env
    if is_windows():
        found = first_file(
            host_dir() / "upgrade_tool.exe",
            host_dir() / "SocToolKit" / "upgrade_tool.exe",
        )
    else:
        found = first_file(
            host_dir() / "linux" / "upgrade_tool",
            host_dir() / "upgrade_tool",
        )
    if found is not None:
        return str(found)
    which = shutil.which("upgrade_tool")
    if which:
        return which
    return "upgrade_tool"


def userdata_img() -> Path | None:
    root = repo_root()
    return first_file(
        update_current() / "userdata.img",
        root / "restore" / "images" / "userdata.img",
        root / "host" / "userdata.img",
        root / "firmware" / "aura-stock" / "Luckfox_Aura_Buildroot_eMMC_260606" / "userdata.img",
        root / "firmware" / "pack-k4a8g" / "userdata.img",
        root / "firmware" / "afp-unpacked" / "Image" / "userdata.img",
    )


def known_good() -> Path:
    return repo_root() / "restore" / "known-good-20260819-camera-adb"


def release_02() -> Path:
    return repo_root() / "restore" / "release-0.2-20260902"


def update_current() -> Path:
    return repo_root() / "restore" / "updates" / "current"


def boot_ok(raw: bytes) -> bool:
    return (
        raw.count(b"camevision-sc233hgs") >= 2
        and b"efference-sc233hgs" not in raw
        and b"efference" not in raw.lower()
    )


def boot_img() -> Path | None:
    root = repo_root()
    cands = (
        update_current() / "camevision_boot_ego.img",
        release_02() / "camevision_boot_ego.img",
        root / "build" / "camevision_boot_ego.img",
        root / "restore" / "images" / "camevision_boot_ego.img",
    )
    for p in cands:
        if not p.is_file() or p.stat().st_size <= 0:
            continue
        if boot_ok(p.read_bytes()):
            return p
    return None


def docs_dir() -> Path:
    return repo_root() / "docs"
