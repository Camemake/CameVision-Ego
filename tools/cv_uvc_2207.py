#!/usr/bin/env python3
"""Force re-enumerate as Rockchip UVC 2207:0005 (same VID Windows already used for ADB)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
G=/sys/kernel/config/usb_gadget/g1
U=$G/functions/uvc.0
echo DISCONNECT
echo none > $G/UDC
sleep 2
echo 0x2207 > $G/idVendor
echo 0x0005 > $G/idProduct
echo 0x00 > $G/bDeviceClass
echo 0x00 > $G/bDeviceSubClass
echo 0x00 > $G/bDeviceProtocol
echo 0x0200 > $G/bcdUSB
# control HS link if possible
ln -s $U/control/header/h $U/control/class/ss/h 2>/dev/null
echo 0 > $U/streaming_bulk
echo 1024 > $U/streaming_maxpacket
echo RECONNECT
echo 21500000.usb > $G/UDC
sleep 1
echo UDC=$(cat $G/UDC)
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo VID=$(cat $G/idVendor) PID=$(cat $G/idProduct) CLASS=$(cat $G/bDeviceClass)
dmesg | tail -8
"""
print(run(CMD, wait=12))
