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
echo -n product=; cat /sys/kernel/config/usb_gadget/rockchip/strings/0x409/product
echo -n name=; cat /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/device_name
echo header=$(ls /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/streaming/header/h)
echo === LIVE LOG ===
cat /userdata/cv-uvc-live.log
echo === PUMP ===
cat /userdata/uvc-mjpg-pump.log 2>/dev/null | tail -c 500
echo === PROCS ===
ps | grep -E 'uvc-mjpg|v4l2-ctl|rkaiq_3A|adbd' | grep -v grep
""", wait=8))
