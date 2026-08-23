#!/usr/bin/env python3
"""Hard USB disconnect: unbind gadget + dwc3 so D+ actually drops, then bind ACM."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
echo === EXTCON ===
ls /sys/devices/platform/21400000.usb2-phy/extcon
find /sys/devices/platform/21400000.usb2-phy/extcon -type f 2>/dev/null | head -30
for f in /sys/devices/platform/21400000.usb2-phy/extcon/*/state /sys/devices/platform/21400000.usb2-phy/extcon/*/name /sys/class/extcon/*/state; do
  [ -e "$f" ] && echo $f=$(cat $f)
done
echo === DEBUGFS ===
ls /sys/kernel/debug 2>/dev/null | head
ls /sys/kernel/debug/21500000.usb 2>/dev/null
ls /sys/kernel/debug/usb 2>/dev/null
echo === NONE UDC ===
echo none > /sys/kernel/config/usb_gadget/g1/UDC
echo none > /sys/kernel/config/usb_gadget/rockchip/UDC
sleep 1
echo G1=$(cat /sys/kernel/config/usb_gadget/g1/UDC)
echo RK=$(cat /sys/kernel/config/usb_gadget/rockchip/UDC)
echo STATE1=$(cat /sys/class/udc/21500000.usb/state)
echo UNBIND_DWC3
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/unbind
sleep 2
ls /sys/class/udc || echo NO_UDC
echo BIND_DWC3
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/bind
sleep 2
ls /sys/class/udc
echo STATE2=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED2=$(cat /sys/class/udc/21500000.usb/current_speed)
echo === ACM GADGET ===
G=/sys/kernel/config/usb_gadget/gacm
rmdir $G/configs/c.1/strings/0x409 2>/dev/null
rmdir $G/configs/c.1 2>/dev/null
rmdir $G/functions/acm.0 2>/dev/null
rmdir $G/strings/0x409 2>/dev/null
rmdir $G 2>/dev/null
mkdir -p $G
echo 0x2207 > $G/idVendor
echo 0x0006 > $G/idProduct
echo 0x0200 > $G/bcdUSB
echo 0x02 > $G/bDeviceClass
echo 0x02 > $G/bDeviceSubClass
echo 0x01 > $G/bDeviceProtocol
mkdir -p $G/strings/0x409
echo camevision > $G/strings/0x409/serialnumber
echo CameMake > $G/strings/0x409/manufacturer
echo CameVisionACM > $G/strings/0x409/product
mkdir -p $G/configs/c.1/strings/0x409
echo acm > $G/configs/c.1/strings/0x409/configuration
echo 250 > $G/configs/c.1/MaxPower
mkdir -p $G/functions/acm.0
ln -s $G/functions/acm.0 $G/configs/c.1/f1
echo BIND_ACM
echo 21500000.usb > $G/UDC
echo UDC=$(cat $G/UDC)
echo STATE3=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED3=$(cat /sys/class/udc/21500000.usb/current_speed)
dmesg | grep -iE 'dwc3|gadget|acm|udc' | tail -20
"""
print(run(CMD, wait=18))
