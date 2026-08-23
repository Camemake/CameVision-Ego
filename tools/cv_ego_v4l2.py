#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd: str) -> None:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


sh("ls -l /dev/video1 /dev/video12 /dev/video24 /dev/video32; echo ---; cat /sys/class/video4linux/video1/name; cat /sys/class/video4linux/video12/name; cat /sys/class/video4linux/video24/name; cat /sys/class/video4linux/video32/name")
sh("ps | grep -v grep | grep -E 'v4l2|hw_rtsp|rkaiq'")
sh("echo === media1 sensor ===; media-ctl -d /dev/media1 -p 2>/dev/null | grep -nE 'sc233|csi2|dphy|entity|video1|Enabled|SBGGR|fmt:' | head -80")
sh("echo === media2 sensor ===; media-ctl -d /dev/media2 -p 2>/dev/null | grep -nE 'sc233|csi2|dphy|entity|video12|Enabled|SBGGR|fmt:' | head -80")
