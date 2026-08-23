#!/bin/sh
# CameVision Single — LSM6DSV on SPI1. Read-only sysfs dump. No gadget changes.
LOG=/userdata/imu.log
: > "$LOG"
log() { echo "$(date +%T) $*" | tee -a "$LOG"; }

log "spi devices:"
ls -l /sys/bus/spi/devices 2>/dev/null | tee -a "$LOG"
for d in /sys/bus/spi/devices/spi*; do
	[ -e "$d" ] || continue
	echo "--- $d ---" | tee -a "$LOG"
	cat "$d/uevent" 2>/dev/null | tee -a "$LOG"
	ls -l "$d/driver" 2>/dev/null | tee -a "$LOG"
done

found=
for d in /sys/bus/iio/devices/iio:device*; do
	[ -e "$d/name" ] || continue
	name=$(cat "$d/name")
	log "iio $(basename "$d") name=$name"
	echo "$name" | grep -qi lsm6 || continue
	found=$d
	for f in in_accel_x_raw in_accel_y_raw in_accel_z_raw \
		in_anglvel_x_raw in_anglvel_y_raw in_anglvel_z_raw \
		in_temp_raw; do
		if [ -f "$d/$f" ]; then
			echo "  $f=$(cat "$d/$f")" | tee -a "$LOG"
		fi
	done
done

if [ -z "$found" ]; then
	log "no LSM6 IIO device yet"
	# Last resort: bind spidev so userspace can talk to SPI1.0 after DTB move.
	if [ -e /sys/bus/spi/devices/spi1.0 ] && [ ! -e /sys/bus/spi/devices/spi1.0/driver ]; then
		echo spidev > /sys/bus/spi/devices/spi1.0/driver_override 2>/dev/null || true
		echo spi1.0 > /sys/bus/spi/drivers/spidev/bind 2>/dev/null || true
		log "spidev bind attempted: $(ls /dev/spidev1.0 2>/dev/null || echo none)"
	fi
	exit 1
fi
log "IMU_READY $found"
exit 0
