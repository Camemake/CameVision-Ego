#!/usr/bin/env python3
import base64
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

S50 = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\live\S50usbdevice.uvc-rk")
overlay = Path(r"C:\Users\stefa\Desktop\CameVision Single\restore\recovery-2-20260821-adb-stream\overlay")
shutil.copy2(S50, overlay / "S50usbdevice.uvc-rk")
b64 = base64.b64encode(S50.read_bytes()).decode("ascii")
print(run(f"""
mount -o remount,rw / 2>/dev/null
echo {b64} | base64 -d > /etc/init.d/S50usbdevice
chmod 755 /etc/init.d/S50usbdevice
grep -n kmpp /etc/init.d/S50usbdevice
echo STATE=$(cat /sys/class/udc/21500000.usb/state) SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
tail -3 /userdata/uvc-h264-pump.log
""", wait=10))
ps = r"""Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_2207' -and $_.Present } | ForEach-Object { '{0}|{1}|{2}|{3}' -f $_.Status, $_.Class, $_.FriendlyName, $_.InstanceId }"""
r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
print("WIN", r.stdout.strip() or "(none)")
