#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd: str) -> None:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print("===", cmd[:90])
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


sh("cat /proc/device-tree/model; echo")
sh("ls /sys/bus/i2c/devices; echo ---; cat /sys/bus/i2c/devices/3-0030/name 2>/dev/null; cat /sys/bus/i2c/devices/4-0030/name 2>/dev/null")
sh("ls /dev/video* /dev/media* 2>/dev/null")
sh("dmesg | grep -iE 'sc233|csi2|rkisp|rkcif|dphy|i2c-3|i2c-4|gpio-regulator|vcc2v8|vcc1v2' | tail -n 60")
