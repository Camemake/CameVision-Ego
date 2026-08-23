#!/usr/bin/env python3
"""Bind Rockchip uvc.gs1 like usb_config.sh (no insmod/umount), then rk_mpi_uvc."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
killall ffmpeg 2>/dev/null
killall rk_mpi_uvc 2>/dev/null
killall v4l2-ctl 2>/dev/null
killall hw_rtsp.py 2>/dev/null

for g in /sys/kernel/config/usb_gadget/*/UDC; do echo none > $g 2>/dev/null; done
sleep 1
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/unbind
sleep 2
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/bind
sleep 2

G=/sys/kernel/config/usb_gadget/rockchip
F=$G/functions
C=$G/configs/b.1
U=$F/uvc.gs1

mkdir -p $G/strings/0x409
mkdir -p $C/strings/0x409
echo 0x2207 > $G/idVendor
echo 0x0016 > $G/idProduct
echo 0x0310 > $G/bcdDevice
echo 0x0200 > $G/bcdUSB
echo 239 > $G/bDeviceClass
echo 2 > $G/bDeviceSubClass
echo 1 > $G/bDeviceProtocol
echo CameVisionUVC > $G/strings/0x409/serialnumber
echo rockchip > $G/strings/0x409/manufacturer
echo UVC > $G/strings/0x409/product
echo 500 > $C/MaxPower

# drop leftover function links
rm -f $C/f1 $C/f2 $C/f3 $C/f4 $C/ffs.adb

mkdir -p $U
echo "UVC RGB" > $U/device_name
echo "UVC RGB" > $U/function_name
echo 3072 > $U/streaming_maxpacket
echo 2 > $U/uvc_num_request
echo 0 > $U/streaming_bulk

mkdir -p $U/control/header/h
if [ ! -e $U/control/class/fs/h ]; then ln -s $U/control/header/h $U/control/class/fs/h; fi
if [ ! -e $U/control/class/ss/h ]; then ln -s $U/control/header/h $U/control/class/ss/h; fi

mkdir -p $U/streaming/header/h
mkdir -p $U/streaming/mjpeg/m/1920_1080p
echo 1920 > $U/streaming/mjpeg/m/1920_1080p/wWidth
echo 1080 > $U/streaming/mjpeg/m/1920_1080p/wHeight
echo 333333 > $U/streaming/mjpeg/m/1920_1080p/dwDefaultFrameInterval
echo 41472000 > $U/streaming/mjpeg/m/1920_1080p/dwMinBitRate
echo 41472000 > $U/streaming/mjpeg/m/1920_1080p/dwMaxBitRate
echo 4147200 > $U/streaming/mjpeg/m/1920_1080p/dwMaxVideoFrameBufferSize
printf '333333\n666666\n1000000\n2000000\n' > $U/streaming/mjpeg/m/1920_1080p/dwFrameInterval
mkdir -p $U/streaming/mjpeg/m/1280_720p
echo 1280 > $U/streaming/mjpeg/m/1280_720p/wWidth
echo 720 > $U/streaming/mjpeg/m/1280_720p/wHeight
echo 333333 > $U/streaming/mjpeg/m/1280_720p/dwDefaultFrameInterval
echo 18432000 > $U/streaming/mjpeg/m/1280_720p/dwMinBitRate
echo 18432000 > $U/streaming/mjpeg/m/1280_720p/dwMaxBitRate
echo 1843200 > $U/streaming/mjpeg/m/1280_720p/dwMaxVideoFrameBufferSize
printf '333333\n666666\n1000000\n2000000\n' > $U/streaming/mjpeg/m/1280_720p/dwFrameInterval
if [ ! -e $U/streaming/header/h/m ]; then ln -s $U/streaming/mjpeg/m $U/streaming/header/h/m; fi
if [ ! -e $U/streaming/class/fs/h ]; then ln -s $U/streaming/header/h $U/streaming/class/fs/h; fi
if [ ! -e $U/streaming/class/hs/h ]; then ln -s $U/streaming/header/h $U/streaming/class/hs/h; fi
if [ ! -e $U/streaming/class/ss/h ]; then ln -s $U/streaming/header/h $U/streaming/class/ss/h; fi

ln -s $U $C/f1
echo WRITE
echo 21500000.usb > $G/UDC
echo UDC=$(cat $G/UDC)
echo STATE0=$(cat /sys/class/udc/21500000.usb/state)

cp /oem/usr/share/rkuvc.ini /tmp/rkuvc.ini
export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH
export rt_log_level=3
export rk_mpi_uvc_log_level=2
touch /tmp/uvc_no_timeout
start-stop-daemon -S -b -m -p /tmp/rk_mpi_uvc.pid -x /oem/usr/bin/rk_mpi_uvc -- -c /tmp/rkuvc.ini -a /oem/usr/share/iqfiles -l 2
sleep 8
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo FUNC=$(cat /sys/class/udc/21500000.usb/function)
echo PID=$(cat $G/idProduct)
ps | grep rk_mpi_uvc | grep -v grep
dmesg | grep -E 'uvc_function|dwc3 21500000|failed to start|rk_mpi' | tail -12
"""
print(run(CMD, wait=28))
