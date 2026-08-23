#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run("""
ls -l /usr/bin/python /usr/bin/python3 /bin/python 2>/dev/null
which python python3
cat /tmp/hold-uvc.log
ps | grep 2892 | grep -v grep
echo === rk_mpi_uvc ===
ls -l /oem/usr/bin/rk_mpi_uvc
/oem/usr/bin/rk_mpi_uvc -h 2>&1 | head -40
/oem/usr/bin/rk_mpi_uvc --help 2>&1 | head -40
echo === strings ===
strings /oem/usr/bin/rk_mpi_uvc | grep -iE 'usage|uvc|gadget|/dev/video|help' | head -40
""", wait=8))
