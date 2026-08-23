#!/bin/sh
# One stable UVC format: MJPEG 1920x1080 @ 15 via RKISP. No rockit. No dwc3 rebind.
export PATH=/oem/usr/bin:/usr/bin:/bin:$PATH
export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH

G=/sys/kernel/config/usb_gadget/rockchip
C=$G/configs/b.1
U=$G/functions/uvc.gs1

# Stop old UVC producers only. Keep rkaiq, wifi, telnet.
if [ -f /tmp/uvc-h264.pid ]; then start-stop-daemon -K -p /tmp/uvc-h264.pid 2>/dev/null; fi
if [ -f /tmp/rk_mpi_uvc.pid ]; then start-stop-daemon -K -p /tmp/rk_mpi_uvc.pid 2>/dev/null; fi
if [ -f /tmp/uvc-mjpg.pid ]; then start-stop-daemon -K -p /tmp/uvc-mjpg.pid 2>/dev/null; fi
if [ -f /tmp/uvc-isp.pid ]; then start-stop-daemon -K -p /tmp/uvc-isp.pid 2>/dev/null; fi
if [ -f /tmp/uvc-ff.pid ]; then start-stop-daemon -K -p /tmp/uvc-ff.pid 2>/dev/null; fi
killall rk_mpi_uvc ffmpeg 2>/dev/null
for p in $(ps | grep -E 'camevision-uvc-h264|camevision-uvc-mjpg' | grep -v grep | awk '{print $1}'); do
	kill $p 2>/dev/null
done
# Drop any leftover ISP grabber that is not 3A.
for p in $(ps | grep 'v4l2-ctl' | grep video13 | grep -v grep | awk '{print $1}'); do
	kill $p 2>/dev/null
done
sleep 1

# Advertise only MJPEG 1920x1080 @ 15. Do not unbind dwc3.
if [ -e $U ]; then
	echo none > $G/UDC 2>/dev/null
	rm -f $C/f1
	rm -f $U/streaming/header/h/f1 $U/streaming/header/h/f
	mkdir -p $U/streaming/mjpeg/m/1920_1080p
	echo 1920 > $U/streaming/mjpeg/m/1920_1080p/wWidth
	echo 1080 > $U/streaming/mjpeg/m/1920_1080p/wHeight
	echo 666666 > $U/streaming/mjpeg/m/1920_1080p/dwDefaultFrameInterval
	echo 16000000 > $U/streaming/mjpeg/m/1920_1080p/dwMinBitRate
	echo 16000000 > $U/streaming/mjpeg/m/1920_1080p/dwMaxBitRate
	echo 3110400 > $U/streaming/mjpeg/m/1920_1080p/dwMaxVideoFrameBufferSize
	printf '666666\n' > $U/streaming/mjpeg/m/1920_1080p/dwFrameInterval
	[ -e $U/streaming/header/h/m ] || ln -s $U/streaming/mjpeg/m $U/streaming/header/h/m
	ln -s $U $C/f1
	echo 21500000.usb > $G/UDC
fi

[ -e /dev/mpp_service ] || insmod /userdata/kmpp-rt52.ko
touch /userdata/uvc-webcam.on

v4l2-ctl -d /dev/video13 --set-fmt-video=width=1920,height=1080,pixelformat=NV12
rm -f /tmp/cam.nv12
mkfifo /tmp/cam.nv12
python3 -c 'import fcntl,os; fd=os.open("/tmp/cam.nv12", os.O_RDWR); fcntl.fcntl(fd,1031,8388608); os.close(fd)'

setsid nohup sh -c 'while true; do v4l2-ctl -d /dev/video13 --stream-mmap=8 --stream-to=/tmp/cam.nv12 --stream-poll >>/userdata/uvc-isp.log 2>&1; echo restart >>/userdata/uvc-isp.log; sleep 0.3; done' \
	</dev/null >/dev/null 2>&1 &
echo $! >/tmp/uvc-isp.pid

start-stop-daemon -S -b -q -m -p /tmp/uvc-mjpg.pid -x /usr/bin/python3 -- /userdata/camevision-uvc-mjpg.py

sleep 2
echo "=== uvc start ==="
echo -n "udc="; cat $G/UDC
echo -n "state="; cat /sys/class/udc/21500000.usb/state
echo -n "speed="; cat /sys/class/udc/21500000.usb/current_speed
echo "header=$(ls $U/streaming/header/h 2>/dev/null)"
ps | grep -E 'camevision-uvc-mjpg|v4l2-ctl|rkaiq_3A' | grep -v grep
tail -c 400 /userdata/uvc-mjpg-pump.log 2>/dev/null
echo "=== 3A ==="
grep sysctl /userdata/rkaiq.log | tail -4
