#!/usr/bin/env python3
"""Prove Cam 1 I2C SCL/SDA swap from the Ego schematic."""
from __future__ import annotations

import subprocess
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
REMOTE = "/tmp/cam1_i2c_swap.sh"
LOCAL = Path(__file__).with_name("cam1_i2c_swap.sh")

SH = r"""#!/bin/sh
set -eu
mount -t debugfs debugfs /sys/kernel/debug 2>/dev/null || true

echo '=== release leftover gpio and unbind i2c4 ==='
for g in 130 134 135; do
  [ -d /sys/class/gpio/gpio$g ] && echo $g > /sys/class/gpio/unexport || true
done
echo 4-0030 > /sys/bus/i2c/drivers/sc233hgs/unbind 2>/dev/null || true
echo 21130000.i2c > /sys/bus/platform/drivers/rk3x-i2c/unbind 2>/dev/null || true
sleep 0.3
echo 'pinmux after unbind:'
grep -E 'gpio4-6|gpio4-7|gpio4-8|i2c4' /sys/kernel/debug/pinctrl/*/pinmux-pins || true

for g in 130 134 135; do
  echo $g > /sys/class/gpio/export
done
echo out > /sys/class/gpio/gpio130/direction
echo out > /sys/class/gpio/gpio134/direction
echo out > /sys/class/gpio/gpio135/direction
echo 'pinmux after gpio claim:'
grep -E 'gpio4-2|gpio4-6|gpio4-7|gpio4-8' /sys/kernel/debug/pinctrl/*/pinmux-pins || true

echo '=== clk ==='
cat /sys/kernel/debug/clk/clk_summary 2>/dev/null | grep -E 'clk_mipi0_out2io|clk_mipi1_out2io' || true

hi() { echo in > /sys/class/gpio/gpio$1/direction; }
lo() { echo out > /sys/class/gpio/gpio$1/direction; echo 0 > /sys/class/gpio/gpio$1/value; }
rd() { cat /sys/class/gpio/gpio$1/value; }

i2c_start() {
  hi $SDA; hi $SCL
  lo $SDA
  lo $SCL
}
i2c_stop() {
  lo $SDA; hi $SCL; hi $SDA
}
i2c_bit() {
  if [ "$1" = 1 ]; then hi $SDA; else lo $SDA; fi
  hi $SCL
  lo $SCL
}
i2c_read_bit() {
  hi $SDA
  hi $SCL
  b=$(rd $SDA)
  lo $SCL
  echo $b
}
i2c_byte() {
  v=$1
  i=0
  while [ $i -lt 8 ]; do
    shiftv=$((7 - i))
    bit=$(( (v >> shiftv) & 1 ))
    i2c_bit $bit
    i=$((i + 1))
  done
  i2c_read_bit
}

scan() {
  SDA=$1
  SCL=$2
  echo "-- SDA=gpio$SDA SCL=gpio$SCL PWDN=$(cat /sys/class/gpio/gpio130/value) --"
  found=0
  for addr in 48 50 32 33 54 55 60 61; do
    i2c_start
    wr=$((addr * 2))
    ack=$(i2c_byte $wr)
    i2c_stop
    if [ "$ack" = 0 ]; then
      echo ACK $addr
      found=1
    fi
  done
  [ $found -eq 1 ] || echo 'no ACK'
}

echo '=== PWDN raw 0 ==='
echo 0 > /sys/class/gpio/gpio130/value
scan 135 134
scan 134 135

echo '=== PWDN raw 1 ==='
echo 1 > /sys/class/gpio/gpio130/value
scan 135 134
scan 134 135
"""


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB device")


def main() -> int:
    LOCAL.write_text(SH.replace("\r\n", "\n"), encoding="utf-8")
    s = serial()
    print("serial", s)
    subprocess.run([ADB, "-s", s, "push", str(LOCAL), REMOTE], check=True)
    r = subprocess.run(
        [ADB, "-s", s, "shell", "sed -i 's/\\r$//' /tmp/cam1_i2c_swap.sh; sh /tmp/cam1_i2c_swap.sh"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    print(r.stdout)
    print(r.stderr)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
