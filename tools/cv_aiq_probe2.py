#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
echo === MOUNTS ===
mount | grep -E 'oem|userdata|root'
echo === OEM WRITABLE ===
touch /oem/usr/share/iqfiles/.wtest 2>&1
rm -f /oem/usr/share/iqfiles/.wtest
echo === 3A STRINGS ===
strings /oem/usr/bin/rkaiq_3A_server | grep -iE 'usage|iqfile|silent|help|--|sysctl|listen' | head -40
echo === J2S ===
j2s4b_dev -h 2>&1 | head -25
strings /oem/usr/bin/j2s4b_dev | grep -iE 'usage|json|bin|iq' | head -20
echo === TOOL PORT ===
strings /oem/usr/bin/rkaiq_tool_server | grep -iE 'port|5543|5542|8080|listen|:5' | head -25
echo === SSH ===
ps | grep -E 'sshd|dropbear' | grep -v grep
echo === UVC / STREAM ===
ps | grep -E 'rk_mpi_uvc|uvc-h264|isp_grab|hw_rtsp|v4l2-ctl' | grep -v grep
echo === OFFICIAL IQ HEAD ===
head -c 400 /oem/usr/share/iqfiles/imx415_CMK-OT1948-PV1_styleDahP0.json; echo
echo === SENSOR MODULE ===
cat /proc/device-tree/i2c@21120000/sc233hgs@30/rockchip,camera-module-name 2>/dev/null; echo
cat /proc/device-tree/i2c@21120000/sc233hgs@30/rockchip,camera-module-lens-name 2>/dev/null; echo
find /proc/device-tree -name 'rockchip,camera-module-name' 2>/dev/null | while read f; do echo $f; cat $f; echo; done
""", wait=12))
