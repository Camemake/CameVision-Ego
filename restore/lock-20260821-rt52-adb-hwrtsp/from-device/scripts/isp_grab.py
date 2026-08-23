#!/usr/bin/env python3
"""Consume ISP NV12 as fast as possible so STREAMON/3A stay up.
Write only ~4 fps to /dev/shm/isp.nv12. Separate process from ffmpeg.
"""
import fcntl
import os
import signal
import sys
import time

FRAME = 1920 * 1200 * 3 // 2
FIFO = "/tmp/cam.nv12"
OUT = "/dev/shm/isp.nv12"
TMP = "/dev/shm/isp.tmp"
F_SETPIPE_SZ = 1031
EVERY = 8  # 30/8 ~ 4 fps

signal.signal(signal.SIGHUP, signal.SIG_IGN)
try:
    os.nice(-15)
except Exception:
    pass

def read_exact(fd, n):
    buf = bytearray(n)
    view = memoryview(buf)
    off = 0
    while off < n:
        got = os.read(fd, n - off)
        if not got:
            return None
        view[off:off + len(got)] = got
        off += len(got)
    return buf

def main():
    fd = os.open(FIFO, os.O_RDONLY)
    try:
        fcntl.fcntl(fd, F_SETPIPE_SZ, 8 * 1024 * 1024)
    except Exception as e:
        sys.stderr.write("pipe sz %s\n" % e)
    n = 0
    t0 = time.time()
    while True:
        frame = read_exact(fd, FRAME)
        if frame is None:
            sys.stderr.write("fifo eof at %d\n" % n)
            time.sleep(0.2)
            continue
        n += 1
        if n % EVERY == 0:
            try:
                f = os.open(TMP, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
                os.write(f, frame)
                os.close(f)
                os.replace(TMP, OUT)
            except OSError as e:
                sys.stderr.write("write %s\n" % e)
        if n % 120 == 0:
            dt = time.time() - t0
            sys.stderr.write("grab %d (%.1f fps)\n" % (n, n / dt if dt else 0))

if __name__ == "__main__":
    main()
