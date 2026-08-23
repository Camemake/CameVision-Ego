#!/usr/bin/env python3
import io
import subprocess
import urllib.request

from PIL import Image

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
S = "4857b9cbd0b99e0b"
r = subprocess.run(
    [
        ADB,
        "-s",
        S,
        "shell",
        "python3 /tmp/ego_i2c_rd.py | grep 3282; "
        "ps | grep rkaiq_3A | grep -v grep; "
        "grep DRC /proc/rkisp-vir0",
    ],
    capture_output=True,
    text=True,
)
print(r.stdout)
data = urllib.request.urlopen("http://127.0.0.1:8081/", timeout=8).read(800000)
s = data.find(b"\xff\xd8")
e = data.find(b"\xff\xd9", s + 2)
print("jpeg", e - s + 2 if e > s else 0)
if e > s:
    im = Image.open(io.BytesIO(data[s : e + 2]))
    print("size", im.size)
    out = r"C:\Users\stefa\Desktop\CameVision Ego\build\stills\cam0_isp_upright.jpg"
    open(out, "wb").write(data[s : e + 2])
    print("wrote", out)
