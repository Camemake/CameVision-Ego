#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"
cmd = r"""
echo === exp ===
v4l2-ctl -d /dev/v4l-subdev10 -C exposure -C analogue_gain
v4l2-ctl -d /dev/v4l-subdev5 -C exposure -C analogue_gain
echo === 3A ===
ps | grep rkaiq_3A | grep -v grep
echo === hw ===
grep -E 'YNR|ENH|DRC|AWBGAIN|BLS|GAMMA' /proc/rkisp-vir0
echo === regs ===
python3 /tmp/ego_i2c_rd.py | grep -E '3e00|3e01|3e02|3e08|3e09|3282'
"""
r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True, timeout=20)
print(r.stdout)
print(r.stderr)
