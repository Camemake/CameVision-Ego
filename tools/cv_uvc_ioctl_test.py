#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run
print(run(r"""
# stop ffmpeg so video28 is free
if [ -f /tmp/uvc-ff.pid ]; then start-stop-daemon -K -p /tmp/uvc-ff.pid 2>/dev/null; fi
killall ffmpeg 2>/dev/null
sleep 1
python3 - <<'PY'
import ctypes, fcntl, os, struct, errno
V4L2_BUF_TYPE_VIDEO_OUTPUT=2
V4L2_MEMORY_MMAP=1
V4L2_PIX_FMT_MJPG=0x47504A4D
def IOC(d,nr,sz): return (d<<30)| (ord('V')<<8)| nr| (sz<<16)
IOWR=lambda nr,sz: IOC(3,nr,sz)
IOW=lambda nr,sz: IOC(1,nr,sz)
class RB(ctypes.Structure):
    _fields_=[('count',ctypes.c_uint32),('type',ctypes.c_uint32),('memory',ctypes.c_uint32),('capabilities',ctypes.c_uint32),('flags',ctypes.c_uint8),('reserved',ctypes.c_uint8*3)]
print('open')
fd=os.open('/dev/video28', os.O_RDWR)
print('fd',fd)
raw=bytearray(208)
struct.pack_into('<I', raw, 0, V4L2_BUF_TYPE_VIDEO_OUTPUT)
struct.pack_into('<IIIIII', raw, 8, 1920,1080,V4L2_PIX_FMT_MJPG,1,0,0)
for name,req,arg in [
    ('S_FMT', IOWR(5,208), raw),
]:
    try:
        fcntl.ioctl(fd, req, arg)
        print(name,'ok')
    except OSError as e:
        print(name, e)
req=RB(); req.count=4; req.type=2; req.memory=1
try:
    fcntl.ioctl(fd, IOWR(8, ctypes.sizeof(RB)), req)
    print('REQBUFS ok', req.count)
except OSError as e:
    print('REQBUFS', e)
typ=ctypes.c_int(2)
try:
    fcntl.ioctl(fd, IOW(18, ctypes.sizeof(ctypes.c_int)), typ)
    print('STREAMON ok')
except OSError as e:
    print('STREAMON', e, 'errno', e.errno)
os.close(fd)
print('done')
PY
echo === 3A ===
grep sysctl /userdata/rkaiq.log | tail -3
ps | grep -E 'v4l2-ctl|rkaiq_3A|ffmpeg' | grep -v grep
""", wait=8))
