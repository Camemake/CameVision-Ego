#!/usr/bin/env python3
"""function_name must stay 'UVC RGB' for rk_mpi_uvc to pull D+ up.
USB product + device_name are CameVision Single (what Windows shows)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
kill -9 $(ps | grep rk_mpi_uvc | grep -v grep | awk '{print $1}') 2>/dev/null
killall -9 ffmpeg 2>/dev/null
G=/sys/kernel/config/usb_gadget/rockchip
U=$G/functions/uvc.gs1
C=$G/configs/b.1
echo none > $G/UDC
sleep 1
rm -f $C/f1
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/unbind
sleep 2
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/bind
sleep 2

echo CameMake > $G/strings/0x409/manufacturer
echo "CameVision Single" > $G/strings/0x409/product
echo camevision > $G/strings/0x409/serialnumber
echo "CameVision Single" > $U/device_name
echo "UVC RGB" > $U/function_name
ln -s $U $C/f1
echo 21500000.usb > $G/UDC
export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH
: > /userdata/rk_mpi_uvc.log
/oem/usr/bin/rk_mpi_uvc -c /tmp/rkuvc.ini -a /oem/usr/share/iqfiles -l 2 >/userdata/rk_mpi_uvc.log 2>&1 &
echo $! > /tmp/rk_mpi_uvc.pid
sleep 8
echo NAME=$(cat $U/device_name) FN=$(cat $U/function_name) PROD=$(cat $G/strings/0x409/product)
echo STATE=$(cat /sys/class/udc/21500000.usb/state) SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo HEADER=$(ls $U/streaming/header/h)
echo H264=$(cat $U/streaming/framebased/f1/1920_1200p/wWidth)x$(cat $U/streaming/framebased/f1/1920_1200p/wHeight)@$(cat $U/streaming/framebased/f1/1920_1200p/dwDefaultFrameInterval)
grep -E 'Please configure|add uvc|rgb_cnt|uvc open|num_formats|Starting' /userdata/rk_mpi_uvc.log | tail -10
dmesg | grep -E 'device reset|set_alt' | tail -6
"""
print(run(CMD, wait=22))
