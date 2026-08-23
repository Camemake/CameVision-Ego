#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd):
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print("===", cmd[:80])
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


sh("uname -a; cat /proc/device-tree/model; echo; cat /proc/cpuinfo | grep Serial")
sh("echo === i2c ===; ls /sys/bus/i2c/devices; echo === spi ===; ls /sys/bus/spi/devices 2>/dev/null; echo === iio ===; ls /sys/bus/iio/devices 2>/dev/null")
sh("echo === video ===; ls /dev/video* 2>/dev/null; echo === media ===; ls /dev/media* 2>/dev/null")
sh("echo === mmc ===; ls /dev/mmcblk* 2>/dev/null; cat /proc/partitions")
sh("echo === usb ===; cat /sys/class/udc/21500000.usb/state 2>/dev/null; cat /sys/kernel/config/usb_gadget/rockchip/strings/0x409/product 2>/dev/null")
sh("echo === wlan ===; ip -4 addr show wlan0 2>/dev/null | grep inet; ls /sys/class/power_supply 2>/dev/null")
sh("dmesg | grep -iE 'sc233|imx|sensor|lsm6|imu|mmc1|sdcard|battery|rkisp' | tail -n 40")
