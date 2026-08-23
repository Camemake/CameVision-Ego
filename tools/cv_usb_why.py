#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
echo === DMESG ===
dmesg | tail -30
echo === UDC DIR ===
ls /sys/class/udc/21500000.usb
echo === PLATFORM USB ===
ls -l /sys/devices/platform/21500000.usb
ls /sys/devices/platform/21500000.usb/driver 2>/dev/null
cat /sys/devices/platform/21500000.usb/uevent 2>/dev/null | head
echo === DRIVERS ===
ls /sys/bus/platform/drivers | grep -iE 'dwc|udc|gadget'
echo === UVC TREE ===
U=/sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs6
find $U -maxdepth 4 2>/dev/null | head -80
echo === FRAME ===
cat $U/streaming/mjpeg/m/360p/wWidth 2>/dev/null
cat $U/streaming/mjpeg/m/360p/wHeight 2>/dev/null
ls $U/control/class/fs $U/control/class/hs $U/streaming/class/fs $U/streaming/class/hs 2>/dev/null
echo === DEBUGFS ===
ls /sys/kernel/debug/usb 2>/dev/null
ls /sys/kernel/debug/21500000.usb 2>/dev/null
ls /sys/kernel/debug/usb/21500000.usb 2>/dev/null
"""
print(run(CMD, wait=10))
