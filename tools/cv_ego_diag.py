#!/usr/bin/env python3
"""Extended CameVision Ego board diagnostics over ADB (read-only)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_ego_paths import adb_exe  # noqa: E402

ADB = adb_exe()

CMD = r"""
echo ===== IDENTITY =====
cat /proc/device-tree/model; echo
uname -a
echo -n uptime:; cat /proc/uptime
echo -n serial_cpu:; tr -d '\0' < /proc/device-tree/serial-number 2>/dev/null; echo
echo -n gadget_mfr=; cat /sys/kernel/config/usb_gadget/rockchip/strings/0x409/manufacturer 2>/dev/null; echo
echo -n gadget_prod=; cat /sys/kernel/config/usb_gadget/rockchip/strings/0x409/product 2>/dev/null; echo
echo -n gadget_ser=; cat /sys/kernel/config/usb_gadget/rockchip/strings/0x409/serialnumber 2>/dev/null; echo
echo -n udc=; cat /sys/class/udc/21500000.usb/state 2>/dev/null; echo
echo -n dr_mode=; tr -d '\0' < /proc/device-tree/usb@21500000/dr_mode 2>/dev/null; echo

echo ===== MEM / CPU / THERMAL / NPU =====
free -m 2>/dev/null || cat /proc/meminfo | head -8
nproc
cat /proc/loadavg
cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null
ls /dev/rknpu /dev/mali* /dev/mpp_service 2>/dev/null

echo ===== STORAGE =====
cat /proc/partitions
df -h
ls /sys/class/mmc_host
for h in /sys/class/mmc_host/mmc*; do
  echo HOST $(basename $h)
  cat $h/mmc*/type 2>/dev/null
  cat $h/mmc*/name 2>/dev/null
done
ls /dev/mmcblk1* 2>/dev/null || echo no_mmcblk1

echo ===== WIFI / SDIO =====
ls /sys/bus/sdio/devices 2>/dev/null || echo no_sdio
for d in /sys/bus/sdio/devices/*; do
  [ -e "$d" ] || continue
  echo DEV $(basename $d)
  echo -n vendor=; cat $d/vendor 2>/dev/null; echo
  echo -n device=; cat $d/device 2>/dev/null; echo
done
ls /sys/class/net
ip -4 addr
wpa_cli -i wlan0 status 2>/dev/null | head -20
ls /userdata/camevision-wifi.sh /userdata/wpa_camevision.conf 2>/dev/null

echo ===== I2C =====
for d in /sys/bus/i2c/devices/*-*; do
  [ -f $d/name ] || continue
  echo $(basename $d) $(cat $d/name)
done
for a in 3-0030 4-0030 6-0030 2-0052 0-0027; do
  if [ -d /sys/bus/i2c/devices/$a ]; then
    echo FOUND $a name=$(cat /sys/bus/i2c/devices/$a/name)
  else
    echo MISSING $a
  fi
done

echo ===== SPI / IMU =====
ls /sys/bus/spi/devices 2>/dev/null
for d in /sys/bus/iio/devices/iio:device*; do
  [ -d "$d" ] || continue
  echo -- $(basename $d) name=$(cat $d/name 2>/dev/null)
  for f in in_accel_x_raw in_accel_y_raw in_accel_z_raw in_anglvel_x_raw in_anglvel_y_raw in_anglvel_z_raw; do
    [ -f $d/$f ] && echo $f=$(cat $d/$f)
  done
done

echo ===== VIDEO =====
ls /dev/video* /dev/media* /dev/v4l-subdev* 2>/dev/null
v4l2-ctl -d /dev/video24 --get-fmt-video 2>/dev/null | head -8 || echo no_video24
v4l2-ctl -d /dev/video32 --get-fmt-video 2>/dev/null | head -8 || echo no_video32

echo ===== SERVICES =====
ps | grep -v grep | grep -E 'rkaiq_3A|ego_stereo|camevision|python' || true
netstat -lnt 2>/dev/null || ss -lnt 2>/dev/null
ls -l /userdata/camevision-stereo.sh /etc/init.d/S99ego-stereo 2>/dev/null

echo ===== RTC / POWER =====
date
hwclock -r 2>/dev/null || true
cat /sys/class/rtc/rtc0/name 2>/dev/null
ls /sys/class/power_supply 2>/dev/null || echo no_power_supply

echo ===== DMESG =====
dmesg | grep -iE 'sc233|rkisp|rkcif|lsm6|imu|mmc2|sdio|6621|wlan|usb gadget|CameVision|NACK|timeout' | tail -60
echo ===== DIAG_DONE =====
"""


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB device")


def main() -> int:
    s = serial()
    print("HOST_ADB_SERIAL", s, flush=True)
    r = subprocess.run(
        [ADB, "-s", s, "shell", CMD],
        capture_output=True,
        text=True,
        timeout=120,
    )
    sys.stdout.write(r.stdout or "")
    if r.stderr:
        sys.stderr.write(r.stderr)
    return r.returncode or 0


if __name__ == "__main__":
    raise SystemExit(main())
