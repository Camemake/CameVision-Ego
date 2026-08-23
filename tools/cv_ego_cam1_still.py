#!/usr/bin/env python3
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
    raise SystemExit("no ADB")


def main() -> int:
    s = serial()
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = (
        "rm -f /userdata/cam1.raw; "
        "v4l2-ctl -d /dev/video12 --set-fmt-video=width=1920,height=1200,pixelformat=SBGGR10 --get-fmt-video; "
        "timeout -k 2 12 v4l2-ctl -d /dev/video12 --stream-mmap=4 --stream-count=3 --stream-to=/userdata/cam1.raw --stream-poll; "
        "echo exit:$?; ls -l /userdata/cam1.raw"
    )
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=40)
    print(r.stdout)
    print(r.stderr)
    subprocess.run([ADB, "-s", s, "pull", "/userdata/cam1.raw", str(OUT / "cam1.raw")], check=True)
    raw = OUT / "cam1.raw"
    print(f"saved {raw} {raw.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
