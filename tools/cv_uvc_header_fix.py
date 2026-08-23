#!/usr/bin/env python3
"""Restore UVC streaming header links (H264 first) after class unlink."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
kill -9 $(ps | grep rk_mpi_uvc | grep -v grep | awk '{print $1}') 2>/dev/null
G=/sys/kernel/config/usb_gadget/rockchip
U=$G/functions/uvc.gs1
C=$G/configs/b.1
echo none > $G/UDC
sleep 1
rm -f $C/f1
sleep 1

echo === unlink class ===
rm -f $U/streaming/class/fs/h $U/streaming/class/hs/h $U/streaming/class/ss/h
rm -f $U/control/class/fs/h $U/control/class/ss/h
sleep 1
echo class_fs=$(ls $U/streaming/class/fs)
echo header=$(ls $U/streaming/header/h)

rm -f $U/streaming/header/h/f1 $U/streaming/header/h/m
ln -s $U/streaming/framebased/f1 $U/streaming/header/h/f1
ln -s $U/streaming/mjpeg/m $U/streaming/header/h/m
echo header2=$(ls $U/streaming/header/h)

ln -s $U/control/header/h $U/control/class/fs/h
ln -s $U/control/header/h $U/control/class/ss/h
ln -s $U/streaming/header/h $U/streaming/class/fs/h
ln -s $U/streaming/header/h $U/streaming/class/hs/h
ln -s $U/streaming/header/h $U/streaming/class/ss/h

echo NAME=$(cat $U/device_name)
echo H264=$(cat $U/streaming/framebased/f1/1920_1200p/wWidth)x$(cat $U/streaming/framebased/f1/1920_1200p/wHeight) fi=$(cat $U/streaming/framebased/f1/1920_1200p/dwDefaultFrameInterval)

ln -s $U $C/f1
echo 21500000.usb > $G/UDC
echo UDC=$(cat $G/UDC) STATE=$(cat /sys/class/udc/21500000.usb/state)

export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH
: > /userdata/rk_mpi_uvc.log
/oem/usr/bin/rk_mpi_uvc -c /tmp/rkuvc.ini -a /oem/usr/share/iqfiles -l 2 >/userdata/rk_mpi_uvc.log 2>&1 &
echo $! > /tmp/rk_mpi_uvc.pid
sleep 4
grep -E 'Please configure|add uvc|uvc open|Setting format|Starting|CameVision|UVC RGB|num_formats' /userdata/rk_mpi_uvc.log | tail -15
ps | grep rk_mpi_uvc | grep -v grep
dmesg | grep -E 'device reset|set_alt' | tail -6
"""
print(run(CMD, wait=16))
