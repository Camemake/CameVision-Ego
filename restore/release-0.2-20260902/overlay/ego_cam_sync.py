#!/usr/bin/env python3
"""CameVision Ego SC233HGS FSYNC / EFSYNC, driven by the RV1126B.

Schematic CameVisionEgo V1.I1, sheets [09] SOC_COM_Audio_Camera,
[14] MIPI_Camera0, [15] MIPI_Camera1.

    net                 SoC pad   GPIO        sensor pin
    MIPI_RX0_SYNC       AG32      GPIO4_A1    U7.D3  FSYNC
    MIPI_RX0_TRIGGER    U31       GPIO6_C2    U7.B5  EFSYNC
    MIPI_RX1_SYNC       AG31      GPIO4_A0    U10.D3 FSYNC
    MIPI_RX1_TRIGGER    V31       GPIO6_C3    U10.B5 EFSYNC

SC233HGS 数据手册 V1.4 §2.2 连续触发模式:
    rising edge on EFSYNC/FSYNC starts readout of both sensors
    0x3222[0] = 1 enables trigger mode
    pulse width > 4 EXTCLK
    trigger fps slightly below the programmed VTS fps

Do not set 0x3282[3] (slave: pulse width = exposure) — that fights 3A.
Do not set 0x3225[2] (single-frame trigger) — that halves the rate.

MIPI PHY (表 1-11) is already 4-lane (0x3018=0x7a). Trigger mode does
not retune those registers.

Both SYNC bits sit in GPIO4 DR_L, both TRIGGER bits in GPIO6 DR_H, so
one register write edges both eyes together.
"""
from __future__ import annotations

import fcntl
import mmap
import os
import struct
import threading
import time

GPIO4 = 0x21800000
GPIO6 = 0x21A00000
DR_L, DR_H = 0x00, 0x04
DDR_L, DDR_H = 0x08, 0x0C
EXT_PORT = 0x70

SYNC_CAM1 = 1 << 0  # GPIO4_A0
SYNC_CAM0 = 1 << 1  # GPIO4_A1
SYNC_BOTH = SYNC_CAM0 | SYNC_CAM1
TRIG_CAM0 = 1 << 2  # GPIO6_C2 in high half
TRIG_CAM1 = 1 << 3  # GPIO6_C3
TRIG_BOTH = TRIG_CAM0 | TRIG_CAM1

DEFAULT_FPS = 12.5
TRIG_WIDTH_S = 50e-6
I2C_SLAVE_FORCE = 0x0706
I2C_BUSES = (3, 6)
REG_TRIG = 0x3222
REG_HOLD = 0x3800
REG_SLAVE = 0x3282
REG_MIPI_LANE = 0x3018
GPIO_GET_LINEHANDLE = 0xC16CB403
GPIOHANDLE_REQUEST_OUTPUT = 0x02

PINS = {
    "cam0": {
        "sync_net": "MIPI_RX0_SYNC",
        "trig_net": "MIPI_RX0_TRIGGER",
        "sync_gpio": "GPIO4_A1",
        "trig_gpio": "GPIO6_C2",
        "fsync": "U7.D3",
        "efsync": "U7.B5",
        "i2c": 3,
    },
    "cam1": {
        "sync_net": "MIPI_RX1_SYNC",
        "trig_net": "MIPI_RX1_TRIGGER",
        "sync_gpio": "GPIO4_A0",
        "trig_gpio": "GPIO6_C3",
        "fsync": "U10.D3",
        "efsync": "U10.B5",
        "i2c": 6,
    },
}


def _wrmask(bits: int, value: int) -> int:
    return ((bits & 0xFFFF) << 16) | (value & bits)


def _i2c_rd(bus: int, reg: int) -> int:
    fd = os.open("/dev/i2c-%d" % bus, os.O_RDWR)
    try:
        fcntl.ioctl(fd, I2C_SLAVE_FORCE, 0x30)
        os.write(fd, bytes([(reg >> 8) & 255, reg & 255]))
        return os.read(fd, 1)[0]
    finally:
        os.close(fd)


def _i2c_wr(bus: int, reg: int, val: int) -> None:
    fd = os.open("/dev/i2c-%d" % bus, os.O_RDWR)
    try:
        fcntl.ioctl(fd, I2C_SLAVE_FORCE, 0x30)
        os.write(fd, bytes([(reg >> 8) & 255, reg & 255, val & 255]))
    finally:
        os.close(fd)


def _hold_wr(bus: int, reg: int, val: int) -> None:
    _i2c_wr(bus, REG_HOLD, 0x00)
    _i2c_wr(bus, reg, val)
    _i2c_wr(bus, REG_HOLD, 0x10)
    _i2c_wr(bus, REG_HOLD, 0x40)


def _request_lines(chip: int, offsets: list[int]) -> int:
    """Ask pinctrl to mux these lines as GPIO outputs. Keep the fd."""
    req = bytearray(364)
    for i, off in enumerate(offsets):
        struct.pack_into("<I", req, i * 4, off)
    struct.pack_into("<I", req, 256, GPIOHANDLE_REQUEST_OUTPUT)
    label = b"ego-fsync"
    req[324 : 324 + len(label)] = label
    struct.pack_into("<I", req, 356, len(offsets))
    fd = os.open("/dev/gpiochip%d" % chip, os.O_RDWR)
    try:
        fcntl.ioctl(fd, GPIO_GET_LINEHANDLE, req)
        line_fd = struct.unpack_from("<i", req, 360)[0]
        return line_fd
    except OSError:
        os.close(fd)
        raise


class CamSync:
    """RV1126B GPIO pulse + SC233HGS continuous-trigger registers."""

    def __init__(self, fps: float = DEFAULT_FPS) -> None:
        self.fps = float(fps) if fps > 0 else DEFAULT_FPS
        self.period = 1.0 / self.fps
        self.armed = False
        self.claimed = False
        self.sensor_on = False
        self.backend = ""
        self.err = ""
        self.pulses = 0
        self.last_t = 0.0
        self.regs = {}
        self._lock = threading.Lock()
        self._fd = -1
        self._g4 = None
        self._g6 = None
        self._line_fds: list[int] = []
        self._last_i2c = 0.0

    def status(self) -> dict:
        with self._lock:
            return {
                "armed": int(self.armed),
                "claimed": int(self.claimed),
                "sensor_on": int(self.sensor_on),
                "backend": self.backend,
                "err": self.err,
                "fps": self.fps,
                "pulses": self.pulses,
                "last_t": self.last_t,
                "regs": dict(self.regs),
                "mode": "continuous-trigger",
                "pins": PINS,
            }

    def arm(self, on: bool) -> None:
        with self._lock:
            want = bool(on)
            if want == self.armed:
                return
            turning_off = self.armed and not want
            turning_on = want and not self.armed
        if turning_off:
            try:
                self._sensor_trigger(False)
            except Exception as exc:
                with self._lock:
                    self.err = type(exc).__name__ + ":" + str(exc)
            with self._lock:
                if self.claimed:
                    try:
                        self._idle()
                    except Exception:
                        pass
                    self._release()
                self.armed = False
                self.sensor_on = False
            return
        if turning_on:
            with self._lock:
                try:
                    self._claim()
                    self._ddr_out()
                    self._idle()
                    self.armed = True
                    self.sensor_on = False
                    self.err = ""
                except Exception as exc:
                    self.err = type(exc).__name__ + ":" + str(exc)
                    self.armed = False
                    self._release()

    def set_fps(self, fps: float) -> None:
        fps = float(fps)
        if fps <= 0:
            return
        with self._lock:
            self.fps = fps
            self.period = 1.0 / fps

    def pulse_once(self) -> None:
        with self._lock:
            if not self.armed or not self.claimed:
                return
            self._pulse()

    def loop(self, flag: dict, key: str = "trig_on") -> None:
        next_t = time.monotonic()
        while True:
            want = bool(flag.get(key))
            if want != self.armed:
                self.arm(want)
            if not self.armed:
                time.sleep(0.05)
                next_t = time.monotonic()
                continue
            now = time.monotonic()
            wait = next_t - now
            if wait > 0.002:
                time.sleep(wait - 0.001)
                continue
            if wait > 0:
                _spin(wait)
            self.pulse_once()
            self._maybe_sensor(flag)
            with self._lock:
                period = self.period
            next_t += period
            if time.monotonic() - next_t > period:
                next_t = time.monotonic() + period

    def _maybe_sensor(self, flag: dict) -> None:
        now = time.monotonic()
        t0 = float(flag.get("cam0_t") or 0.0)
        t1 = float(flag.get("cam1_t") or 0.0)
        last = max(t0, t1)
        with self._lock:
            pulses = self.pulses
            sensor_on = self.sensor_on
            last_i2c = self._last_i2c
        if not sensor_on:
            if pulses >= 5 and last and (now - last) < 1.0:
                try:
                    self._sensor_trigger(True)
                    print("cam sync sensor 0x3222[0]=1 both eyes", flush=True)
                except Exception as exc:
                    with self._lock:
                        self.err = type(exc).__name__ + ":" + str(exc)
            return
        if last and (now - last) > 2.5:
            try:
                self._sensor_trigger(False)
            except Exception:
                pass
            with self._lock:
                self.err = "stream stalled, 0x3222 cleared"
            flag["trig_on"] = False
            print("cam sync reverted, no frames", flush=True)
            return
        if now - last_i2c > 1.0:
            try:
                self._sensor_trigger(True)
            except Exception as exc:
                with self._lock:
                    self.err = type(exc).__name__ + ":" + str(exc)

    def _sensor_trigger(self, on: bool) -> None:
        snap = {}
        for bus in I2C_BUSES:
            cur = _i2c_rd(bus, REG_TRIG)
            want = (cur | 0x01) if on else (cur & 0xFE)
            if cur != want:
                _hold_wr(bus, REG_TRIG, want)
                cur = _i2c_rd(bus, REG_TRIG)
            snap["i2c%d_3222" % bus] = "0x%02x" % cur
            try:
                snap["i2c%d_3282" % bus] = "0x%02x" % _i2c_rd(bus, REG_SLAVE)
                snap["i2c%d_3018" % bus] = "0x%02x" % _i2c_rd(bus, REG_MIPI_LANE)
            except Exception:
                pass
        with self._lock:
            self.sensor_on = bool(on)
            self.regs = snap
            self._last_i2c = time.monotonic()

    def _claim(self) -> None:
        if self.claimed:
            return
        mux = []
        try:
            mux.append(_request_lines(4, [0, 1]))
            mux.append(_request_lines(6, [18, 19]))
        except Exception:
            for fd in mux:
                try:
                    os.close(fd)
                except Exception:
                    pass
            mux = []
        fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
        try:
            g4 = mmap.mmap(
                fd, 0x80, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE,
                offset=GPIO4,
            )
            g6 = mmap.mmap(
                fd, 0x80, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE,
                offset=GPIO6,
            )
        except Exception:
            os.close(fd)
            for line_fd in mux:
                try:
                    os.close(line_fd)
                except Exception:
                    pass
            raise
        self._fd = fd
        self._g4 = g4
        self._g6 = g6
        self._line_fds = mux
        self.claimed = True
        self.backend = "gpiochip+mem" if mux else "mem"

    def _release(self) -> None:
        for mm in (self._g4, self._g6):
            if mm is not None:
                try:
                    mm.close()
                except Exception:
                    pass
        self._g4 = None
        self._g6 = None
        if self._fd >= 0:
            try:
                os.close(self._fd)
            except Exception:
                pass
            self._fd = -1
        for line_fd in self._line_fds:
            try:
                os.close(line_fd)
            except Exception:
                pass
        self._line_fds = []
        self.claimed = False
        self.backend = ""

    def _wr(self, mm, off: int, bits: int, value: int) -> None:
        mm[off : off + 4] = struct.pack("<I", _wrmask(bits, value))

    def _ddr_out(self) -> None:
        self._wr(self._g4, DDR_L, SYNC_BOTH, SYNC_BOTH)
        self._wr(self._g6, DDR_H, TRIG_BOTH, TRIG_BOTH)

    def _idle(self) -> None:
        self._wr(self._g4, DR_L, SYNC_BOTH, 0)
        self._wr(self._g6, DR_H, TRIG_BOTH, 0)

    def _pulse(self) -> None:
        # Both FSYNC and both EFSYNC rise on the same tick (datasheet TRIGGER).
        self._wr(self._g4, DR_L, SYNC_BOTH, SYNC_BOTH)
        self._wr(self._g6, DR_H, TRIG_BOTH, TRIG_BOTH)
        _spin(TRIG_WIDTH_S)
        self._wr(self._g6, DR_H, TRIG_BOTH, 0)
        self._wr(self._g4, DR_L, SYNC_BOTH, 0)
        self.pulses += 1
        self.last_t = time.monotonic()


def _spin(seconds: float) -> None:
    if seconds <= 0:
        return
    deadline = time.perf_counter() + seconds
    while time.perf_counter() < deadline:
        pass


SYNC = CamSync()


def start_thread(flag: dict, key: str = "trig_on", fps: float = DEFAULT_FPS) -> CamSync:
    SYNC.set_fps(fps)
    threading.Thread(target=SYNC.loop, args=(flag, key), daemon=True).start()
    return SYNC
