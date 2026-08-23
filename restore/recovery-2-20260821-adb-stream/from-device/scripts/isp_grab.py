#!/usr/bin/env python3
"""Live 1920x1200: short STREAMON bursts to a file, publish every complete
frame immediately (no pacing). Sensor supports 60 fps.
"""
import os
import signal
import subprocess
import sys
import time

DEV = "/dev/video13"
OUT = "/dev/shm/isp.nv12"
TMP = "/dev/shm/isp.tmp"
BURST = "/dev/shm/isp.burst"
FRAME = 1920 * 1200 * 3 // 2
COUNT = 20
SKIP = 1

signal.signal(signal.SIGHUP, signal.SIG_IGN)
try:
    os.nice(-10)
except Exception:
    pass


def publish(frame):
    fd = os.open(TMP, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    os.write(fd, frame)
    os.close(fd)
    os.replace(TMP, OUT)


def main():
    subprocess.call(
        [
            "v4l2-ctl",
            "-d",
            DEV,
            "--set-fmt-video=width=1920,height=1200,pixelformat=NV12",
        ]
    )
    subprocess.call(
        [
            "v4l2-ctl",
            "-d",
            "/dev/v4l-subdev4",
            "--set-subdev-fps",
            "pad=0,fps=60",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    n = 0
    t0 = time.time()
    while True:
        try:
            os.remove(BURST)
        except OSError:
            pass
        subprocess.call(
            [
                "timeout",
                "1",
                "v4l2-ctl",
                "-d",
                DEV,
                "--stream-mmap=8",
                "--stream-count",
                str(COUNT),
                "--stream-to",
                BURST,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            sz = os.path.getsize(BURST)
        except OSError:
            continue
        frames = sz // FRAME
        if frames <= SKIP:
            continue
        with open(BURST, "rb") as src:
            src.seek(SKIP * FRAME)
            for _ in range(frames - SKIP):
                frame = src.read(FRAME)
                if len(frame) != FRAME:
                    break
                try:
                    publish(frame)
                    n += 1
                except OSError as e:
                    sys.stderr.write("pub %s\n" % e)
                    break
        if n and n % 40 == 0:
            dt = time.time() - t0
            sys.stderr.write("cap %d (%.1f fps)\n" % (n, n / dt if dt else 0))


if __name__ == "__main__":
    main()
