#!/usr/bin/env python3
"""Pack CameVision Ego AM / MIRA220 as a standalone flash kit + offline zip.

Does not write into restore/release-0.2-20260902 or CameVision-Ego-Offline.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import zipfile
from pathlib import Path

from cv_ego_make_ext2 import make_ext2
from cv_ego_paths import first_file, repo_root
from cv_ego_paths_am import AM_RELEASE, BOOT_NAME, MODULE, boot_ok_am, release_am

ROOT = repo_root()
REL02 = ROOT / "restore" / "release-0.2-20260902"
BRING = ROOT / "restore" / "mira220-bringup"
DRV = BRING / "driver"
REL = release_am()
OFF = ROOT / "build" / "CameVision-Ego-AM-Offline"
ZIP = ROOT / "build" / "CameVision-Ego-AM-Offline.zip"

SHARED_IMGS = (
    "rv1126b_spl_loader_k4a8g.bin",
    "env.img",
    "idblock.img",
    "uboot.img",
    "oem_noko.img",
    "rootfs_bootstable.img",
)

AM_KOS = (
    "mira220.ko",
    "miralink.ko",
    "ciflate.ko",
    "clkgo.ko",
    "mfix4.ko",
    "mstart.ko",
)

AM_SRC = (
    "mira220-rk.c",
    "mira220_init.h",
    "rk-camera-module.h",
    "miralink.c",
    "mfix4.c",
    "mstart.c",
    "ciflate.c",
    "clkgo.c",
    "Makefile",
)

TOOL_FILES = (
    "cv_ego_pack_am.py",
    "cv_ego_flash_am.py",
    "cv_ego_overlay_deploy_am.py",
    "cv_ego_paths_am.py",
    "cv_ego_paths.py",
    "cv_ego_make_ext2.py",
    "cv_ego_mira220_fit.py",
    "cv_ego_extract_pylib.py",
    "cv_ego_page.py",
    "ego_stereo.py",
    "ego_cam_sync.py",
    "ego_imu_hud.py",
    "ego_record.py",
    "ego_mtf.py",
    "ego_calib.html",
    "camevision-stereo-am.sh",
    "camevision-wifi.sh",
    "S99ego-stereo",
    "S11hwclock",
    "camemake-logo.png",
    "iso12233.png",
    "stereo_native.c",
)

README = """CameVision EGO AM · MIRA220 · offline pack
==========================================

This pack is ONLY for CameVision Ego AM boards with dual AMS MIRA220.
It is not the SC233HGS V0.2 kit. Do not flash this onto a SC233HGS board.

Windows Maskrom (hold BOOT, tap RESET):
  python tools/cv_ego_flash_am.py

Already running over ADB:
  python tools/cv_ego_overlay_deploy_am.py

Live page: http://127.0.0.1:8081/
USB stays ADB.
"""


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  {src} -> {dst}", flush=True)


def _copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    n = sum(1 for p in dst.rglob("*") if p.is_file())
    print(f"  {src} -> {dst} ({n} files)", flush=True)


def stage_overlay(stg: Path) -> None:
    if stg.exists():
        shutil.rmtree(stg)
    stg.mkdir(parents=True)
    tools = ROOT / "tools"
    mapping = {
        "camevision-stereo.sh": tools / "camevision-stereo-am.sh",
        "camevision-wifi.sh": tools / "camevision-wifi.sh",
        "ego_stereo.py": tools / "ego_stereo.py",
        "ego_cam_sync.py": tools / "ego_cam_sync.py",
        "ego_imu_hud.py": tools / "ego_imu_hud.py",
        "ego_record.py": tools / "ego_record.py",
        "ego_mtf.py": tools / "ego_mtf.py",
        "ego_calib.html": tools / "ego_calib.html",
        "camemake-logo.png": tools / "camemake-logo.png",
        "iso12233.png": tools / "iso12233.png",
        "S99ego-stereo": tools / "S99ego-stereo",
        "S11hwclock": tools / "S11hwclock",
        "S10mira220": BRING / "S10mira220",
        "wpa_camevision.conf": tools / "wpa_camevision.conf",
        "cv_ego_extract_pylib.py": tools / "cv_ego_extract_pylib.py",
        "stereo_native.c": tools / "stereo_native.c",
    }
    for name, src in mapping.items():
        if src.is_file():
            _copy(src, stg / name)
    iq = tools / "iqfiles" / "mira220_camevision-mira220_default.json"
    if not iq.is_file():
        raise SystemExit("missing MIRA220 IQ")
    _copy(iq, stg / "iqfiles" / iq.name)
    so = first_file(ROOT / "build" / "libego_stereo.so", REL02 / "overlay" / "libego_stereo.so")
    if so is None:
        raise SystemExit("missing libego_stereo.so")
    _copy(so, stg / "libego_stereo.so")
    for ko in AM_KOS:
        src = DRV / ko
        if not src.is_file():
            raise SystemExit(f"missing {src}")
        _copy(src, stg / "modules" / ko)
    for folder in ("swt6621-rt52", "swt6621_fw"):
        src = REL02 / "overlay" / folder
        if src.is_dir():
            _copy_tree(src, stg / folder)
    kmpp = first_file(
        REL02 / "overlay" / "kmpp-rt52.ko",
        ROOT / "restore" / "recovery-3-20260822-uvc-wifi-rkaiq" / "overlay" / "kmpp-rt52.ko",
    )
    if kmpp is not None:
        _copy(kmpp, stg / "kmpp-rt52.ko")
    wheels = ROOT / "build" / "wheels"
    if wheels.is_dir():
        for w in wheels.glob("*.whl"):
            low = w.name.lower()
            if low.startswith("numpy-") or low.startswith("opencv_python_headless-4."):
                _copy(w, stg / "wheels" / w.name)


def write_docs(rel: Path) -> None:
    (rel / "SENSOR").write_text("MIRA220\n", encoding="ascii")
    (rel / "BOARD").write_text("AM\n", encoding="ascii")
    (rel / "VERSION").write_text("2.0-am-mira220\n", encoding="ascii")
    (rel / "RELEASE.md").write_text(
        """# CameVision EGO AM · MIRA220 · flash 2.0 — 9 October 2026

This folder is the **AM / MIRA220** Maskrom kit. It is **not** the SC233HGS
V0.2 kit (`restore/release-0.2-20260902`). Do not flash one onto the other.

Hardware: CameVisionEgo_AM V0.3, dual AMS MIRA220 (1600×1400 RAW10, color,
SGRBG), microSD rail **+3.3V_SDC_PWR**. USB stays **ADB**.

```
python tools/cv_ego_flash_am.py
```

Already running:

```
python tools/cv_ego_overlay_deploy_am.py
```

| Partition | Image |
|---|---|
| env / idblock / uboot | same RV1126B SPL set as V0.2 (copied here) |
| boot | `camevision_boot_ego_am.img` (MIRA220 DTB, 3.3 V SD) |
| userdata | AM overlay (CIF stereo, mira modules, MIRA220 IQ) |
| oem / rootfs | CameVision `oem_noko.img` / `rootfs_bootstable.img` |

Overlay:

- Stereo page `:8081` — CIF RAW10, 1400×1600 view, jet depth
- IMU HUD `:8083`
- `S10mira220` — mira220 + ciflate + miralink + mfix4 + mstart
- `S99ego-stereo` — AM stereo start (no rkaiq 3A)
- IQ `mira220_camevision-mira220_default.json`

## Do not

- Flash this kit onto a SC233HGS board
- Use `tools/cv_ego_flash.py` (that is V0.2 SC233HGS)
- Switch USB to a webcam gadget
""",
        encoding="utf-8",
    )
    (rel / "FLASH.md").write_text(
        """# CameVision Ego AM / MIRA220 · Maskrom flash

Empty AM board. USB stays **ADB**.

```
python tools/cv_ego_flash_am.py
```

| LBA | Partition | File |
|---|---|---|
| loader (`db` once) | SPL | `rv1126b_spl_loader_k4a8g.bin` |
| 0x0 | env | `env.img` |
| 0x40 | idblock | `idblock.img` |
| 0x440 | uboot | `uboot.img` |
| 0x2440 | boot | `camevision_boot_ego_am.img` |
| 0x7C40 | userdata | `userdata.img` |
| 0x207C40 | oem | `oem_noko.img` |
| 0x607C40 | rootfs | `rootfs_bootstable.img` |

Hold BOOT, tap RESET → Maskrom. Release BOOT after writes. Overlay deploy
installs MIRA220 modules, CIF stereo, and pylib.

Board already running AM: `restore-am.ps1` or `python tools/cv_ego_overlay_deploy_am.py`.
""",
        encoding="utf-8",
    )
    (rel / "GITHUB_RELEASE.md").write_text(
        """# CameVision EGO AM · MIRA220 · 2.0

**CameVisionEgo_AM V0.3** · dual AMS MIRA220 · 9 October 2026

Standalone Maskrom flash. Not the SC233HGS V0.2 release.

- Live stereo `http://127.0.0.1:8081/`
- IMU HUD `http://127.0.0.1:8083/`
- Boot DTB: `camevision-mira220`, microSD 3.3 V
- USB stays ADB

```
python tools/cv_ego_flash_am.py
```
""",
        encoding="utf-8",
    )
    (rel / "restore-am.ps1").write_text(
        """# Push AM / MIRA220 overlay. Does not flash SC233HGS. USB stays ADB.
$ErrorActionPreference = "Stop"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $root
python "$root\\tools\\cv_ego_overlay_deploy_am.py"
""",
        encoding="utf-8",
    )


def sha256sums(rel: Path) -> None:
    lines = []
    for p in sorted(rel.rglob("*")):
        if not p.is_file() or p.name == "SHA256SUMS.txt":
            continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        rel_name = p.relative_to(rel).as_posix()
        lines.append(f"{digest}  {rel_name}\n")
    (rel / "SHA256SUMS.txt").write_text("".join(lines), encoding="ascii")
    print(f"SHA256SUMS {len(lines)} files", flush=True)


def verify_kit(rel: Path) -> None:
    if (rel / "SENSOR").read_text(encoding="ascii").strip() != "MIRA220":
        raise SystemExit("AM SENSOR is not MIRA220")
    if (REL02 / "SENSOR").read_text(encoding="ascii").strip() != "SC233HGS":
        raise SystemExit("V0.2 SENSOR was overwritten")
    boot = rel / BOOT_NAME
    raw = boot.read_bytes()
    if not boot_ok_am(raw):
        raise SystemExit("AM boot FIT failed MIRA220 / 3.3 V SD check")
    if b"camevision-sc233hgs" in raw:
        raise SystemExit("AM boot still has camevision-sc233hgs")
    ov = rel / "overlay"
    if (ov / "iqfiles" / "sc233hgs_camevision-sc233hgs_default.json").is_file():
        raise SystemExit("AM overlay contains SC233HGS IQ")
    iq = ov / "iqfiles" / "mira220_camevision-mira220_default.json"
    if not iq.is_file():
        raise SystemExit("AM overlay missing MIRA220 IQ")
    for ko in AM_KOS:
        if not (ov / "modules" / ko).is_file():
            raise SystemExit(f"AM overlay missing {ko}")
    ud = (rel / "userdata.img").read_bytes()
    if b"mira220_camevision-mira220_default.json" not in ud:
        raise SystemExit("AM userdata missing MIRA220 IQ")
    if b"sc233hgs_camevision-sc233hgs_default.json" in ud:
        raise SystemExit("AM userdata still has SC233HGS IQ")
    if b"S10mira220" not in ud:
        raise SystemExit("AM userdata missing S10mira220")
    sc_boot = REL02 / "camevision_boot_ego.img"
    if sc_boot.is_file() and hashlib.sha256(sc_boot.read_bytes()).digest() == hashlib.sha256(raw).digest():
        raise SystemExit("AM boot is identical to SC233HGS boot")
    print(
        f"AM_KIT_OK boot={hashlib.sha256(raw).hexdigest()[:16]} "
        f"module={MODULE} sd=3.3V",
        flush=True,
    )


def pack_kit() -> Path:
    if REL.exists():
        shutil.rmtree(REL)
    REL.mkdir(parents=True)
    write_docs(REL)
    boot_src = BRING / "camevision_boot_mira220.img"
    if not boot_src.is_file():
        raise SystemExit(f"missing {boot_src} — flash/patch the AM FIT first")
    raw = boot_src.read_bytes()
    if not boot_ok_am(raw):
        raise SystemExit(f"{boot_src} is not a MIRA220 AM FIT with 3.3 V SD")
    _copy(boot_src, REL / BOOT_NAME)
    for name in SHARED_IMGS:
        src = REL02 / name
        if not src.is_file():
            raise SystemExit(f"missing shared image {src}")
        _copy(src, REL / name)
    stg = ROOT / "build" / "flash-userdata-am"
    stage_overlay(stg)
    _copy_tree(stg, REL / "overlay")
    make_ext2(stg, REL / "userdata.img", 96)
    if (REL / "userdata.img").read_bytes()[0x438:0x43A] != b"\x53\xEF":
        raise SystemExit("baked AM userdata is not ext2")
    drv_out = REL / "driver"
    drv_out.mkdir(parents=True)
    for name in AM_SRC + AM_KOS:
        src = DRV / name
        if src.is_file():
            _copy(src, drv_out / name)
    _copy(BRING / "S10mira220", REL / "S10mira220")
    dts = ROOT / "device-tree" / "rv1126b-camevision-ego.dts"
    if dts.is_file():
        _copy(dts, REL / "device-tree" / dts.name)
    sha256sums(REL)
    verify_kit(REL)
    return REL


def pack_offline(rel: Path) -> None:
    if OFF.exists():
        shutil.rmtree(OFF)
    OFF.mkdir(parents=True)
    _copy_tree(rel, OFF / "restore" / AM_RELEASE)
    (OFF / "tools").mkdir(parents=True)
    for name in TOOL_FILES:
        src = ROOT / "tools" / name
        if src.is_file():
            _copy(src, OFF / "tools" / name)
    iq = ROOT / "tools" / "iqfiles" / "mira220_camevision-mira220_default.json"
    _copy(iq, OFF / "tools" / "iqfiles" / iq.name)
    so = ROOT / "build" / "libego_stereo.so"
    if so.is_file():
        _copy(so, OFF / "build" / "libego_stereo.so")
    src_host = ROOT / "host"
    host = OFF / "host"
    host.mkdir(parents=True)
    for name in ("adb.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll", "upgrade_tool.exe"):
        src = src_host / name
        if src.is_file():
            _copy(src, host / name)
    da = src_host / "DriverAssitant_v5.14"
    if da.is_dir():
        _copy_tree(da, host / "DriverAssitant_v5.14")
    linux_src = src_host / "linux"
    if linux_src.is_dir():
        (host / "linux").mkdir(parents=True, exist_ok=True)
        for p in linux_src.iterdir():
            if p.name in ("py-tmp", "pt-tmp"):
                continue
            if p.is_dir():
                _copy_tree(p, host / "linux" / p.name)
            elif p.is_file():
                _copy(p, host / "linux" / p.name)
    wheels = ROOT / "build" / "wheels"
    if wheels.is_dir():
        dest = OFF / "build" / "wheels"
        dest.mkdir(parents=True)
        for w in wheels.glob("*.whl"):
            low = w.name.lower()
            if low.startswith("numpy-") or low.startswith("opencv_python_headless-4."):
                _copy(w, dest / w.name)
    (OFF / "README.txt").write_text(README, encoding="utf-8")
    (OFF / "VERSION").write_text("CameVision-Ego-AM-Offline 2.0\n", encoding="ascii")
    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in OFF.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(OFF.parent))
    extra = list((OFF / "restore").iterdir())
    if [p.name for p in extra] != [AM_RELEASE]:
        raise SystemExit("AM offline pack has leftover restore trees")
    if list((OFF / "restore").rglob("camevision_boot_ego.img")):
        raise SystemExit("AM offline pack contains SC233HGS boot name")
    boots = list(OFF.rglob("camevision_boot*.img"))
    if len(boots) != 1 or boots[0].name != BOOT_NAME:
        raise SystemExit("AM offline pack must contain exactly the AM boot")
    print(f"wrote {OFF}", flush=True)
    print(f"wrote {ZIP} ({ZIP.stat().st_size} bytes)", flush=True)


def main() -> int:
    rel = pack_kit()
    pack_offline(rel)
    print(f"PACK_AM_OK {rel}", flush=True)
    print(f"PACK_AM_OFFLINE {ZIP}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
