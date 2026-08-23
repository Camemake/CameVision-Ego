#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

CMD = r"""
echo VIDEO
for n in /sys/class/video4linux/video*; do
  echo $(basename $n) $(cat $n/name)
done
echo PUMP
killall ffmpeg 2>/dev/null
UVCDEV=
for n in /sys/class/video4linux/video*; do
  name=$(cat $n/name)
  echo "$name" | grep -qiE 'gadget|uvc' || continue
  UVCDEV=/dev/$(basename $n)
done
echo DST=$UVCDEV
if [ -n "$UVCDEV" ]; then
  ffmpeg -hide_banner -loglevel warning -re -f lavfi -i testsrc2=size=640x360:rate=15 -c:v mjpeg -q:v 7 -pix_fmt yuvj420p -f v4l2 $UVCDEV >/tmp/camevision-uvc.log 2>&1 &
  sleep 2
  ps | grep ffmpeg | grep -v grep
  cat /tmp/camevision-uvc.log
fi
"""
print(run(CMD, wait=10))
