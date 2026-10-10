#!/bin/sh
# RKAIQ / RKISP35 — MIRA220 CameVision IQ, then 3A so ISP blocks attach.
export PATH=/oem/usr/bin:/usr/bin:/bin:$PATH
export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH

IQDIR=/oem/usr/share/iqfiles
IQNAME=mira220_camevision-mira220_default.json
SRC=
for d in /userdata/iqfiles /oem/usr/share/iqfiles; do
	if [ -f "$d/$IQNAME" ]; then
		SRC="$d/$IQNAME"
		break
	fi
done

install_iq() {
	if [ -z "$SRC" ]; then
		echo "MISSING MIRA220 IQ" >&2
		ls "$IQDIR" 2>/dev/null
		return 1
	fi
	mkdir -p "$IQDIR" /userdata/iqfiles 2>/dev/null || true
	mount -o remount,rw /oem 2>/dev/null || true
	cp -f "$SRC" "$IQDIR/$IQNAME" 2>/dev/null \
		|| cp -f "$SRC" /userdata/iqfiles/"$IQNAME"
	cp -f "$SRC" /userdata/iqfiles/"$IQNAME" 2>/dev/null || true
	if [ -f "$IQDIR/$IQNAME" ]; then
		ln -sfn "$IQNAME" "$IQDIR/mira220_default_default.json"
	else
		mkdir -p /userdata/iqfiles-all
		cp -a "$IQDIR/." /userdata/iqfiles-all/ 2>/dev/null || true
		cp -f "$SRC" /userdata/iqfiles-all/"$IQNAME"
		ln -sfn "$IQNAME" /userdata/iqfiles-all/mira220_default_default.json
		mount --bind /userdata/iqfiles-all "$IQDIR"
		echo "bind-mounted $IQDIR"
	fi
	echo "iq $SRC"
	return 0
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

install_iq || exit 1
sync

try=0
ok=0
while [ $try -lt 3 ]; do
	start_3a
	n=0
	while [ $n -lt 12 ]; do
		if grep -q 'sysctl_init success' /userdata/rkaiq.log 2>/dev/null \
			&& grep -q 'mira220' /userdata/rkaiq.log 2>/dev/null; then
			if ! grep -q 'access .*failed' /userdata/rkaiq.log 2>/dev/null; then
				ok=1
				echo "3A loaded MIRA220 IQ"
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
grep -E 'sysctl|iqfiles|mira220|success|error|ERR|engine' /userdata/rkaiq.log 2>/dev/null | tail -25
echo "=== rkisp ==="
for f in /proc/rkisp-vir0 /proc/rkisp-vir1 /proc/rkisp-vir2; do
	[ -f "$f" ] || continue
	echo "---- $f ----"
	grep -E 'AWBGAIN|YNR |CNR |SHARP|DRC |ENH ' "$f" 2>/dev/null | head -12
done
[ "$ok" = 1 ] || exit 1
exit 0
