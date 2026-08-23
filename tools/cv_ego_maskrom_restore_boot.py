#!/usr/bin/env python3
"""Maskrom: loader once, restore the last working boot.img, rd. USB stays ADB."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

UT = r"C:\Users\stefa\Downloads\SocToolKit\bin\windows\upgrade_tool.exe"
ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
KG = Path(r"C:\Users\stefa\Desktop\CameVision Ego\restore\known-good-20260819-camera-adb")
LOADER = KG / "rv1126b_spl_loader_k4a8g.bin"
IDBLOCK = KG / "idblock.img"
UBOOT = KG / "uboot.img"
BOOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\boot_before_ego.img")
REC4 = Path(
    r"C:\Users\stefa\Desktop\CameVision Ego"
    r"\restore\recovery-4-20260822-ego-dtb\camevision_boot_ego.img"
)


def run(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    print(">", " ".join(args), flush=True)
    r = subprocess.run(args, capture_output=True, timeout=timeout)
    text = ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace")
    if text.strip():
        print(text, end="" if text.endswith("\n") else "\n", flush=True)
    return r


def ld() -> str:
    r = run([UT, "ld"], timeout=30)
    return ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace")


def main() -> int:
    for p in (LOADER, IDBLOCK, UBOOT):
        if not p.is_file():
            raise SystemExit(f"missing {p}")
    boot = BOOT if BOOT.is_file() else REC4
    if not boot.is_file():
        raise SystemExit("missing boot image")
    print(f"boot image {boot} ({boot.stat().st_size} bytes)", flush=True)

    info = ld()
    if "Maskrom" not in info:
        raise SystemExit("not in Maskrom")

    loaded = "SerialNo=rockchip" in info or "SerialNo=0" in info
    if loaded:
        print("=== skip db (loader already up) ===", flush=True)
    else:
        print("=== db loader once ===", flush=True)
        r = run([UT, "db", str(LOADER)], timeout=60)
        if r.returncode != 0:
            raise SystemExit("db failed")
        time.sleep(2)
        info = ld()
        print(info, flush=True)
        if "SerialNo=rockchip" not in info and "SerialNo=0" not in info:
            raise SystemExit("loader did not stay up")

    writes = (
        ("0x40", IDBLOCK),
        ("0x440", UBOOT),
        ("0x2440", boot),
    )
    for lba, path in writes:
        print(f"=== wl {lba} {path.name} ({path.stat().st_size} bytes) ===", flush=True)
        r = run([UT, "wl", lba, str(path)], timeout=180)
        if r.returncode != 0:
            raise SystemExit(f"write failed {path.name}")

    print("=== rd — fingers off BOOT ===", flush=True)
    time.sleep(3)
    run([UT, "rd"], timeout=30)

    t0 = time.time()
    serial = None
    while time.time() - t0 < 90:
        time.sleep(3)
        listing = subprocess.run([ADB, "devices"], capture_output=True, text=True).stdout
        print(f"t={time.time()-t0:.0f}s {listing.strip()}", flush=True)
        for line in listing.splitlines():
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
    ).stdout
    print("serial", serial, flush=True)
    print("model", model.strip(), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
