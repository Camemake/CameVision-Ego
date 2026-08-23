#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run
print(run(r"""
echo === ARCH ===
uname -m
python3 -c 'import struct,sys; print("py",sys.version); print("ptr",struct.calcsize("P"), "long",struct.calcsize("l"))'
echo === BINS ===
ls /oem/usr/bin /usr/bin 2>/dev/null | grep -iE 'uvc-gadget|uvc_app|yavta|ffmpeg|gcc'
echo === PYMOD ===
python3 -c 'import v4l2' 2>&1 | head -2
echo === V28 FMT ===
v4l2-ctl -d /dev/video28 --all 2>&1 | grep -A12 'Format Video Output'
echo === ISP FMT ===
v4l2-ctl -d /dev/video13 --all 2>&1 | grep -A8 'Format Video Capture'
echo === PUMP FMT LINE ===
head -c 400 /userdata/uvc-h264-pump.log
echo
echo === 3A AFTER ===
grep sysctl /userdata/rkaiq.log | tail -5
""", wait=8))
