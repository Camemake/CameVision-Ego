#!/bin/sh
# CameVision Ego AM / MIRA220 — start live stereo on boot.
# USB stays ADB. CIF path. Do not start 3A (it rewrites exposure).
export PATH=/oem/usr/bin:/usr/sbin:/sbin:/usr/bin:/bin
export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH
export PYTHONPATH=/userdata/pylib
export TZ=UTC-2

[ -e /dev/rtc0 ] && hwclock -s -f /dev/rtc0 2>/dev/null || true

BC=/userdata/boot_count
n=0
[ -f "$BC" ] && n=$(cat "$BC" 2>/dev/null || echo 0)
n=$((n + 1))
echo "$n" > "$BC"

[ -e /dev/mpp_service ] || insmod /userdata/kmpp-rt52.ko 2>/dev/null || true

if [ -x /etc/init.d/S10mira220 ]; then
	/bin/sh /etc/init.d/S10mira220 >>/userdata/mira220-boot.log 2>&1 || true
elif [ -x /userdata/S10mira220 ]; then
	/bin/sh /userdata/S10mira220 >>/userdata/mira220-boot.log 2>&1 || true
fi

if [ -x /userdata/camevision-wifi.sh ]; then
	if ! ip -4 addr show wlan0 2>/dev/null | grep -q 'inet '; then
		if ! ps | grep -q '[c]amevision-wifi'; then
			setsid /bin/sh /userdata/camevision-wifi.sh \
				</dev/null >/userdata/wifi-boot.log 2>&1 &
		fi
	fi
fi

if [ -f /userdata/ego_imu_hud.py ] && ! ps | grep -q '[e]go_imu_hud'; then
	setsid /usr/bin/python3 /userdata/ego_imu_hud.py \
		</dev/null >/tmp/ego-imu.log 2>&1 &
	echo $! >/tmp/ego-imu.pid
fi

i=0
while [ $i -lt 40 ]; do
	if [ -e /dev/video1 ] && [ -e /dev/video12 ]; then
		break
	fi
	i=$((i + 1))
	sleep 1
done

if [ ! -f /userdata/ego_stereo.py ]; then
	echo "missing /userdata/ego_stereo.py"
	exit 0
fi
if ! PYTHONPATH=/userdata/pylib python3 -c 'import numpy, cv2' >/dev/null 2>&1; then
	if [ -f /userdata/cv_ego_extract_pylib.py ]; then
		python3 /userdata/cv_ego_extract_pylib.py >>/userdata/pylib-boot.log 2>&1 || true
	fi
fi
if ! PYTHONPATH=/userdata/pylib python3 -c 'import numpy, cv2' >/dev/null 2>&1; then
	echo "pylib missing — depth matcher needs numpy/cv2" >&2
fi
if ps | grep -q '[e]go_stereo'; then
	exit 0
fi
killall v4l2-ctl 2>/dev/null || true
echo "starting ego_stereo AM $(date 2>/dev/null)"
setsid /usr/bin/python3 /userdata/ego_stereo.py \
	</dev/null >/userdata/ego-stereo.log 2>&1 &
echo $! >/tmp/ego-stereo.pid
echo "pid=$(cat /tmp/ego-stereo.pid)"
exit 0
