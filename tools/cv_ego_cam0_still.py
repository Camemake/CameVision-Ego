#!/usr/bin/env python3
"""One static raw/NV12 frame from Cam 0 on the live Ego board."""
from __future__ import annotations

import subprocess
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
OUT = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\stills")


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB device")


def sh(s: str, cmd: str, timeout: int = 30) -> str:
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=timeout)
    text = (r.stdout or "") + (r.stderr or "")
    print(text, end="")
    return text


def main() -> int:
    s = serial()
    OUT.mkdir(parents=True, exist_ok=True)
    sh(s, "echo === names ===; for d in /sys/class/video4linux/video*; do echo $(basename $d) $(cat $d/name); done | grep -E 'cif_mipi_id0|rkisp_mainpath'")
    print("--- try CIF cam0 /dev/video1 ---")
    sh(
        s,
        "rm -f /userdata/cam0.raw; "
        "v4l2-ctl -d /dev/video1 --set-fmt-video=width=1920,height=1200,pixelformat=SBGGR10 --get-fmt-video; "
        "timeout -k 2 12 v4l2-ctl -d /dev/video1 --stream-mmap=4 --stream-count=3 --stream-to=/userdata/cam0.raw --stream-poll; "
        "echo exit:$?; ls -l /userdata/cam0.raw",
        timeout=40,
    )
    r = subprocess.run([ADB, "-s", s, "pull", "/userdata/cam0.raw", str(OUT / "cam0.raw")], capture_output=True, text=True)
    print(r.stdout, r.stderr)
    p = OUT / "cam0.raw"
    if p.is_file():
        print(f"saved {p} {p.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
