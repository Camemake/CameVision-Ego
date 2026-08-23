#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run("""
echo === V4L GADGET ===
for n in /sys/class/video4linux/video*; do
  name=$(cat $n/name)
  echo "$name" | grep -qiE 'gadget|uvc|Came|RGB' && echo $(basename $n)=$name
done
echo === ALL video names with uvc ===
cat /sys/class/video4linux/video28/name 2>/dev/null
ls /dev/video2*
echo === LOG ===
wc -l /userdata/rk_mpi_uvc.log
tail -30 /userdata/rk_mpi_uvc.log
echo === STRINGS check ===
strings /oem/usr/bin/rk_mpi_uvc | grep -A2 -B2 check_uvc_video_id | head
strings /oem/usr/bin/rk_mpi_uvc | grep -E 'uvc.gs|/dev/video|Please configure|UVC RGB|function_name'
echo === STATE ===
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo NAME=$(cat /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/device_name)
echo FUNC=$(cat /sys/kernel/config/usb_gadget/rockchip/functions/uvc.gs1/function_name)
echo PROD=$(cat /sys/kernel/config/usb_gadget/rockchip/strings/0x409/product)
""", wait=8))
