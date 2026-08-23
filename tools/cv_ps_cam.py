#!/usr/bin/env python3
import subprocess
ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "0558fa189447bc45"
r = subprocess.run(
    [ADB, "-s", S, "shell", "ps | grep -v grep | grep -E 'rkaiq_3A|v4l2-ctl|timeout|isp_grab|hw_rtsp|python3'"],
    capture_output=True,
    text=True,
)
print(r.stdout)
print(r.stderr)
