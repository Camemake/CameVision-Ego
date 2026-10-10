#!/usr/bin/env python3
"""Selectable CameVision Ego flash packages.

Each package writes loader, env, idblock, U-Boot, boot, userdata, oem,
rootfs, then that model's overlay. Same Maskrom sequence on an empty
board and on a board that already has images.

SC233HGS and AM / MIRA220 stay separate kits. The offline tool lists both.
"""
from __future__ import annotations

from pathlib import Path
from shutil import which

from cv_ego_paths import (
    adb_exe,
    boot_img,
    partition_img,
    upgrade_tool,
    userdata_img,
)
from cv_ego_paths_am import am_partition, boot_img_am, release_am

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

PKG_SC233HGS = "camevision-ego"
PKG_AM = "camevision-ego-am"


def _ut_ok() -> bool:
    ut = upgrade_tool()
    return Path(ut).is_file() or which(ut) is not None


def _ready(files: dict[str, Path | None]) -> tuple[bool, list[str]]:
    missing = [name for name, path in files.items() if path is None or not Path(path).is_file()]
    if not _ut_ok():
        missing.append("upgrade_tool")
    return (not missing, missing)


def _files_sc233hgs() -> dict[str, Path | None]:
    overlay = Path(__file__).resolve().parent / "ego_stereo.py"
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


def _files_am() -> dict[str, Path | None]:
    ov = release_am() / "overlay" / "ego_stereo.py"
    return {
        "loader": am_partition("loader"),
        "env": am_partition("env"),
        "idblock": am_partition("idblock"),
        "uboot": am_partition("uboot"),
        "boot": boot_img_am(),
        "userdata": am_partition("userdata"),
        "oem": am_partition("oem"),
        "rootfs": am_partition("rootfs"),
        "overlay": ov if ov.is_file() else None,
    }


def _entry(pkg_id: str, name: str, sensor: str, board: str, version: str, files: dict[str, Path | None]) -> dict:
    ready, missing = _ready(files)
    return {
        "id": pkg_id,
        "name": name,
        "sensor": sensor,
        "board": board,
        "version": version,
        "parts": list(PACKAGE_PARTS),
        "ready": ready,
        "missing": missing,
    }


def package_ready() -> bool:
    return any(p["ready"] for p in packages())


def packages() -> list[dict]:
    return [
        _entry(
            PKG_SC233HGS,
            "CameVision Ego · SC233HGS",
            "SC233HGS",
            "V1.I1",
            "0.2",
            _files_sc233hgs(),
        ),
        _entry(
            PKG_AM,
            "CameVision Ego AM · MIRA220",
            "MIRA220",
            "AM V0.3",
            "2.0",
            _files_am(),
        ),
    ]


def package_by_id(pkg_id: str) -> dict:
    aliases = {
        "camevision-ego": PKG_SC233HGS,
        "sc233hgs": PKG_SC233HGS,
        "v02": PKG_SC233HGS,
        "camevision-ego-am": PKG_AM,
        "mira220": PKG_AM,
        "am": PKG_AM,
    }
    want = aliases.get((pkg_id or "").strip().lower(), pkg_id)
    for p in packages():
        if p["id"] == want:
            return p
    raise SystemExit(f"unknown package {pkg_id}")


def page_ready() -> bool:
    adb = adb_exe()
    overlay = _files_sc233hgs()["overlay"] or _files_am()["overlay"]
    return overlay is not None and overlay.is_file() and (Path(adb).is_file() or adb == "adb")
