#!/usr/bin/env python3
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
echo === i2c4 device ===
ls -l /sys/devices/platform/21130000.i2c /sys/bus/platform/devices/21130000.i2c 2>/dev/null
echo === driver ===
ls -l /sys/bus/platform/devices/21130000.i2c/driver 2>/dev/null
echo === platform drivers i2c ===
ls /sys/bus/platform/drivers | grep -i i2c
echo === i2c adapters ===
ls /sys/class/i2c-adapter
echo === i2c4 unbind path ===
readlink -f /sys/class/i2c-adapter/i2c-4/device/driver
echo === gpiochips ===
ls /sys/class/gpio
ls /dev/gpiochip*
which gpioset gpioget i2cget 2>/dev/null
echo === clk enable files ===
ls /sys/kernel/debug/clk/clk_mipi1_out2io
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=20)
    print(r.stdout)
    print(r.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
