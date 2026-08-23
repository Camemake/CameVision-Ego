#!/usr/bin/env python3
"""Restore first-working UVC: MJPEG-only header + UVC RGB names + dwc3 + rk_mpi."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
kill -9 $(ps | grep rk_mpi_uvc | grep -v grep | awk '{print $1}') 2>/dev/null
G=/sys/kernel/config/usb_gadget/rockchip
U=$G/functions/uvc.gs1
C=$G/configs/b.1
echo none > $G/UDC
sleep 1
rm -f $C/f1
# drop H264 from advertised formats (keep files, just unlink)
rm -f $U/streaming/class/fs/h $U/streaming/class/hs/h $U/streaming/class/ss/h
rm -f $U/streaming/header/h/f1
ln -s $U/streaming/header/h $U/streaming/class/fs/h
ln -s $U/streaming/header/h $U/streaming/class/hs/h
ln -s $U/streaming/header/h $U/streaming/class/ss/h
echo HEADER=$(ls $U/streaming/header/h)

echo 21500000.usb > /sys/bus/platform/drivers/dwc3/unbind
sleep 2
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/bind
sleep 2
echo CameMake > $G/strings/0x409/manufacturer
echo "CameVision Single" > $G/strings/0x409/product
echo CameVisionUVC > $G/strings/0x409/serialnumber
echo "UVC RGB" > $U/device_name
echo "UVC RGB" > $U/function_name
ln -s $U $C/f1
echo 21500000.usb > $G/UDC
export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH
: > /userdata/rk_mpi_uvc.log
/oem/usr/bin/rk_mpi_uvc -c /tmp/rkuvc.ini -a /oem/usr/share/iqfiles -l 2 >/userdata/rk_mpi_uvc.log 2>&1 &
sleep 8
echo STATE=$(cat /sys/class/udc/21500000.usb/state) SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo DNAME=$(cat $U/device_name) PROD=$(cat $G/strings/0x409/product)
dmesg | grep -E 'device reset|set_alt' | tail -6
"""
print(run(CMD, wait=22))
