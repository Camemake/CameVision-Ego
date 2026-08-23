#!/usr/bin/env python3
"""Read a few samples from both Ego LSM6 IMUs. Cameras/USB untouched."""
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
python3 - <<'PY'
import time
from pathlib import Path

def rd(p):
    return Path(p).read_text().strip()

imus = [
    ("IMU0 U9 SPI0 spi0.0 (next to Cam 0)",
     "/sys/bus/iio/devices/iio:device2",
     "/sys/bus/iio/devices/iio:device1"),
    ("IMU1 U12 SPI1 spi1.0 (next to Cam 1)",
     "/sys/bus/iio/devices/iio:device4",
     "/sys/bus/iio/devices/iio:device3"),
]

for title, A, G in imus:
    try:
        Path(A, "sampling_frequency").write_text("60")
        Path(G, "sampling_frequency").write_text("60")
    except OSError as e:
        print(title, "odr set failed", e)
    ascl = float(rd(f"{A}/in_accel_scale"))
    gscl = float(rd(f"{G}/in_anglvel_scale"))
    print(f"=== {title} ===")
    print(f"accel={A} gyro={G}")
    print(f"scale_a={ascl} m/s2/LSB  scale_g={gscl} rad/s/LSB  odr=60")
    print("n   ax_mps2   ay_mps2   az_mps2   |a|_g    gx_dps    gy_dps    gz_dps   temp_C")
    time.sleep(0.05)
    for i in range(5):
        ax = int(rd(f"{A}/in_accel_x_raw")) * ascl
        ay = int(rd(f"{A}/in_accel_y_raw")) * ascl
        az = int(rd(f"{A}/in_accel_z_raw")) * ascl
        gx = int(rd(f"{G}/in_anglvel_x_raw")) * gscl * 57.2957795
        gy = int(rd(f"{G}/in_anglvel_y_raw")) * gscl * 57.2957795
        gz = int(rd(f"{G}/in_anglvel_z_raw")) * gscl * 57.2957795
        tpath = Path(A, "in_temp_raw")
        if tpath.exists():
            ts = float(rd(f"{A}/in_temp_scale"))
            to = float(rd(f"{A}/in_temp_offset")) if Path(A, "in_temp_offset").exists() else 0.0
            temp = (int(tpath.read_text()) + to) * ts
        else:
            temp = float("nan")
        g = (ax*ax + ay*ay + az*az) ** 0.5 / 9.80665
        print(f"{i}  {ax:8.3f}  {ay:8.3f}  {az:8.3f}  {g:6.3f}  {gx:8.2f}  {gy:8.2f}  {gz:8.2f}  {temp:6.1f}")
        time.sleep(0.1)
    print()
print("cameras", end=" ")
import subprocess
print(subprocess.check_output("ps | grep -E 'rkaiq_3A|ego_mjpeg|ffmpeg' | grep -v grep | wc -l", shell=True).decode().strip())
PY
"""
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=30)
    sys.stdout.write(r.stdout or "")
    if r.stderr:
        sys.stdout.write(r.stderr)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
