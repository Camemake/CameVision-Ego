#!/usr/bin/env python3
import subprocess
import time

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "0558fa189447bc45"


def sh(cmd):
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")
    return r.stdout


# Hard-kill every v4l2-ctl / timeout. Leave 3A and hw_rtsp.
sh(
    "for p in $(ps | grep -E 'v4l2-ctl|timeout' | grep -v grep | awk '{print $1}'); do kill -9 $p; done"
)
time.sleep(1)
print("--- after kill ---")
print(sh("ps | grep -E 'v4l2-ctl|timeout|rkaiq_3A|hw_rtsp' | grep -v grep"))
