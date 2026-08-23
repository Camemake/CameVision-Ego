#!/bin/sh
# FIFO NV12 -> MJPEG -> /dev/video28. Restart if host not streaming yet.
export PATH=/oem/usr/bin:/usr/bin:/bin:$PATH
export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH
: >/userdata/uvc-ff.log
while true; do
	echo "$(cat /proc/uptime) ffmpeg start" >>/userdata/uvc-ff.log
	ffmpeg -nostdin -hide_banner -loglevel warning \
		-fflags nobuffer -flags low_delay \
		-f rawvideo -pixel_format nv12 -video_size 1920x1080 -framerate 15 \
		-i /tmp/cam.nv12 \
		-c:v mjpeg -q:v 5 -an \
		-f v4l2 /dev/video28 >>/userdata/uvc-ff.log 2>&1
	echo "$(cat /proc/uptime) ffmpeg exit $?" >>/userdata/uvc-ff.log
	sleep 0.4
done
