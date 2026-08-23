#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"
cmd = (
    "sh /userdata/camevision-aiq.sh; "
    "killall rkaiq_tool_server 2>/dev/null; "
    "python3 /userdata/ego_hdr_on.py; "
    "ps | grep rkaiq_3A | grep -v grep; "
    "grep DRC /proc/rkisp-vir0"
)
r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True, timeout=35)
print(r.stdout)
print(r.stderr)
