#!/usr/bin/env python3
import base64
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

ff = Path(r"C:\Users\stefa\Desktop\CameVision Single\restore\recovery-2-20260821-adb-stream\overlay\camevision-uvc-ff.sh").read_bytes()
cmd = f"""
echo {base64.b64encode(ff).decode()} | base64 -d > /userdata/camevision-uvc-ff.sh
chmod 755 /userdata/camevision-uvc-ff.sh
# python ioctl pump cannot STREAMON until host opens (ENODEV). Use ffmpeg instead.
if [ -f /tmp/uvc-mjpg.pid ]; then start-stop-daemon -K -p /tmp/uvc-mjpg.pid 2>/dev/null; fi
kill $(ps | grep camevision-uvc-mjpg | grep -v grep | awk '{{print $1}}') 2>/dev/null
if [ -f /tmp/uvc-ff.pid ]; then start-stop-daemon -K -p /tmp/uvc-ff.pid 2>/dev/null; fi
sleep 1
# ISP grab must stay the only producer of the fifo.
if ! ps | grep -q '[v]4l2-ctl -d /dev/video13'; then
  setsid nohup sh -c 'while true; do v4l2-ctl -d /dev/video13 --stream-mmap=8 --stream-to=/tmp/cam.nv12 --stream-poll >>/userdata/uvc-isp.log 2>&1; sleep 0.3; done' </dev/null >/dev/null 2>&1 &
  echo $! >/tmp/uvc-isp.pid
fi
start-stop-daemon -S -b -q -m -p /tmp/uvc-ff.pid -x /bin/sh -- /userdata/camevision-uvc-ff.sh
sleep 2
echo === PROCS ===
ps | grep -E 'ffmpeg|v4l2-ctl|rkaiq_3A|uvc-ff|uvc-mjpg' | grep -v grep
echo === FF LOG ===
cat /userdata/uvc-ff.log
echo === ISP ===
tail -c 200 /userdata/uvc-isp.log
echo === UDC ===
echo -n state=; cat /sys/class/udc/21500000.usb/state
echo -n header=; ls /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/streaming/header/h
"""
print(run(cmd, wait=10))
