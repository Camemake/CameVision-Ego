#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd: str) -> None:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


sh(r"""
for n in 8 9 10 130 131; do
  [ -d /sys/class/gpio/gpio$n ] && echo $n > /sys/class/gpio/unexport
done
echo sc233hgs-avdd > /sys/bus/platform/drivers/reg-fixed-voltage/bind
echo sc233hgs-dvdd > /sys/bus/platform/drivers/reg-fixed-voltage/bind
echo vcc1v5-cam > /sys/bus/platform/drivers/reg-fixed-voltage/bind
echo restored
cat /sys/kernel/debug/gpio | sed -n '1,16p'
""")
