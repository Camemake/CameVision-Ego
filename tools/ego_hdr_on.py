#!/usr/bin/env python3
"""Enable SC233HGS Knee Point HDR on both Ego sensors. Does not touch rockit."""
import fcntl
import os
import time

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


def u32(bus: int, regs: tuple[int, int, int, int]) -> int:
    v = 0
    for r in regs:
        v = (v << 8) | rd(bus, r)
    return v


def write_u32(bus: int, regs: tuple[int, int, int, int], val: int) -> None:
    for i, r in enumerate(regs):
        wr(bus, r, (val >> (8 * (3 - i))) & 255)


def enable(bus: int, name: str) -> None:
    hdr = rd(bus, 0x3282)
    total = u32(bus, (0x3E20, 0x3E00, 0x3E01, 0x3E02))
    exp2 = u32(bus, (0x3E38, 0x3E30, 0x3E31, 0x3E32))
    print("%s before 3282=0x%02x total=%d exp2=%d" % (name, hdr, total, exp2))
    if total < 256:
        total = 0x18C0
    short = max(total // 8, 64)
    if short >= total:
        short = total // 2
    wr(bus, 0x3800, 0x00)
    wr(bus, 0x3282, hdr | 0x02)
    write_u32(bus, (0x3E38, 0x3E30, 0x3E31, 0x3E32), short)
    wr(bus, 0x3800, 0x10)
    wr(bus, 0x3800, 0x40)
    time.sleep(0.05)
    hdr = rd(bus, 0x3282)
    exp2 = u32(bus, (0x3E38, 0x3E30, 0x3E31, 0x3E32))
    total = u32(bus, (0x3E20, 0x3E00, 0x3E01, 0x3E02))
    print("%s after  3282=0x%02x total=%d exp2=%d" % (name, hdr, total, exp2))


enable(3, "cam0")
enable(6, "cam1")
