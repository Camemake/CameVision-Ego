#!/usr/bin/env python3
"""ACM + UVC composite. ACM already enumerated on this port; UVC rides along."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
echo none > /sys/kernel/config/usb_gadget/g4/UDC
sleep 1
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/unbind
sleep 2
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/bind
sleep 2

G=/sys/kernel/config/usb_gadget/g5
U=$G/functions/uvc.4
A=$G/functions/acm.1
mkdir -p $G
echo 0x2207 > $G/idVendor
echo 0x0010 > $G/idProduct
echo 0x0200 > $G/bcdUSB
echo 0xEF > $G/bDeviceClass
echo 0x02 > $G/bDeviceSubClass
echo 0x01 > $G/bDeviceProtocol
mkdir -p $G/strings/0x409
echo CameVisionMix > $G/strings/0x409/serialnumber
echo CameMake > $G/strings/0x409/manufacturer
echo CameVision > $G/strings/0x409/product
mkdir -p $G/configs/c.1/strings/0x409
echo mix > $G/configs/c.1/strings/0x409/configuration
echo 250 > $G/configs/c.1/MaxPower

mkdir -p $A
mkdir -p $U
echo 1 > $U/streaming_bulk
echo 512 > $U/streaming_maxpacket
echo 1 > $U/streaming_interval
echo 0 > $U/streaming_maxburst
mkdir -p $U/control/header/h
if [ ! -e $U/control/class/fs/h ]; then ln -s $U/control/header/h $U/control/class/fs/h; fi
if [ ! -e $U/control/class/ss/h ]; then ln -s $U/control/header/h $U/control/class/ss/h; fi
mkdir -p $U/streaming/mjpeg/m/360p
echo 640 > $U/streaming/mjpeg/m/360p/wWidth
echo 360 > $U/streaming/mjpeg/m/360p/wHeight
echo 666666 > $U/streaming/mjpeg/m/360p/dwDefaultFrameInterval
echo 460800 > $U/streaming/mjpeg/m/360p/dwMaxVideoFrameBufferSize
printf '666666\n' > $U/streaming/mjpeg/m/360p/dwFrameInterval
mkdir -p $U/streaming/header/h
if [ ! -e $U/streaming/header/h/m ]; then ln -s $U/streaming/mjpeg/m $U/streaming/header/h/m; fi
if [ ! -e $U/streaming/class/fs/h ]; then ln -s $U/streaming/header/h $U/streaming/class/fs/h; fi
if [ ! -e $U/streaming/class/hs/h ]; then ln -s $U/streaming/header/h $U/streaming/class/hs/h; fi
if [ ! -e $U/streaming/class/ss/h ]; then ln -s $U/streaming/header/h $U/streaming/class/ss/h; fi

ln -s $A $G/configs/c.1/f1
ln -s $U $G/configs/c.1/f2
echo WRITE
echo 21500000.usb > $G/UDC
echo UDC=$(cat $G/UDC)
sleep 6
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo FUNC=$(cat /sys/class/udc/21500000.usb/function)
dmesg | grep -v rkisp | grep -v CIF_ISP | tail -15
"""
print(run(CMD, wait=24))
