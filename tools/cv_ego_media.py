#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd: str) -> None:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


sh("echo === entities ===")
for m in range(7):
    sh(f"echo ---- media{m}; media-ctl -d /dev/media{m} -p 2>/dev/null | grep 'entity'")

sh("echo === try open ===")
sh("python3 -c \"import os,errno\n"
   "for d in ('/dev/video1','/dev/video12','/dev/video24','/dev/video32'):\n"
   "  try:\n"
   "    fd=os.open(d,os.O_RDWR)\n"
   "    print(d,'ok',fd); os.close(fd)\n"
   "  except OSError as e:\n"
   "    print(d,'FAIL',e.errno,e.strerror)\n\"")

sh("echo === isp24 ===")
sh("v4l2-ctl -d /dev/video24 --list-formats-ext 2>&1 | head -30")
sh("v4l2-ctl -d /dev/video32 --list-formats-ext 2>&1 | head -30")
