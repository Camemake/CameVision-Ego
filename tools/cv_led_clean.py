#!/usr/bin/env python3
from pathlib import Path

p = Path(r"C:\Users\stefa\Desktop\CameVision Single\tools\cv_led_diag.out.txt")
raw = p.read_bytes()
text = raw.replace(b"\x00", b" ").decode("utf-8", "replace")
# keep first 200k of cleaned text plus search hits
out = Path(r"C:\Users\stefa\Desktop\CameVision Single\tools\cv_led_diag.clean.txt")
# Extract around section markers
markers = [
    "=== PING",
    "=== SYSFS",
    "=== LED DEVICE",
    "=== PROC DEVICE",
    "=== DT LED",
    "=== DMESG",
    "=== INIT",
    "=== S99",
    "=== USERDATA",
    "=== PROC CMDLINE",
    "=== DONE",
]
idxs = []
for m in markers:
    i = text.find(m)
    idxs.append((m, i))
print("markers:", idxs[:20])
print("len", len(text), "bytes", len(raw))

# Write a truncated readable version: skip huge binary dumps
chunks = []
# SYSFS section
for start_name, end_name in [
    ("=== PING", "=== LED DEVICE"),
    ("=== DT LED", "=== DMESG"),
    ("=== DMESG", "=== INIT"),
    ("=== INIT", None),
]:
    a = text.find(start_name)
    b = text.find(end_name) if end_name else len(text)
    if a < 0:
        continue
    if b < 0:
        b = min(a + 8000, len(text))
    piece = text[a:b]
    if len(piece) > 30000:
        piece = piece[:30000] + "\n...TRUNC...\n"
    chunks.append(piece)

# Also grab sysfs leds listing if ping-to-led-device missed it
sysfs = text.find("=== SYSFS")
leddev = text.find("=== LED DEVICE")
if sysfs >= 0 and leddev > sysfs:
    chunks.insert(1, text[sysfs:leddev][:20000])

out.write_text("\n\n".join(chunks), encoding="utf-8")
print("wrote", out, "chars", out.stat().st_size)
