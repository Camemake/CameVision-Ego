#!/usr/bin/env python3
"""Push and restart only the on-device IMU HUD. Leaves cameras and 8765 alone."""
import subprocess
import sys
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
HUD = Path(r"C:\Users\stefa\Desktop\CameVision Ego\tools\ego_imu_hud.py")


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def main() -> int:
    s = serial()
    subprocess.run([ADB, "-s", s, "push", str(HUD), "/userdata/ego_imu_hud.py"], check=True)
    cmd = (
        "sed -i 's/\\r$//' /userdata/ego_imu_hud.py; "
        "kill $(cat /tmp/ego-imu.pid 2>/dev/null) 2>/dev/null; "
        "sleep 0.2; "
        "for d in /sys/bus/iio/devices/iio:device1 /sys/bus/iio/devices/iio:device2 "
        "/sys/bus/iio/devices/iio:device3 /sys/bus/iio/devices/iio:device4; do "
        "  echo 0 > $d/buffer/enable 2>/dev/null; "
        "done; "
        "for pid in /proc/[0-9]*; do "
        "  cmd=$(tr '\\0' ' ' < $pid/cmdline 2>/dev/null); "
        "  echo \"$cmd\" | grep -q 'iio:device' && kill ${pid#/proc/} 2>/dev/null; "
        "done; "
        "export TZ=UTC-2; "
        "start-stop-daemon -S -b -m -p /tmp/ego-imu.pid -x /usr/bin/python3 -- "
        "/userdata/ego_imu_hud.py; "
        "sleep 2; echo pid=$(cat /tmp/ego-imu.pid); "
        "ps | grep ego_imu_hud | grep -v grep; "
        "echo === cameras ===; "
        "ps | grep -E 'rkaiq_3A|ego_mjpeg|ffmpeg' | grep -v grep | wc -l"
    )
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=25)
    sys.stdout.write(r.stdout or "")
    sys.stdout.write(r.stderr or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
