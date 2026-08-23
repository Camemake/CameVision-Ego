#!/bin/sh
# CameVision Single — VS6621S80 Wi-Fi only.
# Do not insmod rockit, kmpp, or sensor kos. Do not touch the USB gadget.
set -e

KO=/userdata/swt6621-rt52
OEMKO=/oem/usr/ko
LOG=/userdata/wifi.log
FWDIR=/lib/firmware
FWSRC=/userdata/swt6621_fw
WLAN=wlan0

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
		log "FAIL $mod — this kernel is PREEMPT_RT (6.1.141-rt52)."
		log "Aura/non-RT modules cannot load (unknown symbol __mutex_init)."
		log "Need cfg80211/mac80211/skw_sdio_lite/swt6621s_wifi built against rt52."
		return 1
	fi
}

mkdir -p "$(dirname "$LOG")" /var/run/wpa_supplicant
: > "$LOG"

if [ ! -e /sys/bus/sdio/devices/mmc2:0001:1 ]; then
	log "no SDIO function — VS6621 not enumerated"
	exit 1
fi
id=$(grep '^SDIO_ID=' /sys/bus/sdio/devices/mmc2:0001:1/uevent | cut -d= -f2)
log "sdio id=$id"
[ "$id" = "1FFE:6621" ] || log "WARN unexpected SDIO_ID $id"

mkdir -p "$FWDIR"
if [ -d "$FWSRC" ]; then
	cp -f "$FWSRC"/* "$FWDIR"/ 2>/dev/null || true
	if [ -e /sys/module/firmware_class/parameters/path ]; then
		printf '%s' "$FWSRC" > /sys/module/firmware_class/parameters/path
	fi
elif [ -d "$OEMKO/vs6621_fw" ]; then
	cp -f "$OEMKO"/vs6621_fw/* "$FWDIR"/ 2>/dev/null || true
fi
if [ ! -f "$FWDIR/SWT6621S_NV_SDIO.bin" ] && [ -f "$FWDIR/SWT6621S_NV_SDIO_ALONE.bin" ]; then
	cp -f "$FWDIR/SWT6621S_NV_SDIO_ALONE.bin" "$FWDIR/SWT6621S_NV_SDIO.bin"
fi
if [ ! -f "$FWDIR/SEEKWAVE_NV_SWT6621S.bin" ] && [ -f "$FWDIR/SWT6621S_NV_SDIO_ALONE.bin" ]; then
	cp -f "$FWDIR/SWT6621S_NV_SDIO_ALONE.bin" "$FWDIR/SEEKWAVE_NV_SWT6621S.bin"
fi

ins cfg80211
ins libarc4 || true
ins mac80211
ins ctr || true
ins ccm || true
ins libaes || true
ins aes_generic || true
ins skw_sdio_lite
sleep 1
ins swt6621s_wifi
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
	ls /sys/class/net | tee -a "$LOG"
	lsmod | tee -a "$LOG"
	exit 2
fi

ip link set $WLAN up
log "wlan0 up"

CONF=/userdata/wpa_camevision.conf
if [ -f "$CONF" ]; then
	killall wpa_supplicant 2>/dev/null || true
	rm -rf /var/run/wpa_supplicant
	mkdir -p /var/run/wpa_supplicant
	wpa_supplicant -B -i $WLAN -c "$CONF" -D nl80211 -f /userdata/wpa.log
	n=0
	while [ $n -lt 25 ]; do
		st=$(wpa_cli -i $WLAN status 2>/dev/null | grep wpa_state= | cut -d= -f2)
		log "wpa_state=$st"
		[ "$st" = "COMPLETED" ] && break
		sleep 1
		n=$((n + 1))
	done
	if [ "$st" = "COMPLETED" ]; then
		udhcpc -i $WLAN -n -q -t 10 >>"$LOG" 2>&1 || true
	fi
fi

ip -4 addr show $WLAN | tee -a "$LOG"
log "WIFI_READY"

# BLE (same VS6621 / SWT6621 chip). Safe after Wi-Fi is up.
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
