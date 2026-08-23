#!/usr/bin/env python3
"""Decompile a flattened device tree blob into readable DTS.

Written for the RV1126B boot.img FIT: finds the embedded FDT, rebuilds the node
tree, and resolves phandles back to labels using the /__symbols__ node so the
output can be used as a reference when writing a board .dts by hand.

Usage:
    dtb_decompile.py <boot.img|dtb> [out.dts]
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

FDT_BEGIN_NODE = 0x1
FDT_END_NODE = 0x2
FDT_PROP = 0x3
FDT_NOP = 0x4
FDT_END = 0x9

# Properties whose cells are phandles (so they can be printed as &label).
PHANDLE_PROPS = {
    "interrupt-parent",
    "interrupt-affinity",
    "remote-endpoint",
    "next-level-cache",
    "cpu",
    "memory-region",
    "iommus",
    "operating-points-v2",
    "power-domains",
    "rockchip,pmu",
    "mboxes",
    "sram",
    "nvmem-cells",
    "pinctrl-names-skip",
}
PHANDLE_PREFIX = ("pinctrl-", "clocks", "resets", "phys", "assigned-clocks")
PHANDLE_SUFFIX = ("-supply", "-gpios", "-gpio", "-parents", "-map")

STRING_PROPS = {
    "compatible",
    "status",
    "model",
    "name",
    "clock-names",
    "reset-names",
    "pinctrl-names",
    "phy-names",
    "interrupt-names",
    "label",
    "linux,default-trigger",
    "regulator-name",
    "rockchip,camera-module-name",
    "rockchip,camera-module-lens-name",
    "rockchip,camera-module-index",
    "default-trigger",
    "function",
    "gpio-controller-name",
    "stdout-path",
    "bootargs",
    "device_type",
    "firmware-name",
    "assigned-clock-names",
    "dma-names",
    "io-channel-names",
    "avdd-supply-name",
    "mode",
}


def find_fdts(data: bytes) -> list[tuple[int, int]]:
    out = []
    off = 0
    while True:
        i = data.find(b"\xd0\x0d\xfe\xed", off)
        if i < 0:
            break
        total = int.from_bytes(data[i + 4 : i + 8], "big")
        if 0x100 < total <= len(data) - i:
            out.append((i, total))
        off = i + 4
    return out


class Fdt:
    def __init__(self, blob: bytes):
        self.blob = blob
        (
            _magic,
            self.totalsize,
            self.off_dt_struct,
            self.off_dt_strings,
            self.off_mem_rsvmap,
            self.version,
            self.last_comp_version,
            self.boot_cpuid_phys,
            self.size_dt_strings,
            self.size_dt_struct,
        ) = struct.unpack(">10I", blob[:40])

    def string(self, off: int) -> str:
        end = self.blob.find(b"\x00", self.off_dt_strings + off)
        return self.blob[self.off_dt_strings + off : end].decode("ascii", "replace")

    def walk(self):
        """Yield ('begin', name) / ('prop', name, value) / ('end', None)."""
        pos = self.off_dt_struct
        limit = self.off_dt_struct + self.size_dt_struct
        while pos < limit:
            (token,) = struct.unpack_from(">I", self.blob, pos)
            pos += 4
            if token == FDT_BEGIN_NODE:
                end = self.blob.find(b"\x00", pos)
                name = self.blob[pos:end].decode("ascii", "replace")
                pos = (end + 1 + 3) & ~3
                yield ("begin", name, None)
            elif token == FDT_END_NODE:
                yield ("end", None, None)
            elif token == FDT_PROP:
                plen, nameoff = struct.unpack_from(">II", self.blob, pos)
                pos += 8
                val = self.blob[pos : pos + plen]
                pos = (pos + plen + 3) & ~3
                yield ("prop", self.string(nameoff), val)
            elif token == FDT_NOP:
                continue
            elif token == FDT_END:
                return
            else:
                raise ValueError(f"bad token {token:#x} at {pos:#x}")


class Node:
    __slots__ = ("name", "props", "children", "parent")

    def __init__(self, name: str, parent: "Node | None" = None):
        self.name = name
        self.props: list[tuple[str, bytes]] = []
        self.children: list[Node] = []
        self.parent = parent

    def path(self) -> str:
        parts = []
        n: Node | None = self
        while n is not None and n.parent is not None:
            parts.append(n.name)
            n = n.parent
        return "/" + "/".join(reversed(parts)) if parts else "/"

    def get(self, name: str) -> bytes | None:
        for k, v in self.props:
            if k == name:
                return v
        return None

    def walk(self):
        yield self
        for c in self.children:
            yield from c.walk()


def build(fdt: Fdt) -> Node:
    root = Node("")
    cur = root
    first = True
    for kind, name, val in fdt.walk():
        if kind == "begin":
            if first:
                first = False
                continue
            child = Node(name, cur)
            cur.children.append(child)
            cur = child
        elif kind == "end":
            if cur.parent is not None:
                cur = cur.parent
        else:
            cur.props.append((name, val or b""))
    return root


def is_phandle_prop(name: str) -> bool:
    if name in PHANDLE_PROPS:
        return True
    if any(name.startswith(p) for p in PHANDLE_PREFIX):
        return True
    if any(name.endswith(s) for s in PHANDLE_SUFFIX):
        return True
    return False


def printable_strings(val: bytes) -> list[str] | None:
    if not val or val[-1] != 0:
        return None
    parts = val[:-1].split(b"\x00")
    out = []
    for p in parts:
        if not p:
            return None
        if not all(32 <= c < 127 or c in (9,) for c in p):
            return None
        out.append(p.decode("ascii"))
    return out or None


def fmt_value(name: str, val: bytes, labels: dict[int, str]) -> str:
    if len(val) == 0:
        return ""
    if name in STRING_PROPS or name.endswith("-names"):
        s = printable_strings(val)
        if s:
            return " = " + ", ".join(f'"{x}"' for x in s)
    if len(val) % 4 == 0:
        cells = list(struct.unpack(f">{len(val) // 4}I", val))
        if is_phandle_prop(name) and cells:
            toks = []
            for idx, c in enumerate(cells):
                if idx == 0 and c in labels:
                    toks.append("&" + labels[c])
                elif c in labels and (name.startswith("pinctrl-") or name.endswith("-map")):
                    toks.append("&" + labels[c])
                else:
                    toks.append(f"{c:#x}")
            return " = <" + " ".join(toks) + ">"
        return " = <" + " ".join(f"{c:#x}" for c in cells) + ">"
    s = printable_strings(val)
    if s:
        return " = " + ", ".join(f'"{x}"' for x in s)
    return " = [" + " ".join(f"{b:02x}" for b in val) + "]"


def main() -> int:
    src = Path(sys.argv[1])
    data = src.read_bytes()
    fdts = find_fdts(data)
    if not fdts:
        raise SystemExit("no FDT found")
    # pick the biggest blob: the kernel dtb rather than the FIT header
    off, size = max(fdts, key=lambda t: t[1])
    print(f"using FDT at {off:#x} size {size} (found {len(fdts)})", file=sys.stderr)
    fdt = Fdt(data[off : off + size])
    root = build(fdt)

    # phandle -> path, then label from __symbols__
    ph_to_path: dict[int, str] = {}
    for n in root.walk():
        for pname in ("phandle", "linux,phandle"):
            v = n.get(pname)
            if v and len(v) == 4:
                ph_to_path[struct.unpack(">I", v)[0]] = n.path()

    path_to_label: dict[str, str] = {}
    for n in root.walk():
        if n.name == "__symbols__":
            for k, v in n.props:
                s = printable_strings(v)
                if s:
                    path_to_label[s[0]] = k
    labels = {ph: path_to_label[p] for ph, p in ph_to_path.items() if p in path_to_label}
    print(
        f"phandles={len(ph_to_path)} symbols={len(path_to_label)} resolved={len(labels)}",
        file=sys.stderr,
    )

    lines: list[str] = ["/dts-v1/;", ""]

    def emit(n: Node, depth: int) -> None:
        ind = "\t" * depth
        label = path_to_label.get(n.path())
        prefix = f"{label}: " if label and depth > 0 else ""
        name = n.name if n.name else "/"
        lines.append(f"{ind}{prefix}{name} {{")
        for k, v in n.props:
            if k in ("phandle", "linux,phandle"):
                continue
            lines.append(f"{ind}\t{k}{fmt_value(k, v, labels)};")
        for c in n.children:
            if c.name == "__symbols__":
                continue
            emit(c, depth + 1)
        lines.append(f"{ind}}};")

    emit(root, 0)

    out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".dts")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out} ({len(lines)} lines)", file=sys.stderr)

    idx = out.with_name(out.stem + "_labels.txt")
    idx.write_text(
        "\n".join(f"{lbl}\t{path}" for path, lbl in sorted(path_to_label.items(), key=lambda x: x[1])),
        encoding="utf-8",
    )
    print(f"wrote {idx}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
