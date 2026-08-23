#!/usr/bin/env python3
"""Keep /dev/video28 open so f_uvc can activate D+ (ffmpeg was closing on error)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
echo STATE0=$(cat /sys/class/udc/21500000.usb/state)
echo FUNC=$(cat /sys/class/udc/21500000.usb/function)
which uvc-gadget 2>/dev/null
ls /usr/bin/*uvc* /oem/usr/bin/*uvc* /userdata/*uvc* /userdata/*gadget* 2>/dev/null
# hold OUTPUT node open
killall python 2>/dev/null
python -c '
import os, time, fcntl
fd = os.open("/dev/video28", os.O_RDWR)
print("opened", fd)
time.sleep(20)
' > /tmp/hold-uvc.log 2>&1 &
echo HELD_PID=$!
sleep 3
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
cat /tmp/hold-uvc.log
dmesg | grep -E 'dwc3 21500000' | tail -5
"""
print(run(CMD, wait=10))
