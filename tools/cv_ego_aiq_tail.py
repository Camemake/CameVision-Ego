#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"
cmd = (
    "echo === tail ===; tail -c 4000 /userdata/rkaiq.log; "
    "echo === awb/ae ===; grep -E 'AWB|AE |awb|sysctl_start|3a_status|wait stream' "
    "/userdata/rkaiq.log | tail -30; "
    "echo === 3A running ===; ps | grep rkaiq | grep -v grep"
)
r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
print(r.stdout)
if r.stderr:
    print(r.stderr)
