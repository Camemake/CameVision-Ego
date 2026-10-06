#!/bin/sh
# RKAIQ / RKISP35 — IQ on oem, 3A up, ISP blocks on.
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
		echo "MISSING IQ $IQNAME" >&2
		ls "$IQDIR" 2>/dev/null
		return 1
	fi
	mkdir -p "$IQDIR" 2>/dev/null || true
	if cp -f "$SRC" "$IQDIR/$IQNAME" 2>/dev/null; then
		ln -sf "$IQNAME" "$IQDIR/sc233hgs_default_default.json"
		echo "installed $IQDIR/$IQNAME"
		return 0
	fi
	mount -o remount,rw /oem 2>/dev/null || true
	if cp -f "$SRC" "$IQDIR/$IQNAME" 2>/dev/null; then
		ln -sf "$IQNAME" "$IQDIR/sc233hgs_default_default.json"
		echo "installed $IQDIR/$IQNAME after remount"
		return 0
	fi
	mkdir -p /userdata/iqfiles-all
	cp -a "$IQDIR/." /userdata/iqfiles-all/ 2>/dev/null || true
	cp -f "$SRC" /userdata/iqfiles-all/"$IQNAME"
	ln -sf "$IQNAME" /userdata/iqfiles-all/sc233hgs_default_default.json
	mount --bind /userdata/iqfiles-all "$IQDIR"
	echo "bind-mounted $IQDIR from /userdata/iqfiles-all"
	return 0
}

install_iq
sync

if ! ps | grep -q '[r]kaiq_3A_server'; then
	setsid /oem/usr/bin/rkaiq_3A_server --silent \
		</dev/null >/userdata/rkaiq.log 2>&1 &
	echo $! >/userdata/rkaiq.pid
	sleep 2
fi

n=0
while [ $n -lt 20 ]; do
	if grep -q 'AWBGAIN    ON' /proc/rkisp-vir0 2>/dev/null; then
		if grep -q 'AWBGAIN    ON' /proc/rkisp-vir2 2>/dev/null \
			|| grep -q 'AWBGAIN    ON' /proc/rkisp-vir1 2>/dev/null; then
			echo "ISP on"
			break
		fi
	fi
	n=$((n + 1))
	sleep 1
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
exit 0
