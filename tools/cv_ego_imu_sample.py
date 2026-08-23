#!/usr/bin/env python3
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
    cmd = r"""
for d in /sys/bus/iio/devices/iio:device*; do
  n=$(cat $d/name)
  echo === $d $n ===
  for f in in_accel_x_raw in_accel_y_raw in_accel_z_raw in_anglvel_x_raw in_anglvel_y_raw in_anglvel_z_raw in_temp_raw; do
    if [ -f $d/$f ]; then echo $f $(cat $d/$f); fi
  done
done
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=20)
    print(r.stdout)
    print(r.stderr)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
