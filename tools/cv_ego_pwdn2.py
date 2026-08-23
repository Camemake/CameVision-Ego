#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd: str) -> str:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    text = (r.stdout or "") + (r.stderr or "")
    print(text, end="")
    return text


sh("echo === cam clk pins ===; cat /sys/kernel/debug/pinctrl/*/pinmux-pins | grep -nE 'gpio4-8|gpio4-9|cam.clk|CAM_CLK'")
sh("echo === clk ===; cat /sys/kernel/debug/clk/clk_summary 2>/dev/null | grep -iE 'mipi0_out|mipi1_out|cam0|cam1|out2io' | head -30")

# Drive both PWDN lines and scan I2C for each polarity.
script = r"""
set -e
exp() {
  n=$1
  [ -d /sys/class/gpio/gpio$n ] || echo $n > /sys/class/gpio/export
  echo out > /sys/class/gpio/gpio$n/direction
}
exp 130
exp 131
for a2 in 0 1; do
  for a3 in 0 1; do
    echo $a2 > /sys/class/gpio/gpio130/value
    echo $a3 > /sys/class/gpio/gpio131/value
    usleep 20000
    echo "=== PWDN cam1/A2=$a2 cam0/A3=$a3 ==="
    echo -n "i2c3: "; i2cdetect -y 3 | sed -n '5p'
    echo -n "i2c4: "; i2cdetect -y 4 | sed -n '5p'
  done
done
"""
sh(script)
