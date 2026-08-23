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
    out = (r.stdout or "") + (r.stderr or "")
    return "TTL=" in out


def telnet_ok():
    try:
        s = socket.create_connection((HOST, 2323), 2)
        s.close()
        return True
    except OSError:
        return False


def win_uvc():
    ps = r"""Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_2207' -and $_.Present } | ForEach-Object { '{0}|{1}|{2}|{3}' -f $_.Status, $_.Class, $_.FriendlyName, $_.InstanceId }"""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True,
        text=True,
    )
    return r.stdout.strip()


t0 = time.time()
last_win = None
print("waiting for board...")
while time.time() - t0 < 120:
    w = win_uvc()
    if w and w != last_win:
        print("WIN", int(time.time() - t0), w)
        last_win = w
    p, t = ping_ok(), telnet_ok()
    print("t=%ds ping=%s telnet=%s" % (int(time.time() - t0), p, t))
    if p and t:
        print("BOARD UP")
        print("WIN", win_uvc() or "(none)")
        break
    time.sleep(3)
else:
    print("timeout")
    print("WIN", win_uvc() or "(none)")
