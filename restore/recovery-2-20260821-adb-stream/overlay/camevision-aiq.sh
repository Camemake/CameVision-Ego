#!/bin/sh
# RKAIQ / RKISP35 full 3A. No rockit. Does not grab /dev/video13.
# IQ name must match live DT: sensor_module-lens_scene
#   sc233hgs + efference-sc233hgs + default
export PATH=/oem/usr/bin:/usr/bin:/bin:$PATH
export LD_LIBRARY_PATH=/oem/usr/lib:/oem/lib:$LD_LIBRARY_PATH

IQDIR=/oem/usr/share/iqfiles
IQNAME=sc233hgs_efference-sc233hgs_default.json
SRC=
for d in /userdata/iqfiles /oem/usr/share/iqfiles; do
	if [ -f "$d/$IQNAME" ]; then
		SRC="$d/$IQNAME"
		break
	fi
done

if [ ! -f "$IQDIR/$IQNAME" ]; then
	if [ -z "$SRC" ]; then
		echo "MISSING IQ $IQNAME" >&2
		ls "$IQDIR" 2>/dev/null
		exit 1
	fi
	if cp -f "$SRC" "$IQDIR/$IQNAME" 2>/dev/null; then
		ln -sf "$IQNAME" "$IQDIR/sc233hgs_default_default.json"
		echo "installed $IQDIR/$IQNAME"
	else
		mount -o remount,rw /oem 2>/dev/null
		if ! cp -f "$SRC" "$IQDIR/$IQNAME" 2>/dev/null; then
			mkdir -p /userdata/iqfiles-all
			cp -a "$IQDIR/." /userdata/iqfiles-all/ 2>/dev/null
			cp -f "$SRC" /userdata/iqfiles-all/"$IQNAME"
			ln -sf "$IQNAME" /userdata/iqfiles-all/sc233hgs_default_default.json
			mount --bind /userdata/iqfiles-all "$IQDIR"
			echo "bind-mounted $IQDIR from /userdata/iqfiles-all"
		else
			ln -sf "$IQNAME" "$IQDIR/sc233hgs_default_default.json"
			echo "installed $IQDIR/$IQNAME after remount"
		fi
	fi
	sync
else
	[ -e "$IQDIR/sc233hgs_default_default.json" ] || ln -sf "$IQNAME" "$IQDIR/sc233hgs_default_default.json"
	echo "iq present $IQDIR/$IQNAME"
fi

if ! ps | grep -q '[r]kaiq_3A_server'; then
	setsid nohup rkaiq_3A_server --silent </dev/null >/userdata/rkaiq.log 2>&1 &
	echo $! >/userdata/rkaiq.pid
	sleep 2
fi

# RKISP Tuner bridge (IQ Tools Guide ISP35). After 3A, not before.
if ! ps | grep -q '[r]kaiq_tool_server'; then
	setsid nohup rkaiq_tool_server -d 0 -w 1920 -h 1200 \
		</dev/null >/userdata/rkaiq-tool.log 2>&1 &
	echo $! >/userdata/rkaiq-tool.pid
	sleep 1
fi

echo "=== 3A ==="
ps | grep -E 'rkaiq_3A|rkaiq_tool' | grep -v grep
grep -E 'sysctl|iqfiles|sc233|success|error|ERR|engine' /userdata/rkaiq.log | tail -20
echo "=== tool ==="
tail -c 800 /userdata/rkaiq-tool.log 2>/dev/null
echo "=== rkisp ==="
for f in /proc/rkisp*; do
	echo "---- $f ----"
	sed -n '1,40p' "$f" 2>/dev/null
done
exit 0
