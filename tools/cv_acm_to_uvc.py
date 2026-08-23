#!/usr/bin/env python3
"""Drop ACM, hard-reconnect dwc3, bind HS UVC that Windows will not match as ADB."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
echo DROP_ACM
echo none > /sys/kernel/config/usb_gadget/gacm/UDC
echo none > /sys/kernel/config/usb_gadget/g1/UDC 2>/dev/null
rm -f /sys/kernel/config/usb_gadget/gacm/configs/c.1/f1
sleep 1
echo UNBIND_DWC3
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/unbind
sleep 2
echo BIND_DWC3
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/bind
sleep 2
for f in /sys/class/usb_role/*/role; do echo device > $f; done
ls /sys/class/udc
echo STATE_PRE=$(cat /sys/class/udc/21500000.usb/state)

G=/sys/kernel/config/usb_gadget/g1
U=$G/functions/uvc.0
rm -f $G/configs/c.1/f1
# keep existing uvc.0 tree if present
mkdir -p $G
echo 0x1d6b > $G/idVendor
echo 0x0102 > $G/idProduct
echo 0x0200 > $G/bcdUSB
echo 0x0100 > $G/bcdDevice
echo 0xEF > $G/bDeviceClass
echo 0x02 > $G/bDeviceSubClass
echo 0x01 > $G/bDeviceProtocol
mkdir -p $G/strings/0x409
echo CameVisionUVC > $G/strings/0x409/serialnumber
echo CameMake > $G/strings/0x409/manufacturer
echo CameVision > $G/strings/0x409/product
mkdir -p $G/configs/c.1/strings/0x409
echo uvc > $G/configs/c.1/strings/0x409/configuration
echo 500 > $G/configs/c.1/MaxPower
echo 0x80 > $G/configs/c.1/bmAttributes

mkdir -p $U
echo 1024 > $U/streaming_maxpacket 2>/dev/null
echo 1 > $U/streaming_interval 2>/dev/null
echo 0 > $U/streaming_maxburst 2>/dev/null
echo 0 > $U/streaming_bulk 2>/dev/null
echo 0 > $U/control/enable_interrupt_ep 2>/dev/null
mkdir -p $U/control/header/h
mkdir -p $U/control/class/hs
ln -sf $U/control/header/h $U/control/class/fs/h
ln -sf $U/control/header/h $U/control/class/hs/h
ln -sf $U/control/header/h $U/control/class/ss/h
mkdir -p $U/streaming/mjpeg/m/360p
echo 640 > $U/streaming/mjpeg/m/360p/wWidth
echo 360 > $U/streaming/mjpeg/m/360p/wHeight
echo 666666 > $U/streaming/mjpeg/m/360p/dwDefaultFrameInterval
echo 460800 > $U/streaming/mjpeg/m/360p/dwMinBitRate
echo 1843200 > $U/streaming/mjpeg/m/360p/dwMaxBitRate
echo 460800 > $U/streaming/mjpeg/m/360p/dwMaxVideoFrameBufferSize
printf '666666\n' > $U/streaming/mjpeg/m/360p/dwFrameInterval
mkdir -p $U/streaming/header/h
ln -sf $U/streaming/mjpeg/m $U/streaming/header/h/m
ln -sf $U/streaming/header/h $U/streaming/class/fs/h
ln -sf $U/streaming/header/h $U/streaming/class/hs/h
ln -sf $U/streaming/header/h $U/streaming/class/ss/h
ln -sf $U $G/configs/c.1/f1
echo BIND_UVC
echo 21500000.usb > $G/UDC
sleep 2
echo UDC=$(cat $G/UDC)
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo VID=$(cat $G/idVendor) PID=$(cat $G/idProduct)
echo FUNC=$(cat /sys/class/udc/21500000.usb/function)
ls /sys/class/video4linux
cat /sys/class/video4linux/video28/name 2>/dev/null
dmesg | grep -iE 'dwc3|uvc|gadget' | tail -12
"""
print(run(CMD, wait=20))
