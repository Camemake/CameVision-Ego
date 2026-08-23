#!/usr/bin/env python3
"""Print the schematic pin-table rows that mention the given BGA pads."""
from __future__ import annotations

import re
import sys
from pathlib import Path

TEXT = Path(r"C:\Users\stefa\Desktop\CameVision Single\schematic\schematic_text.txt")

pads = [p.upper() for p in sys.argv[1:]]
lines = TEXT.read_text(encoding="utf-8").splitlines()

for pad in pads:
    print(f"===== pad {pad} =====")
    pat = re.compile(rf"(?<![A-Z0-9]){re.escape(pad)}(?![0-9])")
    hits = 0
    for i, line in enumerate(lines):
        if pat.search(line):
            ctx = " | ".join(
                l.strip() for l in lines[max(0, i - 1) : i + 2] if l.strip()
            )
            print(f"  L{i}: {ctx}")
            hits += 1
            if hits >= 4:
                break
    if not hits:
        print("  (not found)")
