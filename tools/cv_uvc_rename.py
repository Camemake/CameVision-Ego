#!/usr/bin/env python3
"""Rename live UVC gadget to CameVision Single and persist S50."""
import base64
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

ROOT = Path(r"C:\Users\stefa\Desktop\CameVision Single")
S50 = ROOT / "build" / "live" / "S50usbdevice.uvc-rk"
overlay = ROOT / "restore" / "recovery-2-20260821-adb-stream" / "overlay"


def win_uvc():
    ps = r"""Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_2207' -and $_.Present } | ForEach-Object { '{0}|{1}|{2}|{3}' -f $_.Status, $_.Class, $_.FriendlyName, $_.InstanceId }"""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
    )
    return r.stdout.strip()


shutil.copy2(S50, overlay / "S50usbdevice.uvc-rk")
b64 = base64.b64encode(S50.read_bytes()).decode("ascii")

LIVE = r"""
G=/sys/kernel/config/usb_gadget/rockchip
U=$G/functions/uvc.gs1
C=$G/configs/b.1

echo none > $G/UDC
sleep 1

echo CameMake > $G/strings/0x409/manufacturer
echo "CameVision Single" > $G/strings/0x409/product
echo camevision > $G/strings/0x409/serialnumber
echo "CameVision Single" > $C/strings/0x409/configuration
echo "CameVision Single" > $U/device_name
echo "CameVision Single" > $U/function_name

ln -sf $U $C/f1
echo 21500000.usb > $G/UDC
sleep 3
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo MFG=$(cat $G/strings/0x409/manufacturer)
echo PROD=$(cat $G/strings/0x409/product)
echo SN=$(cat $G/strings/0x409/serialnumber)
echo DNAME=$(cat $U/device_name)
echo FNAME=$(cat $U/function_name)
"""

print("=== persist S50 ===")
print(
    run(
        f"mount -o remount,rw / 2>/dev/null; echo {b64} | base64 -d > /etc/init.d/S50usbdevice; chmod 755 /etc/init.d/S50usbdevice; grep -n device_name /etc/init.d/S50usbdevice | head",
        wait=10,
    )
)
print("=== live rename ===")
print(run(LIVE, wait=12))
print("=== WIN ===")
print(win_uvc() or "(none)")
