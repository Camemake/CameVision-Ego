#!/usr/bin/env python3
"""Bake IQ / 3A / stereo into the images Maskrom writes.

After this, first boot starts ISP and depth from the flashed partitions.
The host overlay remains a verify/repair step.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_ego_make_ext2 import make_ext2  # noqa: E402
from cv_ego_paths import known_good, release_02, repo_root  # noqa: E402

ROOT = repo_root()
REL = release_02()
HOOK = b"""#!/bin/sh
[ "$1" = "start" ] || [ -z "$1" ] || exit 0
if [ -x /userdata/camevision-stereo.sh ]; then
	chmod 755 /userdata/camevision-stereo.sh /userdata/camevision-aiq.sh 2>/dev/null
	setsid /bin/sh -c 'sleep 8; exec /userdata/camevision-stereo.sh' \\
		</dev/null >/userdata/ego-stereo-boot.log 2>&1 &
fi
exit 0
"""


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def stage_overlay(stg: Path) -> None:
    if stg.exists():
        shutil.rmtree(stg)
    stg.mkdir(parents=True)
    tools = ROOT / "tools"
    for name in (
        "camevision-aiq.sh",
        "camevision-stereo.sh",
        "camevision-wifi.sh",
        "ego_stereo.py",
        "ego_cam_sync.py",
        "ego_imu_hud.py",
        "ego_record.py",
        "ego_mtf.py",
        "ego_calib.html",
        "camemake-logo.png",
        "iso12233.png",
        "S99ego-stereo",
        "S11hwclock",
        "wpa_camevision.conf",
        "cv_ego_extract_pylib.py",
    ):
        src = tools / name
        if src.is_file():
            _copy(src, stg / name)
    for iq in (tools / "iqfiles").glob("sc233hgs_camevision-*.json"):
        _copy(iq, stg / "iqfiles" / iq.name)
    so = ROOT / "build" / "libego_stereo.so"
    if not so.is_file():
        so = REL / "overlay" / "libego_stereo.so"
    if so.is_file():
        _copy(so, stg / "libego_stereo.so")
    for w in (ROOT / "build" / "wheels").glob("*.whl"):
        low = w.name.lower()
        if low.startswith("numpy-") or low.startswith("opencv_python_headless-4."):
            _copy(w, stg / "wheels" / w.name)
    ov = REL / "overlay"
    for folder in ("swt6621-rt52", "swt6621_fw"):
        src = ov / folder
        if src.is_dir():
            shutil.copytree(src, stg / folder)
    for ko in (
        ov / "kmpp-rt52.ko",
        ROOT / "restore" / "recovery-3-20260822-uvc-wifi-rkaiq" / "overlay" / "kmpp-rt52.ko",
    ):
        if ko.is_file():
            _copy(ko, stg / "kmpp-rt52.ko")
            break


def patch_rootfs() -> Path:
    src = known_good() / "rootfs_bootstable.img"
    dest = REL / "rootfs_bootstable.img"
    raw = bytearray(src.read_bytes())
    mark = b'if [ -e "/oem/rockchip_test/auto_reboot.sh" ]'
    body = raw.find(mark)
    if body < 0:
        raise SystemExit("rootfs missing auto_reboot hook")
    start = raw.rfind(b"#!/bin/sh", 0, body)
    if start < 0:
        raise SystemExit("rootfs auto_reboot shebang missing")
    end = start
    while end < start + 8000 and raw[end] != 0:
        end += 1
    old = bytes(raw[start:end])
    if len(HOOK) > len(old):
        raise SystemExit(f"hook {len(HOOK)} larger than {len(old)}")
    raw[start:end] = HOOK + b"\n" * (len(old) - len(HOOK))
    dest.write_bytes(raw)
    print(f"patched rootfs hook {len(old)} -> {dest}", flush=True)
    return dest


def main() -> int:
    REL.mkdir(parents=True, exist_ok=True)
    stg = ROOT / "build" / "flash-userdata"
    stage_overlay(stg)
    userdata = REL / "userdata.img"
    make_ext2(stg, userdata, 96)
    if userdata.read_bytes()[0x438:0x43A] != b"\x53\xEF":
        raise SystemExit("baked userdata is not ext2")
    patch_rootfs()
    print("BAKE_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
