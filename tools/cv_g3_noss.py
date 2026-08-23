#!/usr/bin/env python3
"""HS-only UVC: no SuperSpeed class links. ACM proved USB2; SS links may block chirp."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
echo NONE
echo none > /sys/kernel/config/usb_gadget/g2/UDC
echo none > /sys/kernel/config/usb_gadget/g1/UDC
sleep 1
echo UNBIND
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/unbind
sleep 2
echo BIND
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/bind
sleep 2

G=/sys/kernel/config/usb_gadget/g3
U=$G/functions/uvc.2
mkdir -p $G
echo 0x1d6b > $G/idVendor
echo 0x0102 > $G/idProduct
echo 0x0200 > $G/bcdUSB
echo 0xEF > $G/bDeviceClass
echo 0x02 > $G/bDeviceSubClass
echo 0x01 > $G/bDeviceProtocol
mkdir -p $G/strings/0x409
echo CameVisionUVC > $G/strings/0x409/serialnumber
echo CameMake > $G/strings/0x409/manufacturer
echo CameVision > $G/strings/0x409/product
mkdir -p $G/configs/c.1/strings/0x409
echo uvc > $G/configs/c.1/strings/0x409/configuration
echo 250 > $G/configs/c.1/MaxPower

mkdir -p $U
echo 512 > $U/streaming_maxpacket
echo 1 > $U/streaming_interval
echo 0 > $U/streaming_maxburst
echo 0 > $U/streaming_bulk
echo 0 > $U/control/enable_interrupt_ep

mkdir -p $U/control/header/h
if [ ! -e $U/control/class/fs/h ]; then ln -s $U/control/header/h $U/control/class/fs/h; fi
# deliberately no control/class/ss

mkdir -p $U/streaming/mjpeg/m/360p
echo 640 > $U/streaming/mjpeg/m/360p/wWidth
echo 360 > $U/streaming/mjpeg/m/360p/wHeight
echo 666666 > $U/streaming/mjpeg/m/360p/dwDefaultFrameInterval
echo 460800 > $U/streaming/mjpeg/m/360p/dwMinBitRate
echo 1843200 > $U/streaming/mjpeg/m/360p/dwMaxBitRate
echo 460800 > $U/streaming/mjpeg/m/360p/dwMaxVideoFrameBufferSize
printf '666666\n' > $U/streaming/mjpeg/m/360p/dwFrameInterval

mkdir -p $U/streaming/header/h
if [ ! -e $U/streaming/header/h/m ]; then ln -s $U/streaming/mjpeg/m $U/streaming/header/h/m; fi
if [ ! -e $U/streaming/class/fs/h ]; then ln -s $U/streaming/header/h $U/streaming/class/fs/h; fi
if [ ! -e $U/streaming/class/hs/h ]; then ln -s $U/streaming/header/h $U/streaming/class/hs/h; fi
# deliberately no streaming/class/ss

if [ ! -e $G/configs/c.1/f1 ]; then ln -s $U $G/configs/c.1/f1; fi
echo SS_SKIPPED
ls $U/control/class $U/streaming/class
echo WRITE
echo 21500000.usb > $G/UDC
echo UDC_RC=$?
echo UDC=$(cat $G/UDC)
echo STATE0=$(cat /sys/class/udc/21500000.usb/state)
# open gadget node so f_uvc can finish connect
start-stop-daemon -S -b -q -x /userdata/camevision-uvc-pump.sh
sleep 6
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
ps | grep ffmpeg | grep -v grep
cat /tmp/camevision-uvc.log 2>/dev/null
dmesg | grep -E 'uvc_function|dwc3 21500000' | tail -8
"""
print(run(CMD, wait=24))
