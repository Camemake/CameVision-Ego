#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
echo === UPTIME ===
cat /proc/uptime
echo === S50 ===
ls -l /etc/init.d/S50usbdevice /etc/init.d/S50usbdevice.bak-uvc 2>/dev/null
head -5 /etc/init.d/S50usbdevice
echo === BOOTLOG ===
cat /userdata/cv-uvc-boot.log
echo === MPI LOG ===
tail -40 /userdata/rk_mpi_uvc.log
echo === HEADER ===
ls -l /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/streaming/header/h
ls -l /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/streaming/class/fs
ls -l /sys/kernel/config/usb_gadget/rockchip/configs/b.1
echo === PHY ROLE ===
for p in /sys/firmware/devicetree/base/usb@* /sys/devices/platform/21400000.usb2-phy /sys/class/udc/21500000.usb; do echo -- $p; done
ls /sys/devices/platform/21400000.usb2-phy/ 2>/dev/null
cat /sys/devices/platform/21400000.usb2-phy/otg_mode 2>/dev/null
cat /sys/class/udc/21500000.usb/state
echo === USB ROLE ===
find /sys -name role -o -name mode 2>/dev/null | grep -iE 'usb|dwc|phy' | head -20
echo === ENC ===
ls /oem/usr/bin | grep -iE 'enc|uvc|mpp'
ls /dev/mpp* /dev/mpi* 2>/dev/null
echo === VIDEO28 FMT ===
v4l2-ctl -d /dev/video28 --all 2>/dev/null | head -50
echo === PUMP LOG ===
cat /userdata/uvc-h264-pump.log 2>/dev/null
echo === DMESG USB ===
dmesg | grep -iE 'dwc3 21500000|usb 215|gadget|not attached|failed to start' | tail -20
""", wait=12))
