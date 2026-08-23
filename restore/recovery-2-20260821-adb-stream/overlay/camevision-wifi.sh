#!/bin/sh
# CameVision Single — VS6621S80 STA. Always join wpa_camevision.conf.
# Do not insmod rockit. Do not touch the USB gadget.
# Root is often ro — never fail on /lib/firmware.

KO=/userdata/swt6621-rt52
OEMKO=/oem/usr/ko
LOG=/userdata/wifi.log
FWDIR=/lib/firmware
FWSRC=/userdata/swt6621_fw
WLAN=wlan0
CONF=/userdata/wpa_camevision.conf

log() { echo "$(date +%T) $*" | tee -a "$LOG"; }

already() {
	lsmod | awk '{print $1}' | grep -qx "$1"
}

modpath() {
	mod="$1"
	if [ -f "$KO/${mod}_rt52.ko" ]; then
		echo "$KO/${mod}_rt52.ko"
	elif [ -f "$KO/${mod}.ko" ]; then
		echo "$KO/${mod}.ko"
	elif [ -f "$OEMKO/${mod}.ko" ]; then
		echo "$OEMKO/${mod}.ko"
	fi
}

ins() {
	mod="$1"
	shift
	if already "$mod"; then
		return 0
	fi
	path=$(modpath "$mod")
	if [ -z "$path" ]; then
		log "missing $mod.ko"
		return 1
	fi
	log "insmod $path $*"
	if ! insmod "$path" "$@"; then
		log "FAIL $mod"
		return 1
	fi
}

mkdir -p /var/run/wpa_supplicant
: > "$LOG"

n=0
while [ $n -lt 40 ]; do
	if [ -e /sys/bus/sdio/devices/mmc2:0001:1 ]; then
		break
	fi
	sleep 1
	n=$((n + 1))
done
if [ ! -e /sys/bus/sdio/devices/mmc2:0001:1 ]; then
	log "no SDIO function — VS6621 not enumerated"
	exit 1
fi
id=$(grep '^SDIO_ID=' /sys/bus/sdio/devices/mmc2:0001:1/uevent | cut -d= -f2)
log "sdio id=$id"
[ "$id" = "1FFE:6621" ] || log "WARN unexpected SDIO_ID $id"

if [ -e /sys/module/firmware_class/parameters/path ]; then
	printf '%s' "$FWSRC" > /sys/module/firmware_class/parameters/path
	log "firmware path=$FWSRC"
fi
if [ -d "$FWSRC" ]; then
	if [ ! -f "$FWSRC/SWT6621S_NV_SDIO.bin" ] && [ -f "$FWSRC/SWT6621S_NV_SDIO_ALONE.bin" ]; then
		cp -f "$FWSRC/SWT6621S_NV_SDIO_ALONE.bin" "$FWSRC/SWT6621S_NV_SDIO.bin"
	fi
	if [ ! -f "$FWSRC/SEEKWAVE_NV_SWT6621S.bin" ] && [ -f "$FWSRC/SWT6621S_NV_SDIO_ALONE.bin" ]; then
		cp -f "$FWSRC/SWT6621S_NV_SDIO_ALONE.bin" "$FWSRC/SEEKWAVE_NV_SWT6621S.bin"
	fi
	if mkdir -p "$FWDIR" 2>/dev/null; then
		cp -f "$FWSRC"/* "$FWDIR"/ 2>/dev/null || true
	fi
fi

ins cfg80211 || exit 1
ins libarc4 || true
ins mac80211 || exit 1
ins gf128mul || true
ins ctr || true
ins ccm || true
ins libaes || true
ins aes_generic || true
ins skw_sdio_lite || exit 1
sleep 1
ins swt6621s_wifi || exit 1
sleep 1

n=0
while [ $n -lt 20 ]; do
	if [ -d /sys/class/net/$WLAN ]; then
		break
	fi
	sleep 1
	n=$((n + 1))
done
if [ ! -d /sys/class/net/$WLAN ]; then
	log "no $WLAN after driver load"
	ls /sys/class/net >>"$LOG" 2>/dev/null
	lsmod >>"$LOG" 2>/dev/null
	exit 2
fi

ip link set $WLAN up
log "wlan0 up"

if [ ! -f "$CONF" ]; then
	log "missing $CONF"
	exit 3
fi

killall wpa_supplicant 2>/dev/null || true
rm -rf /var/run/wpa_supplicant
mkdir -p /var/run/wpa_supplicant
wpa_supplicant -B -i $WLAN -c "$CONF" -D nl80211 -f /userdata/wpa.log

n=0
st=
while [ $n -lt 30 ]; do
	st=$(wpa_cli -i $WLAN status 2>/dev/null | grep wpa_state= | cut -d= -f2)
	log "wpa_state=$st"
	[ "$st" = "COMPLETED" ] && break
	sleep 1
	n=$((n + 1))
done

if [ "$st" = "COMPLETED" ]; then
	udhcpc -i $WLAN -n -q -t 12 >>"$LOG" 2>&1 || true
	# dhcpcd may already be running (S41); ask it too
	dhcpcd -n $WLAN 2>/dev/null || true
else
	log "WARN not associated after 30s"
fi

ip -4 addr show $WLAN | tee -a "$LOG"
log "WIFI_READY"

if ins skwbt; then
	sleep 1
	hciconfig hci0 up 2>/dev/null || true
	hciconfig hci0 piscan 2>/dev/null || true
	if hciconfig hci0 2>/dev/null | grep -q 'UP RUNNING'; then
		log "BLE_READY hci0"
	else
		log "BLE_WARN hci0 not UP"
	fi
else
	log "BLE_SKIP skwbt not loaded"
fi

exit 0
