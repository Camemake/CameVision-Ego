#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run("""
echo === usb_config ===
ls -l /oem/usr/bin/usb_config.sh /usr/bin/usb_config.sh /etc/init.d/S50usbdevice 2>/dev/null
echo === ini ===
ls -l /usr/share/rkuvc.ini /oem/usr/share/rkuvc.ini /tmp/rkuvc.ini /userdata/rkuvc.ini 2>/dev/null
echo === iq ===
ls /oem/usr/share/iqfiles 2>/dev/null | head
ls /etc/iqfiles 2>/dev/null | head
echo === usb_config.sh ===
sed -n '1,120p' /oem/usr/bin/usb_config.sh 2>/dev/null
echo === ini content ===
sed -n '1,80p' /oem/usr/share/rkuvc.ini 2>/dev/null
sed -n '1,80p' /usr/share/rkuvc.ini 2>/dev/null
""", wait=8))
