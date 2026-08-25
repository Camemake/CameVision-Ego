#!/usr/bin/env python3
"""Assemble Release 1 — current working Ego baseline (no flash)."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

ROOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego")
REL = ROOT / "restore" / "release-1-20260824"
OV = REL / "overlay"
IQ_SRC = ROOT / "tools" / "iqfiles" / "sc233hgs_efference-sc233hgs_flicker50.json"
if not IQ_SRC.is_file():
    IQ_SRC = ROOT / "build" / "live" / "sc233hgs_efference-sc233hgs_flicker50.json"

FILES = [
    ("tools/ego_stereo.py", "overlay/ego_stereo.py"),
    ("tools/ego_cam_sync.py", "overlay/ego_cam_sync.py"),
    ("tools/ego_calib.html", "overlay/ego_calib.html"),
    ("tools/ego_imu_hud.py", "overlay/ego_imu_hud.py"),
    ("tools/camemake-logo.png", "overlay/camemake-logo.png"),
    ("tools/stereo_native.c", "overlay/stereo_native.c"),
    ("tools/cv_ego_build_stereo.py", "overlay/cv_ego_build_stereo.py"),
    ("tools/cv_ego_stereo_start.py", "overlay/cv_ego_stereo_start.py"),
    ("tools/cv_ego_iq_flicker50.py", "overlay/cv_ego_iq_flicker50.py"),
    ("tools/camevision-stereo.sh", "overlay/camevision-stereo.sh"),
    ("tools/S99ego-stereo", "overlay/S99ego-stereo"),
    ("tools/cv_ego_autostart.py", "overlay/cv_ego_autostart.py"),
    ("tools/cv_ego_page.py", "overlay/cv_ego_page.py"),
    ("tools/cv_ego_page.cmd", "overlay/cv_ego_page.cmd"),
    ("build/libego_stereo.so", "overlay/libego_stereo.so"),
]


def copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    try:
        print(f"  {src.relative_to(ROOT)} -> {dst.relative_to(REL)}")
    except ValueError:
        print(f"  {src.relative_to(ROOT)} -> {dst.relative_to(ROOT)}")


def main() -> int:
    keep = {}
    so_keep = None
    if REL.exists():
        for name in ("RELEASE.md", "restore-release1.ps1"):
            p = REL / name
            if p.is_file():
                keep[name] = p.read_bytes()
        so = REL / "overlay" / "libego_stereo.so"
        if so.is_file():
            so_keep = so.read_bytes()
        shutil.rmtree(REL)
    REL.mkdir(parents=True)
    for name, data in keep.items():
        (REL / name).write_bytes(data)
        print(f"  kept {name}")
    OV.mkdir(parents=True, exist_ok=True)
    for rel_src, rel_dst in FILES:
        src = ROOT / rel_src
        if rel_src.endswith("libego_stereo.so") and not src.is_file() and so_keep:
            dst = REL / rel_dst
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(so_keep)
            print(f"  kept overlay/libego_stereo.so ({len(so_keep)} bytes)")
            continue
        if not src.is_file():
            raise SystemExit(f"missing {src}")
        copy(src, REL / rel_dst)
    if not IQ_SRC.is_file():
        raise SystemExit(f"missing IQ {IQ_SRC}")
    copy(IQ_SRC, OV / "iqfiles" / "sc233hgs_efference-sc233hgs_default.json")
    tracked = ROOT / "tools" / "iqfiles" / "sc233hgs_efference-sc233hgs_flicker50.json"
    if IQ_SRC.resolve() != tracked.resolve():
        copy(IQ_SRC, tracked)

    lines = []
    for p in sorted(REL.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS.txt":
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            lines.append(f"{digest}  {p.relative_to(REL).as_posix()}")
    (REL / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {REL} ({len(lines)} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
