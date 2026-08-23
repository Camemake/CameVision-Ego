#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
echo === STATE ===
echo STATE=$(cat /sys/class/udc/21500000.usb/state) SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo === V28 FMT ===
v4l2-ctl -d /dev/video28 --get-fmt-video
v4l2-ctl -d /dev/video28 --list-formats-ext 2>/dev/null | head -60
echo === MPI LOG ===
tail -30 /userdata/rk_mpi_uvc.log
echo === PUMP ===
cat /userdata/uvc-h264-pump.log
echo === DMESG ALT ===
dmesg | grep uvc_function | tail -15
echo === FN ===
echo function_name=$(cat /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/function_name)
echo device_name=$(cat /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/device_name)
""", wait=10))
