#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

ping = subprocess.run(
    ["ping", "-n", "1", "-w", "1000", "192.168.1.23"],
    capture_output=True,
    text=True,
)
ps = r"Get-PnpDevice | Where-Object { $_.InstanceId -match 'VID_2207' -and $_.Present } | ForEach-Object { '{0}|{1}|{2}' -f $_.Status, $_.FriendlyName, $_.InstanceId }"
usb = subprocess.run(
    ["powershell", "-NoProfile", "-Command", ps],
    capture_output=True,
    text=True,
)
print("PING", "TTL=" in (ping.stdout or ""))
print("USB", (usb.stdout or "").strip() or "(none)")
print(run("cat /proc/uptime; echo LED; for n in red green blue; do echo -n $n=; cat /sys/class/leds/status:$n/trigger | tr ' ' / | sed 's/.*\\[//;s/\\].*//' ; echo -n /$n-bri=; cat /sys/class/leds/status:$n/brightness; done", wait=4))
