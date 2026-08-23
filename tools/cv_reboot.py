#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run
try:
    print(run("sync; sleep 1; reboot", wait=2))
except Exception as e:
    print("reboot issued:", e)
