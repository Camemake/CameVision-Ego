#!/usr/bin/env python3
"""Read SC233HGS regs via I2C_SLAVE_FORCE while the driver owns the bus."""
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"
py = r"""
import fcntl, os
I2C_SLAVE_FORCE = 0x0706
def rd(bus, reg):
    fd = os.open('/dev/i2c-%d' % bus, os.O_RDWR)
    try:
        fcntl.ioctl(fd, I2C_SLAVE_FORCE, 0x30)
        os.write(fd, bytes([(reg >> 8) & 255, reg & 255]))
        return os.read(fd, 1)[0]
    finally:
        os.close(fd)
for bus, name in ((3, 'cam0'), (6, 'cam1')):
    print('===', name, 'i2c', bus, '===')
    for r in (0x3282, 0x3e20, 0x3e00, 0x3e01, 0x3e02, 0x3e38, 0x3e30, 0x3e31, 0x3e32, 0x3221, 0x3800):
        try:
            print('0x%04x 0x%02x' % (r, rd(bus, r)))
        except Exception as e:
            print('0x%04x ERR' % r, e)
"""
r = subprocess.run(
    [ADB, "-s", S, "shell", "python3", "-c", py],
    capture_output=True,
    text=True,
    timeout=20,
)
print(r.stdout)
print(r.stderr)
