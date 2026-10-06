#!/usr/bin/env python3
"""Selectable CameVision Ego flash packages.

Every package writes loader, env, idblock, U-Boot, boot, userdata, oem,
rootfs, then the overlay. Same sequence on an empty board and on a board
that already has images.
"""
from __future__ import annotations

from pathlib import Path
from shutil import which

from cv_ego_paths import (
    adb_exe,
    boot_img,
    partition_img,
    repo_root,
    upgrade_tool,
    userdata_img,
)

PACKAGE_PARTS = (
    "loader",
    "env",
    "idblock",
    "uboot",
    "boot",
    "userdata",
    "oem",
    "rootfs",
    "overlay",
)


def _files() -> dict[str, Path | None]:
    root = repo_root()
    overlay = root / "tools" / "ego_stereo.py"
    return {
        "loader": partition_img("loader"),
        "env": partition_img("env"),
        "idblock": partition_img("idblock"),
        "uboot": partition_img("uboot"),
        "boot": boot_img(),
        "userdata": userdata_img(),
        "oem": partition_img("oem"),
        "rootfs": partition_img("rootfs"),
        "overlay": overlay if overlay.is_file() else None,
    }


def package_ready() -> bool:
    files = _files()
    ut = upgrade_tool()
    ut_ok = Path(ut).is_file() or which(ut) is not None
    return ut_ok and all(p is not None and Path(p).is_file() for p in files.values())


def packages() -> list[dict]:
    files = _files()
    missing = [name for name, path in files.items() if path is None or not Path(path).is_file()]
    ready = package_ready()
    return [
        {
            "id": "camevision-ego",
            "name": "CameVision Ego",
            "parts": list(PACKAGE_PARTS),
            "ready": ready,
            "missing": missing,
        }
    ]


def page_ready() -> bool:
    adb = adb_exe()
    overlay = _files()["overlay"]
    return overlay is not None and overlay.is_file() and (Path(adb).is_file() or adb == "adb")
