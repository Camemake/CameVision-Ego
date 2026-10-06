#!/bin/sh
# CameVision Ego Release 1 — start live stereo on boot.
# USB stays ADB. Do not start UVC. Do not insmod rockit.
export PATH=/oem/usr/bin:/usr/sbin:/sbin:/usr/bin:/bin
export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH
export PYTHONPATH=/userdata/pylib
export TZ=UTC-2

# RV-3028 is rtc0. Load it so logs are not 1970.
[ -e /dev/rtc0 ] && hwclock -s -f /dev/rtc0 2>/dev/null || true

# VS6621 STA. Background so the live page does not wait on WPA.
if [ -x /userdata/camevision-wifi.sh ]; then
	if ! ip -4 addr show wlan0 2>/dev/null | grep -q 'inet '; then
		if ! ps | grep -q '[c]amevision-wifi'; then
			setsid /bin/sh /userdata/camevision-wifi.sh \
				</dev/null >/userdata/wifi-boot.log 2>&1 &
		fi
	fi
fi

if [ -f /userdata/iqfiles/sc233hgs_camevision-sc233hgs_default.json ]; then
	cp -f /userdata/iqfiles/sc233hgs_camevision-sc233hgs_default.json \
		/oem/usr/share/iqfiles/sc233hgs_camevision-sc233hgs_default.json 2>/dev/null \
		|| (mount -o remount,rw /oem 2>/dev/null \
		    && cp -f /userdata/iqfiles/sc233hgs_camevision-sc233hgs_default.json \
			/oem/usr/share/iqfiles/sc233hgs_camevision-sc233hgs_default.json)
fi

if ! ps | grep -q '[r]kaiq_3A_server'; then
	setsid /oem/usr/bin/rkaiq_3A_server --silent \
		</dev/null >/userdata/rkaiq.log 2>&1 &
	echo $! >/userdata/rkaiq.pid
fi

if [ -f /userdata/ego_imu_hud.py ] && ! ps | grep -q '[e]go_imu_hud'; then
	setsid /usr/bin/python3 /userdata/ego_imu_hud.py \
		</dev/null >/tmp/ego-imu.log 2>&1 &
	echo $! >/tmp/ego-imu.pid
fi

i=0
while [ $i -lt 40 ]; do
	if [ -e /dev/video24 ] && [ -e /dev/video32 ]; then
		break
	fi
	i=$((i + 1))
	sleep 1
done

if [ ! -f /userdata/ego_stereo.py ]; then
	echo "missing /userdata/ego_stereo.py"
	exit 0
fi
if ps | grep -q '[e]go_stereo'; then
	exit 0
fi
echo "starting ego_stereo $(date 2>/dev/null)"
setsid /usr/bin/python3 /userdata/ego_stereo.py \
	</dev/null >/userdata/ego-stereo.log 2>&1 &
echo $! >/tmp/ego-stereo.pid
echo "pid=$(cat /tmp/ego-stereo.pid)"
exit 0
