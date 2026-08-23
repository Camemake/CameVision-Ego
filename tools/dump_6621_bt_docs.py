#!/usr/bin/env python3
"""Dump Seekwave BT AT xlsx + PDF into plain text."""
from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from pypdf import PdfReader

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
SRC = Path(r"c:\Users\stefa\Downloads\6621-s_BT认证定频AT指令和文档(1)\6621-s_BT认证定频AT指令和文档")
OUT = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\live\swt6621-docs")


def colrow(cell_ref: str) -> tuple[int, int]:
    m = re.match(r"([A-Z]+)(\d+)", cell_ref)
    if not m:
        return 0, 0
    col = 0
    for ch in m.group(1):
        col = col * 26 + (ord(ch) - 64)
    return col - 1, int(m.group(2)) - 1


def load_shared(z: zipfile.ZipFile) -> list[str]:
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    out = []
    for si in root.findall("m:si", NS):
        out.append("".join(t.text or "" for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")))
    return out


def sheet_to_text(z: zipfile.ZipFile, name: str, shared: list[str]) -> str:
    root = ET.fromstring(z.read(name))
    rows: dict[int, dict[int, str]] = {}
    for c in root.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
        ref = c.get("r") or "A1"
        col, row = colrow(ref)
        t = c.get("t")
        v = c.find("m:v", NS)
        is_el = c.find("m:is", NS)
        if t == "s" and v is not None and v.text:
            val = shared[int(v.text)]
        elif t == "inlineStr" and is_el is not None:
            val = "".join(t2.text or "" for t2 in is_el.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"))
        elif v is not None:
            val = v.text or ""
        else:
            val = ""
        rows.setdefault(row, {})[col] = val.strip()
    lines = []
    for r in sorted(rows):
        maxc = max(rows[r]) if rows[r] else 0
        cells = [rows[r].get(c, "") for c in range(maxc + 1)]
        if any(cells):
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def dump_xlsx() -> None:
    xlsx = next(SRC.glob("*.xlsx"))
    z = zipfile.ZipFile(xlsx)
    shared = load_shared(z)
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    sheets = []
    for sh in wb.findall("m:sheets/m:sheet", NS):
        sheets.append((sh.get("name"), sh.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")))
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {
        r.get("Id"): r.get("Target")
        for r in rels
    }
    parts = [f"# {xlsx.name}\n"]
    for name, rid in sheets:
        target = rid_to_target[rid].lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        body = sheet_to_text(z, target, shared)
        parts.append(f"\n## sheet: {name}\n")
        parts.append(body)
        parts.append("")
    text = "\n".join(parts)
    (OUT / "bt-at-list.txt").write_text(text, encoding="utf-8")
    print("xlsx sheets", [n for n, _ in sheets], "chars", len(text))


def dump_pdf() -> None:
    pdf = next(p for p in SRC.iterdir() if p.suffix.lower() == ".pdf")
    reader = PdfReader(str(pdf))
    pages = []
    for i, page in enumerate(reader.pages):
        t = page.extract_text() or ""
        pages.append(f"\n----- page {i+1} -----\n{t}")
    text = "\n".join(pages)
    (OUT / "bt-at-manual.txt").write_text(text, encoding="utf-8")
    print("pdf pages", len(reader.pages), "chars", len(text))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    dump_xlsx()
    dump_pdf()
