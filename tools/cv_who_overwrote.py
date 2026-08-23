#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
echo === INIT ===
ls -l /etc/init.d
echo === USB SCRIPTS ===
grep -l UDC /etc/init.d/* /userdata/*.sh /oem/usr/bin/*.sh /usr/bin/*.sh 2>/dev/null
echo === CAMEVISIONUVC HITS ===
grep -r CameVisionUVC /etc /userdata /oem/usr/bin /usr 2>/dev/null | head
echo === USB_CONFIG ===
ls -l /oem/usr/bin/usb_config.sh /usr/bin/usb_config.sh /tmp/.usb_config 2>/dev/null
head -5 /oem/usr/bin/usb_config.sh 2>/dev/null
cat /tmp/.usb_config 2>/dev/null
echo === RKLUNCH ===
ps | grep -iE 'RkLunch|usb_config|S50' | grep -v grep
ls /oem/usr/bin/RkLunch* 2>/dev/null
echo === INITTAB ===
cat /etc/inittab 2>/dev/null
ls /etc/init.d/S[0-9]*
echo === USERDATA S50 ===
ls -l /userdata/S50* /userdata/*.sh 2>/dev/null
echo === MFG ===
cat /sys/kernel/config/usb_gadget/rockchip/strings/0x409/manufacturer
echo === DMESG DWC3 ===
dmesg | grep -iE 'dwc3|gadget|uvc_function|21500000' | grep -v rkisp | tail -40
""", wait=12))
