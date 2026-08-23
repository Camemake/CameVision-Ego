#!/usr/bin/env python3
"""Read-only dump of both Ego LSM6 IMUs. Does not touch cameras or USB."""
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
echo === cameras ===
ps | grep -E 'rkaiq_3A|ego_mjpeg|ffmpeg' | grep -v grep | wc -l
echo === spi / imu dt ===
for n in /proc/device-tree/spi@211e0000 /proc/device-tree/spi@211f0000; do
  echo -n "$(basename $n) status="; cat $n/status; echo
  echo -n "  imu status="; cat $n/imu@0/status 2>/dev/null; echo
  echo -n "  compatible="; cat $n/imu@0/compatible 2>/dev/null | tr '\0' ' '; echo
done
echo === spi masters ===
ls -l /sys/class/spi_master /sys/bus/spi/devices 2>/dev/null
echo === iio ===
ls /sys/bus/iio/devices 2>/dev/null
for d in /sys/bus/iio/devices/iio:device*; do
  [ -d "$d" ] || continue
  n=$(cat $d/name)
  of=$(readlink -f $d/of_node 2>/dev/null)
  dev=$(readlink -f $d/device 2>/dev/null)
  echo "--- $d name=$n"
  echo "    of=$of"
  echo "    device=$dev"
  echo -n "    sampling="; cat $d/sampling_frequency 2>/dev/null; echo
  for f in in_accel_scale in_anglvel_scale in_temp_scale; do
    [ -f $d/$f ] && echo "    $f $(cat $d/$f)"
  done
done
echo === dmesg imu ===
dmesg | grep -iE 'lsm6|spi0|spi1|211e0000|211f0000' | tail -40
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=25)
    sys.stdout.write(r.stdout or "")
    if r.stderr:
        sys.stdout.write(r.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
