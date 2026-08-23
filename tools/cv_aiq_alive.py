#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run
print(run(r"""
echo === ALIVE ===
ps | grep -E 'rkaiq_3A|rkaiq_tool' | grep -v grep
echo === 3A TAIL ===
tail -c 1500 /userdata/rkaiq.log
echo === INIT_ENS ===
grep -n 'AiqCamHw_start\|sysctl_start\|sysctl_stop\|wait' /userdata/rkaiq.log | tail -15
""", wait=6))
