#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
echo === GADGET LINK ===
ls -l /sys/class/udc/21500000.usb/gadget
echo === FUNCTION FILE ===
cat /sys/class/udc/21500000.usb/function
echo === GADGET.0 ===
ls -l /sys/devices/platform/21500000.usb/gadget.0
find /sys/devices/platform/21500000.usb/gadget.0 -maxdepth 3 | head -40
echo === CONFIGFS UDC USERS ===
grep -r . /sys/kernel/config/usb_gadget/*/UDC 2>/dev/null
echo === SOFT ===
cat /sys/class/udc/21500000.usb/soft_connect
echo === IS_A ===
cat /sys/class/udc/21500000.usb/is_a_peripheral
cat /sys/class/udc/21500000.usb/is_otg
"""
print(run(CMD, wait=8))
