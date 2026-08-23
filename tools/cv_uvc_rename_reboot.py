#!/usr/bin/env python3
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import HOST, run


def ping_ok():
    r = subprocess.run(
        ["ping", "-n", "1", "-w", "800", HOST],
        capture_output=True,
        text=True,
    )
    return "TTL=" in (r.stdout or "")


def telnet_ok():
    try:
        s = socket.create_connection((HOST, 2323), 2)
        s.close()
        return True
    except OSError:
        return False


def win_uvc():
    ps = r"""Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_2207&PID_0016' -and $_.Present } | ForEach-Object { '{0}|{1}|{2}' -f $_.Status, $_.FriendlyName, $_.InstanceId }"""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
    )
    return r.stdout.strip()


print("=== reboot ===")
try:
    run("sync; reboot -f", wait=1)
except Exception as e:
    print("reboot", e)

time.sleep(12)
t0 = time.time()
last = ""
while time.time() - t0 < 90:
    w = win_uvc()
    if w and w != last:
        print("WIN", int(time.time() - t0), w)
        last = w
    p, t = ping_ok(), telnet_ok()
    print("t=%ds ping=%s telnet=%s" % (int(time.time() - t0), p, t))
    if p and t and time.time() - t0 > 18:
        break
    time.sleep(3)

time.sleep(8)
print(
    run(
        r"""
echo UP=$(cat /proc/uptime)
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
G=/sys/kernel/config/usb_gadget/rockchip
echo PROD=$(cat $G/strings/0x409/product)
echo DNAME=$(cat $G/functions/uvc.gs1/device_name)
echo FNAME=$(cat $G/functions/uvc.gs1/function_name)
echo SN=$(cat $G/strings/0x409/serialnumber)
dmesg | grep -E 'device reset|uvc_function_set_alt' | tail -6
cat /userdata/cv-uvc-boot.log | tail -8
""",
        wait=10,
    )
)
print("WIN final", win_uvc() or "(none)")
