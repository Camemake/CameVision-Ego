#!/usr/bin/env python3
"""RKISP NV12 1920x1080 -> JPEG -> UVC. Keep ISP and gadget STREAMON."""
import ctypes
import fcntl
import mmap
import os
import select
import signal
import struct
import subprocess
import threading
import time

UVC = "/dev/video28"
FIFO = "/tmp/cam.nv12"
W, H = 1920, 1080
FRAME = W * H * 3 // 2
LOG = "/userdata/uvc-mjpg-pump.log"

os.environ["PATH"] = "/oem/usr/bin:/usr/bin:/bin:" + os.environ.get("PATH", "")
os.environ["LD_LIBRARY_PATH"] = "/oem/usr/lib:/oem/lib:" + os.environ.get(
    "LD_LIBRARY_PATH", ""
)
signal.signal(signal.SIGHUP, signal.SIG_IGN)
signal.signal(signal.SIGPIPE, signal.SIG_IGN)
signal.signal(signal.SIGTTOU, signal.SIG_IGN)

V4L2_BUF_TYPE_VIDEO_OUTPUT = 2
V4L2_MEMORY_MMAP = 1
V4L2_PIX_FMT_MJPG = 0x47504A4D


def _IOC(dir_, type_, nr, size):
    return (
        (dir_ << 30)
        | (ord(type_) << 8)
        | nr
        | (size << 16)
    )


def IOWR(nr, size):
    return _IOC(3, "V", nr, size)


def IOW(nr, size):
    return _IOC(1, "V", nr, size)


class timeval(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_int64), ("tv_usec", ctypes.c_int64)]


class v4l2_timecode(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("frames", ctypes.c_uint8),
        ("seconds", ctypes.c_uint8),
        ("minutes", ctypes.c_uint8),
        ("hours", ctypes.c_uint8),
        ("userbits", ctypes.c_uint8 * 4),
    ]


class v4l2_buffer(ctypes.Structure):
    class _m(ctypes.Union):
        _fields_ = [
            ("offset", ctypes.c_uint32),
            ("userptr", ctypes.c_ulong),
            ("planes", ctypes.c_void_p),
            ("fd", ctypes.c_int32),
        ]

    _fields_ = [
        ("index", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("bytesused", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("field", ctypes.c_uint32),
        ("timestamp", timeval),
        ("timecode", v4l2_timecode),
        ("sequence", ctypes.c_uint32),
        ("memory", ctypes.c_uint32),
        ("m", _m),
        ("length", ctypes.c_uint32),
        ("reserved2", ctypes.c_uint32),
        ("request_fd", ctypes.c_int32),
    ]


class v4l2_requestbuffers(ctypes.Structure):
    _fields_ = [
        ("count", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("memory", ctypes.c_uint32),
        ("capabilities", ctypes.c_uint32),
        ("flags", ctypes.c_uint8),
        ("reserved", ctypes.c_uint8 * 3),
    ]


VIDIOC_S_FMT = IOWR(5, 208)
VIDIOC_REQBUFS = IOWR(8, ctypes.sizeof(v4l2_requestbuffers))
VIDIOC_QUERYBUF = IOWR(9, ctypes.sizeof(v4l2_buffer))
VIDIOC_QBUF = IOWR(15, ctypes.sizeof(v4l2_buffer))
VIDIOC_DQBUF = IOWR(17, ctypes.sizeof(v4l2_buffer))
VIDIOC_STREAMON = IOW(18, ctypes.sizeof(ctypes.c_int))

latest = {"buf": None}
lock = threading.Lock()


def log(msg):
    with open(LOG, "a") as f:
        f.write(msg + "\n")


def find_uvc():
    for ent in os.listdir("/sys/class/video4linux"):
        try:
            name = open("/sys/class/video4linux/%s/name" % ent).read().strip()
        except OSError:
            continue
        if "gadget" in name.lower():
            return "/dev/" + ent
    return UVC


def read_exact(fd, n):
    buf = bytearray(n)
    view = memoryview(buf)
    off = 0
    while off < n:
        got = os.read(fd, n - off)
        if not got:
            return None
        view[off : off + len(got)] = got
        off += len(got)
    return bytes(buf)


def grabber():
    fd = None
    while True:
        try:
            fd = os.open(FIFO, os.O_RDONLY)
            try:
                fcntl.fcntl(fd, 1031, 8 * 1024 * 1024)
            except OSError:
                pass
            while True:
                frame = read_exact(fd, FRAME)
                if frame is None:
                    break
                with lock:
                    latest["buf"] = frame
        except Exception as e:
            log("grab %s" % e)
            time.sleep(0.3)
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
            fd = None


def encode_jpeg(nv12):
    inp = "/dev/shm/uvc.nv12"
    outp = "/tmp/uvc.jpg"
    tmp = inp + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    os.write(fd, nv12)
    os.close(fd)
    os.replace(tmp, inp)
    subprocess.check_call(
        [
            "/oem/usr/bin/mpi_enc_test",
            "-i",
            inp,
            "-o",
            outp,
            "-w",
            str(W),
            "-h",
            str(H),
            "-hstride",
            str(W),
            "-vstride",
            str(H),
            "-f",
            "0",
            "-t",
            "8",
            "-n",
            "1",
            "-fps",
            "15:15",
            "-v",
            "q",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return open(outp, "rb").read()


class UvcOut:
    def __init__(self, dev):
        self.fd = os.open(dev, os.O_RDWR)
        self.maps = []
        self.nbuf = 0
        self.queued = 0
        self.streaming = False

    def setup(self):
        raw = bytearray(208)
        struct.pack_into("<I", raw, 0, V4L2_BUF_TYPE_VIDEO_OUTPUT)
        struct.pack_into("<IIIIII", raw, 8, W, H, V4L2_PIX_FMT_MJPG, 1, 0, 0)
        fcntl.ioctl(self.fd, VIDIOC_S_FMT, raw)
        req = v4l2_requestbuffers()
        req.count = 4
        req.type = V4L2_BUF_TYPE_VIDEO_OUTPUT
        req.memory = V4L2_MEMORY_MMAP
        fcntl.ioctl(self.fd, VIDIOC_REQBUFS, req)
        self.nbuf = int(req.count)
        if self.nbuf < 2:
            raise OSError("reqbufs %d" % self.nbuf)
        for i in range(self.nbuf):
            buf = v4l2_buffer()
            buf.type = V4L2_BUF_TYPE_VIDEO_OUTPUT
            buf.memory = V4L2_MEMORY_MMAP
            buf.index = i
            fcntl.ioctl(self.fd, VIDIOC_QUERYBUF, buf)
            mm = mmap.mmap(
                self.fd,
                buf.length,
                mmap.MAP_SHARED,
                mmap.PROT_READ | mmap.PROT_WRITE,
                offset=buf.m.offset,
            )
            self.maps.append((mm, buf.length))
        log("uvc mmap %d x %d (wait host STREAMON)" % (self.nbuf, self.maps[0][1]))

    def ensure_stream(self):
        if self.streaming:
            return True
        typ = ctypes.c_int(V4L2_BUF_TYPE_VIDEO_OUTPUT)
        try:
            fcntl.ioctl(self.fd, VIDIOC_STREAMON, typ)
        except OSError as e:
            if e.errno == 19:
                return False
            raise
        self.streaming = True
        log("STREAMON ok")
        return True

    def _dq(self, timeout):
        r, _, _ = select.select([self.fd], [], [], timeout)
        if not r:
            return None
        buf = v4l2_buffer()
        buf.type = V4L2_BUF_TYPE_VIDEO_OUTPUT
        buf.memory = V4L2_MEMORY_MMAP
        fcntl.ioctl(self.fd, VIDIOC_DQBUF, buf)
        self.queued -= 1
        return buf.index

    def push(self, blob):
        if not blob:
            return False
        if self.queued >= self.nbuf:
            idx = self._dq(0.8)
            if idx is None:
                return False
        else:
            idx = self.queued
        mm, length = self.maps[idx]
        n = min(len(blob), length)
        mm.seek(0)
        mm.write(blob[:n])
        buf = v4l2_buffer()
        buf.type = V4L2_BUF_TYPE_VIDEO_OUTPUT
        buf.memory = V4L2_MEMORY_MMAP
        buf.index = idx
        buf.bytesused = n
        buf.length = length
        buf.field = 1
        fcntl.ioctl(self.fd, VIDIOC_QBUF, buf)
        self.queued += 1
        return True


def wait_frame(timeout=2.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        with lock:
            buf = latest["buf"]
        if buf:
            return buf
        time.sleep(0.02)
    return None


def main():
    open(LOG, "w").write(
        "pump start buf=%d req=%d\n"
        % (ctypes.sizeof(v4l2_buffer), ctypes.sizeof(v4l2_requestbuffers))
    )
    threading.Thread(target=grabber, daemon=True).start()
    uvc = None
    n = 0
    last_sz = 0
    while True:
        try:
            if uvc is None:
                uvc = UvcOut(find_uvc())
                uvc.setup()
            frame = wait_frame()
            if frame is None:
                time.sleep(0.05)
                continue
            jpg = encode_jpeg(frame)
            if len(jpg) < 200:
                time.sleep(0.05)
                continue
            if not uvc.ensure_stream():
                time.sleep(0.25)
                continue
            if not uvc.push(jpg):
                continue
            n += 1
            if n == 1 or n % 30 == 0 or len(jpg) != last_sz:
                log("sent %d MJPG %d bytes queued=%d" % (n, len(jpg), uvc.queued))
                last_sz = len(jpg)
        except OSError as e:
            log("uvc %s" % e)
            try:
                if uvc:
                    os.close(uvc.fd)
            except Exception:
                pass
            uvc = None
            time.sleep(0.4)
        except Exception as e:
            log("err %s" % e)
            time.sleep(0.2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
