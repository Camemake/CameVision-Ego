#!/usr/bin/env python3
"""Print node subtrees from a .dts by label or node name, using brace matching."""
from __future__ import annotations

import re
import sys
from pathlib import Path

DTS = Path(r"C:\Users\stefa\Desktop\CameVision Single\sdk-dt\aura-stock.dts")


def find_nodes(lines: list[str], needle: str) -> list[int]:
    pat = re.compile(rf"(?:^|\s)(?:{re.escape(needle)}:\s|{re.escape(needle)}\s*\{{)")
    hits = []
    for i, line in enumerate(lines):
        if line.rstrip().endswith("{") and pat.search(line):
            hits.append(i)
    return hits


def emit(lines: list[str], start: int, max_lines: int) -> None:
    depth = 0
    for i in range(start, len(lines)):
        line = lines[i]
        depth += line.count("{") - line.count("}")
        print(line.rstrip())
        if i - start >= max_lines:
            print("\t\t... truncated ...")
            break
        if depth <= 0:
            break


def main() -> int:
    lines = DTS.read_text(encoding="utf-8").splitlines()
    max_lines = 90
    for needle in sys.argv[1:]:
        if needle.isdigit():
            max_lines = int(needle)
            continue
        hits = find_nodes(lines, needle)
        print(f"\n########## {needle}  ({len(hits)} match) ##########")
        for h in hits[:2]:
            emit(lines, h, max_lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
