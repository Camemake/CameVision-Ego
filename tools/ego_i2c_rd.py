#!/usr/bin/env python3
import fcntl
import os

I2C_SLAVE_FORCE = 0x0706


def rd(bus: int, reg: int) -> int:
    fd = os.open("/dev/i2c-%d" % bus, os.O_RDWR)
    try:
        fcntl.ioctl(fd, I2C_SLAVE_FORCE, 0x30)
        os.write(fd, bytes([(reg >> 8) & 255, reg & 255]))
        return os.read(fd, 1)[0]
    finally:
        os.close(fd)


for bus, name in ((3, "cam0"), (6, "cam1")):
    print("===", name, "i2c", bus, "===")
    for r in (
        0x3282,
        0x3E20,
        0x3E00,
        0x3E01,
        0x3E02,
        0x3E38,
        0x3E30,
        0x3E31,
        0x3E32,
        0x3221,
        0x3800,
    ):
        try:
            print("0x%04x 0x%02x" % (r, rd(bus, r)))
        except Exception as e:
            print("0x%04x ERR" % r, e)
