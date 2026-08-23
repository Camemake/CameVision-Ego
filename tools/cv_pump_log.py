#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
echo === PUMP ===
cat /userdata/uvc-h264-pump.log
echo === ISP ===
ls -l /dev/shm/isp.nv12 /tmp/uvc_au.bin 2>/dev/null
echo === VIDEO13 ===
v4l2-ctl -d /dev/video13 --get-fmt-video
echo === PS ===
ps | grep -E 'python3|v4l2-ctl|mpi_enc' | grep -v grep
echo === STATE ===
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
""", wait=8))
