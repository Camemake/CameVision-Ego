#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
killall -9 ffmpeg 2>/dev/null
start-stop-daemon -S -b -q -x /usr/bin/ffmpeg -- -hide_banner -loglevel warning -re -f lavfi -i testsrc2=size=640x360:rate=15 -c:v mjpeg -q:v 7 -pix_fmt yuvj420p -f v4l2 /dev/video28
sleep 1
ps | grep ffmpeg | grep -v grep
echo STATE
cat /sys/class/udc/21500000.usb/state
cat /sys/class/udc/21500000.usb/current_speed
cat /sys/kernel/config/usb_gadget/g1/UDC
cat /sys/kernel/config/usb_gadget/g1/idVendor
cat /sys/kernel/config/usb_gadget/g1/idProduct
"""
print(run(CMD, wait=6))
