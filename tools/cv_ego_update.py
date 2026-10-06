#!/usr/bin/env python3
"""Apply a CameVision Ego package update from GitHub or a local zip.

Extracts into restore/updates/current. Image files and overlay land in
the same places the installer already uses.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_ego_paths import known_good, release_02, repo_root, update_current  # noqa: E402

ROOT = repo_root()
GITHUB_API = "https://api.github.com/repos/Camemake/CameVision-Ego/releases/latest"
GITHUB_ZIPBALL = "https://github.com/Camemake/CameVision-Ego/archive/refs/heads/main.zip"

IMAGE_NAMES = {
    "env.img",
    "idblock.img",
    "uboot.img",
    "camevision_boot_ego.img",
    "userdata.img",
    "oem_noko.img",
    "rootfs_bootstable.img",
    "rv1126b_spl_loader_k4a8g.bin",
}


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"GET {url}", flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "CameVision-Ego-offline"})
    with urllib.request.urlopen(req, timeout=60) as src, dest.open("wb") as out:
        n = 0
        while True:
            chunk = src.read(1024 * 256)
            if not chunk:
                break
            out.write(chunk)
            n += len(chunk)
            if n == len(chunk) or n % (8 * 1024 * 1024) < len(chunk):
                print(f"downloaded {n} bytes", flush=True)
    print(f"wrote {dest} ({dest.stat().st_size} bytes)", flush=True)


def _github_zip_url() -> str:
    try:
        req = urllib.request.Request(GITHUB_API, headers={"User-Agent": "CameVision-Ego-offline"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        zipball = data.get("zipball_url")
        assets = data.get("assets") or []
        for a in assets:
            name = str(a.get("name") or "").lower()
            if name.endswith(".zip") and a.get("browser_download_url"):
                print(f"release {data.get('tag_name')}", flush=True)
                return str(a["browser_download_url"])
        if zipball:
            print(f"release {data.get('tag_name')} zipball", flush=True)
            return str(zipball)
    except Exception as e:
        print(f"release API: {e}", flush=True)
    return GITHUB_ZIPBALL


def _extract(zip_path: Path, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest)
    print(f"extracted {zip_path.name} -> {dest}", flush=True)
    return dest


def _apply_tree(extracted: Path) -> None:
    current = update_current()
    if current.exists():
        shutil.rmtree(current)
    current.mkdir(parents=True)
    kg = known_good()
    rel = release_02()
    rel.mkdir(parents=True, exist_ok=True)
    kg.mkdir(parents=True, exist_ok=True)

    files = [p for p in extracted.rglob("*") if p.is_file()]
    overlay_root = None
    for p in files:
        if p.name == "ego_stereo.py" and "overlay" in p.parts:
            overlay_root = p.parent
            break
        if p.name == "ego_stereo.py" and p.parent.name == "tools":
            overlay_root = p.parent

    copied = 0
    for p in files:
        if p.name in IMAGE_NAMES:
            if p.name == "camevision_boot_ego.img":
                target = rel / p.name
            elif p.name == "userdata.img":
                target = ROOT / "restore" / "images" / p.name
                target.parent.mkdir(parents=True, exist_ok=True)
            else:
                target = kg / p.name
            shutil.copy2(p, target)
            shutil.copy2(p, current / p.name)
            print(f"image {p.name}", flush=True)
            copied += 1

    if overlay_root is not None:
        ov_dest = current / "overlay"
        if ov_dest.exists():
            shutil.rmtree(ov_dest)
        shutil.copytree(overlay_root, ov_dest)
        pack_ov = rel / "overlay"
        if pack_ov.exists():
            shutil.rmtree(pack_ov)
        shutil.copytree(overlay_root, pack_ov)
        print(f"overlay {overlay_root}", flush=True)
        copied += 1

    (current / "SOURCE.txt").write_text(str(extracted) + "\n", encoding="utf-8")
    if copied == 0:
        raise SystemExit("zip had no overlay or image files")
    print("update ready", flush=True)


def apply_zip(zip_path: Path) -> int:
    zip_path = Path(zip_path)
    if not zip_path.is_file():
        raise SystemExit(f"missing {zip_path}")
    with tempfile.TemporaryDirectory(prefix="cv-ego-upd-") as tmp:
        extracted = _extract(zip_path, Path(tmp) / "unpacked")
        _apply_tree(extracted)
    return 0


def apply_github() -> int:
    with tempfile.TemporaryDirectory(prefix="cv-ego-gh-") as tmp:
        zpath = Path(tmp) / "update.zip"
        _download(_github_zip_url(), zpath)
        extracted = _extract(zpath, Path(tmp) / "unpacked")
        _apply_tree(extracted)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="CameVision Ego package update")
    p.add_argument("--github", action="store_true")
    p.add_argument("--file", type=Path)
    args = p.parse_args()
    if args.github:
        return apply_github()
    if args.file:
        return apply_zip(args.file)
    raise SystemExit("use --github or --file PATH")


if __name__ == "__main__":
    raise SystemExit(main())
