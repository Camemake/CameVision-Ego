#!/usr/bin/env python3
"""Maskrom write of the CameVision Ego package.

Writes loader, env, idblock, U-Boot, boot, userdata, oem, rootfs, then
the overlay once ADB is up.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_ego_paths import (  # noqa: E402
    adb_exe,
    boot_img as find_boot_img,
    boot_ok,
    first_file,
    known_good,
    release_02,
    repo_root,
    update_current,
    upgrade_tool,
    userdata_img,
)

UT = upgrade_tool()
ADB = adb_exe()
ROOT = repo_root()
KG = known_good()
REL02 = release_02()
LOADER = first_file(update_current() / "rv1126b_spl_loader_k4a8g.bin", KG / "rv1126b_spl_loader_k4a8g.bin") or (
    KG / "rv1126b_spl_loader_k4a8g.bin"
)


def boot_img() -> Path:
    p = find_boot_img()
    if p is None:
        raise SystemExit("missing camevision_boot_ego.img — run cv_ego_wifi_fix_dtb.py or pack the offline kit")
    raw = p.read_bytes()
    if not boot_ok(raw):
        raise SystemExit(
            f"{p} is not a CameVision IQ boot — run tools/cv_ego_wifi_fix_dtb.py"
        )
    print(f"boot {p} sha256={hashlib.sha256(raw).hexdigest()}", flush=True)
    return p


def staged_boot() -> Path:
    src = boot_img()
    dst = Path(os.environ.get("TEMP") or "/tmp") / "camevision_boot_ego.img"
    shutil.copy2(src, dst)
    raw = dst.read_bytes()
    if not boot_ok(raw):
        raise SystemExit("staged boot is not a CameVision IQ FIT")
    print(f"staged boot {dst} sha256={hashlib.sha256(raw).hexdigest()}", flush=True)
    return dst


def writes() -> tuple[tuple[str, Path], ...]:
    upd = update_current()
    return (
        ("0x0", first_file(upd / "env.img", KG / "env.img") or (KG / "env.img")),
        ("0x40", first_file(upd / "idblock.img", KG / "idblock.img") or (KG / "idblock.img")),
        ("0x440", first_file(upd / "uboot.img", KG / "uboot.img") or (KG / "uboot.img")),
        ("0x2440", staged_boot()),
        ("0x7C40", userdata_img() or Path("userdata.img")),
        ("0x207C40", first_file(upd / "oem_noko.img", KG / "oem_noko.img") or (KG / "oem_noko.img")),
        ("0x607C40", first_file(upd / "rootfs_bootstable.img", KG / "rootfs_bootstable.img") or (KG / "rootfs_bootstable.img")),
    )


def run(args: list[str], timeout: int = 180) -> subprocess.CompletedProcess:
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
    if not LOADER.is_file():
        raise SystemExit(f"missing {LOADER}")
    parts = writes()
    for _, p in parts:
        if not p.is_file():
            raise SystemExit(f"missing {p}")
        print(f"  {p.name:28s} {p.stat().st_size:12d}", flush=True)

    info = ld()
    if "Maskrom" not in info and "Loader" not in info:
        raise SystemExit("no Rockusb device")

    loaded = ("SerialNo=rockchip" in info) or ("SerialNo=0" in info)
    if "Maskrom" in info and not loaded:
        print("=== db loader once ===", flush=True)
        r = run([UT, "db", str(LOADER)], timeout=60)
        if r.returncode != 0:
            raise SystemExit("db failed")
        time.sleep(2)
        info = ld()
        print(info, flush=True)
        if "SerialNo=rockchip" not in info and "SerialNo=0" not in info:
            raise SystemExit("loader did not stay up")
    else:
        print("=== skip db ===", flush=True)

    for lba, path in parts:
        print(f"=== wl {lba} {path.name} ({path.stat().st_size} bytes) ===", flush=True)
        r = run([UT, "wl", lba, str(path)], timeout=900)
        if r.returncode != 0:
            raise SystemExit(f"write failed {path.name}")

    print("=== RELEASE BOOT NOW — waiting 8s ===", flush=True)
    time.sleep(8)
    print("=== rd ===", flush=True)
    run([UT, "rd"], timeout=30)

    t0 = time.time()
    serial = None
    while time.time() - t0 < 150:
        time.sleep(4)
        listing = subprocess.run([ADB, "devices"], capture_output=True, text=True).stdout
        rock = subprocess.run([UT, "ld"], capture_output=True, text=True).stdout
        print(f"t={time.time()-t0:.0f}s adb={listing.strip()!r}", flush=True)
        if "Maskrom" in rock:
            print(rock, flush=True)
        for line in listing.splitlines():
            if "\tdevice" in line:
                serial = line.split()[0]
                break
        if serial:
            break
    if not serial:
        raise SystemExit("board did not enumerate ADB — release BOOT if it is held")

    model = subprocess.run(
        [ADB, "-s", serial, "shell", "cat /proc/device-tree/model; echo"],
        capture_output=True,
        text=True,
        timeout=20,
    ).stdout
    print("serial", serial, flush=True)
    print("model", model.strip(), flush=True)
    if "CameVision Ego" not in model:
        raise SystemExit("DTB model is not CameVision Ego")
    serial = force_camevision_dtb(serial)
    print("=== overlay (stereo + Wi-Fi STA + pylib) ===", flush=True)
    sys.path.insert(0, str(ROOT / "tools"))
    import cv_ego_overlay_deploy

    cv_ego_overlay_deploy.deploy(serial)
    print("EGO_UP", flush=True)
    return 0


def _module_names(serial: str) -> str:
    r = subprocess.run(
        [
            ADB,
            "-s",
            serial,
            "shell",
            "cat '/proc/device-tree/i2c@21120000/sc233hgs@30/rockchip,camera-module-name'; echo; "
            "cat '/proc/device-tree/i2c-gpio-cam1/sc233hgs@30/rockchip,camera-module-name'; echo",
        ],
        capture_output=True,
        text=True,
        timeout=20,
    )
    return r.stdout or ""


def wait_adb(serial: str, seconds: int = 120) -> None:
    t0 = time.time()
    while time.time() - t0 < seconds:
        time.sleep(3)
        listing = subprocess.run([ADB, "devices"], capture_output=True, text=True).stdout
        if serial in listing and "device" in listing:
            try:
                model = subprocess.run(
                    [ADB, "-s", serial, "shell", "cat /proc/device-tree/model; echo"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                ).stdout
            except Exception:
                continue
            if "CameVision Ego" in (model or ""):
                return
    raise SystemExit("board did not return after boot rewrite")


def ensure_camevision_dtb(serial: str) -> str:
    return force_camevision_dtb(serial)


def force_camevision_dtb(serial: str) -> str:
    names = _module_names(serial)
    print("camera-module-name before force", names.replace("\n", " ").strip(), flush=True)
    img = boot_img()
    remote = "/userdata/camevision_boot_ego.img"
    print(f"=== forcing CameVision boot over ADB from {img} ===", flush=True)
    r = subprocess.run([ADB, "-s", serial, "push", str(img), remote], capture_output=True, timeout=180)
    if r.returncode != 0:
        raise SystemExit("failed to push CameVision boot")
    r = subprocess.run(
        [
            ADB,
            "-s",
            serial,
            "shell",
            f"dd if={remote} of=/dev/mmcblk0p4 bs=1M conv=fsync; sync; echo DD_OK",
        ],
        capture_output=True,
        timeout=180,
    )
    text = ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace")
    print(text, flush=True)
    if "DD_OK" not in text:
        raise SystemExit("boot rewrite dd failed")
    subprocess.run([ADB, "-s", serial, "reboot"], capture_output=True, timeout=20)
    wait_adb(serial)
    names = _module_names(serial)
    print("camera-module-name after force", names.replace("\n", " ").strip(), flush=True)
    if names.count("camevision-sc233hgs") < 2:
        raise SystemExit("boot rewrite did not switch camera-module-name to CameVision")
    return serial


if __name__ == "__main__":
    raise SystemExit(main())
