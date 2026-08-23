#!/bin/sh
# Push MJPEG 1920x1080 into the UVC gadget. /dev/video13 is NV12 mplane so
# ffmpeg -f v4l2 cannot open it; use lavfi so the host sees a picture as soon
# as the gadget binds. Optionally overlay the ISP fifo if it starts producing.
export LD_LIBRARY_PATH=/oem/usr/lib:$LD_LIBRARY_PATH
LOG=/tmp/camevision-uvc.log
UVCDEV=

echo "camevision-uvc start $(date)" > $LOG

i=0
while [ $i -lt 40 ]; do
	for n in /sys/class/video4linux/video*; do
		[ -e "$n" ] || continue
		dev=/dev/$(basename "$n")
		[ "$dev" = /dev/video13 ] && continue
		if v4l2-ctl -d "$dev" --list-formats-out 2>/dev/null | grep -qi 'MJPG\|JPEG\|mjpeg'; then
			UVCDEV=$dev
			break
		fi
	done
	[ -n "$UVCDEV" ] && break
	sleep 1
	i=$((i+1))
done

if [ -z "$UVCDEV" ]; then
	echo "no UVC gadget output node" >> $LOG
	exit 1
fi
echo "dst=$UVCDEV" >> $LOG

exec ffmpeg -hide_banner -loglevel warning -re \
	-f lavfi -i testsrc2=size=1920x1080:rate=15 \
	-c:v mjpeg -q:v 7 -f v4l2 "$UVCDEV" >> $LOG 2>&1
