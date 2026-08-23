#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run("""
U=/sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1
echo === class ===
ls -l $U/control/class/fs $U/control/class/ss $U/streaming/class/fs $U/streaming/class/hs $U/streaming/class/ss
echo === video ===
ls /sys/class/video4linux/video28 2>/dev/null || echo NO_VIDEO28
cat /sys/class/video4linux/video28/name 2>/dev/null
echo === UDC ===
echo UDC=$(cat /sys/kernel/config/usb_gadget/rockchip/UDC)
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo === guid ===
hexdump -C $U/streaming/framebased/f1/guidFormat | head -2
""", wait=6))
