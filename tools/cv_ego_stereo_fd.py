#!/usr/bin/env python3
import subprocess
import sys

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def main() -> int:
    s = serial()
    cmd = r"""
echo === ps ===
ps | grep -E 'stereo|v4l2|ffmpeg' | grep -v grep
echo === fifo ===
ls -l /tmp/*.grey /tmp/f.grey /tmp/cam* 2>/dev/null
echo === fd ===
ls -l /proc/3631/fd 2>/dev/null | head -30
echo === threads ===
ls /proc/3631/task 2>/dev/null
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=15)
    sys.stdout.write(r.stdout or "")
    sys.stdout.write(r.stderr or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
