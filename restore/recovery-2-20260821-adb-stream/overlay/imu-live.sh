#!/bin/sh
# Live LSM6DSV dump. Finds IIO nodes by name. SI units: m/s^2 and deg/s.
# Usage: imu-live.sh [count] [period_s]
#   count=0 means forever. Default 0 forever, 0.1 s.

n=${1:-0}
dt=${2:-0.1}

A=
G=
for d in /sys/bus/iio/devices/iio:device*; do
	name=$(cat "$d/name" 2>/dev/null) || continue
	case "$name" in
		lsm6dsv_accel) A=$d ;;
		lsm6dsv_gyro)  G=$d ;;
	esac
done

if [ -z "$A" ] || [ -z "$G" ]; then
	echo "IMU not bound (need lsm6dsv_accel + lsm6dsv_gyro)" >&2
	ls /sys/bus/iio/devices 2>/dev/null
	exit 1
fi

# Faster than the 7.5 Hz boot default so motion is visible.
echo 60 > "$A/sampling_frequency" 2>/dev/null || true
echo 60 > "$G/sampling_frequency" 2>/dev/null || true

as=$(cat "$A/in_accel_scale")
gs=$(cat "$G/in_anglvel_scale")
echo "accel=$A gyro=$G  scale_a=$as m/s2/LSB  scale_g=$gs rad/s/LSB  odr=60Hz"
echo "time          ax_mps2   ay_mps2   az_mps2   |a|_g    gx_dps    gy_dps    gz_dps"

i=0
while :; do
	ax=$(cat "$A/in_accel_x_raw")
	ay=$(cat "$A/in_accel_y_raw")
	az=$(cat "$A/in_accel_z_raw")
	gx=$(cat "$G/in_anglvel_x_raw")
	gy=$(cat "$G/in_anglvel_y_raw")
	gz=$(cat "$G/in_anglvel_z_raw")
	t=$(date +%H:%M:%S)
	awk -v t="$t" -v ax="$ax" -v ay="$ay" -v az="$az" -v gx="$gx" -v gy="$gy" -v gz="$gz" \
		-v as="$as" -v gs="$gs" 'BEGIN{
			ax*=as; ay*=as; az*=as
			gx*=gs*57.2957795; gy*=gs*57.2957795; gz*=gs*57.2957795
			g=sqrt(ax*ax+ay*ay+az*az)/9.80665
			printf "%s  %8.3f  %8.3f  %8.3f  %6.3f  %8.2f  %8.2f  %8.2f\n",
				t, ax, ay, az, g, gx, gy, gz
		}'
	i=$((i + 1))
	[ "$n" -gt 0 ] && [ "$i" -ge "$n" ] && break
	sleep "$dt"
done
