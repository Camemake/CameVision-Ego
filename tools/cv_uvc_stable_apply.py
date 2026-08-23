#!/usr/bin/env python3
"""Live-apply one MJPEG RKISP UVC stream. No dwc3 unbind."""
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

ROOT = Path(r"C:\Users\stefa\Desktop\CameVision Single")
OVERLAY = ROOT / r"restore\recovery-2-20260821-adb-stream\overlay"
LIVE = ROOT / r"build\live"

pump = (OVERLAY / "camevision-uvc-mjpg.py").read_bytes()
start = (OVERLAY / "camevision-uvc-start.sh").read_bytes()
s50 = (LIVE / "S50usbdevice.uvc-rk").read_bytes()

# Keep telnet command small enough: push scripts via base64 (these are small).
cmd = f"""
mount -o remount,rw / 2>/dev/null
echo {base64.b64encode(pump).decode()} | base64 -d > /userdata/camevision-uvc-mjpg.py
echo {base64.b64encode(start).decode()} | base64 -d > /userdata/camevision-uvc-start.sh
echo {base64.b64encode(s50).decode()} | base64 -d > /etc/init.d/S50usbdevice
chmod 755 /userdata/camevision-uvc-mjpg.py /userdata/camevision-uvc-start.sh /etc/init.d/S50usbdevice
/userdata/camevision-uvc-start.sh
sleep 3
echo === AFTER ===
echo -n state=; cat /sys/class/udc/21500000.usb/state
echo -n speed=; cat /sys/class/udc/21500000.usb/current_speed
ps | grep -E 'uvc-mjpg|v4l2-ctl|rkaiq_3A|rk_mpi' | grep -v grep
echo --- pump ---
cat /userdata/uvc-mjpg-pump.log
echo --- isp ---
tail -c 300 /userdata/uvc-isp.log 2>/dev/null
echo --- v28 ---
v4l2-ctl -d /dev/video28 --all 2>&1 | grep -A8 'Format Video Output'
echo --- 3A ---
grep sysctl /userdata/rkaiq.log | tail -6
echo --- dmesg ---
dmesg | grep -iE 'uvc_function|reset UVC' | tail -8
"""

text = run(cmd, wait=22)
out = Path(__file__).with_name("cv_uvc_stable_apply.out.txt")
out.write_text(text, encoding="utf-8", errors="replace")
print(text)
print("wrote", out)
