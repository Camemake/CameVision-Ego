#!/usr/bin/env python3
"""Assemble recovery-5: proven dual-cam ISP + ADB Ego image."""
from __future__ import annotations

import hashlib
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego")
REC5 = ROOT / "restore" / "recovery-5-20260823-imaging-adb"
REC3 = ROOT / "restore" / "recovery-3-20260822-uvc-wifi-rkaiq"
REC4 = ROOT / "restore" / "recovery-4-20260822-ego-dtb"
BUILD = ROOT / "build"
DT = ROOT / "device-tree"
BOOT = BUILD / "boot_imaging_good.img"
if not BOOT.is_file():
    BOOT = BUILD / "boot_before_ego.img"

sys.path.insert(0, str(ROOT / "tools"))
from dtb_decompile import Fdt, build  # noqa: E402
from patch_boot_usb import find  # noqa: E402


def copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  {src.name} -> {dst.relative_to(REC5)}")


def extract_dtb(boot: Path, dst: Path) -> bytes:
    data = boot.read_bytes()
    fit = build(Fdt(data))
    img = find(fit, "/images/fdt")
    pos = struct.unpack(">I", img.get("data-position"))[0]
    size = struct.unpack(">I", img.get("data-size"))[0]
    blob = data[pos : pos + size]
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(blob)
    print(f"  extracted fdt {size} bytes -> {dst.relative_to(REC5)}")
    return blob


def main() -> int:
    if not BOOT.is_file():
        raise SystemExit(f"missing {BOOT}")
    keep = {}
    if REC5.exists():
        for name in ("RECOVERY.md", "flash-boot-ego.ps1"):
            p = REC5 / name
            if p.is_file():
                keep[name] = p.read_bytes()
        shutil.rmtree(REC5)
    REC5.mkdir(parents=True)
    for name, data in keep.items():
        (REC5 / name).write_bytes(data)
        print(f"  kept {name}")

    copy(BOOT, REC5 / "camevision_boot_ego.img")
    extract_dtb(BOOT, REC5 / "device-tree" / "rv1126b-camevision-ego.dtb")
    copy(DT / "rv1126b-camevision-ego.dts", REC5 / "device-tree" / "rv1126b-camevision-ego.dts")
    copy(REC4 / "overlay" / "S50usbdevice.adb", REC5 / "overlay" / "S50usbdevice.adb")
    copy(ROOT / "tools" / "ego_mjpeg.py", REC5 / "overlay" / "ego_mjpeg.py")
    copy(ROOT / "tools" / "cv_ego_start_live.py", REC5 / "overlay" / "cv_ego_start_live.py")
    copy(
        BUILD / "live" / "sc233hgs_efference-sc233hgs_backlight.json",
        REC5 / "overlay" / "iqfiles" / "sc233hgs_efference-sc233hgs_default.json",
    )
    copy(REC3 / "overlay" / "camevision-aiq.sh", REC5 / "overlay" / "camevision-aiq.sh")

    boot_sha = hashlib.sha256((REC5 / "camevision_boot_ego.img").read_bytes()).hexdigest()
    status = (
        "model: CameVision Ego\n"
        "kernel: 6.1.141-rt52 #24 SMP PREEMPT_RT\n"
        "adb: 4857b9cbd0b99e0b  2207:0006\n"
        "usb: CameVision Ego (ADB, high-speed peripheral)\n"
        "cam0: i2c 3-0030 chip id 0xcb61  CSI RX0 / dphy0 / rkisp-vir0 /dev/video24\n"
        "cam1: i2c-gpio 6-0030 chip id 0xcb61  CSI RX1 / dphy3 / rkisp-vir2 /dev/video32\n"
        "i2c4 hardware disabled (SCL/SDA swapped on PCB)\n"
        "preview: 1920x1200 NV12 ISP, hflip+vflip, http://127.0.0.1:8765/\n"
        f"boot.img sha256: {boot_sha}\n"
    )
    (REC5 / "from-device" / "logs").mkdir(parents=True)
    (REC5 / "from-device" / "logs" / "live-status.txt").write_text(status, encoding="utf-8")

    sha = hashlib.sha256((REC5 / "camevision_boot_ego.img").read_bytes()).hexdigest()
    (REC5 / "SHA256SUMS.txt").write_text("", encoding="utf-8")  # filled below

    lines = []
    for p in sorted(REC5.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS.txt":
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            rel = p.relative_to(REC5).as_posix()
            lines.append(f"{digest}  {rel}")
    (REC5 / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"boot sha256 {sha}")
    print(f"wrote {REC5} ({len(lines)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
