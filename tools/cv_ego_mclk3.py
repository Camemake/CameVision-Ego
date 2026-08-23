#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd: str) -> None:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


sh("echo === functions ===; grep -n cam /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-functions")
sh("echo === pingroups cam ===; sed -n '1,20p' /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pingroups")

# pinmux-select formats
for s in (
    "gpio4-9 3",
    "gpio4-8 3",
    "gpio4-9 cam_clk0",
    "cam-clk0-pins cam_clk0",
):
    sh(f"echo 'try {s}'; echo {s} > /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-select; echo rc:$?")

sh("grep 'gpio4-8\\|gpio4-9' /sys/kernel/debug/pinctrl/pinctrl-rockchip-pinctrl/pinmux-pins")

# CRU CLKGATE_CON(15) @ 0x2000083C — HIWORD mask, SET_TO_DISABLE: write 0 + mask to enable
sh("echo === cru gate15 ===; /sbin/devmem 0x2000083C 32")
sh("/sbin/devmem 0x2000083C 32 0x00180000")
sh("/sbin/devmem 0x2000083C 32")
sh("echo === clk after ===; cat /sys/kernel/debug/clk/clk_mipi0_out2io/clk_enable_count; cat /sys/kernel/debug/clk/clk_summary | grep mipi0_out2io")
