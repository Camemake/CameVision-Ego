#!/usr/bin/env python3
"""Start RKAIQ 3A and IMU HUD if they are down. Does not touch stereo or USB."""
from __future__ import annotations

import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def main() -> int:
    s = serial()
    cmd = (
        "export PATH=/oem/usr/bin:/usr/sbin:/sbin:/usr/bin:/bin; "
        "export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib; "
        "ps | grep rkaiq_3A | grep -v grep "
        "|| (setsid /oem/usr/bin/rkaiq_3A_server --silent </dev/null >/userdata/rkaiq.log 2>&1 & echo $! >/userdata/rkaiq.pid); "
        "export TZ=UTC-2; "
        "ps | grep ego_imu_hud | grep -v grep "
        "|| (setsid /usr/bin/python3 /userdata/ego_imu_hud.py </dev/null >/tmp/ego-imu.log 2>&1 & echo $! >/tmp/ego-imu.pid); "
        "sleep 2; "
        "ps | grep -E 'rkaiq_3A|ego_imu|ego_stereo' | grep -v grep"
    )
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=25)
    print((r.stdout or "") + (r.stderr or ""), end="")
    subprocess.run([ADB, "-s", s, "forward", "tcp:8083", "tcp:8083"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
