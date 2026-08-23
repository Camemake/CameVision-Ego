#!/usr/bin/env python3
"""Probe Ego ISP / RKAIQ nodes over ADB. No STREAMON burst."""
from __future__ import annotations

import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True, check=False)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB device")


def sh(s: str, cmd: str, timeout: int = 25) -> str:
    r = subprocess.run(
        [ADB, "-s", s, "shell", cmd],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    out = (r.stdout or "") + (r.stderr or "")
    print(out, end="" if out.endswith("\n") else "\n")
    return out


def main() -> int:
    s = serial()
    print("serial", s)
    sh(
        s,
        "echo === model ===; cat /proc/device-tree/model; echo; "
        "echo === v4l names ===; "
        "for n in /sys/class/video4linux/video*; do "
        "  echo $(basename $n) $(cat $n/name); "
        "done | grep -iE 'rkisp|stats|params|mainpath|selfpath|cif_mipi_id0'; "
        "echo === iq ===; "
        "ls -l /oem/usr/share/iqfiles/sc233hgs* /userdata/iqfiles/sc233hgs* "
        "/userdata/camevision-aiq.sh /oem/usr/bin/rkaiq_3A_server 2>/dev/null; "
        "echo === ps ===; "
        "ps | grep -v grep | grep -E 'rkaiq|v4l2|ffmpeg|ego_mjpeg|python3' || true; "
        "echo === module names ===; "
        "find /proc/device-tree -name 'rockchip,camera-module-name' 2>/dev/null | while read f; do "
        "  echo $f; cat $f; echo; done; "
        "echo === rkisp proc ===; "
        "for f in /proc/rkisp*; do echo ---- $f ----; sed -n '1,25p' $f; done",
        timeout=20,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
