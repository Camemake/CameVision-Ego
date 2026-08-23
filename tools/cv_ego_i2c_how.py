#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"
cmd = r"""
echo === tools ===
which i2ctransfer i2cget i2cset i2cdump 2>/dev/null
ls /usr/sbin/i2c* /usr/bin/i2c* /oem/usr/bin/i2c* 2>/dev/null
echo === i2c devices ===
ls /sys/bus/i2c/devices/
echo === cam0 sys ===
ls /sys/bus/i2c/devices/3-0030/ 2>/dev/null
echo === cam1 sys ===
ls /sys/bus/i2c/devices/6-0030/ 2>/dev/null
echo === try i2ctransfer ===
i2ctransfer -y 3 w2@0x30 0x32 0x21 r1; echo rc:$?
echo === try i2cget ===
i2cget -y 3 0x30 0x3221 w; echo rc:$?
echo === v4l names ===
for n in /sys/class/video4linux/v4l-subdev*; do echo $(basename $n) $(cat $n/name); done
"""
r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True, timeout=20)
print(r.stdout)
print(r.stderr)
