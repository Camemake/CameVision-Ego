#!/bin/sh
# CameVision Single — Seekwave SWT6621S / VS6621S80 AT channel.
# Source: HW_SWT6621-S_Wi-Fi认证测试操作指南.docx
#         BT_AT 命令说明文档_0511.pdf
#         BT_认证定频AT指令列表_V1.1.xlsx
#
# Linux NPI: do NOT load skwbt.ko. /dev/ATC comes from skw_sdio_lite after
# firmware. Wi-Fi NPI: AT+wifimpset=1 within 1 minute of the driver coming up,
# with wlan0 down. BT NPI: AT+PLDBTEN then AT+BTRESET before every TX/RX.
#
# Usage: swt6621.sh <cmd> [args]
#   load                 copy F26.26.3.1 firmware from /userdata/swt6621_fw
#                        and insmod /userdata/swt6621-rt52/skw_sdio_lite.ko
#                        (must be compiled from H26.27.6.1 against 6.1.141-rt52)
#   listen               cat /dev/ATC in background
#   at 'AT+...'          send one command (Linux: no CR)
#   wifi-npi             enter Wi-Fi engineering mode
#   wifi-tx <preset>     11b-1m-ch1 | 11b-1m-ch13 | 11g-6m-ch1 | n20-mcs0-ch1 | ax20-ch1
#   wifi-rx <preset>     24g-20-ch1 | 24g-20-ch13 | 5g-20-ch36 | 5g-20-ch165
#   wifi-cw <ch>         single tone (reboot after wlan0 down, then npi first)
#   wifi-rxinfo          AT+WIFIPHYGETINFO=0,1
#   bt-npi               AT+PLDBTEN (start BT AT thread, no skwbt)
#   bt-reset             AT+BTRESET
#   bt-tx <preset>       br-dh1 | br-dh5 | edr-2dh5 | edr-3dh5 | le-1m | le-2m | le-s8 | le-s2
#   bt-hop <preset>      same names, last param 0xeeee
#   bt-rx <preset>       classic-br | classic-edr | le-1m | le-2m | le-coded
#   bt-rxdata            classic RX counters
#   bt-lerxdata          LE RX counters
#   bt-eut               signalling DUT mode
#   bt-cw [ch]           single tone, default ch 0
#   bt-tpc               default power table from the list

set -e
ATC=/dev/ATC
LOG=/userdata/swt6621-atc.log
PIDF=/tmp/swt6621-atc.pid

die() { echo "swt6621: $*" >&2; exit 1; }

need_atc() {
	[ -e "$ATC" ] || die "no $ATC — skw_sdio_lite is not bound. SDIO 1FFE:6621 is up; this kernel (6.1.141-rt52 PREEMPT_RT) rejects Aura skw_sdio_lite.ko (__mutex_init). Rebuild that module against rt52, then: $0 load"
}

listen() {
	need_atc
	if [ -f "$PIDF" ] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
		return 0
	fi
	: > "$LOG"
	cat "$ATC" >>"$LOG" 2>/dev/null &
	echo $! >"$PIDF"
	sleep 0.2
}

at() {
	need_atc
	cmd=$1
	[ -n "$cmd" ] || die "empty AT command"
	listen
	printf '%s' "$cmd" >"$ATC"
	sleep 0.4
	if [ -s "$LOG" ]; then
		tail -20 "$LOG"
	else
		# docs: if no auto-print, poke the channel twice
		cat "$ATC" 2>/dev/null || true
		cat "$ATC" 2>/dev/null || true
	fi
}

load() {
	OEM=/oem/usr/ko
	# Real PREEMPT_RT build of H26.27.6.1 — not the vermagic-patched Aura kos.
	KO=/userdata/swt6621-rt52
	FW=/userdata/swt6621_fw
	mkdir -p /lib/firmware
	if [ -d "$FW" ]; then
		cp -f "$FW"/* /lib/firmware/ 2>/dev/null || true
		if [ -e /sys/module/firmware_class/parameters/path ]; then
			printf '%s' "$FW" > /sys/module/firmware_class/parameters/path
			echo "firmware_path $FW"
		fi
	elif [ -d "$OEM/vs6621_fw" ]; then
		cp -f "$OEM"/vs6621_fw/* /lib/firmware/ || true
	fi
	if [ ! -f /lib/firmware/SWT6621S_NV_SDIO.bin ] && [ -f /lib/firmware/SWT6621S_NV_SDIO_ALONE.bin ]; then
		cp -f /lib/firmware/SWT6621S_NV_SDIO_ALONE.bin /lib/firmware/SWT6621S_NV_SDIO.bin
	fi
	if [ ! -f /lib/firmware/SEEKWAVE_NV_SWT6621S.bin ] && [ -f /lib/firmware/SWT6621S_NV_SDIO_ALONE.bin ]; then
		cp -f /lib/firmware/SWT6621S_NV_SDIO_ALONE.bin /lib/firmware/SEEKWAVE_NV_SWT6621S.bin
	fi
	id=$(cat /sys/bus/sdio/devices/*/uevent 2>/dev/null | grep '^SDIO_ID=' | head -1)
	echo "sdio $id"
	echo "$id" | grep -q '1FFE:6621' || echo "WARN expected 1FFE:6621"
	# NPI does not need swt6621s_wifi / skwbt. STA/AP does.
	for m in skw_sdio_lite; do
		if lsmod | awk '{print $1}' | grep -qx "$m"; then
			echo "already $m"
			continue
		fi
		path=
		[ -f "$KO/${m}.ko" ] && path=$KO/${m}.ko
		[ -z "$path" ] && [ -f "$KO/${m}_rt52.ko" ] && path=$KO/${m}_rt52.ko
		[ -n "$path" ] || die "missing $KO/${m}.ko — build H26.27.6.1 against 6.1.141-rt52 PREEMPT_RT (Aura/wifi-rt52 kos export __mutex_init and will not load)"
		echo "insmod $path"
		insmod "$path" || die "insmod $m failed (PREEMPT_RT ABI). Need $m built for 6.1.141-rt52."
	done
	n=0
	while [ $n -lt 15 ]; do
		[ -e "$ATC" ] && break
		sleep 1
		n=$((n + 1))
	done
	[ -e "$ATC" ] || die "firmware/driver ran but $ATC never appeared"
	echo "ATC_READY $ATC"
	ls -l "$ATC"
}

wifi_npi() {
	# Within 1 minute of driver/firmware coming up. wlan0 must be down.
	if [ -d /sys/class/net/wlan0 ]; then
		ip link set wlan0 down 2>/dev/null || true
	fi
	at "AT+wifimpset=1"
}

wifi_tx() {
	case "$1" in
		11b-1m-ch1)  at "AT+WIFIPHYTX=1,0x2,0,0,1,0,0x20,0X8000002A,0,1500,0,0,0" ;;
		11b-1m-ch13) at "AT+WIFIPHYTX=1,0x2,0,0,13,0,0x20,0X8000002A,0,1500,0,0,0" ;;
		11b-11m-ch1) at "AT+WIFIPHYTX=1,0x2,0,0,1,0,0x23,0X8000002A,0,1500,0,0,0" ;;
		11g-6m-ch1)  at "AT+WIFIPHYTX=1,0x2,0,0,1,0,0x30,0X80000032,0,5000,0,0,0" ;;
		n20-mcs0-ch1) at "AT+WIFIPHYTX=1,0x2,0,0,1,0,0x40,0X80000032,0,5000,0,0,0" ;;
		n20-mcs7-ch1) at "AT+WIFIPHYTX=1,0x2,0,0,1,0,0x47,0X80000032,0,5000,0,0,0" ;;
		demo)        at "AT+WIFIPHYTX=1,0,0,0,6,0,0x20,0,0,1500,0,0,0" ;;
		*) die "wifi-tx preset: 11b-1m-ch1 | 11b-1m-ch13 | 11b-11m-ch1 | 11g-6m-ch1 | n20-mcs0-ch1 | n20-mcs7-ch1 | demo" ;;
	esac
}

wifi_rx() {
	case "$1" in
		24g-20-ch1)  at "AT+WIFIPHYRX=1,0,0,0,1,0,0,0,0,0,1" ;;
		24g-20-ch13) at "AT+WIFIPHYRX=1,0,0,0,13,0,0,0,0,0,1" ;;
		24g-40-ch3)  at "AT+WIFIPHYRX=1,0,1,0,3,0,0,0,0,0,1" ;;
		5g-20-ch36)  at "AT+WIFIPHYRX=1,0,0,0,36,0,0,0,0,0,1" ;;
		5g-20-ch165) at "AT+WIFIPHYRX=1,0,0,0,165,0,0,0,0,0,1" ;;
		demo)        at "AT+WIFIPHYRX=2,0,0,0,1,0,0,0,0,0,1" ;;
		*) die "wifi-rx preset: 24g-20-ch1 | 24g-20-ch13 | 24g-40-ch3 | 5g-20-ch36 | 5g-20-ch165 | demo" ;;
	esac
}

wifi_cw() {
	ch=${1:-1}
	at "AT+WIFIPHYTTG=0,$ch,0,0,469,0,0,1,20,0,0"
}

bt_npi() {
	# Do not insmod skwbt.ko for this path.
	if lsmod | awk '{print $1}' | grep -qx skwbt; then
		echo "WARN skwbt is loaded; docs say unload it for Linux NPI (hciconfig hci0 down if needed)"
		hciconfig hci0 down 2>/dev/null || true
		hciconfig hci1 down 2>/dev/null || true
	fi
	if [ -d /sys/class/net/wlan0 ]; then
		echo "WARN stop Wi-Fi scan before BT NPI"
		ip link set wlan0 down 2>/dev/null || true
	fi
	at "AT+PLDBTEN"
}

bt_tx() {
	at "AT+BTRESET"
	case "$1" in
		br-dh1)    at "AT+BTTXTESTENA=4,0,4,27,1,5,0" ;;
		br-dh3)    at "AT+BTTXTESTENA=4,0,11,183,1,5,0" ;;
		br-dh5)    at "AT+BTTXTESTENA=4,0,15,339,1,5,0" ;;
		edr-2dh1)  at "AT+BTTXTESTENA=4,0,18,54,1,5,0" ;;
		edr-2dh5)  at "AT+BTTXTESTENA=4,0,27,679,1,5,0" ;;
		edr-3dh5)  at "AT+BTTXTESTENA=4,0,28,1021,1,5,0" ;;
		le-1m)     at "AT+BTLETXTESTENA=0,37,0,1" ;;
		le-2m)     at "AT+BTLETXTESTENA=0,37,0,2" ;;
		le-s8)     at "AT+BTLETXTESTENA=0,37,0,3" ;;
		le-s2)     at "AT+BTLETXTESTENA=0,37,0,4" ;;
		*) die "bt-tx: br-dh1 | br-dh3 | br-dh5 | edr-2dh1 | edr-2dh5 | edr-3dh5 | le-1m | le-2m | le-s8 | le-s2" ;;
	esac
}

bt_hop() {
	at "AT+BTRESET"
	case "$1" in
		br-dh1)   at "AT+BTTXTESTENA=4,0,4,27,1,5,0xeeee" ;;
		br-dh5)   at "AT+BTTXTESTENA=4,0,15,339,1,5,0xeeee" ;;
		edr-3dh5) at "AT+BTTXTESTENA=4,0,28,1021,1,5,0xeeee" ;;
		*) die "bt-hop: br-dh1 | br-dh5 | edr-3dh5" ;;
	esac
}

bt_rx() {
	at "AT+BTRESET"
	case "$1" in
		classic-br)  at "AT+BTRXTESTENA=0,0x0F,0,0x6dc6,0x967e" ;;
		classic-edr) at "AT+BTRXTESTENA=0,0x1c,0,0x6dc6,0x967e" ;;
		le-1m)       at "AT+BTLERXTESTENA=0,1,0" ;;
		le-2m)       at "AT+BTLERXTESTENA=0,2,0" ;;
		le-coded)    at "AT+BTLERXTESTENA=0,3,0" ;;
		*) die "bt-rx: classic-br | classic-edr | le-1m | le-2m | le-coded" ;;
	esac
}

cmd=$1
shift || true
case "$cmd" in
	load) load ;;
	listen) listen; echo "listening pid=$(cat $PIDF) log=$LOG" ;;
	at) at "$1" ;;
	wifi-npi) wifi_npi ;;
	wifi-tx) wifi_tx "$1" ;;
	wifi-rx) wifi_rx "$1" ;;
	wifi-cw) wifi_cw "$1" ;;
	wifi-rxinfo) at "AT+WIFIPHYGETINFO=0,1" ;;
	bt-npi) bt_npi ;;
	bt-reset) at "AT+BTRESET" ;;
	bt-tx) bt_tx "$1" ;;
	bt-hop) bt_hop "$1" ;;
	bt-rx) bt_rx "$1" ;;
	bt-rxdata) at "AT+BTRXGETDATA=" ;;
	bt-lerxdata) at "AT+BTLERXGETDATA=" ;;
	bt-eut)
		at "AT+PLDBTEN"
		at "AT+BTRESET"
		at "AT+BTEUTENA"
		at "AT+BTEUTEVTFILTER"
		;;
	bt-cw)
		ch=${1:-0}
		at "AT+PLDBTEN"
		at "AT+WIFIMPSET=1"
		at "AT+BTRESET"
		at "AT+BTTXTESTENA=4,$ch,28,1,0,58,0xffff"
		;;
	bt-tpc)
		at "AT+BTTPC=0X02FFFCF9,0XFCF90805,0X080502FF,0X00000000,0X00000000,0X00000000,0X00000000,0X00000000,0X00000000"
		;;
	""|-h|--help|help)
		sed -n '2,28p' "$0"
		;;
	*) die "unknown cmd '$cmd' (try: $0 help)" ;;
esac
