#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
G=/sys/kernel/config/usb_gadget/rockchip
echo TEARDOWN
echo none > $G/UDC
sleep 1
rm -f $G/configs/b.1/f1 $G/configs/b.1/f2 $G/configs/b.1/f3
echo AFTER_RM
ls -l $G/configs/b.1/
echo ACM
mkdir -p $G/functions/acm.gs6
ln -sf $G/functions/acm.gs6 $G/configs/b.1/f1
echo 0x2207 > $G/idVendor
echo 0x0006 > $G/idProduct
echo 0x0200 > $G/bcdUSB
echo 0x02 > $G/bDeviceClass
echo BIND_ACM
echo 21500000.usb > $G/UDC
echo UDC
cat $G/UDC
echo STATE
cat /sys/class/udc/21500000.usb/state
echo SPEED
cat /sys/class/udc/21500000.usb/current_speed
"""
print(run(CMD, wait=12))
