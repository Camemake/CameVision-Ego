#!/usr/bin/env python3
"""device_name=CameVision Single (Windows); function_name=UVC RGB (rk_mpi_uvc matcher)."""
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
sleep 1
echo CameMake > $G/strings/0x409/manufacturer
echo "CameVision Single" > $G/strings/0x409/product
echo camevision > $G/strings/0x409/serialnumber
echo "CameVision Single" > $U/device_name
echo "UVC RGB" > $U/function_name
echo NAME=$(cat $U/device_name) FN=$(cat $U/function_name) PROD=$(cat $G/strings/0x409/product)
echo HEADER=$(ls $U/streaming/header/h)
echo H264=$(cat $U/streaming/framebased/f1/1920_1200p/wWidth)x$(cat $U/streaming/framebased/f1/1920_1200p/wHeight)@$(cat $U/streaming/framebased/f1/1920_1200p/dwDefaultFrameInterval)
ln -s $U $C/f1
echo 21500000.usb > $G/UDC
sleep 2
echo STATE=$(cat /sys/class/udc/21500000.usb/state) SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH
: > /userdata/rk_mpi_uvc.log
/oem/usr/bin/rk_mpi_uvc -c /tmp/rkuvc.ini -a /oem/usr/share/iqfiles -l 2 >/userdata/rk_mpi_uvc.log 2>&1 &
echo $! > /tmp/rk_mpi_uvc.pid
sleep 6
grep -E 'Please configure|add uvc|uvc open|rgb_cnt|ir_cnt|num_formats|Starting video|Setting format|uvc device' /userdata/rk_mpi_uvc.log | tail -20
dmesg | grep -E 'device reset|set_alt' | tail -8
"""
print(run(CMD, wait=18))
