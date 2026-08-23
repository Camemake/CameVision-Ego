#!/usr/bin/env python3
"""Install the working Rockchip UVC S50 onto the live board over telnet."""
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

src = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\live\S50usbdevice.uvc-rk")
b64 = base64.b64encode(src.read_bytes()).decode("ascii")
# busybox base64 -d
cmd = f"""
mount -o remount,rw / 2>/dev/null
cp -f /etc/init.d/S50usbdevice /etc/init.d/S50usbdevice.bak-uvc
echo {b64} | base64 -d > /etc/init.d/S50usbdevice
chmod 755 /etc/init.d/S50usbdevice
wc -c /etc/init.d/S50usbdevice
head -3 /etc/init.d/S50usbdevice
"""
print(run(cmd, wait=8))
