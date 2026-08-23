#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd: str) -> None:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


sh("mount -t debugfs debugfs /sys/kernel/debug 2>/dev/null; echo mounted")
sh("echo === gpiochip labels ===; for c in /sys/class/gpio/gpiochip*; do echo $c base=$(cat $c/base) ngpio=$(cat $c/ngpio) label=$(cat $c/label); done")
sh("echo === debug gpio ===; cat /sys/kernel/debug/gpio")
sh("echo === pinctrl i2c/cam ===; cat /sys/kernel/debug/pinctrl/*/pinmux-pins 2>/dev/null | grep -nE 'i2c3|i2c4|gpio4-a|GPIO4_A' | head -40")
sh("which gpioget gpioset; ls /usr/bin/gpio*")
