#!/usr/bin/env python3
import pathlib
import urllib.request

p = pathlib.Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\stills")
p.mkdir(parents=True, exist_ok=True)
data = urllib.request.urlopen("http://127.0.0.1:8081/", timeout=8).read(800000)
s = data.find(b"\xff\xd8")
e = data.find(b"\xff\xd9", s + 2)
out = p / "cam0_isp_upright.jpg"
out.write_bytes(data[s : e + 2])
print(out, e - s + 2)
