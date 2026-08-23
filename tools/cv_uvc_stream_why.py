#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run("""
echo === VIDEO13 ===
v4l2-ctl -d /dev/video13 --get-fmt-video 2>/dev/null
v4l2-ctl -d /dev/video13 --get-parm 2>/dev/null | head -20
echo === SENSOR ===
dmesg | grep -iE 'sc233|233hgs|detected' | tail -15
echo === RK_MPI LOG ===
ls /tmp /userdata | grep -iE 'uvc|mpi|rkuvc'
logread 2>/dev/null | grep -i rk_mpi | tail -20
echo === STRINGS INI ===
strings /oem/usr/bin/rk_mpi_uvc | grep -iE '\\[video|venc|h264|mjpeg|width|height|format|uvc.gs|function_name|1920|1200|1080' | head -80
echo === IQ MATCH ===
ls /oem/usr/share/iqfiles | grep -i sc233
ls /etc/iqfiles | grep -i sc233
echo === PROC ===
ls /proc/$(cat /tmp/rk_mpi_uvc.pid)/fd 2>/dev/null | wc -l
cat /proc/$(cat /tmp/rk_mpi_uvc.pid)/status 2>/dev/null | head -8
ls -l /proc/$(cat /tmp/rk_mpi_uvc.pid)/fd 2>/dev/null | grep -iE 'video|uvc' | head
""", wait=10))
