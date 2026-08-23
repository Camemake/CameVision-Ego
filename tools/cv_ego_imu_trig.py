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
echo === triggers ===
ls /sys/bus/iio/devices | grep -i trig
for t in /sys/bus/iio/devices/trigger*; do
  echo $t name=$(cat $t/name)
done
echo === current / buffer ===
for d in /sys/bus/iio/devices/iio:device1 /sys/bus/iio/devices/iio:device2 /sys/bus/iio/devices/iio:device3 /sys/bus/iio/devices/iio:device4; do
  echo -- $(cat $d/name) $d
  echo odr=$(cat $d/sampling_frequency) buf=$(cat $d/buffer/enable) avail=$(cat $d/buffer/data_available)
  echo trig=$(cat $d/trigger/current_trigger 2>/dev/null)
  echo scan=$(cat $d/scan_elements/in_accel_x_en 2>/dev/null)$(cat $d/scan_elements/in_anglvel_x_en 2>/dev/null) ts=$(cat $d/scan_elements/in_timestamp_en)
done
echo === hud log / dmesg ===
dmesg | grep -iE 'iio|lsm6|buffer' | tail -20
echo === cameras ===
ps | grep -E 'rkaiq_3A|ego_mjpeg' | grep -v grep | wc -l
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=20)
    sys.stdout.write(r.stdout or "")
    sys.stdout.write(r.stderr or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
