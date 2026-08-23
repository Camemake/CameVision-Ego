#!/usr/bin/env python3
import urllib.request

live = urllib.request.urlopen("http://127.0.0.1:8081/", timeout=8).read()
cal = urllib.request.urlopen("http://127.0.0.1:8081/cal", timeout=8).read()
logo = urllib.request.urlopen("http://127.0.0.1:8081/brand.png", timeout=8).read()
print("live title", b"Camemake CameVision Ego" in live, "NPU", b"NPU" in live, "no rv", b"RV1126" not in live)
print("cal title", b"CameVision Ego" in cal, "NPU", b"NPU" in cal, "no rv", b"RV1126" not in cal)
print("logo", len(logo), logo[:8])
