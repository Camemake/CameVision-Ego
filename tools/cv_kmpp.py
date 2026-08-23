#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
echo === DEV ===
ls -l /dev/mpp* /dev/vcodec* /dev/rkvenc* /dev/vpu* 2>/dev/null
ls /dev | grep -iE 'mpp|venc|vpu|vcodec|rkv'
echo === LSMOD ===
lsmod | grep -iE 'kmpp|mpp|rkv|vcodec|rockit'
echo === KO ===
ls -l /userdata/kmpp*.ko /oem/usr/ko/kmpp*.ko 2>/dev/null
echo === KMPP FLAG 1200 ===
/oem/usr/bin/mpi_enc_test -i /dev/shm/isp.nv12 -o /tmp/uvc_h264.bin -w 1920 -h 1200 -hstride 1920 -vstride 1200 -f 0 -t 7 -n 1 -kmpp 1 -v q
echo kmpp_exit:$?
ls -l /tmp/uvc_h264.bin
echo === 1200 NO KMPP ===
# recapture native size
v4l2-ctl -d /dev/video13 --set-fmt-video=width=1920,height=1200,pixelformat=NV12 --get-fmt-video
timeout 8 v4l2-ctl -d /dev/video13 --stream-mmap=4 --stream-count=1 --stream-to=/dev/shm/isp.nv12 --stream-poll
ls -l /dev/shm/isp.nv12
/oem/usr/bin/mpi_enc_test -i /dev/shm/isp.nv12 -o /tmp/uvc_h264.bin -w 1920 -h 1200 -hstride 1920 -vstride 1200 -f 0 -t 7 -n 1 -g 1:30:0 -fps 30:30 -bps 8000000 -rc 1 -v q
ls -l /tmp/uvc_h264.bin
""", wait=20))
