#!/usr/bin/env python3
"""On-device: test one IIO accel buffer rate. Cameras left running."""
import subprocess
import sys

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB")


def main() -> int:
    s = serial()
    cmd = r"""
kill $(cat /tmp/ego-imu.pid 2>/dev/null) 2>/dev/null
sleep 0.2
for d in /sys/bus/iio/devices/iio:device1 /sys/bus/iio/devices/iio:device2 /sys/bus/iio/devices/iio:device3 /sys/bus/iio/devices/iio:device4; do
  echo 0 > $d/buffer/enable 2>/dev/null
done
python3 - <<'PY'
import os, time, struct
from pathlib import Path
D=Path('/sys/bus/iio/devices/iio:device2')
for ax in ('in_accel_x','in_accel_y','in_accel_z','in_timestamp'):
    (D/'scan_elements'/f'{ax}_en').write_text('1')
(D/'sampling_frequency').write_text('240')
(D/'buffer'/'length').write_text('128')
(D/'buffer'/'enable').write_text('1')
fd=os.open('/dev/iio:device2', os.O_RDONLY)
pkt=struct.Struct('<hhh2xq')
t0=time.monotonic(); n=0; last=None
while time.monotonic()-t0<1.2:
    buf=os.read(fd, pkt.size*8)
    if not buf:
        continue
    n += len(buf)//pkt.size
    if len(buf)>=pkt.size:
        last=pkt.unpack_from(buf, 0)
print('n',n,'hz',n/(time.monotonic()-t0),'last',last,'avail',open('/sys/bus/iio/devices/iio:device2/buffer/data_available').read().strip())
os.close(fd)
(D/'buffer'/'enable').write_text('0')
PY
echo === preview ===
ps | grep -E 'rkaiq_3A|ego_mjpeg|ffmpeg' | grep -v grep | wc -l
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=30)
    sys.stdout.write(r.stdout or "")
    sys.stdout.write(r.stderr or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
