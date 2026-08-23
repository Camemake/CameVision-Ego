#!/bin/sh
# RKISP 1920x1080 NV12 -> JPEG -> UVC. No gadget change. No dwc3. No rockit.
export PATH=/oem/usr/bin:/usr/bin:/bin:$PATH
export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH

if [ -f /tmp/uvc-mjpg.pid ]; then start-stop-daemon -K -p /tmp/uvc-mjpg.pid 2>/dev/null; fi
if [ -f /tmp/uvc-isp.pid ]; then kill $(cat /tmp/uvc-isp.pid) 2>/dev/null; fi
for p in $(ps | grep 'v4l2-ctl' | grep video13 | grep -v grep | awk '{print $1}'); do
	kill $p 2>/dev/null
done
killall rk_mpi_uvc ffmpeg 2>/dev/null
sleep 1

[ -e /dev/mpp_service ] || insmod /userdata/kmpp-rt52.ko
touch /userdata/uvc-webcam.on

if [ -x /userdata/camevision-aiq.sh ]; then
	/userdata/camevision-aiq.sh >/userdata/aiq-boot.log 2>&1
fi

v4l2-ctl -d /dev/video13 --set-fmt-video=width=1920,height=1080,pixelformat=NV12
rm -f /tmp/cam.nv12
mkfifo /tmp/cam.nv12
python3 -c 'import fcntl,os; fd=os.open("/tmp/cam.nv12", os.O_RDWR); fcntl.fcntl(fd,1031,8388608); os.close(fd)'

setsid nohup sh -c 'while true; do v4l2-ctl -d /dev/video13 --stream-mmap=8 --stream-to=/tmp/cam.nv12 --stream-poll >>/userdata/uvc-isp.log 2>&1; echo restart >>/userdata/uvc-isp.log; sleep 0.3; done' \
	</dev/null >/dev/null 2>&1 &
echo $! >/tmp/uvc-isp.pid

start-stop-daemon -S -b -q -m -p /tmp/uvc-mjpg.pid -x /usr/bin/python3 -- /userdata/camevision-uvc-mjpg.py
sleep 1
echo "=== cam ==="
ps | grep -E 'camevision-uvc-mjpg|v4l2-ctl|rkaiq_3A' | grep -v grep
tail -c 300 /userdata/uvc-mjpg-pump.log 2>/dev/null
