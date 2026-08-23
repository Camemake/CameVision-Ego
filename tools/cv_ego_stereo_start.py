#!/usr/bin/env python3
"""Push on-board stereo, replace 1920 MJPEG only, then exit.

3A / IMU / USB stay up. Host does not compute depth.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
SRC = Path(r"C:\Users\stefa\Desktop\CameVision Ego\tools\ego_stereo.py")
CAL = Path(r"C:\Users\stefa\Desktop\CameVision Ego\tools\ego_calib.html")
LOGO = Path(r"C:\Users\stefa\Desktop\CameVision Ego\tools\camemake-logo.png")
SO = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\libego_stereo.so")


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def adb(s: str, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run([ADB, "-s", s, *args], capture_output=True, text=True, timeout=timeout)


def main() -> int:
    s = serial()
    print("serial", s, flush=True)
    adb(s, "push", str(SRC), "/userdata/ego_stereo.py", timeout=20)
    adb(s, "push", str(CAL), "/userdata/ego_calib.html", timeout=20)
    if LOGO.exists():
        adb(s, "push", str(LOGO), "/userdata/camemake-logo.png", timeout=20)
    if SO.exists() and SO.stat().st_size > 4000:
        adb(s, "push", str(SO), "/userdata/libego_stereo.so", timeout=20)
        print("pushed native matcher", SO.stat().st_size, "bytes", flush=True)
    else:
        print("no native matcher yet; numpy fallback", flush=True)
    r = adb(
        s,
        "shell",
        "sed -i 's/\\r$//' /userdata/ego_stereo.py /userdata/ego_calib.html; "
        "kill $(cat /tmp/ego-stereo.pid 2>/dev/null) 2>/dev/null; "
        "P=$(ps | grep ego_stereo | grep -v grep | awk '{print $1}'); "
        "[ -n \"$P\" ] && kill $P 2>/dev/null; "
        "P=$(ps | grep v4l2-ctl | grep -v grep | awk '{print $1}'); "
        "[ -n \"$P\" ] && kill $P 2>/dev/null; "
        "killall ffmpeg 2>/dev/null; "
        "sleep 0.4; "
        "export PYTHONPATH=/userdata/pylib; "
        "start-stop-daemon -S -b -m -p /tmp/ego-stereo.pid -x /usr/bin/python3 -- "
        "/userdata/ego_stereo.py; "
        "sleep 2; echo pid=$(cat /tmp/ego-stereo.pid 2>/dev/null); "
        "ps | grep -E 'ego_stereo|rkaiq_3A|ego_imu|ego_mjpeg|ffmpeg' | grep -v grep",
        timeout=25,
    )
    print((r.stdout or "") + (r.stderr or ""), end="")
    adb(s, "forward", "tcp:8081", "tcp:8081")
    adb(s, "forward", "tcp:8083", "tcp:8083")
    print("page http://127.0.0.1:8081/", flush=True)
    print("cal  http://127.0.0.1:8081/cal", flush=True)
    # wait until a jpeg exists
    t0 = time.time()
    while time.time() - t0 < 20:
        chk = adb(s, "shell", "netstat -lnt 2>/dev/null | grep 8081 || ss -lnt | grep 8081", timeout=8)
        if "8081" in (chk.stdout or ""):
            break
        time.sleep(1)
    print("3A and IMU left running. Depth and calibration stay on the board.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
