#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
# Free UDC from rockchip gadget
echo none > /sys/kernel/config/usb_gadget/rockchip/UDC
sleep 1
rm -f /sys/kernel/config/usb_gadget/rockchip/configs/b.1/f1

G=/sys/kernel/config/usb_gadget/g1
U=$G/functions/uvc.0
rm -rf $G 2>/dev/null
mkdir -p $G
echo 0x1d6b > $G/idVendor
echo 0x0102 > $G/idProduct
echo 0x0200 > $G/bcdUSB
echo 0x0100 > $G/bcdDevice
echo 0xEF > $G/bDeviceClass
echo 0x02 > $G/bDeviceSubClass
echo 0x01 > $G/bDeviceProtocol
mkdir -p $G/strings/0x409
echo camevision > $G/strings/0x409/serialnumber
echo CameMake > $G/strings/0x409/manufacturer
echo "CameVision UVC" > $G/strings/0x409/product
mkdir -p $G/configs/c.1/strings/0x409
echo uvc > $G/configs/c.1/strings/0x409/configuration
echo 500 > $G/configs/c.1/MaxPower
echo 0x80 > $G/configs/c.1/bmAttributes

mkdir -p $U
echo 1024 > $U/streaming_maxpacket
echo 1 > $U/streaming_interval
echo 0 > $U/streaming_maxburst
echo 0 > $U/streaming_bulk
echo 0 > $U/control/enable_interrupt_ep

mkdir -p $U/control/header/h
ln -s $U/control/header/h $U/control/class/fs/h
ln -s $U/control/header/h $U/control/class/ss/h

mkdir -p $U/streaming/mjpeg/m/360p
echo 640 > $U/streaming/mjpeg/m/360p/wWidth
echo 360 > $U/streaming/mjpeg/m/360p/wHeight
echo 666666 > $U/streaming/mjpeg/m/360p/dwDefaultFrameInterval
echo 460800 > $U/streaming/mjpeg/m/360p/dwMinBitRate
echo 1843200 > $U/streaming/mjpeg/m/360p/dwMaxBitRate
echo 460800 > $U/streaming/mjpeg/m/360p/dwMaxVideoFrameBufferSize
printf '666666\n' > $U/streaming/mjpeg/m/360p/dwFrameInterval

mkdir -p $U/streaming/header/h
ln -s $U/streaming/mjpeg/m $U/streaming/header/h/m
ln -s $U/streaming/header/h $U/streaming/class/fs/h
ln -s $U/streaming/header/h $U/streaming/class/hs/h
ln -s $U/streaming/header/h $U/streaming/class/ss/h

ln -s $U $G/configs/c.1/f1
echo BIND_G1
echo 21500000.usb > $G/UDC
echo UDC
cat $G/UDC
echo STATE
cat /sys/class/udc/21500000.usb/state
echo SPEED
cat /sys/class/udc/21500000.usb/current_speed
echo PID
cat $G/idProduct
"""
print(run(CMD, wait=14))
