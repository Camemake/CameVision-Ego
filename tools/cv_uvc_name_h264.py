#!/usr/bin/env python3
"""Rename gadget to CameVision Single and add H.264 1920x1200@30, then restart rk_mpi_uvc."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
# ISP is owned by the RTSP grabber — UVC cannot stream until that dies
killall hw_rtsp.py 2>/dev/null
killall camevision-stream.sh 2>/dev/null
killall v4l2-ctl 2>/dev/null
killall rk_mpi_uvc 2>/dev/null
sleep 1

G=/sys/kernel/config/usb_gadget/rockchip
U=$G/functions/uvc.gs1
C=$G/configs/b.1
echo none > $G/UDC
sleep 1

echo 0x2207 > $G/idVendor
echo 0x0016 > $G/idProduct
echo CameMake > $G/strings/0x409/manufacturer
echo "CameVision Single" > $G/strings/0x409/product
echo camevision > $G/strings/0x409/serialnumber
echo "CameVision Single" > $U/device_name
echo "CameVision Single" > $U/function_name

# H.264 1920x1200 @ 30fps (native SC233HGS)
mkdir -p $U/streaming/framebased/f1/1920_1200p
echo 1920 > $U/streaming/framebased/f1/1920_1200p/wWidth
echo 1200 > $U/streaming/framebased/f1/1920_1200p/wHeight
echo 333333 > $U/streaming/framebased/f1/1920_1200p/dwDefaultFrameInterval
echo 18432000 > $U/streaming/framebased/f1/1920_1200p/dwMinBitRate
echo 18432000 > $U/streaming/framebased/f1/1920_1200p/dwMaxBitRate
printf '333333\n' > $U/streaming/framebased/f1/1920_1200p/dwFrameInterval
printf 'H264\x00\x00\x10\x00\x80\x00\x00\xaa\x00\x38\x9b\x71' > $U/streaming/framebased/f1/guidFormat

# H.264 1920x1080 @ 30fps (16:9 hosts)
mkdir -p $U/streaming/framebased/f1/1920_1080p
echo 1920 > $U/streaming/framebased/f1/1920_1080p/wWidth
echo 1080 > $U/streaming/framebased/f1/1920_1080p/wHeight
echo 333333 > $U/streaming/framebased/f1/1920_1080p/dwDefaultFrameInterval
echo 16588800 > $U/streaming/framebased/f1/1920_1080p/dwMinBitRate
echo 16588800 > $U/streaming/framebased/f1/1920_1080p/dwMaxBitRate
printf '333333\n' > $U/streaming/framebased/f1/1920_1080p/dwFrameInterval

# MJPEG native 30fps as fallback
mkdir -p $U/streaming/mjpeg/m/1920_1200p
echo 1920 > $U/streaming/mjpeg/m/1920_1200p/wWidth
echo 1200 > $U/streaming/mjpeg/m/1920_1200p/wHeight
echo 333333 > $U/streaming/mjpeg/m/1920_1200p/dwDefaultFrameInterval
echo 41472000 > $U/streaming/mjpeg/m/1920_1200p/dwMinBitRate
echo 41472000 > $U/streaming/mjpeg/m/1920_1200p/dwMaxBitRate
echo 3456000 > $U/streaming/mjpeg/m/1920_1200p/dwMaxVideoFrameBufferSize
printf '333333\n' > $U/streaming/mjpeg/m/1920_1200p/dwFrameInterval
echo 333333 > $U/streaming/mjpeg/m/1920_1080p/dwDefaultFrameInterval 2>/dev/null
printf '333333\n' > $U/streaming/mjpeg/m/1920_1080p/dwFrameInterval 2>/dev/null

[ -e $U/streaming/header/h/f1 ] || ln -s $U/streaming/framebased/f1 $U/streaming/header/h/f1

echo WRITE
echo 21500000.usb > $G/UDC
echo UDC=$(cat $G/UDC)
echo NAME=$(cat $U/device_name)
echo PROD=$(cat $G/strings/0x409/product)
echo MFG=$(cat $G/strings/0x409/manufacturer)
ls $U/streaming/header/h
ls $U/streaming/framebased/f1

cp -f /oem/usr/share/rkuvc.ini /tmp/rkuvc.ini
sed -i 's/enable_aiq = 1/enable_aiq = 0/' /tmp/rkuvc.ini
grep -q enable_venc_0 /tmp/rkuvc.ini || sed -i '/enable_aiq = 0/a enable_venc_0 = 1' /tmp/rkuvc.ini
sed -n '1,12p' /tmp/rkuvc.ini

export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH
export rt_log_level=3
export rk_mpi_uvc_log_level=2
touch /tmp/uvc_no_timeout /userdata/uvc-webcam.on
: > /userdata/rk_mpi_uvc.log
/oem/usr/bin/rk_mpi_uvc -c /tmp/rkuvc.ini -a /oem/usr/share/iqfiles -l 2 >/userdata/rk_mpi_uvc.log 2>&1 &
echo $! > /tmp/rk_mpi_uvc.pid
sleep 5
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
ps | grep rk_mpi_uvc | grep -v grep
echo === log ===
tail -40 /userdata/rk_mpi_uvc.log
dmesg | grep -E 'uvc_function_set_alt|device reset' | tail -8
"""
print(run(CMD, wait=22))
