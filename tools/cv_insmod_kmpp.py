#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
echo === INSMOD kmpp-rt52 ===
insmod /userdata/kmpp-rt52.ko
echo insmod:$?
ls -l /dev/mpp* /dev/vcodec* 2>/dev/null
lsmod | grep kmpp
dmesg | tail -8
echo === ENC H264 ===
/oem/usr/bin/mpi_enc_test -i /dev/shm/isp.nv12 -o /tmp/uvc_h264.bin -w 1920 -h 1200 -hstride 1920 -vstride 1200 -f 0 -t 7 -n 1 -g 1:30:0 -fps 30:30 -bps 8000000 -rc 1 -v q
echo enc:$?
ls -l /tmp/uvc_h264.bin
""", wait=15))
