#!/usr/bin/env python3
import subprocess

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
echo === leftover ===
ps | grep -v grep | grep -E 'v4l2|ffmpeg' || true
echo === cam0 file ===
rm -f /userdata/t0.raw
timeout -k 2 8 v4l2-ctl -d /dev/video1 --stream-mmap=4 --stream-count=1 --stream-to=/userdata/t0.raw --stream-poll
ls -l /userdata/t0.raw
echo === cam1 file ===
rm -f /userdata/t1.raw
timeout -k 2 8 v4l2-ctl -d /dev/video12 --stream-mmap=4 --stream-count=1 --stream-to=/userdata/t1.raw --stream-poll
ls -l /userdata/t1.raw
echo === nc ffmpeg ===
which nc; ffmpeg -version | head -1
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=30)
    print(r.stdout)
    print(r.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
