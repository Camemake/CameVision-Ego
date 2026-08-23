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
kill $(cat /tmp/ego-stereo.pid 2>/dev/null) 2>/dev/null
P=$(ps | grep -E 'ego_stereo|v4l2-ctl' | grep -v grep | awk '{print $1}')
[ -n "$P" ] && kill $P 2>/dev/null
sleep 0.5
rm -f /tmp/g24.raw /tmp/g32.raw
timeout 4 v4l2-ctl -d /dev/video24 --set-fmt-video=width=320,height=200,pixelformat=GREY --stream-mmap=4 --stream-count=3 --stream-to=/tmp/g24.raw
echo rc24=$?
ls -l /tmp/g24.raw
timeout 4 v4l2-ctl -d /dev/video32 --set-fmt-video=width=320,height=200,pixelformat=GREY --stream-mmap=4 --stream-count=3 --stream-to=/tmp/g32.raw
echo rc32=$?
ls -l /tmp/g32.raw
# restart stereo
start-stop-daemon -S -b -m -p /tmp/ego-stereo.pid -x /usr/bin/python3 -- /userdata/ego_stereo.py
sleep 1
echo pid=$(cat /tmp/ego-stereo.pid)
ps | grep -E 'ego_stereo|rkaiq_3A' | grep -v grep
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=30)
    sys.stdout.write(r.stdout or "")
    sys.stdout.write(r.stderr or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
