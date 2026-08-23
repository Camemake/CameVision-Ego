#!/usr/bin/env python3
import subprocess
ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "0558fa189447bc45"

def sh(cmd):
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")
    return r.returncode

sh("killall timeout 2>/dev/null; true")
sh("killall v4l2-ctl 2>/dev/null; true")
# keep 3A; restart one ISP grab for RTSP
sh(
    "export PATH=/oem/usr/bin:/usr/bin:/bin:$PATH; "
    "v4l2-ctl -d /dev/video13 --set-fmt-video=width=1920,height=1200,pixelformat=NV12; "
    "setsid nohup sh -c 'v4l2-ctl -d /dev/video13 --stream-mmap=8 --stream-to=/tmp/cam.nv12 --stream-poll' "
    "</dev/null >/userdata/v4l2-stream.log 2>&1 &"
)
sh("echo v4l=$(ps | grep '[v]4l2-ctl' | wc -l); echo 3A=$(ps | grep '[r]kaiq_3A' | wc -l); echo rtsp=$(ps | grep '[h]w_rtsp' | wc -l); grep sysctl_start /userdata/rkaiq.log | tail -1")
