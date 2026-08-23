#!/usr/bin/env python3
"""Copy and inspect the Seekwave 6621 archives (RAR/PDF/DOCX)."""
from pathlib import Path

DOWNLOADS = Path(r"c:\Users\stefa\Downloads")
OUT = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\live\swt6621-docs")
OUT.mkdir(parents=True, exist_ok=True)

rar = next(p for p in DOWNLOADS.iterdir() if p.suffix.lower() == ".rar" and "6621" in p.name)
print("rar", rar, "size", rar.stat().st_size)
data = rar.read_bytes()
print("magic", data[:16].hex(), data[:8])
(OUT / "6621-bt.rar").write_bytes(data)

# list zip-like local headers if any
print("RAR4" if data[:7] == b"Rar!\x1a\x07\x00" else "RAR5" if data[:8] == b"Rar!\x1a\x07\x01\x00" else "unknown")
