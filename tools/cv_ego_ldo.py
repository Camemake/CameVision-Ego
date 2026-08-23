#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd: str) -> None:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


sh("echo === map ===; for r in /sys/class/regulator/regulator.*; do echo $(basename $r) $(cat $r/name); done")
sh("echo === drivers ===; ls /sys/bus/platform/drivers/reg-fixed-voltage")
sh("echo === unbind cam ldos ===")
sh("echo sc233hgs-avdd > /sys/bus/platform/drivers/reg-fixed-voltage/unbind; echo avdd:$?")
sh("echo sc233hgs-dvdd > /sys/bus/platform/drivers/reg-fixed-voltage/unbind; echo dvdd:$?")
sh("echo vcc1v5-cam > /sys/bus/platform/drivers/reg-fixed-voltage/unbind; echo 15:$?")
sh("echo === gpio after unbind ===; cat /sys/kernel/debug/gpio | sed -n '1,20p'")
