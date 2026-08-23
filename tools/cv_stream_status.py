#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run
print(run(r"""
echo -n state=; cat /sys/class/udc/21500000.usb/state
echo -n speed=; cat /sys/class/udc/21500000.usb/current_speed
echo === pump ===
tail -c 400 /userdata/uvc-mjpg-pump.log
echo === isp ===
tail -c 300 /userdata/uvc-isp.log
echo === 3A ===
grep sysctl /userdata/rkaiq.log | tail -6
echo === video13 ===
v4l2-ctl -d /dev/video13 --get-fmt-video
""", wait=8))
