#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd: str) -> None:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


sh(r"""
echo cam-clk0-pins cam_clk0 > /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-select
echo cam-clk1-pins cam_clk1 > /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-select
/sbin/devmem 0x2000083C 32 0x00180000
for n in 8 9 10 130 131; do
  [ -d /sys/class/gpio/gpio$n ] || echo $n > /sys/class/gpio/export
  echo out > /sys/class/gpio/gpio$n/direction
done
for ldo in 0 1; do
  echo $ldo > /sys/class/gpio/gpio8/value
  echo $ldo > /sys/class/gpio/gpio9/value
  echo $ldo > /sys/class/gpio/gpio10/value
  for a2 in 0 1; do
    for a3 in 0 1; do
      echo $a2 > /sys/class/gpio/gpio130/value
      echo $a3 > /sys/class/gpio/gpio131/value
      sleep 0.08
      echo "=== LDO=$ldo A2=$a2 A3=$a3 ==="
      echo -n "i2c3 "; i2cdetect -y 3 | sed -n '/^30:/p'
      echo -n "i2c4 "; i2cdetect -y 4 | sed -n '/^30:/p'
    done
  done
done
""")
