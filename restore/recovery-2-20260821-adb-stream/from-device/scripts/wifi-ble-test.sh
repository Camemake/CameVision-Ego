#!/bin/sh
# CameVision Single — STA join + BLE bring-up. Do not touch USB / rockit / adbd.
set -x
KO=/userdata/swt6621-rt52
FW=/userdata/swt6621_fw
LOG=/userdata/wifi-ble-test.log
CONF=/userdata/wpa_camevision.conf
WLAN=wlan0

: > "$LOG"
log() { echo "$@" | tee -a "$LOG"; }

already() { lsmod | awk '{print $1}' | grep -qx "$1"; }

ins() {
	mod=$1
	if already "$mod"; then
		log "already $mod"
		return 0
	fi
	if [ -f "$KO/${mod}.ko" ]; then
		p=$KO/${mod}.ko
	else
		log "MISSING $mod"
		return 1
	fi
	log "insmod $p"
	if insmod "$p"; then
		log "OK $mod"
		return 0
	fi
	log "FAIL $mod rc=$?"
	dmesg | tail -15 | tee -a "$LOG"
	return 1
}

if [ -e /sys/module/firmware_class/parameters/path ]; then
	printf %s "$FW" > /sys/module/firmware_class/parameters/path
fi
log "firmware_path=$(cat /sys/module/firmware_class/parameters/path 2>/dev/null)"
log "sdio=$(cat /sys/bus/sdio/devices/mmc2:0001:1/uevent 2>/dev/null | grep SDIO_ID)"

ins cfg80211 || exit 10
ins libarc4 || true
ins mac80211 || exit 11
ins gf128mul || true
ins ctr || true
ins ccm || true
ins aes_generic || true
ins skw_sdio_lite || exit 12
sleep 1
ins swt6621s_wifi || exit 13

n=0
while [ $n -lt 25 ]; do
	[ -d /sys/class/net/$WLAN ] && break
	sleep 1
	n=$((n + 1))
done
if [ ! -d /sys/class/net/$WLAN ]; then
	log "NO_WLAN"
	ls /sys/class/net | tee -a "$LOG"
	lsmod | tee -a "$LOG"
	dmesg | grep -iE 'skw|swt6621|cfg80211|wlan' | tail -40 | tee -a "$LOG"
	exit 20
fi
ip link set $WLAN up
log "wlan0_up"
iw dev $WLAN scan 2>>"$LOG" | grep -E 'SSID:|signal:|freq:' | head -40 | tee -a "$LOG"

killall wpa_supplicant 2>/dev/null || true
rm -rf /var/run/wpa_supplicant
mkdir -p /var/run/wpa_supplicant
wpa_supplicant -B -i $WLAN -c "$CONF" -D nl80211 -f /userdata/wpa.log
st=
n=0
while [ $n -lt 30 ]; do
	st=$(wpa_cli -i $WLAN status 2>/dev/null | grep wpa_state= | cut -d= -f2)
	log "wpa_state=$st"
	[ "$st" = "COMPLETED" ] && break
	sleep 1
	n=$((n + 1))
done
if [ "$st" = "COMPLETED" ]; then
	udhcpc -i $WLAN -n -q -t 12 >>"$LOG" 2>&1 || true
fi
ip -4 addr show $WLAN | tee -a "$LOG"
ip route | tee -a "$LOG"
gw=$(ip route | awk '/default/ {print $3; exit}')
if [ -n "$gw" ]; then
	ping -c 3 -W 2 "$gw" | tee -a "$LOG"
	log "PING_GW=$?"
else
	log "NO_DEFAULT_ROUTE"
fi
wpa_cli -i $WLAN status | tee -a "$LOG"

ins skwbt || true
sleep 1
ls /sys/class/bluetooth 2>/dev/null | tee -a "$LOG"
hciconfig -a 2>/dev/null | tee -a "$LOG"
for h in hci0 hci1; do
	hciconfig $h up 2>/dev/null || true
	hciconfig $h piscan 2>/dev/null || true
done
hciconfig -a 2>/dev/null | tee -a "$LOG"
rm -f /userdata/ble-scan.log
hcitool lescan > /userdata/ble-scan.log 2>&1 &
bp=$!
sleep 8
kill $bp 2>/dev/null || true
wait $bp 2>/dev/null || true
log "BLE_SCAN"
cat /userdata/ble-scan.log | tee -a "$LOG"
log "DONE"
lsmod | tee -a "$LOG"
exit 0
