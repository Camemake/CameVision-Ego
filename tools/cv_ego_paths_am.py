#!/usr/bin/env python3
"""Paths for the CameVision Ego AM / MIRA220 kit.

Never resolve the SC233HGS V0.2 boot or overlay.
"""
from __future__ import annotations

from pathlib import Path

from cv_ego_paths import first_file, repo_root

AM_RELEASE = "release-2.0-am-mira220-20261009"
BOOT_NAME = "camevision_boot_ego_am.img"
MODULE = "camevision-mira220"


def release_am() -> Path:
    return repo_root() / "restore" / AM_RELEASE


def boot_ok_am(raw: bytes) -> bool:
    if raw.count(MODULE.encode("ascii")) < 2:
        return False
    if b"camevision-sc233hgs" in raw:
        return False
    if b"vcc3v3_sd" not in raw:
        return False
    return True


def boot_img_am() -> Path | None:
    p = release_am() / BOOT_NAME
    if p.is_file() and p.stat().st_size > 0 and boot_ok_am(p.read_bytes()):
        return p
    return None


def am_partition(name: str) -> Path | None:
    names = {
        "loader": "rv1126b_spl_loader_k4a8g.bin",
        "env": "env.img",
        "idblock": "idblock.img",
        "uboot": "uboot.img",
        "oem": "oem_noko.img",
        "rootfs": "rootfs_bootstable.img",
        "userdata": "userdata.img",
        "boot": BOOT_NAME,
    }
    fname = names.get(name, name)
    return first_file(release_am() / fname)
