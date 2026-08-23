#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
echo === USB_ROLE ===
ls -l /sys/class/usb_role 2>/dev/null
for f in /sys/class/usb_role/*/role; do
  echo BEFORE $f=$(cat $f)
  echo device > $f
  echo AFTER $f=$(cat $f)
done
echo === DWC3 SYS ===
ls /sys/devices/platform/21500000.usb
cat /sys/devices/platform/21500000.usb/mode 2>/dev/null
find /sys/devices/platform/21500000.usb -name role -o -name mode -o -name 'usb_role*' 2>/dev/null | head
echo === STATE ===
echo UDC=$(cat /sys/kernel/config/usb_gadget/gacm/UDC)
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo MAX=$(cat /sys/class/udc/21500000.usb/maximum_speed)
echo FUNC=$(cat /sys/class/udc/21500000.usb/function)
echo === EXTCON ===
cat /sys/class/extcon/extcon0/state
echo === CABLES ===
for i in 0 1 2 3 4 5 6; do
  n=/sys/class/extcon/extcon0/cable.$i/name
  s=/sys/class/extcon/extcon0/cable.$i/state
  [ -e "$n" ] && echo $i $(cat $n)=$(cat $s)
done
dmesg | grep -iE 'dwc3|role|gadget|acm' | tail -25
"""
print(run(CMD, wait=8))
