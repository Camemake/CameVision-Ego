#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd: str) -> None:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


sh("echo === regulators ===; ls /sys/class/regulator; echo; for r in /sys/class/regulator/regulator.*; do echo $(cat $r/name) state=$(cat $r/state 2>/dev/null) uv=$(cat $r/microvolts 2>/dev/null); done")
sh("echo === gpio ===; cat /sys/kernel/debug/gpio 2>/dev/null | head -120")
sh("echo === chips ===; ls /sys/class/gpio; ls /dev/gpiochip*")
sh("echo === i2c ===; which i2cdetect; ls /dev/i2c-*")
sh("echo === i2c3 ===; i2cdetect -y 3 2>/dev/null || echo no_i2cdetect")
sh("echo === i2c4 ===; i2cdetect -y 4 2>/dev/null || echo no_i2cdetect")
