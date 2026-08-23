#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run("""
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo G1=$(cat /sys/kernel/config/usb_gadget/g1/UDC)
echo VID=$(cat /sys/kernel/config/usb_gadget/g1/idVendor)
echo PID=$(cat /sys/kernel/config/usb_gadget/g1/idProduct)
echo --- control fs ---
ls -l /sys/kernel/config/usb_gadget/g1/functions/uvc.0/control/class/fs
echo --- streaming hs ---
ls -l /sys/kernel/config/usb_gadget/g1/functions/uvc.0/streaming/class/hs
echo --- configs ---
ls -l /sys/kernel/config/usb_gadget/g1/configs/c.1
""", wait=6))
