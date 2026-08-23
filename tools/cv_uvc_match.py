#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run("""
strings /oem/usr/bin/rk_mpi_uvc | grep -iE 'uvc_mpi_cfg|UVC RGB|function_name|device_name|configfs_find'
echo === MPP ===
ls -l /dev/mpp_service /dev/rkaiq* 2>/dev/null
lsmod | grep -iE 'rockit|kmpp|rk_vcodec' 
echo === STREAM PROCS ===
ps | grep -E 'camevision-stream|v4l2-ctl|hw_rtsp|rk_mpi' | grep -v grep | head
""", wait=8))
