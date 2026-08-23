#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run
print(run(r"""
echo -n uptime=; cat /proc/uptime
echo -n state=; cat /sys/class/udc/21500000.usb/state
echo -n speed=; cat /sys/class/udc/21500000.usb/current_speed
echo -n product=; cat /sys/kernel/config/usb_gadget/rockchip/strings/0x409/product 2>/dev/null
echo -n name=; cat /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/device_name 2>/dev/null
echo === boot log ===
cat /userdata/cv-uvc-boot.log 2>/dev/null
echo === s50 head ===
head -5 /etc/init.d/S50usbdevice
echo === procs ===
ps | grep -E 'uvc-mjpg|v4l2-ctl|rkaiq|adbd|telnetd' | grep -v grep
echo === extcon ===
cat /sys/devices/platform/21400000.usb2-phy/extcon/extcon0/state
""", wait=6))
