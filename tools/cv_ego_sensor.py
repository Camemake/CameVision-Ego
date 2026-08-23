#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd: str) -> None:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


sh("echo === subdev ===; ls -l /dev/v4l-subdev*; echo; for d in /sys/class/video4linux/v4l-subdev*; do echo $(basename $d) $(cat $d/name); done")
sh("echo === i2c driver ===; ls -l /sys/bus/i2c/devices/3-0030 /sys/bus/i2c/devices/4-0030")
sh("echo === dmesg sc233 ===; dmesg | grep -i sc233")
sh("echo === dphy0 ===; media-ctl -d /dev/media1 -p -e rockchip-csi2-dphy0")
sh("echo === dphy1 ===; media-ctl -d /dev/media2 -p -e rockchip-csi2-dphy1")
sh("echo === list-devices ===; v4l2-ctl --list-devices")
