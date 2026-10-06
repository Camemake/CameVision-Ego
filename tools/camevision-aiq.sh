#!/bin/sh
# RKAIQ / RKISP35 — IQ on oem, then 3A restarted so ISP blocks attach.
# IQ name matches the Ego DTB: sc233hgs + camevision-sc233hgs + default
export PATH=/oem/usr/bin:/usr/bin:/bin:$PATH
export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH

IQDIR=/oem/usr/share/iqfiles
IQNAME=sc233hgs_camevision-sc233hgs_default.json
SRC=
for d in /userdata/iqfiles /oem/usr/share/iqfiles; do
	if [ -f "$d/$IQNAME" ]; then
		SRC="$d/$IQNAME"
		break
	fi
done

install_iq() {
	if [ -z "$SRC" ]; then
		echo "MISSING IQ" >&2
		ls "$IQDIR" 2>/dev/null
		return 1
	fi
	mkdir -p "$IQDIR" /userdata/iqfiles 2>/dev/null || true
	mount -o remount,rw /oem 2>/dev/null || true
	for d in "$IQDIR" /userdata/iqfiles /userdata/iqfiles-all; do
		[ -d "$d" ] || continue
		find "$d" -maxdepth 1 -type f -name 'sc233hgs_*_default.json' \
			! -name "$IQNAME" -exec rm -f {} +
	done
	cp -f "$SRC" "$IQDIR/$IQNAME" 2>/dev/null \
		|| cp -f "$SRC" /userdata/iqfiles/"$IQNAME"
	cp -f "$SRC" /userdata/iqfiles/"$IQNAME" 2>/dev/null || true
	if [ -f "$IQDIR/$IQNAME" ]; then
		ln -sfn "$IQNAME" "$IQDIR/sc233hgs_default_default.json"
	else
		mkdir -p /userdata/iqfiles-all
		cp -a "$IQDIR/." /userdata/iqfiles-all/ 2>/dev/null || true
		find /userdata/iqfiles-all -maxdepth 1 -type f \
			-name 'sc233hgs_*_default.json' ! -name "$IQNAME" -exec rm -f {} +
		cp -f "$SRC" /userdata/iqfiles-all/"$IQNAME"
		ln -sfn "$IQNAME" /userdata/iqfiles-all/sc233hgs_default_default.json
		mount --bind /userdata/iqfiles-all "$IQDIR"
		echo "bind-mounted $IQDIR"
	fi
	echo "iq $SRC"
	return 0
}

wait_sensors() {
	n=0
	while [ $n -lt 25 ]; do
		if [ -e /dev/video24 ] && [ -e /dev/video32 ]; then
			return 0
		fi
		n=$((n + 1))
		sleep 1
	done
	echo "sensors not up yet" >&2
	return 1
}

start_3a() {
	killall rkaiq_3A_server rkaiq_tool_server 2>/dev/null || true
	sleep 1
	rm -f /userdata/rkaiq.log
	setsid /oem/usr/bin/rkaiq_3A_server --silent \
		</dev/null >/userdata/rkaiq.log 2>&1 &
	echo $! >/userdata/rkaiq.pid
	sleep 2
}

isp_on() {
	grep -q 'AWBGAIN    ON' /proc/rkisp-vir0 2>/dev/null || return 1
	grep -q 'AWBGAIN    ON' /proc/rkisp-vir2 2>/dev/null \
		|| grep -q 'AWBGAIN    ON' /proc/rkisp-vir1 2>/dev/null
}

install_iq || exit 1
sync
wait_sensors || true

try=0
ok=0
while [ $try -lt 3 ]; do
	start_3a
	n=0
	while [ $n -lt 12 ]; do
		if grep -q 'sysctl_init success' /userdata/rkaiq.log 2>/dev/null \
			&& grep -q 'sc233hgs_camevision-sc233hgs_default.json' /userdata/rkaiq.log 2>/dev/null; then
			if ! grep -q 'access .*failed' /userdata/rkaiq.log 2>/dev/null; then
				ok=1
				echo "3A loaded CameVision IQ"
				break 2
			fi
		fi
		n=$((n + 1))
		sleep 1
	done
	try=$((try + 1))
	echo "3A not ready, restart ($try)"
done

echo "=== 3A ==="
ps | grep -E 'rkaiq_3A' | grep -v grep
grep -E 'sysctl|iqfiles|sc233|success|error|ERR|engine' /userdata/rkaiq.log 2>/dev/null | tail -20
echo "=== rkisp ==="
for f in /proc/rkisp-vir0 /proc/rkisp-vir1 /proc/rkisp-vir2; do
	[ -f "$f" ] || continue
	echo "---- $f ----"
	grep -E 'AWBGAIN|YNR |CNR |SHARP|DRC |ENH ' "$f" 2>/dev/null | head -12
done
if isp_on; then
	echo "ISP on"
fi
[ "$ok" = 1 ] || exit 1
exit 0
