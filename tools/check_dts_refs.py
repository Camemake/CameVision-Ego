#!/usr/bin/env python3
"""Sanity-check a board .dts against the labels present in the stock DTB.

Reports every &reference that is neither defined in the .dts itself nor known
from the decompiled stock device tree, which catches typos and nodes that do not
exist on this SoC.
"""
from __future__ import annotations

import re
from pathlib import Path

DTS = Path(r"C:\Users\stefa\Desktop\CameVision Single\device-tree\rv1126b-camevision-single.dts")
LABELS = Path(r"C:\Users\stefa\Desktop\CameVision Single\sdk-dt\aura-stock_labels.txt")

text = DTS.read_text(encoding="utf-8")
# strip comments so commented-out examples do not count
text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
text = re.sub(r"//.*", "", text)

known = {line.split("\t")[0] for line in LABELS.read_text(encoding="utf-8").splitlines() if line}
defined = set(re.findall(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*):\s", text, re.M))
refs = set(re.findall(r"&([a-zA-Z_][a-zA-Z0-9_]*)", text))

print(f"labels defined here: {len(defined)}")
print(f"references: {len(refs)}")

missing = sorted(r for r in refs if r not in defined and r not in known)
print("\n-- references NOT found in stock DTB (need confirmation) --")
for m in missing:
    print(f"  {m}")

clash = sorted(d for d in defined if d in known)
print("\n-- labels defined here that also exist in the stock DTB --")
for c in clash:
    path = next(l.split("\t")[1] for l in LABELS.read_text(encoding="utf-8").splitlines() if l.split("\t")[0] == c)
    print(f"  {c:24s} stock path: {path}")

# brace balance
depth = 0
for i, line in enumerate(text.splitlines(), 1):
    depth += line.count("{") - line.count("}")
    if depth < 0:
        print(f"\nunbalanced brace at line {i}")
        break
print(f"\nfinal brace depth: {depth} (0 = balanced)")

semi = [
    (i, l.rstrip())
    for i, l in enumerate(text.splitlines(), 1)
    if re.search(r"=\s*<[^>]*>\s*$", l) or re.search(r'=\s*"[^"]*"\s*$', l)
]
print(f"property lines missing a trailing semicolon: {len(semi)}")
for i, l in semi[:10]:
    print(f"  L{i}: {l.strip()}")
