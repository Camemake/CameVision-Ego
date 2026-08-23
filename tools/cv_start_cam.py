#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run
print(run(r"""
echo === extcon ===
find /sys/class/extcon /sys/devices/platform/21400000.usb2-phy/extcon -type f 2>/dev/null | head -40
for f in $(find /sys/class/extcon /sys/devices/platform/21400000.usb2-phy/extcon -type f 2>/dev/null); do echo -n "$f="; cat $f; echo; done
echo === role ===
find /sys/class/usb_role /sys/devices/platform -name role 2>/dev/null | head
for f in $(find /sys/class/usb_role /sys/devices/platform -name role 2>/dev/null); do echo -n "$f="; cat $f; echo; done
echo === start cam ===
/userdata/camevision-uvc-cam.sh
""", wait=12))
