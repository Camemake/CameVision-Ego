#!/usr/bin/env python3
"""UVC with SS header links (required) + streaming_bulk=1 (USB2-friendly)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
echo none > /sys/kernel/config/usb_gadget/g3/UDC
echo none > /sys/kernel/config/usb_gadget/g2/UDC
sleep 1
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/unbind
sleep 2
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/bind
sleep 2

G=/sys/kernel/config/usb_gadget/g4
U=$G/functions/uvc.3
mkdir -p $G
echo 0x2207 > $G/idVendor
echo 0x0005 > $G/idProduct
echo 0x0200 > $G/bcdUSB
echo 0x00 > $G/bDeviceClass
echo 0x00 > $G/bDeviceSubClass
echo 0x00 > $G/bDeviceProtocol
mkdir -p $G/strings/0x409
echo CameVisionUVC > $G/strings/0x409/serialnumber
echo CameMake > $G/strings/0x409/manufacturer
echo CameVision > $G/strings/0x409/product
mkdir -p $G/configs/c.1/strings/0x409
echo uvc > $G/configs/c.1/strings/0x409/configuration
echo 250 > $G/configs/c.1/MaxPower

mkdir -p $U
echo 1 > $U/streaming_bulk
echo 512 > $U/streaming_maxpacket
echo 1 > $U/streaming_interval
echo 0 > $U/streaming_maxburst
echo 0 > $U/control/enable_interrupt_ep

mkdir -p $U/control/header/h
if [ ! -e $U/control/class/fs/h ]; then ln -s $U/control/header/h $U/control/class/fs/h; fi
if [ ! -e $U/control/class/ss/h ]; then ln -s $U/control/header/h $U/control/class/ss/h; fi

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
if [ ! -e $U/streaming/class/ss/h ]; then ln -s $U/streaming/header/h $U/streaming/class/ss/h; fi

if [ ! -e $G/configs/c.1/f1 ]; then ln -s $U $G/configs/c.1/f1; fi
echo bulk=$(cat $U/streaming_bulk) mp=$(cat $U/streaming_maxpacket)
echo WRITE
echo 21500000.usb > $G/UDC
echo UDC=$(cat $G/UDC)
sleep 8
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo FUNC=$(cat /sys/class/udc/21500000.usb/function)
dmesg | grep -E 'uvc_function|dwc3 21500000|failed to start' | tail -10
"""
print(run(CMD, wait=26))
