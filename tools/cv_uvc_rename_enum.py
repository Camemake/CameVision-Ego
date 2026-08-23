#!/usr/bin/env python3
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run


def win_all():
    ps = r"""
Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_2207&PID_0016' } | ForEach-Object { '{0}|present={1}|{2}|{3}' -f $_.Status, $_.Present, $_.FriendlyName, $_.InstanceId }
"""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
    )
    return r.stdout.strip()


print("=== before dwc3 ===")
print(
    run(
        r"""
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo EXTCON
cat /sys/class/extcon/extcon0/state
echo DNAME=$(cat /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/device_name)
echo FNAME=$(cat /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/function_name)
echo PROD=$(cat /sys/kernel/config/usb_gadget/rockchip/strings/0x409/product)
""",
        wait=6,
    )
)
print("WIN", win_all() or "(none)")

print("=== one dwc3 rebind ===")
print(
    run(
        r"""
G=/sys/kernel/config/usb_gadget/rockchip
echo none > $G/UDC
sleep 1
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/unbind
sleep 1
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/bind
sleep 1
echo 21500000.usb > $G/UDC
sleep 5
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo DNAME=$(cat $G/functions/uvc.gs1/device_name)
echo FNAME=$(cat $G/functions/uvc.gs1/function_name)
echo PROD=$(cat $G/strings/0x409/product)
dmesg | grep -E 'device reset|uvc_function_set_alt|uvc_function_bind' | tail -8
""",
        wait=16,
    )
)
time.sleep(2)
print("WIN after", win_all() or "(none)")
