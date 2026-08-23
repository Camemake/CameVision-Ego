#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
echo === JPEG now ===
/oem/usr/bin/mpi_enc_test -i /dev/shm/isp.nv12 -o /tmp/uvc_au.bin -w 1920 -h 1200 -hstride 1920 -vstride 1200 -f 0 -t 8 -n 1 -v q
ls -l /tmp/uvc_au.bin
echo === STATE ===
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
v4l2-ctl -d /dev/video28 --all 2>&1 | grep -A6 'Format Video Output'
""", wait=10))
