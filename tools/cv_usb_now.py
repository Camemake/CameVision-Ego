#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "0558fa189447bc45"


def sh(cmd):
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="" if (r.stdout or "").endswith("\n") else (r.stdout or "") + "\n")
    if r.stderr:
        print(r.stderr, end="" if r.stderr.endswith("\n") else r.stderr + "\n")
    return r.returncode


sh("echo -n up=; cat /proc/uptime")
sh("echo -n state=; cat /sys/class/udc/21500000.usb/state")
sh("echo -n speed=; cat /sys/class/udc/21500000.usb/current_speed")
sh("echo -n product=; cat /sys/kernel/config/usb_gadget/rockchip/strings/0x409/product")
sh("ls /sys/kernel/config/usb_gadget/rockchip/configs/b.1/")
sh("ps | grep -E 'adbd|rkaiq_3A|v4l2-ctl|uvc-mjpg|telnetd' | grep -v grep")
sh("ip -4 addr show wlan0 | grep inet")
sh("head -4 /etc/init.d/S50usbdevice")
