#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"
cmd = r"""
echo === cam0 ctrls ===
v4l2-ctl -d /dev/v4l-subdev10 --list-ctrls-menus 2>&1 | head -80
echo === cam1 ctrls ===
v4l2-ctl -d /dev/v4l-subdev5 --list-ctrls-menus 2>&1 | head -80
echo === dbg ===
which v4l2-dbg; v4l2-ctl -d /dev/v4l-subdev10 --help 2>&1 | grep -iE 'reg|dbg|hdr' | head
echo === try get 3221 ===
v4l2-dbg -d /dev/v4l-subdev10 -g 0x3221 2>&1 | head
"""
r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True, timeout=20)
print(r.stdout)
print(r.stderr)
