#!/bin/sh
# CameVision Single D1 RGB (gpio-leds, common-anode, active-low).
# Live DT: status:red default-trigger=panic, status:green default-state=on.
# Force healthy userspace look: green = powered/OK, red/blue off.
# Do not use heartbeat/mmc/timer (those look like a fault during boot).
LED=/sys/class/leds

set_led() {
	name=$1
	trig=$2
	bri=$3
	[ -e "$LED/$name/trigger" ] || return 0
	echo "$trig" > "$LED/$name/trigger"
	echo "$bri" > "$LED/$name/brightness"
}

set_led status:red none 0
set_led status:green none 1
set_led status:blue none 0
# Aura leftover name, if a DTB still registers it
set_led work-led none 0
exit 0
