#!/usr/bin/env python3
import subprocess
ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd):
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


sh("for d in /sys/bus/i2c/devices/0-0027 /sys/bus/i2c/devices/2-0052 /sys/bus/i2c/devices/3-0030 /sys/bus/i2c/devices/4-0030; do echo ---- $d; cat $d/name 2>/dev/null; cat $d/of_node/name 2>/dev/null; echo; done")
sh("echo === iio ===; cat /sys/bus/iio/devices/iio:device0/name 2>/dev/null; ls /sys/bus/iio/devices/iio:device0 2>/dev/null | head")
sh("echo === i2c scan names ===; ls -l /sys/bus/i2c/devices")
sh("echo === mmc hosts ===; ls /sys/class/mmc_host; cat /sys/class/mmc_host/mmc*/name 2>/dev/null")
sh("echo === power ===; ls /sys/class/power_supply; ls /sys/class/hwmon 2>/dev/null")
