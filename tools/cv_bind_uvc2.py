#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
G=/sys/kernel/config/usb_gadget/rockchip
U=$G/functions/uvc.gs6
echo UNBIND_ACM
echo none > $G/UDC
sleep 1
rm -f $G/configs/b.1/f1
echo 0x00 > $G/bDeviceClass
echo 0x00 > $G/bDeviceSubClass
echo 0x00 > $G/bDeviceProtocol
echo 0x0005 > $G/idProduct
echo 0x0200 > $G/bcdUSB
ln -sf $U $G/configs/b.1/f1
echo LINKED
ls -l $G/configs/b.1/
echo BIND_UVC
echo 21500000.usb > $G/UDC
echo UDC
cat $G/UDC
echo STATE
cat /sys/class/udc/21500000.usb/state
echo SPEED
cat /sys/class/udc/21500000.usb/current_speed
echo SOFT
echo 1 > /sys/class/udc/21500000.usb/soft_connect
echo SOFT_RC
cat /sys/class/udc/21500000.usb/state
"""
print(run(CMD, wait=12))
