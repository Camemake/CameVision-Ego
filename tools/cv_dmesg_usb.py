#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run("""
echo === dmesg no isp ===
dmesg | grep -v rkisp | grep -v CIF_ISP | grep -v vpss | tail -40
echo === g4 ===
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo is_selfpowered=$(cat /sys/class/udc/21500000.usb/is_selfpowered 2>/dev/null)
ls /sys/class/udc/21500000.usb
""", wait=8))
