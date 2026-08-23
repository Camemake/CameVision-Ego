#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
echo === PHY TREE ===
ls /sys/devices/platform/21400000.usb2-phy
find /sys/devices/platform/21400000.usb2-phy -name '*vbus*' -o -name '*otg*' -o -name '*mode*' -o -name '*u2*' 2>/dev/null | head -40
echo === USB3PHY ===
ls /sys/devices/platform/21410000.usb3-phy 2>/dev/null | head
echo === USB_DEVICES ===
cat /sys/kernel/debug/usb/devices 2>/dev/null | head -5
ls /sys/bus/usb/devices 2>/dev/null
echo === BOUNCE PHY ===
echo host > /sys/devices/platform/21400000.usb2-phy/otg_mode
sleep 1
cat /sys/devices/platform/21400000.usb2-phy/otg_mode
echo peripheral > /sys/devices/platform/21400000.usb2-phy/otg_mode
sleep 1
cat /sys/devices/platform/21400000.usb2-phy/otg_mode
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo UDC_G1=$(cat /sys/kernel/config/usb_gadget/g1/UDC)
dmesg | tail -15
"""
print(run(CMD, wait=12))
