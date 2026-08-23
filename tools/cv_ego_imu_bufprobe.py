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
echo === odr now ===
for d in /sys/bus/iio/devices/iio:device1 /sys/bus/iio/devices/iio:device2 /sys/bus/iio/devices/iio:device3 /sys/bus/iio/devices/iio:device4; do
  echo $(cat $d/name) odr=$(cat $d/sampling_frequency)
done
echo === scan device2 ===
ls /sys/bus/iio/devices/iio:device2/scan_elements
for f in /sys/bus/iio/devices/iio:device2/scan_elements/*; do echo $(basename $f)=$(cat $f); done
echo === scan device1 ===
ls /sys/bus/iio/devices/iio:device1/scan_elements
for f in /sys/bus/iio/devices/iio:device1/scan_elements/*; do echo $(basename $f)=$(cat $f); done
echo === iio dev ===
ls -l /dev/iio* 2>/dev/null
echo === raw gyro/accel ===
echo g0 $(cat /sys/bus/iio/devices/iio:device1/in_anglvel_x_raw) $(cat /sys/bus/iio/devices/iio:device1/in_anglvel_y_raw) $(cat /sys/bus/iio/devices/iio:device1/in_anglvel_z_raw)
echo a0 $(cat /sys/bus/iio/devices/iio:device2/in_accel_x_raw) $(cat /sys/bus/iio/devices/iio:device2/in_accel_y_raw) $(cat /sys/bus/iio/devices/iio:device2/in_accel_z_raw)
echo === cameras ===
ps | grep -E 'rkaiq_3A|ego_mjpeg|ffmpeg' | grep -v grep | wc -l
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=25)
    sys.stdout.write(r.stdout or "")
    sys.stdout.write(r.stderr or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
