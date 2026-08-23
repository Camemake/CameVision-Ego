#!/usr/bin/env python3
"""Turn the MCU schematic PDF into a machine-readable netlist.

Altium's PDF export contains two useful layers of text:

  1. Pin tables, e.g.  "I2C0_SCL_M0 <tab> SPI2AHB_CSN <tab> GPIO0_C2_U 1AA12"
     which map a BGA pad to its mux options.
  2. A flat netlist where pin ids are listed and then terminated by a net label
     or sheet port.  Altium encodes every non-alphanumeric character as '0', so
     "U1-AA12" becomes "PIU10AA12" and "I2C0_SCL_PMIC" becomes
     "NLI2C00SCL0PMIC".

This script rebuilds pad -> function and net -> pads, then joins them so every
net that touches the SoC reports the GPIO bank/pin and available mux functions.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from pypdf import PdfReader

PDF = Path(
    r"C:\Users\stefa\Desktop\Project Efference\M1\PCB's\V2"
    r"\V2.1 MONO-MCU-DDR4-PCB2_Filip_2\Manufacturing Files\Schematics.PDF"
)
OUT = Path(r"C:\Users\stefa\Desktop\CameVision Single\schematic")

PAD_RE = r"[12]?[A-Z]{1,2}\d{1,2}"
GPIO_RE = re.compile(rf"(GPIO\d_[A-D]\d)_([UDZ])\s+({PAD_RE})\b")
PIN_RE = re.compile(r"^PI([A-Z]+\d+[A-Z]*)0(.+)$")


def decode(label: str) -> str:
    """Altium replaces '_' (and other punctuation) with '0'. Show both forms."""
    return label


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(PDF)
    pages = [p.extract_text() or "" for p in reader.pages]
    full = "\n".join(pages)
    (OUT / "schematic_text.txt").write_text(full, encoding="utf-8")
    print(f"pages={len(pages)} chars={len(full)}")

    # ---- 1. pad -> gpio + mux functions -------------------------------------
    pad_gpio: dict[str, str] = {}
    pad_pull: dict[str, str] = {}
    pad_funcs: dict[str, list[str]] = {}
    for page in pages:
        for line in page.splitlines():
            for gpio, pull, pad in GPIO_RE.findall(line):
                pad_gpio[pad] = gpio
                pad_pull[pad] = pull
                head = line.split(gpio)[0]
                funcs = [t for t in re.split(r"[\s\t]+", head.strip()) if t]
                pad_funcs.setdefault(pad, [])
                for f in funcs:
                    if f not in pad_funcs[pad]:
                        pad_funcs[pad].append(f)
    print(f"pads with GPIO mapping: {len(pad_gpio)}")

    # power / analog pins have no GPIO name, capture them too
    pad_power: dict[str, str] = {}
    pwr_re = re.compile(rf"^([A-Z0-9_]+?)\s+({PAD_RE})$")
    for page in pages:
        for line in page.splitlines():
            m = pwr_re.match(line.strip())
            if m:
                name, pad = m.groups()
                if pad not in pad_gpio and len(name) > 2:
                    pad_power.setdefault(pad, name)

    # ---- 2. netlist: pin ids grouped by trailing net label ------------------
    # The export has two blocks. First every component is declared as its pins
    # followed by a CO<designator> token; then each net lists its pins followed
    # by NL<net> / PO<port>. Resetting on CO keeps the declaration block from
    # bleeding into the first net. Unlabelled power nets still run into the next
    # label, so power/ground pads are dropped and oversized groups are flagged.
    power_pat = re.compile(r"VSS|VDD|AVSS|AVDD|VCC|DVDD|_VCC|RTC_AVDD|OTP_VCC")

    nets: dict[str, set[str]] = defaultdict(set)
    flagged: set[str] = set()
    pending: list[str] = []
    for line in full.splitlines():
        for tok in re.split(r"[\s\t]+", line.strip()):
            if not tok:
                continue
            if tok.startswith("CO"):
                pending = []
            elif tok.startswith("PI"):
                pending.append(tok)
            elif tok.startswith("NL") or tok.startswith("PO"):
                label = tok[2:]
                group = pending
                pending = []
                if len(group) > 12:
                    flagged.add(label)
                    kept = []
                    for pin in group:
                        m = PIN_RE.match(pin)
                        if not m:
                            continue
                        pad = m.group(2)
                        name = pad_power.get(pad, "")
                        if pad in pad_gpio or not power_pat.search(name):
                            kept.append(pin)
                    group = kept
                nets[label].update(group)
    print(f"net labels: {len(nets)} (flagged oversized: {len(flagged)})")
    (OUT / "flagged_nets.txt").write_text("\n".join(sorted(flagged)), encoding="utf-8")

    # ---- 3. join ------------------------------------------------------------
    report: dict[str, dict] = {}
    for label, pins in sorted(nets.items()):
        entry: dict = {"pins": [], "soc": []}
        for pin in sorted(pins):
            m = PIN_RE.match(pin)
            if not m:
                entry["pins"].append(pin)
                continue
            desig, pad = m.groups()
            entry["pins"].append(f"{desig}.{pad}")
            if desig == "U1":
                entry["soc"].append(
                    {
                        "pad": pad,
                        "gpio": pad_gpio.get(pad),
                        "pull": pad_pull.get(pad),
                        "funcs": pad_funcs.get(pad, []),
                        "power": pad_power.get(pad),
                    }
                )
        report[label] = entry

    (OUT / "netlist.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    (OUT / "pad_map.json").write_text(
        json.dumps(
            {
                "pad_gpio": pad_gpio,
                "pad_pull": pad_pull,
                "pad_funcs": pad_funcs,
                "pad_power": pad_power,
            },
            indent=1,
        ),
        encoding="utf-8",
    )

    # ---- 4. human readable summary for nets that reach the SoC --------------
    lines = []
    for label, entry in sorted(report.items()):
        if not entry["soc"]:
            continue
        for s in entry["soc"]:
            gpio = s["gpio"] or (s["power"] or "?")
            pull = f"_{s['pull']}" if s["pull"] else ""
            funcs = " | ".join(s["funcs"][:6])
            lines.append(f"{label:32s} U1.{s['pad']:6s} {gpio}{pull:3s}  {funcs}")
    (OUT / "soc_nets.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"soc net rows: {len(lines)}")

    if len(sys.argv) > 1:
        needle = sys.argv[1].upper()
        for line in lines:
            if needle in line.upper():
                print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
