#!/usr/bin/env python3
import socket
import subprocess
import time

HOST = "192.168.1.23"


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


t0 = time.time()
last = ""
while time.time() - t0 < 70:
    w = win_2207()
    if w and w != last:
        print("USB", int(time.time() - t0), w.replace("\n", " | "))
        last = w
    print(
        "t=%ds ping=%s telnet=%s"
        % (int(time.time() - t0), ping_ok(), telnet_ok())
    )
    if ping_ok() and telnet_ok():
        print("UP")
        print("USB", win_2207() or "(none)")
        break
    time.sleep(3)
else:
    print("still down")
    print("USB", win_2207() or "(none)")
