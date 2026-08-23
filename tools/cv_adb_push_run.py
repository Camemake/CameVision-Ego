#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"
src = Path(sys.argv[1])
dst = "/tmp/" + src.name
subprocess.run([ADB, "-s", S, "push", str(src), dst], check=True)
r = subprocess.run(
    [ADB, "-s", S, "shell", "sed -i 's/\\r$//' " + dst + "; python3 " + dst],
    capture_output=True,
    text=True,
    timeout=30,
)
print(r.stdout)
print(r.stderr)
sys.exit(r.returncode)
