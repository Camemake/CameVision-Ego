#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run
print(run(r"""
echo === usb ===
echo -n state=; cat /sys/class/udc/21500000.usb/state
echo -n speed=; cat /sys/class/udc/21500000.usb/current_speed
echo -n otg=; cat /sys/devices/platform/21400000.usb2-phy/otg_mode 2>/dev/null
ls /sys/devices/platform/21400000.usb2-phy/ 2>/dev/null
ls /sys/bus/platform/drivers/dwc3/21500000.usb 2>/dev/null | head
echo === oops ===
dmesg | grep -E 'Oops|Internal error|uvc_function|dwc3|not attached|gadget' | tail -n 40
echo === leds ===
cat /sys/class/leds/status:red/brightness /sys/class/leds/status:green/brightness
""", wait=8))
