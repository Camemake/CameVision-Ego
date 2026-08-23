#!/bin/sh
OUT=/userdata/camevision_frame.nv12
rm -f $OUT
v4l2-ctl -d /dev/video13 --set-fmt-video=width=1920,height=1200,pixelformat=NV12
echo capturing
timeout -k 2 15 v4l2-ctl -d /dev/video13 --stream-mmap=4 --stream-count=2 --stream-to=$OUT --stream-poll
echo v4l_exit:$?
ls -l $OUT