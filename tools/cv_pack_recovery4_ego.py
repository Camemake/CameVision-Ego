#!/usr/bin/env python3
"""Assemble recovery-4: first Ego DTB boot image (ADB USB)."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

ROOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego")
REC3 = ROOT / "restore" / "recovery-3-20260822-uvc-wifi-rkaiq"
REC4 = ROOT / "restore" / "recovery-4-20260822-ego-dtb"
BUILD = ROOT / "build"
DT = ROOT / "device-tree"


def copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  {src.name} -> {dst.relative_to(REC4)}")


def main() -> int:
    if REC4.exists():
        shutil.rmtree(REC4)
    REC4.mkdir(parents=True)
    (REC4 / "from-device" / "logs").mkdir(parents=True)
    (REC4 / "overlay").mkdir()
    (REC4 / "device-tree").mkdir()

    copy(BUILD / "camevision_boot_ego.img", REC4 / "camevision_boot_ego.img")
    if (BUILD / "boot_before_ego.img").is_file():
        copy(BUILD / "boot_before_ego.img", REC4 / "boot_before_ego.img")
    copy(DT / "rv1126b-camevision-ego.dtb", REC4 / "device-tree" / "rv1126b-camevision-ego.dtb")
    copy(DT / "rv1126b-camevision-ego.dts", REC4 / "device-tree" / "rv1126b-camevision-ego.dts")
    copy(REC3 / "overlay" / "S50usbdevice.adb", REC4 / "overlay" / "S50usbdevice.adb")

    status = (
        "model: CameVision Ego\n"
        "kernel: 6.1.141-rt52 #24 SMP PREEMPT_RT\n"
        "adb: b9129b95306c7715  2207:0006\n"
        "usb: CameVision Ego (ADB)\n"
        "i2c: 0-0027 2-0052 3-0030 4-0030\n"
        "boot.img sha256: "
        "28cf1d7b90079a05941ef7419b005e64a5bddafbc3cc342034d50154e46e3b27\n"
        "note: both SC233 nodes present; chip-id still -5 (I2C NACK)\n"
    )
    (REC4 / "from-device" / "logs" / "live-status.txt").write_text(status, encoding="utf-8")

    lines = []
    for p in sorted(REC4.rglob("*")):
        if p.is_file():
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            rel = p.relative_to(REC4).as_posix()
            lines.append(f"{digest}  {rel}")
    (REC4 / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {REC4} ({len(lines)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
