#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
echo === RCS ===
cat /etc/init.d/rcS
echo === ADB-STOCK HEAD ===
head -30 /etc/init.d/S50usbdevice.adb-stock
grep -n 'start)\|usb_config\|UDC\|idProduct\|product\|device_name' /etc/init.d/S50usbdevice.adb-stock | head -40
echo === BAK STRINGS ===
grep -n 'product\|serial\|device_name\|UDC\|dwc3' /etc/init.d/S50usbdevice.bak-uvc | head -30
""", wait=8))
