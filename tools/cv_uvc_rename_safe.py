#!/usr/bin/env python3
"""Set CameVision Single names + new serial so Windows drops the UVC RGB cache.
No dwc3 unbind. No reboot.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run


def win_uvc():
    ps = r"""Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_2207&PID_0016' -and $_.Present } | ForEach-Object { '{0}|{1}|{2}' -f $_.Status, $_.FriendlyName, $_.InstanceId }"""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
    )
    return r.stdout.strip()


print(
    run(
        r"""
echo BEFORE
G=/sys/kernel/config/usb_gadget/rockchip
U=$G/functions/uvc.gs1
C=$G/configs/b.1
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo DNAME=$(cat $U/device_name)
echo FNAME=$(cat $U/function_name)
echo PROD=$(cat $G/strings/0x409/product)
echo SN=$(cat $G/strings/0x409/serialnumber)

echo none > $G/UDC
sleep 1
rm -f $C/f1 $C/f2 $C/f3 $C/f4
sleep 1
echo CameMake > $G/strings/0x409/manufacturer
echo "CameVision Single" > $G/strings/0x409/product
echo CVSingle > $G/strings/0x409/serialnumber
echo "CameVision Single" > $U/device_name
echo "CameVision Single" > $U/function_name
ln -s $U $C/f1
echo 21500000.usb > $G/UDC
sleep 5
echo AFTER
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo DNAME=$(cat $U/device_name)
echo FNAME=$(cat $U/function_name)
echo PROD=$(cat $G/strings/0x409/product)
echo SN=$(cat $G/strings/0x409/serialnumber)
dmesg | grep -E 'device reset|uvc_function_set_alt' | tail -5
""",
        wait=16,
    )
)
print("WIN", win_uvc() or "(none)")
