#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
echo === UDC ===
echo -n state=; cat /sys/class/udc/21500000.usb/state
echo -n speed=; cat /sys/class/udc/21500000.usb/current_speed
echo -n func=; cat /sys/class/udc/21500000.usb/function
echo -n udc=; cat /sys/kernel/config/usb_gadget/rockchip/UDC
echo === PROCS ===
ps | grep -E 'rk_mpi_uvc|uvc-h264|mpi_enc|v4l2-ctl|rkaiq|ffmpeg' | grep -v grep
echo === VIDEO ===
for n in /sys/class/video4linux/video*; do echo $(basename $n) $(cat $n/name); done
echo === V28 ===
v4l2-ctl -d /dev/video28 --all 2>&1 | sed -n '1,80p'
echo === FORMATS OUT ===
v4l2-ctl -d /dev/video28 --list-formats-out 2>&1
echo === HEADER ===
ls -l /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/streaming/header/h
ls /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/streaming/mjpeg/m
ls /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/streaming/framebased/f1
echo === PUMP LOG ===
tail -c 2500 /userdata/uvc-h264-pump.log 2>/dev/null
echo === RKMPI LOG ===
tail -c 1500 /userdata/rk_mpi_uvc.log 2>/dev/null
echo === UVC BOOT ===
tail -c 800 /userdata/cv-uvc-boot.log 2>/dev/null
echo === DMESG USB/UVC ===
dmesg | grep -iE 'uvc|dwc3|gadget|g_uvc|usb .*error|stall' | tail -25
echo === 3A ===
ps | grep rkaiq | grep -v grep
""", wait=12))
