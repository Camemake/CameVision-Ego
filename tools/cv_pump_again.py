#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
kill -9 $(cat /tmp/uvc-h264.pid) 2>/dev/null
sleep 1
: > /userdata/uvc-h264-pump.log
start-stop-daemon -S -b -q -m -p /tmp/uvc-h264.pid -x /usr/bin/python3 -- /userdata/camevision-uvc-h264.py
sleep 12
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo LOG
cat /userdata/uvc-h264-pump.log
ls -l /tmp/uvc_au.bin /dev/shm/isp.nv12
ps | grep camevision-uvc-h264 | grep -v grep
dmesg | grep uvc_function_set_alt | tail -4
""", wait=20))
