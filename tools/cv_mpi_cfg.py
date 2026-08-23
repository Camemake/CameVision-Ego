#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run("""
echo === uvc_mpi_cfg.conf ===
wc -l /oem/usr/share/uvc_mpi_cfg.conf /etc/uvc_mpi_cfg.conf /tmp/uvc_mpi_cfg.conf 2>/dev/null
ls -l /oem/usr/share/uvc_mpi_cfg.conf
echo ---
cat /oem/usr/share/uvc_mpi_cfg.conf
""", wait=8))
