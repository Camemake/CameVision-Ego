#!/usr/bin/env python3
from pathlib import Path

root = Path(r"C:\Users\stefa\Desktop\CameVision Single\firmware\aura-stock\Luckfox_Aura_Buildroot_eMMC_260606\rootfs.img")
data = root.read_bytes()

# dump inittab
i = data.find(b"::sysinit:")
print("inittab sysinit", i)
if i > 0:
    print(data[i - 40 : i + 400])

# oem mentions
idx = 0
n = 0
while n < 20:
    i = data.find(b"/oem/", idx)
    if i < 0:
        break
    ctx = data[max(0, i - 30) : i + 60]
    if b"\x00" in ctx:
        # printable
        s = "".join(chr(c) if 32 <= c < 127 else "." for c in ctx)
        print(hex(i), s)
    n += 1
    idx = i + 1

print("--- rkwifi nearby files ---")
i = data.find(b"rkwifi_server")
print("rkwifi_server", i)
if i > 0:
    print(data[i - 50 : i + 80])

for k in (b"S00", b"S01logging", b"S10udev", b"S20urandom", b"S21mountall", b"S30dbus", b"S40network", b"S50sshd", b"S60", b"S70", b"S80", b"S90", b"S99local", b"S99"):
    print(k, data.find(k))

# list /etc/init.d from searching consecutive Sxx names near S10udev
i = data.find(b"S10udev")
print("around S10udev dir?", data[i - 200 : i + 400] if i > 0 else None)
