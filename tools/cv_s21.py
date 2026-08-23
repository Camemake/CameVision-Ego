#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
echo === S21 ===
cat /etc/init.d/S21appinit
echo === LAUNCH ===
cat /userdata/camevision-uvc-launch.sh
echo === BAK HEAD ===
head -20 /etc/init.d/S50usbdevice.bak-uvc
echo === USB_CONFIG GREP ===
grep -n 'device_name\|CameVision\|UVC RGB\|UDC\|uvc.gs' /oem/usr/bin/usb_config.sh | head -40
echo === RKIPC USB ===
grep -n 'device_name\|UDC\|uvc' /oem/usr/bin/rkipc_usb_config.sh | head -20
echo === S99 AUTO ===
cat /etc/init.d/S99_auto_reboot
""", wait=10))
