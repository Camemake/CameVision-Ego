#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run
print(run(r"""
echo === udc attrs ===
ls /sys/class/udc/21500000.usb/
for f in state current_speed maximum_speed is_a_peripheral is_selfpowered soft_connect function; do
  [ -e /sys/class/udc/21500000.usb/$f ] || continue
  echo -n "$f="; cat /sys/class/udc/21500000.usb/$f; echo
done
if [ -e /sys/class/udc/21500000.usb/soft_connect ]; then
  echo connect > /sys/class/udc/21500000.usb/soft_connect
  sleep 2
  echo -n after_soft=; cat /sys/class/udc/21500000.usb/state
fi
""", wait=6))
