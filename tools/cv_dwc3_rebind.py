#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
G=/sys/kernel/config/usb_gadget/rockchip
U=$G/functions/uvc.gs6
# Complete FS/HS/SS header links (kernel.org gadget_uvc.rst)
ln -sf $U/control/header/h $U/control/class/fs/h
ln -sf $U/control/header/h $U/control/class/ss/h 2>/dev/null
mkdir -p $U/control/class/hs
ln -sf $U/control/header/h $U/control/class/hs/h 2>/dev/null
ln -sf $U/streaming/header/h $U/streaming/class/fs/h
ln -sf $U/streaming/header/h $U/streaming/class/hs/h
ln -sf $U/streaming/header/h $U/streaming/class/ss/h
echo 0 > $U/streaming_bulk
echo 1024 > $U/streaming_maxpacket
echo 0 > $U/control/enable_interrupt_ep
echo 0x0005 > $G/idProduct
echo LINKS_OK
ls $U/control/class/fs $U/control/class/ss $U/streaming/class/ss
echo UNBIND_DWC3
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/unbind
sleep 2
echo BIND_DWC3
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/bind
sleep 2
ls /sys/class/udc
echo WRITE_UDC
echo 21500000.usb > $G/UDC
echo RC_UDC
cat $G/UDC
echo STATE
cat /sys/class/udc/21500000.usb/state 2>/dev/null
echo SPEED
cat /sys/class/udc/21500000.usb/current_speed 2>/dev/null
"""
print(run(CMD, wait=16))
