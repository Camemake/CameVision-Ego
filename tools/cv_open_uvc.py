#!/usr/bin/env python3
"""Open the UVC V4L2 node — f_uvc keeps D+ down until userspace opens it."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
echo STATE0=$(cat /sys/class/udc/21500000.usb/state)
echo FUNC=$(cat /sys/class/udc/21500000.usb/function)
echo G4=$(cat /sys/kernel/config/usb_gadget/g4/UDC)
for n in /sys/class/video4linux/video*; do
  name=$(cat $n/name)
  echo $(basename $n)=$name
done
killall ffmpeg 2>/dev/null
start-stop-daemon -S -b -q -x /userdata/camevision-uvc-pump.sh
# also poke the node in case ffmpeg is slow
( v4l2-ctl -d /dev/video28 --all > /tmp/v28.txt 2>&1 & )
sleep 4
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
ps | grep -E 'ffmpeg|v4l2' | grep -v grep
cat /tmp/camevision-uvc.log
dmesg | grep -E 'dwc3 21500000|uvc:' | tail -8
"""
print(run(CMD, wait=10))
