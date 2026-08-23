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
echo === time ===
date; date +%s.%N; cat /proc/driver/rtc 2>/dev/null | head -5
hwclock -r 2>/dev/null || true
echo === odr ===
for d in /sys/bus/iio/devices/iio:device1 /sys/bus/iio/devices/iio:device2 /sys/bus/iio/devices/iio:device3 /sys/bus/iio/devices/iio:device4; do
  echo -- $(cat $d/name) $d
  cat $d/sampling_frequency_available 2>/dev/null; echo
  ls $d/buffer $d/scan_elements 2>/dev/null | head
done
echo === preview ===
ps | grep -E 'rkaiq_3A|ego_mjpeg|ffmpeg' | grep -v grep
netstat -lnt 2>/dev/null | grep -E '8081|8082|8083|8765' || ss -lnt 2>/dev/null | grep -E '8081|8082|8083'
echo === font ===
ls /oem/usr/share/SourceHanSansEN.ttf /usr/share/fonts 2>/dev/null | head
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=20)
    sys.stdout.write(r.stdout or "")
    sys.stdout.write(r.stderr or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
