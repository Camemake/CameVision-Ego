#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run
print(run(r"""
echo -n state=; cat /sys/class/udc/21500000.usb/state
echo -n speed=; cat /sys/class/udc/21500000.usb/current_speed
ps | grep -E 'uvc-mjpg|v4l2-ctl -d /dev/video13|rkaiq_3A' | grep -v grep
echo --- pump ---
tail -c 600 /userdata/uvc-mjpg-pump.log
echo --- dmesg ---
dmesg | grep -iE 'uvc_function|reset UVC' | tail -6
""", wait=6))
