#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
ls -l /dev/shm/isp.nv12
echo === JPEG ===
/oem/usr/bin/mpi_enc_test -i /dev/shm/isp.nv12 -o /tmp/uvc_au.bin -w 1920 -h 1080 -hstride 1920 -vstride 1080 -f 0 -t 8 -n 1 -v q
echo jpeg_exit:$?
ls -l /tmp/uvc_au.bin
echo === H264 ===
/oem/usr/bin/mpi_enc_test -i /dev/shm/isp.nv12 -o /tmp/uvc_h264.bin -w 1920 -h 1080 -hstride 1920 -vstride 1080 -f 0 -t 7 -n 1 -g 1:30:0 -fps 30:30 -bps 8000000 -rc 1 -v q
echo h264_exit:$?
ls -l /tmp/uvc_h264.bin
""", wait=15))
