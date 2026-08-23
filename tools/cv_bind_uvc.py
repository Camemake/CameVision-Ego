#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
G=/sys/kernel/config/usb_gadget/rockchip
echo 0x0005 > $G/idProduct
echo 0x0200 > $G/bcdUSB
echo PID_NOW
cat $G/idProduct
echo UDC_BEFORE
cat $G/UDC
echo 21500000.usb > $G/UDC
echo BIND_DONE
echo UDC_AFTER
cat $G/UDC
echo STATE
cat /sys/class/udc/21500000.usb/state
echo SPEED
cat /sys/class/udc/21500000.usb/current_speed
echo LINKS
ls -l $G/configs/b.1/
"""
print(run(CMD, wait=8))
