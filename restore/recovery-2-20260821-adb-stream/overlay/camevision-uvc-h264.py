#!/usr/bin/env python3
"""ISP NV12 -> kmpp H.264/JPEG -> UVC gadget output. No rockit."""
import os
import signal
import subprocess
import sys
import time

ISP = "/dev/shm/isp.nv12"
OUT = "/tmp/uvc_au.bin"
FRAME = 1920 * 1200 * 3 // 2
UVC = "/dev/video28"

os.environ["PATH"] = "/oem/usr/bin:/usr/bin:/bin:" + os.environ.get("PATH", "")
os.environ["LD_LIBRARY_PATH"] = "/oem/usr/lib:/oem/lib:" + os.environ.get(
    "LD_LIBRARY_PATH", ""
)
signal.signal(signal.SIGHUP, signal.SIG_IGN)
signal.signal(signal.SIGPIPE, signal.SIG_IGN)
signal.signal(signal.SIGTTOU, signal.SIG_IGN)

LOG = "/userdata/uvc-h264-pump.log"


def log(msg):
    with open(LOG, "a") as f:
        f.write(msg + "\n")


def find_uvc():
    for ent in os.listdir("/sys/class/video4linux"):
        try:
            name = open("/sys/class/video4linux/%s/name" % ent).read().strip()
        except OSError:
            continue
        if "gadget" in name.lower() or "uvc" in name.lower() or "RGB" in name:
            return "/dev/" + ent
    return UVC


def fmt_of(dev):
    try:
        out = subprocess.check_output(
            ["v4l2-ctl", "-d", dev, "--all"],
            stderr=subprocess.STDOUT,
            timeout=3,
        ).decode("utf-8", "replace")
    except Exception:
        return "", 0, 0
    pix = w = h = ""
    in_out = False
    for line in out.splitlines():
        if "Format Video Output" in line:
            in_out = True
            continue
        if not in_out:
            continue
        if line and not line.startswith(" ") and not line.startswith("\t"):
            break
        if "Pixel Format" in line and "'" in line:
            pix = line.split("'")[1]
        elif "Width/Height" in line:
            parts = line.replace(" ", "").split(":")[-1].split("/")
            if len(parts) == 2:
                w, h = parts
    try:
        return pix, int(w), int(h)
    except ValueError:
        return pix, 0, 0


def ensure_grab():
    if not os.path.exists("/dev/video13"):
        return
    subprocess.call(
        [
            "v4l2-ctl",
            "-d",
            "/dev/video13",
            "--set-fmt-video=width=1920,height=1200,pixelformat=NV12",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if os.path.exists("/userdata/isp_grab.py") and os.path.exists("/tmp/cam.nv12"):
        return
    os.makedirs("/dev/shm", exist_ok=True)


def grab_one(w=1920, h=1200):
    subprocess.call(
        [
            "v4l2-ctl",
            "-d",
            "/dev/video13",
            "--set-fmt-video=width=%d,height=%d,pixelformat=NV12" % (w, h),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.call(
        [
            "v4l2-ctl",
            "-d",
            "/dev/video13",
            "--stream-mmap=4",
            "--stream-count=1",
            "--stream-to=" + ISP,
            "--stream-poll",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=8,
    )


def encode(typ, w=1920, h=1200):
    cmd = [
        "/oem/usr/bin/mpi_enc_test",
        "-i",
        ISP,
        "-o",
        OUT,
        "-w",
        str(w),
        "-h",
        str(h),
        "-hstride",
        str(w),
        "-vstride",
        str(h),
        "-f",
        "0",
        "-t",
        str(typ),
        "-n",
        "1",
        "-g",
        "1:30:0",
        "-fps",
        "30:30",
        "-bps",
        "8000000",
        "-rc",
        "1",
        "-v",
        "q",
    ]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return open(OUT, "rb").read()


def push_uvc(dev, blob):
    open(OUT, "wb").write(blob)
    subprocess.check_call(
        [
            "v4l2-ctl",
            "-d",
            dev,
            "--stream-from=" + OUT,
            "--stream-mmap",
            "--stream-count=1",
            "--stream-poll",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=8,
    )


def main():
    open(LOG, "w").write("pump start\n")
    n = 0
    last_pix = ""
    while True:
        try:
            dev = find_uvc()
            pix, w, h = fmt_of(dev)
            if pix != last_pix:
                log("fmt %s %dx%d on %s" % (pix, w, h, dev))
                last_pix = pix
            if pix not in ("H264", "MJPG"):
                time.sleep(0.4)
                continue
            need = w * h * 3 // 2 if w and h else FRAME
            gw, gh = (w, h) if w and h else (1920, 1200)
            if not os.path.exists(ISP) or os.path.getsize(ISP) < need:
                grab_one(gw, gh)
            if not os.path.exists(ISP) or os.path.getsize(ISP) < 1000:
                time.sleep(0.2)
                continue
            typ = 7 if pix == "H264" else 8
            au = encode(typ, gw, gh)
            if len(au) < 100:
                time.sleep(0.05)
                continue
            push_uvc(dev, au)
            n += 1
            if n == 1 or n % 30 == 0:
                log("sent %d %s %d bytes" % (n, pix, len(au)))
        except subprocess.TimeoutExpired:
            time.sleep(0.2)
        except Exception as e:
            log("err %s" % e)
            time.sleep(0.3)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
