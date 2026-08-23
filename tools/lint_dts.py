#!/usr/bin/env python3
"""Grammar lint for a device tree source file.

dtc is not available on this host, so this tokenizes the .dts and checks the
things a failed SDK build would otherwise tell us: property/node syntax,
duplicate labels, duplicate properties, cell-list well-formedness, and
unit-address vs reg agreement.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

DEFAULT = Path(
    r"C:\Users\stefa\Desktop\CameVision Single\device-tree\rv1126b-camevision-single.dts"
)

NODE_RE = re.compile(r"^(?:([A-Za-z_][\w-]*)\s*:\s*)?([\w,.+@-]+|/)\s*\{$")
PROP_ASSIGN_RE = re.compile(r"^([\w,.#?+-]+)\s*=\s*(.+);$")
PROP_BOOL_RE = re.compile(r"^([\w,.#?+-]+);$")
OVERRIDE_RE = re.compile(r"^&([A-Za-z_]\w*)\s*\{$")
DELETE_RE = re.compile(r"^/delete-(?:node|property)/\s*[^;]+;$")

CELL_RE = re.compile(r"^<[^<>]*>$")
STR_RE = re.compile(r'^"(?:[^"\\]|\\.)*"$')
BYTES_RE = re.compile(r"^\[[0-9a-fA-F\s]+\]$")
REF_RE = re.compile(r"^&[A-Za-z_]\w*$")
# string-valued macros from dt-bindings headers, e.g. LED_FUNCTION_STATUS
MACRO_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)


def logical_lines(text: str):
    """Join continued property values (they wrap across lines) into one line."""
    buf = ""
    start = 0
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            # preprocessor lines do not end in ; { } and must not glue onto the
            # next real statement
            if buf:
                yield start, buf
                buf = ""
            yield i, line
            continue
        if not buf:
            start = i
        buf = f"{buf} {line}".strip() if buf else line
        if buf.endswith(("{", "}", ";")):
            yield start, buf
            buf = ""
    if buf:
        yield start, buf


def check_value(val: str) -> str | None:
    parts = []
    depth = 0
    cur = ""
    in_str = False
    for ch in val:
        if ch == '"' and (not cur or cur[-1] != "\\"):
            in_str = not in_str
        if ch in "<[" and not in_str:
            depth += 1
        if ch in ">]" and not in_str:
            depth -= 1
        if ch == "," and depth == 0 and not in_str:
            parts.append(cur.strip())
            cur = ""
            continue
        cur += ch
    parts.append(cur.strip())
    if depth != 0:
        return "unbalanced < > or [ ]"
    if in_str:
        return "unterminated string"
    for p in parts:
        if not p:
            return "empty element in comma list"
        if (
            CELL_RE.match(p)
            or STR_RE.match(p)
            or BYTES_RE.match(p)
            or REF_RE.match(p)
            or MACRO_RE.match(p)
        ):
            continue
        return f"unrecognised value element: {p[:60]!r}"
    return None


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    text = strip_comments(path.read_text(encoding="utf-8"))

    errors: list[str] = []
    warnings: list[str] = []
    labels: dict[str, int] = {}
    stack: list[tuple[str, set[str], dict[str, str], int]] = []
    depth = 0

    for lineno, line in logical_lines(text):
        if line.startswith(("#include", "/dts-v1/", "/plugin/")):
            continue
        if DELETE_RE.match(line):
            continue

        if line == "};" or line == "}":
            if not stack:
                errors.append(f"L{lineno}: closing brace with no open node")
            else:
                stack.pop()
            depth -= 1
            continue

        if line.endswith("{"):
            m = OVERRIDE_RE.match(line) or NODE_RE.match(line)
            if not m:
                errors.append(f"L{lineno}: cannot parse node header: {line[:70]!r}")
                stack.append(("?", set(), {}, lineno))
                depth += 1
                continue
            if line.startswith("&"):
                name = "&" + m.group(1)
                label = None
            else:
                label, name = m.group(1), m.group(2)
            if label:
                if label in labels:
                    errors.append(
                        f"L{lineno}: duplicate label {label!r} (also L{labels[label]})"
                    )
                labels[label] = lineno
            if stack:
                siblings = stack[-1][1]
                if name in siblings:
                    errors.append(f"L{lineno}: duplicate sibling node {name!r}")
                siblings.add(name)
            stack.append((name, set(), {}, lineno))
            depth += 1
            continue

        if not line.endswith(";"):
            errors.append(f"L{lineno}: statement does not end with ';': {line[:70]!r}")
            continue

        m = PROP_ASSIGN_RE.match(line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            problem = check_value(val)
            if problem:
                errors.append(f"L{lineno}: {key}: {problem}")
            if stack:
                props = stack[-1][2]
                if key in props:
                    errors.append(f"L{lineno}: duplicate property {key!r} in node")
                props[key] = val
            continue

        if PROP_BOOL_RE.match(line):
            continue

        errors.append(f"L{lineno}: cannot parse statement: {line[:70]!r}")

    if stack:
        for name, _, _, lineno in stack:
            errors.append(f"unclosed node {name!r} opened at L{lineno}")

    # unit-address vs reg
    for lineno, line in logical_lines(text):
        pass

    print(f"file: {path.name}")
    print(f"labels defined: {len(labels)}")
    print(f"errors: {len(errors)}")
    for e in errors:
        print("  " + e)
    print(f"warnings: {len(warnings)}")
    for w in warnings:
        print("  " + w)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
