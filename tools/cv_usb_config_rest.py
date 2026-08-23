#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run("""
wc -l /oem/usr/bin/usb_config.sh
echo === bottom ===
sed -n '120,400p' /oem/usr/bin/usb_config.sh
""", wait=8))
