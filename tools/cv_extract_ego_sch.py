#!/usr/bin/env python3
"""Extract text from the CameVision Ego schematic PDF."""
from pathlib import Path
from pypdf import PdfReader

src = Path(r"c:\Users\stefa\Downloads\Schematic PDF_[No Variations] (12).pdf")
dst_dir = Path(r"C:\Users\stefa\Desktop\CameVision Ego\schematic-ego")
dst_dir.mkdir(parents=True, exist_ok=True)
out = dst_dir / "schematic_text.txt"

reader = PdfReader(str(src))
print("pages", len(reader.pages))
chunks = []
for i, page in enumerate(reader.pages, 1):
    t = page.extract_text() or ""
    chunks.append(f"\n\n===== PAGE {i} =====\n")
    chunks.append(t)
    print(f"page {i} chars {len(t)}")

out.write_text("".join(chunks), encoding="utf-8")
print("wrote", out, "bytes", out.stat().st_size)
