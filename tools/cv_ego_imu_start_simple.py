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
echo 0 > /sys/bus/iio/devices/iio:device1/buffer/enable
echo 0 > /sys/bus/iio/devices/iio:device2/buffer/enable
echo 0 > /sys/bus/iio/devices/iio:device3/buffer/enable
echo 0 > /sys/bus/iio/devices/iio:device4/buffer/enable
if [ -f /tmp/ego-imu.pid ]; then kill $(cat /tmp/ego-imu.pid) 2>/dev/null; fi
export TZ=UTC-2
start-stop-daemon -S -b -m -p /tmp/ego-imu.pid -x /usr/bin/python3 -- /userdata/ego_imu_hud.py
sleep 1
echo pid=$(cat /tmp/ego-imu.pid)
ps | grep -E 'ego_imu_hud|rkaiq_3A|ego_mjpeg|ffmpeg' | grep -v grep
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=20)
    sys.stdout.write(r.stdout or "")
    sys.stdout.write(r.stderr or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
