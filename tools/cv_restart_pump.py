#!/usr/bin/env python3
import base64
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

PUMP = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\live\camevision-uvc-h264.py")
overlay = Path(r"C:\Users\stefa\Desktop\CameVision Single\restore\recovery-2-20260821-adb-stream\overlay")
shutil.copy2(PUMP, overlay / "camevision-uvc-h264.py")
b64 = base64.b64encode(PUMP.read_bytes()).decode("ascii")
print(run(f"""
echo {b64} | base64 -d > /userdata/camevision-uvc-h264.py
chmod 755 /userdata/camevision-uvc-h264.py
kill -9 $(cat /tmp/uvc-h264.pid) 2>/dev/null
killall python3 2>/dev/null
sleep 1
: > /userdata/uvc-h264-pump.log
start-stop-daemon -S -b -q -m -p /tmp/uvc-h264.pid -x /usr/bin/python3 -- /userdata/camevision-uvc-h264.py
sleep 8
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo PUMPLOG
cat /userdata/uvc-h264-pump.log
ps | grep camevision-uvc-h264 | grep -v grep
dmesg | grep uvc_function_set_alt | tail -5
""", wait=16))
