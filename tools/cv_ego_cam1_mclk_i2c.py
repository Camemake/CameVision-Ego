#!/usr/bin/env python3
"""Enable Cam1 MCLK, then bit-bang I2C with both SCL/SDA mappings."""
from __future__ import annotations

import subprocess
from pathlib import Path

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
REMOTE = "/tmp/cam1_mclk_i2c.sh"
LOCAL = Path(__file__).with_name("cam1_mclk_i2c.sh")

SH = r"""#!/bin/sh
set -eu
mount -t debugfs debugfs /sys/kernel/debug 2>/dev/null || true

echo '=== cam0 still on i2c3? ==='
i2cdetect -y 3 | sed -n '/^30:/p'

echo '=== mux cam-clk1 and ungate CRU ==='
echo cam-clk1-pins cam_clk1 > /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-select || true
/sbin/devmem 0x2000083C 32 0x00180000
echo 'gpio4-8 / clk:'
grep gpio4-8 /sys/kernel/debug/pinctrl/*/pinmux-pins || true
cat /sys/kernel/debug/clk/clk_summary | grep -E 'clk_mipi0_out2io|clk_mipi1_out2io'

echo '=== ioc dump gpio4-ish ==='
/sbin/devmem 0x201A0000 32
/sbin/devmem 0x201A0004 32
/sbin/devmem 0x201A0008 32
/sbin/devmem 0x201A000C 32
/sbin/devmem 0x201A0010 32
/sbin/devmem 0x201A0014 32
/sbin/devmem 0x201A0018 32
/sbin/devmem 0x201A001C 32

# Keep A6/A7 as GPIO for bitbang. A2 is PWDN.
for g in 130 134 135; do
  [ -d /sys/class/gpio/gpio$g ] || echo $g > /sys/class/gpio/export
  echo out > /sys/class/gpio/gpio$g/direction
done

hi() { echo in > /sys/class/gpio/gpio$1/direction; }
lo() { echo out > /sys/class/gpio/gpio$1/direction; echo 0 > /sys/class/gpio/gpio$1/value; }
rd() { cat /sys/class/gpio/gpio$1/value; }

i2c_start() { hi $SDA; hi $SCL; lo $SDA; lo $SCL; }
i2c_stop() { lo $SDA; hi $SCL; hi $SDA; }
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
  for addr in 48 50; do
    i2c_start
    ack=$(i2c_byte $((addr * 2)))
    i2c_stop
    if [ "$ack" = 0 ]; then
      echo ACK $addr
      found=1
    fi
  done
  [ $found -eq 1 ] || echo 'no ACK'
}

echo '=== PWDN 0 then 1, schematic mapping first ==='
echo 0 > /sys/class/gpio/gpio130/value
scan 135 134
scan 134 135
echo 1 > /sys/class/gpio/gpio130/value
scan 135 134
scan 134 135

echo '=== cam0 still on i2c3? ==='
i2cdetect -y 3 | sed -n '/^30:/p'
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
        [ADB, "-s", s, "shell", "sed -i 's/\\r$//' /tmp/cam1_mclk_i2c.sh; sh /tmp/cam1_mclk_i2c.sh"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    print(r.stdout)
    print(r.stderr)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
