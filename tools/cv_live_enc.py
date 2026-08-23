#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
echo === VIDEO NAMES ===
for n in /sys/class/video4linux/video*; do echo $(basename $n) $(cat $n/name); done
echo === S99 ===
head -40 /etc/init.d/S99camevision 2>/dev/null
echo === PUMP SH ===
cat /userdata/camevision-uvc-pump.sh
echo === MPI HELP ===
/oem/usr/bin/mpi_enc_test -h 2>&1 | head -60
echo === FFMPEG ENC ===
ffmpeg -hide_banner -encoders 2>/dev/null | grep -iE '264|mjpeg|mpp'
echo === V4L2M2M DEV ===
for n in /sys/class/video4linux/video*; do
  echo $(basename $n) $(cat $n/name)
done
echo === EXTCON ===
cat /sys/class/extcon/extcon0/state 2>/dev/null
for i in 0 1 2 3 4 5; do
  n=/sys/class/extcon/extcon0/cable.$i/name
  s=/sys/class/extcon/extcon0/cable.$i/state
  [ -e "$n" ] && echo $i $(cat $n)=$(cat $s)
done
echo === STRINGS RGB ===
strings /oem/usr/bin/rk_mpi_uvc | grep -E 'RGB|uvc_rgb|device_name|Please configure' | head -30
""", wait=12))
