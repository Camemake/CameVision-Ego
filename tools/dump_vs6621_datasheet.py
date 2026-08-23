#!/usr/bin/env python3
from pathlib import Path
from pypdf import PdfReader

src = next(
    p
    for p in Path(r"c:\Users\stefa\Desktop\Project Efference\M1").iterdir()
    if "VS6621S80_datasheet" in p.name and p.suffix.lower() == ".pdf"
)
out = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\live\swt6621-docs\vs6621s80-datasheet.txt")
print("src", src)
reader = PdfReader(str(src))
parts = []
for i, page in enumerate(reader.pages):
    t = page.extract_text() or ""
    parts.append(f"\n----- page {i+1} -----\n{t}")
text = "\n".join(parts)
out.write_text(text, encoding="utf-8")
print("pages", len(reader.pages), "chars", len(text))
