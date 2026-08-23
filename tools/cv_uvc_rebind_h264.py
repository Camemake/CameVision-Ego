#!/usr/bin/env python3
"""Fully unbind uvc.gs1, set CameVision names, add H264, rebind, start rk_mpi_uvc."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
kill -9 $(ps | grep rk_mpi_uvc | grep -v grep | awk '{print $1}') 2>/dev/null
sleep 1
ps | grep rk_mpi_uvc | grep -v grep && echo STILL_ALIVE || echo MPI_DEAD

G=/sys/kernel/config/usb_gadget/rockchip
U=$G/functions/uvc.gs1
C=$G/configs/b.1
echo none > $G/UDC
sleep 1
rm -f $C/f1
sleep 1
echo UDC_NOW=$(cat $G/UDC)

echo CameMake > $G/strings/0x409/manufacturer
echo "CameVision Single" > $G/strings/0x409/product
echo camevision > $G/strings/0x409/serialnumber
echo "CameVision Single" > $U/device_name
echo "CameVision Single" > $U/function_name
echo NAME=$(cat $U/device_name)

# H264 native 30fps
echo 1920 > $U/streaming/framebased/f1/1920_1200p/wWidth
echo 1200 > $U/streaming/framebased/f1/1920_1200p/wHeight
echo 333333 > $U/streaming/framebased/f1/1920_1200p/dwDefaultFrameInterval
echo 18432000 > $U/streaming/framebased/f1/1920_1200p/dwMinBitRate
echo 18432000 > $U/streaming/framebased/f1/1920_1200p/dwMaxBitRate
printf '333333\n' > $U/streaming/framebased/f1/1920_1200p/dwFrameInterval
printf 'H264\x00\x00\x10\x00\x80\x00\x00\xaa\x00\x38\x9b\x71' > $U/streaming/framebased/f1/guidFormat
echo 1920 > $U/streaming/framebased/f1/1920_1080p/wWidth
echo 1080 > $U/streaming/framebased/f1/1920_1080p/wHeight
echo 333333 > $U/streaming/framebased/f1/1920_1080p/dwDefaultFrameInterval
echo 16588800 > $U/streaming/framebased/f1/1920_1080p/dwMinBitRate
echo 16588800 > $U/streaming/framebased/f1/1920_1080p/dwMaxBitRate
printf '333333\n' > $U/streaming/framebased/f1/1920_1080p/dwFrameInterval
echo 1920 > $U/streaming/mjpeg/m/1920_1200p/wWidth
echo 1200 > $U/streaming/mjpeg/m/1920_1200p/wHeight
echo 333333 > $U/streaming/mjpeg/m/1920_1200p/dwDefaultFrameInterval
printf '333333\n' > $U/streaming/mjpeg/m/1920_1200p/dwFrameInterval
echo H264_W=$(cat $U/streaming/framebased/f1/1920_1200p/wWidth)
echo H264_H=$(cat $U/streaming/framebased/f1/1920_1200p/wHeight)
echo H264_FI=$(cat $U/streaming/framebased/f1/1920_1200p/dwDefaultFrameInterval)

rm -f $U/streaming/header/h/f1 $U/streaming/header/h/m
ln -s $U/streaming/framebased/f1 $U/streaming/header/h/f1
ln -s $U/streaming/mjpeg/m $U/streaming/header/h/m
echo HEADER=$(ls $U/streaming/header/h)

ln -s $U $C/f1
echo 21500000.usb > $G/UDC
echo UDC=$(cat $G/UDC) STATE=$(cat /sys/class/udc/21500000.usb/state)

cp -f /oem/usr/share/rkuvc.ini /tmp/rkuvc.ini
sed -i 's/enable_aiq = 1/enable_aiq = 0/' /tmp/rkuvc.ini
grep -q enable_venc_0 /tmp/rkuvc.ini || sed -i 's/enable_2uvc = 0/enable_2uvc = 0\nenable_venc_0 = 1/' /tmp/rkuvc.ini
export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH
: > /userdata/rk_mpi_uvc.log
/oem/usr/bin/rk_mpi_uvc -c /tmp/rkuvc.ini -a /oem/usr/share/iqfiles -l 2 >/userdata/rk_mpi_uvc.log 2>&1 &
echo $! > /tmp/rk_mpi_uvc.pid
sleep 4
ps | grep rk_mpi_uvc | grep -v grep
echo NAME2=$(cat $U/device_name) PROD=$(cat $G/strings/0x409/product)
grep -E 'Please configure|Setting format|Starting video|uvc open|add uvc|UVC RGB|CameVision|fail|error' /userdata/rk_mpi_uvc.log | tail -20
dmesg | grep -E 'device reset|uvc_function' | tail -6
"""
print(run(CMD, wait=18))
