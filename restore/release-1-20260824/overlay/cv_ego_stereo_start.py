#!/usr/bin/env python3
"""Push on-board stereo, replace 1920 MJPEG only, then exit.

3A / IMU / USB stay up. Host does not compute depth.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
ROOT = Path(r"C:\Users\stefa\Desktop\CameVision Ego")
SRC = ROOT / "tools" / "ego_stereo.py"
SYNC = ROOT / "tools" / "ego_cam_sync.py"
CAL = ROOT / "tools" / "ego_calib.html"
IMU = ROOT / "tools" / "ego_imu_hud.py"
LOGO = ROOT / "tools" / "camemake-logo.png"
SO = ROOT / "build" / "libego_stereo.so"
IQ_NAME = "sc233hgs_efference-sc233hgs_default.json"
IQ_CANDIDATES = (
    ROOT / "tools" / "iqfiles" / "sc233hgs_efference-sc233hgs_flicker50.json",
    ROOT / "build" / "live" / "sc233hgs_efference-sc233hgs_flicker50.json",
    ROOT / "restore" / "release-1-20260824" / "overlay" / "iqfiles" / IQ_NAME,
)


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
    if SYNC.exists():
        adb(s, "push", str(SYNC), "/userdata/ego_cam_sync.py", timeout=20)
    adb(s, "push", str(CAL), "/userdata/ego_calib.html", timeout=20)
    if IMU.exists():
        adb(s, "push", str(IMU), "/userdata/ego_imu_hud.py", timeout=20)
    if LOGO.exists():
        adb(s, "push", str(LOGO), "/userdata/camemake-logo.png", timeout=20)
    if SO.exists() and SO.stat().st_size > 4000:
        adb(s, "push", str(SO), "/userdata/libego_stereo.so", timeout=20)
        print("pushed native matcher", SO.stat().st_size, "bytes", flush=True)
    else:
        print("no native matcher yet; numpy fallback", flush=True)
    iq = next((p for p in IQ_CANDIDATES if p.is_file() and p.stat().st_size > 10000), None)
    if iq is not None:
        adb(s, "shell", "mkdir -p /userdata/iqfiles")
        adb(s, "push", str(iq), "/userdata/iqfiles/" + IQ_NAME, timeout=20)
        print("pushed 50 Hz IQ", iq.stat().st_size, "bytes", flush=True)
    r = adb(
        s,
        "shell",
        "sed -i 's/\\r$//' /userdata/ego_stereo.py /userdata/ego_cam_sync.py /userdata/ego_calib.html /userdata/ego_imu_hud.py; "
        "rm -f /userdata/ego_dense.py /userdata/hitnet.onnx; "
        "if [ -f /userdata/iqfiles/sc233hgs_efference-sc233hgs_default.json ]; then "
        "cp -f /userdata/iqfiles/sc233hgs_efference-sc233hgs_default.json "
        "/oem/usr/share/iqfiles/sc233hgs_efference-sc233hgs_default.json 2>/dev/null || "
        "(mount -o remount,rw /oem && cp -f /userdata/iqfiles/sc233hgs_efference-sc233hgs_default.json "
        "/oem/usr/share/iqfiles/sc233hgs_efference-sc233hgs_default.json); fi; "
        "kill $(cat /tmp/ego-stereo.pid 2>/dev/null) 2>/dev/null; "
        "P=$(ps | grep ego_stereo | grep -v grep | awk '{print $1}'); "
        "[ -n \"$P\" ] && kill $P 2>/dev/null; "
        "P=$(ps | grep v4l2-ctl | grep -v grep | awk '{print $1}'); "
        "[ -n \"$P\" ] && kill $P 2>/dev/null; "
        "killall ffmpeg 2>/dev/null; "
        "export PATH=/oem/usr/bin:/usr/sbin:/sbin:/usr/bin:/bin; "
        "export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib; "
        "ps | grep rkaiq_3A | grep -v grep "
        "|| (setsid /oem/usr/bin/rkaiq_3A_server --silent </dev/null >/userdata/rkaiq.log 2>&1 & echo $! >/userdata/rkaiq.pid); "
        "export TZ=UTC-2; "
        "ps | grep ego_imu_hud | grep -v grep "
        "|| (setsid /usr/bin/python3 /userdata/ego_imu_hud.py </dev/null >/tmp/ego-imu.log 2>&1 & echo $! >/tmp/ego-imu.pid); "
        "sleep 0.4; "
        "export PYTHONPATH=/userdata/pylib; "
        "start-stop-daemon -S -b -m -p /tmp/ego-stereo.pid -x /usr/bin/python3 -- "
        "/userdata/ego_stereo.py; "
        "sleep 2; "
        "ps | grep rkaiq_3A | grep -v grep "
        "|| (setsid /oem/usr/bin/rkaiq_3A_server --silent </dev/null >/userdata/rkaiq.log 2>&1 &); "
        "ps | grep ego_imu_hud | grep -v grep "
        "|| (setsid /usr/bin/python3 /userdata/ego_imu_hud.py </dev/null >/tmp/ego-imu.log 2>&1 &); "
        "sleep 1; echo pid=$(cat /tmp/ego-stereo.pid 2>/dev/null); "
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
    # Grab restart STREAMOFFs, so 3A can be alive with ISP blocks off.
    time.sleep(3)
    r2 = adb(
        s,
        "shell",
        "export PATH=/oem/usr/bin:/usr/sbin:/sbin:/usr/bin:/bin; "
        "export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib; "
        "grep -q 'AWBGAIN    ON' /proc/rkisp-vir0 || ("
        "killall rkaiq_3A_server 2>/dev/null; sleep 0.5; "
        "setsid /oem/usr/bin/rkaiq_3A_server --silent </dev/null >>/userdata/rkaiq.log 2>&1 & "
        "echo $! >/userdata/rkaiq.pid; sleep 4); "
        "grep -E 'AWBGAIN|CCM|GAMMA_OUT' /proc/rkisp-vir0; "
        "ps | grep rkaiq_3A | grep -v grep",
        timeout=20,
    )
    print((r2.stdout or "") + (r2.stderr or ""), end="")
    print("3A and IMU left running. Depth and calibration stay on the board.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
