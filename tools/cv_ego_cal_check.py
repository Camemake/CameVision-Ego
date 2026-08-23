#!/usr/bin/env python3
import time
import urllib.request

time.sleep(1)
print(urllib.request.urlopen("http://127.0.0.1:8081/cal/stat", timeout=8).read().decode())
html = urllib.request.urlopen("http://127.0.0.1:8081/cal", timeout=8).read()
print("cal11", b'value="11"' in html, "move", b"While recording" in html, "cam0", b"CAM0" in html)
live = urllib.request.urlopen("http://127.0.0.1:8081/", timeout=8).read()
print("live cam0", b"LEFT CAM0" in live)
time.sleep(2)
r = urllib.request.urlopen("http://127.0.0.1:8081/snapr0", timeout=8)
print("raw0", r.status, r.headers.get("Content-Length"))
