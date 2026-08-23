#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd: str) -> str:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")
    return r.stdout


sh(
    "echo === names ===; "
    "for d in /sys/class/video4linux/video*; do "
    "echo $(basename $d) $(cat $d/name 2>/dev/null); "
    "done"
)
sh("echo === media ===; for m in /dev/media*; do echo ---- $m; media-ctl -d $m -p 2>/dev/null | head -20; done")
sh("echo === ps ===; ps | grep -v grep | grep -E 'rkaiq|v4l2-ctl|uvc|hw_rtsp|python'")
