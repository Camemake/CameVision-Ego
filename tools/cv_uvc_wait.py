#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run("""
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
echo NAME=$(cat /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/device_name)
echo PROD=$(cat /sys/kernel/config/usb_gadget/rockchip/strings/0x409/product)
dmesg | grep -E 'device reset|set_alt|uvc_function_bind' | tail -8
# resume ffmpeg without TTY
killall -9 ffmpeg 2>/dev/null
start-stop-daemon -S -b -q -x /usr/bin/ffmpeg -- -hide_banner -loglevel warning \
  -f v4l2 -input_format nv12 -video_size 1920x1200 -framerate 30 -i /dev/video13 \
  -c:v h264_v4l2m2m -b:v 8M -r 30 -f v4l2 /dev/video28
sleep 3
ps | grep ffmpeg | grep -v grep
tail -20 /userdata/rk_mpi_uvc.log | grep -v param | grep -v isp.0 | tail -15
""", wait=10))
