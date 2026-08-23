#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

print(run(r"""
echo === ALL ===
v4l2-ctl -d /dev/video28 --all 2>&1 | head -80
echo === HELP FMT ===
v4l2-ctl --help 2>&1 | grep -iE 'fmt-video|formats-out|stream-from' | head
echo === LIST OUT ===
v4l2-ctl -d /dev/video28 --list-formats-out --list-framesizes-out 2>&1 | head -40
""", wait=8))
