#!/usr/bin/env python3
"""Grab one static raw frame from each Ego SC233HGS over ADB."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"
OUT = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\stills")

# CIF id0 is the full raw dump for each MIPI pipeline.
CAMS = (
    ("cam0", "/dev/video1", "rkcif-mipi-lvds"),
    ("cam1", "/dev/video12", "rkcif-mipi-lvds1"),
)


def adb(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run([ADB, "-s", S, *args], capture_output=True, timeout=timeout)


def shell(cmd: str, timeout: int = 60) -> str:
    r = adb("shell", cmd, timeout=timeout)
    return ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print(shell("cat /proc/device-tree/model; echo").strip())

    # Leftover Single pump targets /dev/video13, which is now CIF1 id1.
    print("stopping leftover video13 pump")
    print(shell(
        "killall v4l2-ctl 2>/dev/null; "
        "killall hw_rtsp.py 2>/dev/null; "
        "for p in /proc/[0-9]*; do "
        "cmd=$(tr '\\0' ' ' < $p/cmdline 2>/dev/null); "
        "case $cmd in *video13*) echo KILL $p $cmd; kill -9 ${p#/proc/} ;; esac; "
        "done; "
        "sleep 0.3; "
        "ps | grep -v grep | grep -E 'v4l2-ctl|hw_rtsp|video13' || echo pump_gone"
    ))

    for name, dev, _ in CAMS:
        print(f"\n=== {name} {dev} ===")
        print(shell(f"v4l2-ctl -d {dev} --all 2>&1 | sed -n '1,40p'"))
        print(shell(f"v4l2-ctl -d {dev} --list-formats-ext 2>&1 | head -40"))

    # Prefer packed 10-bit Bayer if the CIF node advertises it.
    for name, dev, _ in CAMS:
        remote = f"/userdata/{name}.raw"
        print(f"\n--- capture {name} ---")
        print(shell(
            f"rm -f {remote}; "
            f"v4l2-ctl -d {dev} --set-fmt-video=width=1920,height=1200,pixelformat=SBGGR10 --get-fmt-video; "
            f"timeout -k 2 12 v4l2-ctl -d {dev} --stream-mmap=4 --stream-count=3 --stream-to={remote} --stream-poll; "
            f"echo exit:$?; ls -l {remote}"
        , timeout=30))

    for name, _, _ in CAMS:
        remote = f"/userdata/{name}.raw"
        local = OUT / f"{name}.raw"
        r = adb("pull", remote, str(local), timeout=60)
        print(((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace"), end="")
        if local.is_file():
            print(f"  {local} {local.stat().st_size} bytes")
        else:
            print(f"  MISSING {local}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
