#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run("""
echo v4l_fn=$(cat /sys/class/video4linux/video28/function_name)
echo v4l_name=$(cat /sys/class/video4linux/video28/name)
echo UVC RGB > /sys/class/video4linux/video28/function_name
echo after=$(cat /sys/class/video4linux/video28/function_name)
kill -9 $(ps | grep rk_mpi_uvc | grep -v grep | awk '{print $1}') 2>/dev/null
export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH
: > /userdata/rk_mpi_uvc.log
/oem/usr/bin/rk_mpi_uvc -c /tmp/rkuvc.ini -a /oem/usr/share/iqfiles -l 2 >/userdata/rk_mpi_uvc.log 2>&1 &
sleep 8
echo STATE=$(cat /sys/class/udc/21500000.usb/state) SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
grep -E 'Please configure|add uvc|rgb_cnt|uvc open|num_formats|Starting|CameVision' /userdata/rk_mpi_uvc.log | tail -15
dmesg | grep -E 'device reset|set_alt' | tail -5
""", wait=14))
