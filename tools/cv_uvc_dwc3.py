#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run
print(run(r"""
export PATH=/oem/usr/bin:/usr/bin:/bin:$PATH
# Stop ISP/pump so USB rebind is not fighting STREAMON.
if [ -f /tmp/uvc-mjpg.pid ]; then start-stop-daemon -K -p /tmp/uvc-mjpg.pid 2>/dev/null; fi
if [ -f /tmp/uvc-isp.pid ]; then kill $(cat /tmp/uvc-isp.pid) 2>/dev/null; fi
for p in $(ps | grep 'v4l2-ctl' | grep video13 | grep -v grep | awk '{print $1}'); do kill $p 2>/dev/null; done
for p in $(ps | grep camevision-uvc-mjpg | grep -v grep | awk '{print $1}'); do kill $p 2>/dev/null; done
sleep 1
G=/sys/kernel/config/usb_gadget/rockchip
C=$G/configs/b.1
U=$G/functions/uvc.gs1
echo none > $G/UDC 2>/dev/null
rm -f $C/f1
sleep 1
echo -n pre_state=; cat /sys/class/udc/21500000.usb/state
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/unbind
sleep 1
echo 21500000.usb > /sys/bus/platform/drivers/dwc3/bind
sleep 1
echo -n post_dwc3=; ls /sys/class/udc
[ -e $C/f1 ] || ln -s $U $C/f1
echo 21500000.usb > $G/UDC
sleep 2
echo -n UDC=; cat $G/UDC
echo -n state=; cat /sys/class/udc/21500000.usb/state
echo -n speed=; cat /sys/class/udc/21500000.usb/current_speed
echo -n product=; cat $G/strings/0x409/product
dmesg | tail -n 15
""", wait=16))
