#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd: str) -> None:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


sh("echo cam-clk0-pins cam_clk0 > /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-select")
sh("echo cam-clk1-pins cam_clk1 > /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-select")
sh("grep 'gpio4-8\\|gpio4-9\\|gpio4-2\\|gpio4-3' /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-pins")
sh("/sbin/devmem 0x2000083C 32 0x00180000")

sh(r"""
for n in 130 131; do
  [ -d /sys/class/gpio/gpio$n ] || echo $n > /sys/class/gpio/export
  echo out > /sys/class/gpio/gpio$n/direction
done
for a2 in 0 1; do
  for a3 in 0 1; do
    echo $a2 > /sys/class/gpio/gpio130/value
    echo $a3 > /sys/class/gpio/gpio131/value
    sleep 0.05
    echo "=== A2=$a2 A3=$a3 ==="
    echo -n "i2c3 "; i2cdetect -y 3 | sed -n '/^30:/p'
    echo -n "i2c4 "; i2cdetect -y 4 | sed -n '/^30:/p'
  done
done
""")
