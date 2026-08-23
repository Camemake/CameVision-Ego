#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "b9129b95306c7715"


def sh(cmd: str) -> None:
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


sh("ls /sys/kernel/debug/clk/clk_mipi0_out2io; echo ---; ls /sys/kernel/debug/clk | head")
sh("ls /sys/kernel/debug/pinctrl")
sh("ls /sys/kernel/debug/pinctrl/*/")
sh("which devmem; ls /usr/sbin/devmem /sbin/devmem 2>/dev/null")
sh("echo === pinmux files ===; ls /sys/kernel/debug/pinctrl/pinctrl*")
