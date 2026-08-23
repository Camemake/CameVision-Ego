#!/bin/sh
# CameVision: camera + 3A + HW H.264 RTSP. No rockit, no USB gadget change, no eMMC dd.
export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH
echo 8388608 > /proc/sys/fs/pipe-max-size 2>/dev/null

# Stop previous stream only. Keep adbd.
killall v4l2-ctl ffmpeg mpi_enc_test 2>/dev/null
if [ -f /userdata/hw-rtsp.pid ]; then kill $(cat /userdata/hw-rtsp.pid) 2>/dev/null; fi
if [ -f /userdata/isp-grab.pid ]; then kill $(cat /userdata/isp-grab.pid) 2>/dev/null; fi
killall rkaiq_3A_server 2>/dev/null
sleep 1

[ -e /dev/mpp_service ] || insmod /userdata/kmpp-rt52.ko

if ! ps | grep -q '[r]kaiq_3A_server'; then
	setsid nohup rkaiq_3A_server --silent </dev/null >/userdata/rkaiq.log 2>&1 &
	sleep 2
fi

rm -f /tmp/cam.nv12 /dev/shm/isp.nv12 /dev/shm/isp.tmp
mkfifo /tmp/cam.nv12
python3 -c 'import fcntl,os; fd=os.open("/tmp/cam.nv12", os.O_RDWR); fcntl.fcntl(fd,1031,8388608); os.close(fd)'

v4l2-ctl -d /dev/video13 --set-fmt-video=width=1920,height=1200,pixelformat=NV12

setsid nohup python3 -u /userdata/isp_grab.py </dev/null >/userdata/isp-grab.log 2>&1 &
echo $! >/userdata/isp-grab.pid

setsid nohup sh -c 'while true; do nice -n -15 v4l2-ctl -d /dev/video13 --stream-mmap=8 --stream-to=/tmp/cam.nv12 --stream-poll >>/userdata/v4l2-stream.log 2>&1; echo restart_v4l2 >>/userdata/v4l2-stream.log; sleep 0.3; done' \
	</dev/null >/dev/null 2>&1 &

# Wait for a real NV12 frame before encoder/RTSP.
n=0
while [ $n -lt 40 ]; do
	if [ -f /dev/shm/isp.nv12 ]; then
		sz=$(wc -c < /dev/shm/isp.nv12)
		if [ "$sz" -ge 3456000 ]; then
			break
		fi
	fi
	n=$((n+1))
	sleep 0.25
done

setsid nohup python3 -u /userdata/hw_rtsp.py </dev/null >/userdata/hw-rtsp.log 2>&1 &
echo $! >/userdata/hw-rtsp.pid
sleep 2

echo '=== stream ==='
ps | grep -E 'rkaiq_3A|v4l2-ctl|isp_grab|hw_rtsp' | grep -v grep
ls -l /dev/video13 /dev/mpp_service /dev/shm/isp.nv12 2>/dev/null
echo '--- 3A ---'
grep sysctl /userdata/rkaiq.log | tail -3
echo '--- grab ---'
tail -c 300 /userdata/isp-grab.log
echo '--- rtsp ---'
tail -c 400 /userdata/hw-rtsp.log
echo RTSP=rtsp://127.0.0.1:8554/live
