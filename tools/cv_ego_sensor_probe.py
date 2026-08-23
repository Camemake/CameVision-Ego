#!/usr/bin/env python3
"""Probe Ego sensors on whichever board is on ADB right now."""
from __future__ import annotations

import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB device")


def sh(s: str, cmd: str) -> None:
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True)
    print("===", cmd[:90])
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


def main() -> int:
    s = serial()
    print("serial", s)
    sh(s, "cat /proc/device-tree/model; echo")
    sh(s, "echo === i2c names ===; for d in /sys/bus/i2c/devices/*-00*; do echo $d $(cat $d/name 2>/dev/null); done")
    sh(s, "echo === dmesg sc233 ===; dmesg | grep -iE 'sc233|chip id'")
    sh(s, "echo === i2c3 ===; i2cdetect -y 3")
    sh(s, "echo === i2c4 ===; i2cdetect -y 4")
    sh(s, "echo === spi ===; ls /sys/bus/spi/devices; echo === iio ===; ls /sys/bus/iio/devices 2>/dev/null; cat /sys/bus/iio/devices/iio:device*/name 2>/dev/null")
    sh(s, "echo === dmesg imu ===; dmesg | grep -iE 'lsm6|imu|spi0|spi1' | tail -n 30")
    sh(s, "echo === gpio ldos ===; mount -t debugfs debugfs /sys/kernel/debug 2>/dev/null; cat /sys/kernel/debug/gpio | head -40")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
