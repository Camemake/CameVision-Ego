#!/usr/bin/env python3
import fcntl
import os

I2C_SLAVE_FORCE = 0x0706


def wr(bus: int, reg: int, val: int) -> None:
    fd = os.open("/dev/i2c-%d" % bus, os.O_RDWR)
    try:
        fcntl.ioctl(fd, I2C_SLAVE_FORCE, 0x30)
        os.write(fd, bytes([(reg >> 8) & 255, reg & 255, val & 255]))
    finally:
        os.close(fd)


def rd(bus: int, reg: int) -> int:
    fd = os.open("/dev/i2c-%d" % bus, os.O_RDWR)
    try:
        fcntl.ioctl(fd, I2C_SLAVE_FORCE, 0x30)
        os.write(fd, bytes([(reg >> 8) & 255, reg & 255]))
        return os.read(fd, 1)[0]
    finally:
        os.close(fd)


for bus, name in ((3, "cam0"), (6, "cam1")):
    cur = rd(bus, 0x3282)
    wr(bus, 0x3282, cur & ~0x02)
    print(name, "3282", hex(cur), "->", hex(rd(bus, 0x3282)))
