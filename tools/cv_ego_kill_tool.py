#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"
r = subprocess.run(
    [ADB, "-s", S, "shell", "killall rkaiq_tool_server 2>/dev/null; echo killed-tool; ps | grep rkaiq | grep -v grep"],
    capture_output=True,
    text=True,
)
print(r.stdout)
