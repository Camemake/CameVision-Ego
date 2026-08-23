#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run
print(run(r"""
dmesg | grep -E 'dwc3|gadget|uvc|configfs|UDC' | tail -n 30
echo === bounce UDC ===
G=/sys/kernel/config/usb_gadget/rockchip
echo none > $G/UDC
sleep 2
echo -n state1=; cat /sys/class/udc/21500000.usb/state
echo 21500000.usb > $G/UDC
sleep 2
echo -n UDC=; cat $G/UDC
echo -n state2=; cat /sys/class/udc/21500000.usb/state
echo -n speed=; cat /sys/class/udc/21500000.usb/current_speed
echo -n product=; cat $G/strings/0x409/product
ls -l $G/configs/b.1/
""", wait=10))
