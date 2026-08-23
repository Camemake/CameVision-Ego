#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd: str) -> None:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


sh("grep -n cam /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pingroups")
sh("echo === select try ===")
sh("echo cam-clk0-pins > /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-select; echo sel0:$?")
sh("echo cam-clk1-pins > /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-select; echo sel1:$?")
sh("grep -n 'gpio4-8\\|gpio4-9' /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-pins")
sh("echo === clk rate write ===")
sh("cat /sys/kernel/debug/clk/clk_mipi0_out2io/clk_rate; echo 27000000 > /sys/kernel/debug/clk/clk_mipi0_out2io/clk_rate; cat /sys/kernel/debug/clk/clk_mipi0_out2io/clk_rate; cat /sys/kernel/debug/clk/clk_mipi0_out2io/clk_enable_count")
