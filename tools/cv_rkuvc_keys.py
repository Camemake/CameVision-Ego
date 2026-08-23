#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run("""
echo === SECTION KEYS ===
strings /oem/usr/bin/rk_mpi_uvc | grep -E '^[a-z0-9_.]+$' | grep -iE 'venc|video|uvc|isp|vi\\.|vpss|common|h264|mjpeg|param' | sort -u | head -80
echo === BRACKET ===
strings /oem/usr/bin/rk_mpi_uvc | grep '\\[' | grep -v '\\[' | head
strings /oem/usr/bin/rk_mpi_uvc | grep -E '^\\[' | sort -u
echo === video.source ===
strings /oem/usr/bin/rk_mpi_uvc | grep 'video.source'
echo === venc_cfg ===
strings /oem/usr/bin/rk_mpi_uvc | grep venc_cfg
echo === SAMPLE LINES ===
strings /oem/usr/bin/rk_mpi_uvc | grep -E 'enable_|fps =|gop|bps|1920|1200|param_init' | head -50
echo === JSON ===
ls /oem/usr/share /etc | grep -iE 'uvc|mpi'
find /oem /etc /usr/share -name '*uvc*' -o -name '*venc*' 2>/dev/null | head -30
""", wait=10))
