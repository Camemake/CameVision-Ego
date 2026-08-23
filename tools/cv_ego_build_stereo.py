#!/usr/bin/env python3
"""Cross-compile tools/stereo_native.c to an aarch64 libego_stereo.so via Zig."""
from __future__ import annotations

import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego")
SRC = ROOT / "tools" / "stereo_native.c"
OUT = ROOT / "build" / "libego_stereo.so"
ZIG_DIR = ROOT / "build" / "zig"
ZIG_URLS = [
    "https://ziglang.org/download/0.14.1/zig-windows-x86_64-0.14.1.zip",
    "https://ziglang.org/download/0.13.0/zig-windows-x86_64-0.13.0.zip",
]


def find_zig() -> Path | None:
    for p in ZIG_DIR.rglob("zig.exe"):
        return p
    return None


def ensure_zig() -> Path:
    z = find_zig()
    if z:
        return z
    ZIG_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = ZIG_DIR / "zig.zip"
    last_err = None
    for url in ZIG_URLS:
        print("download", url, flush=True)
        try:
            urllib.request.urlretrieve(url, zip_path)
            last_err = None
            break
        except Exception as exc:
            last_err = exc
            print("fail", exc, flush=True)
    if last_err and not zip_path.exists():
        raise SystemExit(f"zig download failed: {last_err}")
    print("extract zig", flush=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(ZIG_DIR)
    z = find_zig()
    if not z:
        raise SystemExit("zig.exe missing after extract")
    return z


def main() -> int:
    zig = ensure_zig()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(zig),
        "cc",
        "-target",
        "aarch64-linux-gnu",
        "-O3",
        "-shared",
        "-fPIC",
        "-s",
        str(SRC),
        "-o",
        str(OUT),
    ]
    print(" ".join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=str(ROOT))
    if r.returncode != 0:
        return r.returncode
    print("wrote", OUT, "bytes", OUT.stat().st_size, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
