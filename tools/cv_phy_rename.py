#!/usr/bin/env python3
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(
    run(
        r"""
G=/sys/kernel/config/usb_gadget/rockchip
echo none > $G/UDC
sleep 1
echo host > /sys/devices/platform/21400000.usb2-phy/otg_mode
sleep 1
echo peripheral > /sys/devices/platform/21400000.usb2-phy/otg_mode
sleep 1
echo 21500000.usb > $G/UDC
sleep 5
echo PHY=$(cat /sys/devices/platform/21400000.usb2-phy/otg_mode)
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo DNAME=$(cat $G/functions/uvc.gs1/device_name)
echo FNAME=$(cat $G/functions/uvc.gs1/function_name)
echo SN=$(cat $G/strings/0x409/serialnumber)
dmesg | grep -E 'device reset|uvc_function_set_alt' | tail -4
""",
        wait=16,
    )
)
time.sleep(2)
ps = r"""Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_2207' -and $_.Present } | ForEach-Object { '{0}|{1}|{2}' -f $_.Status, $_.FriendlyName, $_.InstanceId }"""
r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
print("WIN", r.stdout.strip() or "(none)")
