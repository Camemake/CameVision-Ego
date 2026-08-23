#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
echo === PROCS ===
ps | grep -E 'rkaiq|uvc-h264|rk_mpi_uvc|v4l2-ctl' | grep -v grep
echo === 3A LOG KEY ===
grep -E 'sysctl|wait stream|engine|success|error|ERR:|iq:' /userdata/rkaiq.log | tail -30
echo === TOOL LISTEN ===
netstat -lptu 2>/dev/null | grep -iE 'tool|5543|8000|8080|5542|rkaiq' || true
ss -lptu 2>/dev/null | head -20
echo === TOOL LOG TAIL ===
tail -c 1200 /userdata/rkaiq-tool.log
echo === FILES ===
ls -l /userdata/camevision-aiq.sh /userdata/iqfiles/*.json /oem/usr/share/iqfiles/sc233hgs*
echo === UDC ===
cat /sys/class/udc/21500000.usb/state 2>/dev/null
echo === STREAMON TEST ===
if ! ps | grep -q '[v]4l2-ctl.*video13'; then
  v4l2-ctl -d /dev/video13 --set-fmt-video=width=1920,height=1200,pixelformat=NV12
  timeout 4 v4l2-ctl -d /dev/video13 --stream-mmap=4 --stream-count=20 --stream-poll
  echo stream_rc=$?
else
  echo video13 already streaming
fi
sleep 1
echo === 3A AFTER STREAM ===
grep -E 'sysctl|wait stream|engine|apply|success|error' /userdata/rkaiq.log | tail -20
echo === RKISP AFTER ===
sed -n '1,80p' /proc/rkisp-vir0
""", wait=16))
