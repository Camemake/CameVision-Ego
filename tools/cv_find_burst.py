#!/usr/bin/env python3
import subprocess

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "0558fa189447bc45"


def sh(cmd):
    r = subprocess.run([ADB, "-s", S, "shell", cmd], capture_output=True, text=True)
    print(r.stdout, end="")
    if r.stderr:
        print(r.stderr, end="")


sh("ps | grep -v grep | grep -E 'burst|isp_grab|camevision|while true'")
sh("grep -l isp.burst /userdata/* /etc/init.d/* 2>/dev/null")
sh("tr '\\0' ' ' < /proc/2368/cmdline; echo; cat /proc/2368/status | grep -E 'PPid|State'")
sh("ls -l /proc/2368/cwd /proc/2370/cwd 2>/dev/null")
