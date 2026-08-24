#!/usr/bin/env python3
"""Maskrom first-flash of CameVision Ego: known-good eMMC + Recovery 4 Ego DTB.

USB stays ADB. Loader db once. No userdata wipe. No Aura images.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

UT = r"C:\Users\stefa\Downloads\SocToolKit\bin\windows\upgrade_tool.exe"
ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
KG = Path(r"C:\Users\stefa\Desktop\CameVision Ego\restore\known-good-20260819-camera-adb")
BOOT = Path(
    r"C:\Users\stefa\Desktop\CameVision Ego\restore\recovery-5-20260823-imaging-adb"
    r"\camevision_boot_ego.img"
)
LOADER = KG / "rv1126b_spl_loader_k4a8g.bin"

WRITES = (
    ("0x0", KG / "env.img"),
    ("0x40", KG / "idblock.img"),
    ("0x440", KG / "uboot.img"),
    ("0x2440", BOOT),
    ("0x207C40", KG / "oem_noko.img"),
    ("0x607C40", KG / "rootfs_bootstable.img"),
)


def run(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    print(">", " ".join(args))
    r = subprocess.run(args, capture_output=True, timeout=timeout)
    text = ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace")
    if text.strip():
        print(text, end="" if text.endswith("\n") else "\n")
    return r


def ld() -> str:
    r = run([UT, "ld"], timeout=30)
    return ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace")


def main() -> int:
    if not BOOT.is_file():
        raise SystemExit(f"missing {BOOT}")
    if not LOADER.is_file():
        raise SystemExit(f"missing {LOADER}")
    for _, f in WRITES:
        if not f.is_file():
            raise SystemExit(f"missing {f}")

    info = ld()
    if "Maskrom" not in info and "Loader" not in info and "rockchip" not in info:
        raise SystemExit("no Rockusb device")

    loader_up = ("SerialNo=rockchip" in info) or ("SerialNo=0" in info)
    if "Maskrom" in info and not loader_up:
        print("=== db loader once ===")
        r = run([UT, "db", str(LOADER)], timeout=60)
        if r.returncode != 0:
            raise SystemExit("db failed")
        time.sleep(2)
        print(ld())
    else:
        print("=== skip db ===")

    for lba, path in WRITES:
        print(f"=== wl {lba} {path.name} ({path.stat().st_size} bytes) ===")
        r = run([UT, "wl", lba, str(path)], timeout=600)
        if r.returncode != 0:
            raise SystemExit(f"write failed {path}")

    print("=== rd — RELEASE BOOT ===")
    time.sleep(2)
    run([UT, "rd"], timeout=30)
    print("EGO_FLASH_DONE — waiting for ADB")

    t0 = time.time()
    serial = None
    while time.time() - t0 < 90:
        time.sleep(3)
        r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
        print(f"t={time.time()-t0:.0f}s {r.stdout.strip()}")
        for line in (r.stdout or "").splitlines():
            if "\tdevice" in line:
                serial = line.split()[0]
                break
        if serial:
            break
    if not serial:
        raise SystemExit("board did not enumerate ADB")

    model = subprocess.run(
        [ADB, "-s", serial, "shell", "cat /proc/device-tree/model; echo"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    print("serial", serial)
    print("model", (model.stdout or "").strip())
    if "CameVision Ego" not in (model.stdout or ""):
        raise SystemExit("DTB model is not CameVision Ego")
    print("EGO_UP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
