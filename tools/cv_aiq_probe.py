#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
echo === UPTIME ===
cat /proc/uptime
echo === IQ PATHS ===
ls -l /etc/iqfiles /oem/usr/share/iqfiles /usr/share/iqfiles 2>/dev/null
ls /etc/iqfiles 2>/dev/null
ls /oem/usr/share/iqfiles 2>/dev/null
echo === RKAIQ BINS ===
ls /oem/usr/bin | grep -iE 'rkaiq|iq|tool_server|j2s'
ls /usr/bin | grep -iE 'rkaiq|iq|tool_server|j2s'
echo === MEDIA ===
ls /dev/media*
for m in /dev/media0 /dev/media1 /dev/media2; do
  echo -- $m --
  media-ctl -d $m -p 2>/dev/null | head -25
done
echo === VIDEO ISP ===
for n in /sys/class/video4linux/video*; do echo $(basename $n) $(cat $n/name); done | grep -iE 'isp|stats|params'
echo === 3A / TOOL ===
ps | grep -E 'rkaiq|tool_server' | grep -v grep
rkaiq_3A_server -h 2>&1 | head -30
rkaiq_tool_server -h 2>&1 | head -30
echo === SENSOR ===
dmesg | grep -iE 'sc233|233hgs' | tail -8
echo === RKAIQ LOG ===
tail -20 /userdata/rkaiq.log 2>/dev/null
""", wait=14))
