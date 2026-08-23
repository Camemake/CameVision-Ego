#!/usr/bin/env python3
"""Install aarch64 numpy + OpenCV into /userdata/pylib on the board."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
WHEELS = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\wheels")


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def main() -> int:
    s = serial()
    extract = Path(__file__).with_name("cv_ego_extract_pylib.py")
    import zipfile

    wheels = []
    for w in sorted(WHEELS.glob("*.whl")):
        if w.stat().st_size < 8_000_000:
            print("skip small", w.name, w.stat().st_size, flush=True)
            continue
        if not zipfile.is_zipfile(w):
            print("skip incomplete", w.name, w.stat().st_size, flush=True)
            continue
        wheels.append(w)
    if not wheels:
        print("no complete wheels in", WHEELS)
        return 1
    subprocess.run([ADB, "-s", s, "shell", "mkdir -p /userdata/wheels /userdata/pylib"], check=False)
    for w in wheels:
        print("push", w.name, w.stat().st_size, flush=True)
        subprocess.run([ADB, "-s", s, "push", str(w), "/userdata/wheels/" + w.name], check=False)
    subprocess.run([ADB, "-s", s, "push", str(extract), "/userdata/cv_ego_extract_pylib.py"], check=False)
    r = subprocess.run(
        [
            ADB,
            "-s",
            s,
            "shell",
            "sed -i 's/\\r$//' /userdata/cv_ego_extract_pylib.py; "
            "python3 /userdata/cv_ego_extract_pylib.py",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    sys.stdout.write(r.stdout or "")
    sys.stdout.write(r.stderr or "")
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
