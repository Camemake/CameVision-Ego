#!/usr/bin/env python3
import base64
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

pump = Path(r"C:\Users\stefa\Desktop\CameVision Single\restore\recovery-2-20260821-adb-stream\overlay\camevision-uvc-mjpg.py").read_bytes()
cmd = f"""
echo {base64.b64encode(pump).decode()} | base64 -d > /userdata/camevision-uvc-mjpg.py
chmod 755 /userdata/camevision-uvc-mjpg.py
if [ -f /tmp/uvc-ff.pid ]; then start-stop-daemon -K -p /tmp/uvc-ff.pid 2>/dev/null; fi
if [ -f /tmp/uvc-mjpg.pid ]; then start-stop-daemon -K -p /tmp/uvc-mjpg.pid 2>/dev/null; fi
killall ffmpeg 2>/dev/null
sleep 1
# keep ISP grab
if ! ps | grep -q '[v]4l2-ctl -d /dev/video13'; then
  [ -p /tmp/cam.nv12 ] || mkfifo /tmp/cam.nv12
  v4l2-ctl -d /dev/video13 --set-fmt-video=width=1920,height=1080,pixelformat=NV12
  setsid nohup sh -c 'while true; do v4l2-ctl -d /dev/video13 --stream-mmap=8 --stream-to=/tmp/cam.nv12 --stream-poll >>/userdata/uvc-isp.log 2>&1; sleep 0.3; done' </dev/null >/dev/null 2>&1 &
  echo $! >/tmp/uvc-isp.pid
fi
start-stop-daemon -S -b -q -m -p /tmp/uvc-mjpg.pid -x /usr/bin/python3 -- /userdata/camevision-uvc-mjpg.py
sleep 2
echo === PROCS ===
ps | grep -E 'uvc-mjpg|v4l2-ctl|rkaiq_3A|ffmpeg' | grep -v grep
echo === PUMP ===
cat /userdata/uvc-mjpg-pump.log
echo === UDC ===
echo -n state=; cat /sys/class/udc/21500000.usb/state
echo -n speed=; cat /sys/class/udc/21500000.usb/current_speed
echo header=$(ls /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/streaming/header/h)
"""
print(run(cmd, wait=10))
