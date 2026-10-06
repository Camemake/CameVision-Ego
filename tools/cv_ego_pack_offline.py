#!/usr/bin/env python3
"""Build the CameVision Ego offline installer folder + zip.

Copies the website pages, live-page tools, prebuilt flash images (when
present), and Windows host binaries into build/CameVision-Ego-Offline.

    python tools/cv_ego_pack_offline.py
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_ego_paths import (  # noqa: E402
    PARTITION_FILES,
    boot_img,
    boot_ok,
    partition_img,
    release_02,
    repo_root,
    userdata_img,
)

ROOT = repo_root()
OUT = ROOT / "build" / "CameVision-Ego-Offline"
ZIP = ROOT / "build" / "CameVision-Ego-Offline.zip"

TOOL_FILES = (
    "cv_ego_studio.py",
    "cv_ego_paths.py",
    "cv_ego_packages.py",
    "cv_ego_driver.py",
    "cv_ego_host_setup.py",
    "cv_ego_setup.py",
    "cv_ego_diag.py",
    "cv_ego_update.py",
    "cv_ego_flash.py",
    "cv_ego_wifi_full_flash.py",
    "cv_ego_overlay_deploy.py",
    "cv_ego_page.py",
    "cv_ego_autostart.py",
    "cv_ego_extract_pylib.py",
    "cv_ego_stereo_start.py",
    "ego_stereo.py",
    "ego_cam_sync.py",
    "ego_imu_hud.py",
    "ego_record.py",
    "ego_mtf.py",
    "ego_calib.html",
    "camevision-stereo.sh",
    "camevision-aiq.sh",
    "camevision-wifi.sh",
    "S99ego-stereo",
    "S11hwclock",
    "camemake-logo.png",
    "iso12233.png",
    "CameVision-Ego.sh",
)

SKIP_PACK = {"schematic", "schematic-ego"}

README = """CameVision EGO · offline installer
=================================

Windows:  double-click CameVision-Ego.exe
Linux:    open CameVision-Ego (or the desktop entry)

The Camemake window installs Python, ADB, the flash tool, and USB access.

The tool opens at http://127.0.0.1:8765/tool.html

USB / Maskrom
  Install USB driver. Hold BOOT, tap RESET, keep BOOT held.

Package
  Select CameVision Ego, or load a GitHub update / a zip.
  Install. Writes loader, env, idblock, U-Boot, boot,
  userdata, oem, rootfs, and the overlay.
  Release BOOT when the board starts.

ADB
  Open: live page http://127.0.0.1:8081/
  Extended diagnostics: full board dump in the log.

Same path on an empty board and on a board that already has images.
"""


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  {src} -> {dst.relative_to(OUT)}")


def _ignore_schematic(_directory: str, names: list[str]) -> set[str]:
    skip = set()
    for name in names:
        low = name.lower()
        if low in SKIP_PACK or low.startswith("schematic") or name == "parse_schematic.py":
            skip.add(name)
        if name.startswith("camevision_boot") and name.endswith(".img"):
            skip.add(name)
    return skip


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=_ignore_schematic)
    n = sum(1 for p in dst.rglob("*") if p.is_file())
    print(f"  {src} -> {dst.relative_to(OUT)} ({n} files)")


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    copy_tree(ROOT / "docs", OUT / "docs")
    (OUT / "tools").mkdir(parents=True)
    for name in TOOL_FILES:
        src = ROOT / "tools" / name
        if src.is_file():
            copy_file(src, OUT / "tools" / name)
    wpa = ROOT / "tools" / "wpa_camevision.conf"
    if wpa.is_file():
        copy_file(wpa, OUT / "tools" / "wpa_camevision.conf")
    for iq_name in (
        "sc233hgs_camevision-sc233hgs_default.json",
        "sc233hgs_camevision-sc233hgs_flicker50.json",
    ):
        iq = ROOT / "tools" / "iqfiles" / iq_name
        if iq.is_file():
            copy_file(iq, OUT / "tools" / "iqfiles" / iq.name)

    so = ROOT / "build" / "libego_stereo.so"
    ov_so = ROOT / "restore" / "release-0.2-20260902" / "overlay" / "libego_stereo.so"
    if so.is_file():
        copy_file(so, OUT / "build" / "libego_stereo.so")
    elif ov_so.is_file():
        copy_file(ov_so, OUT / "build" / "libego_stereo.so")

    from cv_ego_bake_flash import main as bake_flash

    if bake_flash():
        raise SystemExit("failed to bake flash images")

    rel_out = OUT / "restore" / "release-0.2-20260902"
    rel_out.mkdir(parents=True)
    boot = boot_img()
    if boot is None:
        raise SystemExit("no CameVision IQ boot to pack — refuse to ship")
    raw = boot.read_bytes()
    if not boot_ok(raw):
        raise SystemExit(f"boot {boot} is not a CameVision IQ FIT")
    copy_file(boot, rel_out / "camevision_boot_ego.img")
    (rel_out / "BOOT.sha256").write_text(
        hashlib.sha256(raw).hexdigest() + "  camevision_boot_ego.img\n",
        encoding="ascii",
    )

    for key, fname in PARTITION_FILES.items():
        src = partition_img(key) if key != "userdata" else userdata_img()
        if src is None or not src.is_file():
            raise SystemExit(f"missing CameVision image {fname}")
        copy_file(src, rel_out / fname)

    src_ov = release_02() / "overlay"
    for folder in ("swt6621-rt52", "swt6621_fw", "iqfiles"):
        src = src_ov / folder
        if src.is_dir():
            copy_tree(src, rel_out / "overlay" / folder)
    for name in ("libego_stereo.so", "cv_ego_extract_pylib.py"):
        src = src_ov / name
        if src.is_file():
            copy_file(src, rel_out / "overlay" / name)
    for ko_src in (
        src_ov / "kmpp-rt52.ko",
        ROOT / "restore" / "recovery-3-20260822-uvc-wifi-rkaiq" / "overlay" / "kmpp-rt52.ko",
        ROOT / "restore" / "recovery-2-20260821-adb-stream" / "overlay" / "kmpp-rt52.ko",
    ):
        if ko_src.is_file():
            copy_file(ko_src, rel_out / "overlay" / "kmpp-rt52.ko")
            break
    else:
        print("WARN kmpp-rt52.ko not found — record encode may be missing")

    host = OUT / "host"
    host.mkdir(parents=True)
    src_host = ROOT / "host"
    win_adb = src_host / "adb.exe"
    if win_adb.is_file():
        copy_file(win_adb, host / "adb.exe")
        for extra in ("AdbWinApi.dll", "AdbWinUsbApi.dll"):
            sib = src_host / extra
            if sib.is_file():
                copy_file(sib, host / extra)
    else:
        print("WARN host/adb.exe not found")
    win_ut = src_host / "upgrade_tool.exe"
    if win_ut.is_file():
        copy_file(win_ut, host / "upgrade_tool.exe")
    else:
        print("WARN host/upgrade_tool.exe not found")

    da = src_host / "DriverAssitant_v5.14"
    if da.is_dir():
        copy_tree(da, host / "DriverAssitant_v5.14")
    else:
        print("WARN host/DriverAssitant_v5.14 not found — USB driver will be missing")

    linux_src = src_host / "linux"
    if linux_src.is_dir():
        (host / "linux").mkdir(parents=True, exist_ok=True)
        for p in linux_src.iterdir():
            if p.name in ("py-tmp", "pt-tmp"):
                continue
            if p.is_dir():
                copy_tree(p, host / "linux" / p.name)
            elif p.is_file():
                copy_file(p, host / "linux" / p.name)

    py_src = src_host / "python"
    if py_src.is_dir() and (py_src / "python.exe").is_file():
        copy_tree(py_src, host / "python")

    wheels = ROOT / "build" / "wheels"
    if wheels.is_dir():
        dest = OUT / "build" / "wheels"
        dest.mkdir(parents=True)
        for w in wheels.glob("*.whl"):
            name = w.name.lower()
            if name.startswith("numpy-") or name.startswith("opencv_python_headless-4."):
                copy_file(w, dest / w.name)

    exe = ROOT / "CameVision-Ego.exe"
    if exe.is_file():
        copy_file(exe, OUT / "CameVision-Ego.exe")
    linux_app = ROOT / "CameVision-Ego"
    if linux_app.is_file():
        copy_file(linux_app, OUT / "CameVision-Ego")
        os.chmod(OUT / "CameVision-Ego", 0o755)
    desk = ROOT / "CameVision-Ego.desktop"
    if desk.is_file():
        copy_file(desk, OUT / "CameVision-Ego.desktop")
    inst = ROOT / "tools" / "installer" / "CameVisionEgoSetup.cs"
    if inst.is_file():
        copy_file(inst, OUT / "tools" / "installer" / "CameVisionEgoSetup.cs")
    (OUT / "README.txt").write_text(README, encoding="utf-8")
    (OUT / "VERSION").write_text("CameVision-Ego-Offline 0.2\n", encoding="ascii")

    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in OUT.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(OUT.parent))
    print(f"wrote {OUT}")
    print(f"wrote {ZIP} ({ZIP.stat().st_size} bytes)")
    _verify_pack(OUT)
    return 0


ALLOWED_IMGS = {
    "camevision_boot_ego.img",
    "env.img",
    "idblock.img",
    "uboot.img",
    "oem_noko.img",
    "rootfs_bootstable.img",
    "userdata.img",
}
FORBIDDEN_DIR_BITS = (
    "known-good",
    "recovery-",
    "release-1",
    "updates",
    "rootfs_adbwait",
)


def _verify_pack(out: Path) -> None:
    env = os.environ.get("CAMEVISION_EGO_ROOT")
    os.environ["CAMEVISION_EGO_ROOT"] = str(out)
    try:
        from cv_ego_paths import boot_img as packed_boot, boot_ok as packed_ok, partition_img as packed_part
        from cv_ego_packages import packages

        img = packed_boot()
        if img is None or not packed_ok(img.read_bytes()):
            raise SystemExit("packed tree has no CameVision IQ boot")
        aiq = out / "tools" / "camevision-aiq.sh"
        ov = out / "tools" / "cv_ego_overlay_deploy.py"
        stereo = out / "tools" / "camevision-stereo.sh"
        if not aiq.is_file() or not ov.is_file() or not stereo.is_file():
            raise SystemExit("packed tree missing IQ/stereo overlay scripts")
        text = ov.read_text(encoding="utf-8")
        if "start IQ / 3A" not in text or "cv_ego_extract_pylib.py" not in text:
            raise SystemExit("packed overlay is not the pylib-before-stereo deploy")
        if text.find("cv_ego_extract_pylib.py") > text.find("start live page"):
            raise SystemExit("packed overlay still starts stereo before pylib")
        wheels = list((out / "build" / "wheels").glob("numpy-*.whl")) + list(
            (out / "build" / "wheels").glob("opencv_python_headless-4.*.whl")
        )
        if len(wheels) < 2:
            raise SystemExit("packed tree missing numpy/opencv wheels")
        boots = [p for p in out.rglob("camevision_boot*.img") if p.is_file()]
        if len(boots) != 1:
            raise SystemExit(
                "pack must contain exactly one camevision_boot*.img, got "
                + ", ".join(str(p.relative_to(out)) for p in boots)
            )
        only = boots[0]
        if only.resolve() != img.resolve():
            raise SystemExit(f"flash boot is {img}, but pack also has {only}")
        raw = only.read_bytes()
        if b"efference-sc233hgs" in raw or not packed_ok(raw):
            raise SystemExit(f"packed boot is not CameVision IQ: {only}")
        restore = out / "restore"
        extra_dirs = [
            p.name
            for p in restore.iterdir()
            if p.is_dir() and p.name != "release-0.2-20260902"
        ]
        if extra_dirs:
            raise SystemExit("pack has leftover restore trees: " + ", ".join(extra_dirs))
        for p in restore.rglob("*"):
            rel = str(p.relative_to(out)).replace("\\", "/").lower()
            if any(bit in rel for bit in FORBIDDEN_DIR_BITS):
                raise SystemExit(f"pack still contains old tree {p.relative_to(out)}")
        imgs = [p for p in out.rglob("*.img") if p.is_file()]
        extra_imgs = [p for p in imgs if p.name not in ALLOWED_IMGS]
        if extra_imgs:
            raise SystemExit(
                "pack has unused images: "
                + ", ".join(str(p.relative_to(out)) for p in extra_imgs)
            )
        missing_imgs = [name for name in ALLOWED_IMGS if not any(p.name == name for p in imgs)]
        if missing_imgs:
            raise SystemExit("pack missing images: " + ", ".join(missing_imgs))
        for key in PARTITION_FILES:
            if packed_part(key) is None and key != "userdata":
                raise SystemExit(f"packed tree cannot resolve {key}")
        if userdata_img() is None:
            raise SystemExit("packed tree cannot resolve userdata")
        pkgs = packages()
        if len(pkgs) != 1 or pkgs[0]["id"] != "camevision-ego":
            raise SystemExit("pack must expose only CameVision Ego")
        if not pkgs[0]["ready"]:
            raise SystemExit("CameVision Ego package is not ready: " + ", ".join(pkgs[0]["missing"]))
        ud = (out / "restore" / "release-0.2-20260902" / "userdata.img").read_bytes()
        if b"camevision-aiq.sh" not in ud or b"sc233hgs_camevision-sc233hgs_default.json" not in ud:
            raise SystemExit("userdata.img is missing IQ/3A — bake failed")
        rf = (out / "restore" / "release-0.2-20260902" / "rootfs_bootstable.img").read_bytes()
        if b"/userdata/camevision-stereo.sh" not in rf:
            raise SystemExit("rootfs does not start CameVision 3A/stereo on boot")
        setup = (out / "tools" / "cv_ego_setup.py").read_text(encoding="utf-8")
        if "pack_board" in setup or "Board flash" in setup:
            raise SystemExit("host installer still auto-flashes")
        print(
            f"PACK_OK boot={img} sha={hashlib.sha256(raw).hexdigest()[:16]} "
            f"wheels={len(wheels)} imgs={len(imgs)}",
            flush=True,
        )
    finally:
        if env is None:
            os.environ.pop("CAMEVISION_EGO_ROOT", None)
        else:
            os.environ["CAMEVISION_EGO_ROOT"] = env


if __name__ == "__main__":
    raise SystemExit(main())
