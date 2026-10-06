#!/usr/bin/env python3
"""CameVision Ego Maskrom package install.

Writes loader, env, idblock, U-Boot, boot, userdata, oem, rootfs, then
the overlay. Same sequence on an empty board and on a flashed board.

    python tools/cv_ego_flash.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_ego_paths import boot_img, repo_root  # noqa: E402

ROOT = repo_root()
sys.path.insert(0, str(ROOT / "tools"))
import cv_ego_wifi_full_flash  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="CameVision Ego Maskrom package install")
    p.add_argument(
        "--prebuilt",
        action="store_true",
        help="write existing boot/overlay images (offline installer default)",
    )
    p.add_argument(
        "--rebuild",
        action="store_true",
        help="rebuild the Ego boot FIT before write",
    )
    p.add_argument(
        "--package",
        default="camevision-ego",
        help="package id from the offline tool",
    )
    args = p.parse_args()
    prebuilt = args.prebuilt or (not args.rebuild and boot_img() is not None)
    print(f"=== install {args.package} ===", flush=True)
    if not prebuilt:
        import cv_ego_wifi_fix_dtb  # noqa: E402
        import cv_pack_release02  # noqa: E402

        print("=== rebuild Ego Wi-Fi + RTC boot FIT ===", flush=True)
        rc = cv_ego_wifi_fix_dtb.main()
        if rc:
            return rc
        print("=== pack restore/release-0.2-20260902 ===", flush=True)
        rc = cv_pack_release02.main()
        if rc:
            return rc
    elif boot_img() is None:
        raise SystemExit("missing camevision_boot_ego.img — run with --rebuild or pack the offline kit")
    else:
        print("=== using prebuilt boot FIT ===", flush=True)
    print("=== Maskrom write + overlay ===", flush=True)
    return cv_ego_wifi_full_flash.main()


if __name__ == "__main__":
    raise SystemExit(main())
