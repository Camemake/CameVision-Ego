#!/usr/bin/env python3
import base64
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import HOST, run

S50 = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\live\S50usbdevice.uvc-rk")


def ping_ok():
    r = subprocess.run(["ping", "-n", "1", "-w", "800", HOST], capture_output=True, text=True)
    return "TTL=" in (r.stdout or "")


def telnet_ok():
    try:
        s = socket.create_connection((HOST, 2323), 2)
        s.close()
        return True
    except OSError:
        return False


def win_uvc():
    ps = r"""Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_2207' -and $_.Present } | ForEach-Object { '{0}|{1}|{2}|{3}' -f $_.Status, $_.Class, $_.FriendlyName, $_.InstanceId }"""
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    return r.stdout.strip()


b64 = base64.b64encode(S50.read_bytes()).decode("ascii")
print("=== disable extra S50 + push ===")
print(run(f"""
mount -o remount,rw / 2>/dev/null
mkdir -p /etc/usbdevice.disabled
mv -f /etc/init.d/S50usbdevice.adb-stock /etc/usbdevice.disabled/ 2>/dev/null
mv -f /etc/init.d/S50usbdevice.bak-uvc /etc/usbdevice.disabled/ 2>/dev/null
ls /etc/init.d/S50*
echo {b64} | base64 -d > /etc/init.d/S50usbdevice
chmod 755 /etc/init.d/S50usbdevice
grep -n dwc3 /etc/init.d/S50usbdevice | head
wc -c /etc/init.d/S50usbdevice
sync
""", wait=10))

print("=== reboot ===")
try:
    run("sync; sleep 1; reboot -f", wait=1)
except Exception as e:
    print("reboot", e)

print("waiting...")
time.sleep(12)
t0 = time.time()
last_win = ""
while time.time() - t0 < 100:
    w = win_uvc()
    if w and w != last_win:
        print("WIN", int(time.time() - t0), w)
        last_win = w
    p, t = ping_ok(), telnet_ok()
    print("t=%ds ping=%s telnet=%s" % (int(time.time() - t0), p, t))
    if p and t and time.time() - t0 > 20:
        break
    time.sleep(3)

time.sleep(6)
print("=== after boot ===")
print(run(r"""
echo UP=$(cat /proc/uptime)
echo INIT=$(ls /etc/init.d/S50*)
cat /userdata/cv-uvc-boot.log
echo STATE=$(cat /sys/class/udc/21500000.usb/state)
echo SPEED=$(cat /sys/class/udc/21500000.usb/current_speed)
G=/sys/kernel/config/usb_gadget/rockchip
echo PROD=$(cat $G/strings/0x409/product)
echo SN=$(cat $G/strings/0x409/serialnumber)
echo DNAME=$(cat $G/functions/uvc.gs1/device_name)
echo HEADER=$(ls $G/functions/uvc.gs1/streaming/header/h)
ps | grep -E 'rk_mpi_uvc|uvc-h264' | grep -v grep
dmesg | grep -iE 'device reset|uvc_function_set_alt|failed to start' | tail -10
""", wait=10))
print("WIN final", win_uvc() or "(none)")
