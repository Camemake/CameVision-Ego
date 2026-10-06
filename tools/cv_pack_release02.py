#!/usr/bin/env python3
"""Assemble CameVision Ego flash V0.2 — Wi-Fi + RTC + stereo overlay."""
from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_ego_paths import repo_root  # noqa: E402

ROOT = repo_root()
REL = ROOT / "restore" / "release-0.2-20260902"
OV = REL / "overlay"
IQ_SRC = ROOT / "tools" / "iqfiles" / "sc233hgs_camevision-sc233hgs_flicker50.json"
if not IQ_SRC.is_file():
    IQ_SRC = ROOT / "build" / "live" / "sc233hgs_camevision-sc233hgs_flicker50.json"
KEEP_DOCS = (
    "RELEASE.md",
    "FLASH.md",
    "GITHUB_RELEASE.md",
    "restore-v02.ps1",
    "VERSION",
)

FILES = [
    ("tools/ego_stereo.py", "overlay/ego_stereo.py"),
    ("tools/ego_cam_sync.py", "overlay/ego_cam_sync.py"),
    ("tools/ego_calib.html", "overlay/ego_calib.html"),
    ("tools/ego_imu_hud.py", "overlay/ego_imu_hud.py"),
    ("tools/camemake-logo.png", "overlay/camemake-logo.png"),
    ("tools/stereo_native.c", "overlay/stereo_native.c"),
    ("tools/camevision-stereo.sh", "overlay/camevision-stereo.sh"),
    ("tools/camevision-wifi.sh", "overlay/camevision-wifi.sh"),
    ("tools/wpa_camevision.conf", "overlay/wpa_camevision.conf"),
    ("tools/S99ego-stereo", "overlay/S99ego-stereo"),
    ("tools/S11hwclock", "overlay/S11hwclock"),
    ("tools/cv_ego_autostart.py", "overlay/cv_ego_autostart.py"),
    ("tools/cv_ego_page.py", "overlay/cv_ego_page.py"),
    ("tools/cv_ego_overlay_deploy.py", "overlay/cv_ego_overlay_deploy.py"),
    ("tools/cv_ego_extract_pylib.py", "overlay/cv_ego_extract_pylib.py"),
    ("build/libego_stereo.so", "overlay/libego_stereo.so"),
]


def copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    try:
        print(f"  {src.relative_to(ROOT)} -> {dst.relative_to(REL)}")
    except ValueError:
        print(f"  {src} -> {dst.relative_to(REL)}")


def flatten_content_dir(p: Path) -> Path:
    cur = p
    for _ in range(4):
        entries = [e for e in cur.iterdir() if not e.name.startswith(".")]
        files = [e for e in entries if e.is_file()]
        dirs = [e for e in entries if e.is_dir()]
        if files or len(dirs) != 1:
            return cur
        cur = dirs[0]
    return cur


def first_dir(*cands: Path) -> Path | None:
    for p in cands:
        if p.is_dir() and any(p.iterdir()):
            return flatten_content_dir(p)
    return None


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    n = sum(1 for x in dst.rglob("*") if x.is_file())
    print(f"  {src} -> {dst.relative_to(REL)} ({n} files)")


def main() -> int:
    docs: dict[str, bytes] = {}
    boot_keep: bytes | None = None
    so_keep: bytes | None = None
    if REL.exists():
        for name in KEEP_DOCS:
            p = REL / name
            if p.is_file():
                docs[name] = p.read_bytes()
        boot = REL / "camevision_boot_ego.img"
        if boot.is_file():
            boot_keep = boot.read_bytes()
        so = REL / "overlay" / "libego_stereo.so"
        if so.is_file():
            so_keep = so.read_bytes()
        shutil.rmtree(REL)
    REL.mkdir(parents=True)
    OV.mkdir(parents=True, exist_ok=True)
    for name, data in docs.items():
        (REL / name).write_bytes(data)
        print(f"  kept {name}")

    for rel_src, rel_dst in FILES:
        src = ROOT / rel_src
        if rel_src.endswith("libego_stereo.so") and not src.is_file() and so_keep:
            dst = REL / rel_dst
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(so_keep)
            print(f"  kept overlay/libego_stereo.so ({len(so_keep)} bytes)")
            continue
        if rel_src.endswith("wpa_camevision.conf") and not src.is_file():
            print(f"  skip missing {src} (local Wi-Fi credentials)")
            continue
        if not src.is_file():
            print(f"  skip missing {src}")
            continue
        copy(src, REL / rel_dst)

    if IQ_SRC.is_file():
        copy(IQ_SRC, OV / "iqfiles" / "sc233hgs_camevision-sc233hgs_default.json")
    else:
        print(f"  skip missing IQ {IQ_SRC}")

    kos = first_dir(
        ROOT / "build" / "live" / "swt6621-rt52",
        ROOT / "restore" / "release-1-20260824" / "overlay" / "swt6621-rt52",
        ROOT / "restore" / "release-0.2-20260902" / "overlay" / "swt6621-rt52",
    )
    fw = first_dir(
        ROOT / "build" / "live" / "swt6621_fw",
        ROOT / "restore" / "release-1-20260824" / "overlay" / "swt6621_fw",
        ROOT / "restore" / "release-0.2-20260902" / "overlay" / "swt6621_fw",
    )
    if kos:
        copy_tree(kos, OV / "swt6621-rt52")
    else:
        print("  skip missing swt6621-rt52")
    if fw:
        copy_tree(fw, OV / "swt6621_fw")
    else:
        print("  skip missing swt6621_fw")

    built = ROOT / "build" / "camevision_boot_ego.img"
    if built.is_file():
        copy(built, REL / "camevision_boot_ego.img")
    elif boot_keep:
        (REL / "camevision_boot_ego.img").write_bytes(boot_keep)
        print(f"  kept camevision_boot_ego.img ({len(boot_keep)} bytes)")
    else:
        raise SystemExit("missing build/camevision_boot_ego.img — run cv_ego_wifi_fix_dtb.py first")

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
