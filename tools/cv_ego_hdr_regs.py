#!/usr/bin/env python3
"""Read SC233HGS Knee HDR registers on both Ego cameras."""
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"
cmd = r"""
read16() {
  bus=$1; reg=$2
  hi=$(printf '%d' $((reg >> 8)))
  lo=$(printf '%d' $((reg & 255)))
  i2ctransfer -y $bus w2@0x30 $hi $lo r1 2>/dev/null
}
echo === buses ===
ls -d /sys/bus/i2c/devices/i2c-* 2>/dev/null
echo === cam0 i2c3 ===
for r in 0x3282 0x3e20 0x3e00 0x3e01 0x3e02 0x3e38 0x3e30 0x3e31 0x3e32 0x3221; do
  echo $r $(read16 3 $r)
done
echo === cam1 i2c6 ===
for r in 0x3282 0x3e20 0x3e00 0x3e01 0x3e02 0x3e38 0x3e30 0x3e31 0x3e32 0x3221; do
  echo $r $(read16 6 $r)
done
echo === v4l hdr ===
v4l2-ctl -d /dev/v4l-subdev0 --list-ctrls 2>/dev/null | head -40
ls /sys/class/video4linux | head
"""
r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True, timeout=25)
print(r.stdout)
if r.stderr:
    print(r.stderr)
