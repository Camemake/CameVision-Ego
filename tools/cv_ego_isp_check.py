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
        "grep sysctl /userdata/rkaiq.log | tail -8; echo ---; "
        "sed -n '1,16p' /proc/rkisp-vir0; echo ----; sed -n '1,16p' /proc/rkisp-vir2",
    ],
    capture_output=True,
    text=True,
)
print(r.stdout)
if r.stderr:
    print(r.stderr)

for p in (8081, 8082):
    try:
        data = urllib.request.urlopen(f"http://127.0.0.1:{p}/", timeout=8).read(800000)
        s = data.find(b"\xff\xd8")
        e = data.find(b"\xff\xd9", s + 2)
        print(p, "sof", s, "eof", e, "n", len(data))
        if s >= 0 and e > s:
            im = Image.open(io.BytesIO(data[s : e + 2]))
            print(p, "size", im.size, im.mode)
    except Exception as ex:
        print(p, "ERR", ex)
