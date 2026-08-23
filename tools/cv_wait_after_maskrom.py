#!/usr/bin/env python3
import socket
import subprocess
import time

HOST = "192.168.1.23"
ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"


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


def win_2207():
    ps = r"""Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_2207' -and $_.Present } | ForEach-Object { '{0}|{1}|{2}' -f $_.Status, $_.FriendlyName, $_.InstanceId }"""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
    )
    return r.stdout.strip()


def adb():
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    return r.stdout.strip()


t0 = time.time()
last = ""
print("waiting after maskrom reset...")
while time.time() - t0 < 75:
    w = win_2207()
    if w and w != last:
        print("USB", int(time.time() - t0), w.replace("\n", " | "))
        last = w
    p, t = ping_ok(), telnet_ok()
    print("t=%ds ping=%s telnet=%s" % (int(time.time() - t0), p, t))
    if (p and t) or (w and "0016" in w and "OK" in w) or (w and "0006" in w):
        if time.time() - t0 > 12:
            break
    time.sleep(3)

print("ADB")
print(adb())
print("USB final", win_2207() or "(none)")
print("ping", ping_ok(), "telnet", telnet_ok())
