#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"
cmd = (
    "strings /oem/usr/bin/rkaiq_3A_server | grep -E 'ae_strategy_|ae_measArea_|overExp|backLit' | sort -u | head -40"
)
r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True, timeout=20)
print(r.stdout)
print(r.stderr)
