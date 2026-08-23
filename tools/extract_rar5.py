#!/usr/bin/env python3
"""Minimal RAR5 extractor for stored (uncompressed) members."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

MAGIC = b"Rar!\x1a\x07\x01\x00"


def vint(data: bytes, off: int) -> tuple[int, int]:
    n = 0
    shift = 0
    while True:
        b = data[off]
        off += 1
        n |= (b & 0x7F) << shift
        if not (b & 0x80):
            return n, off
        shift += 7
        if shift > 70:
            raise ValueError("vint too long")


def extract(archive: Path, dest: Path) -> None:
    data = archive.read_bytes()
    if not data.startswith(MAGIC):
        raise SystemExit(f"not rar5: {data[:8]!r}")
    dest.mkdir(parents=True, exist_ok=True)
    pos = 8
    files = 0
    while pos + 8 < len(data):
        if pos + 4 > len(data):
            break
        hdr_crc = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        size, pos = vint(data, pos)
        hdr_start = pos
        htype, pos = vint(data, pos)
        hflags, pos = vint(data, pos)
        extra_size = 0
        data_size = 0
        if hflags & 0x0001:
            extra_size, pos = vint(data, pos)
        if hflags & 0x0002:
            data_size, pos = vint(data, pos)
        # skip rest of header to hdr_start+size
        # parse file header fields if type==2
        name = ""
        method = None
        unpacked = 0
        if htype == 2:  # file
            file_flags, pos = vint(data, pos)
            unpacked, pos = vint(data, pos)
            _attr, pos = vint(data, pos)
            if file_flags & 0x0002:
                pos += 4  # mtime
            if file_flags & 0x0004:
                pos += 4  # crc
            comp_info, pos = vint(data, pos)
            method = (comp_info >> 7) & 0x1F
            _host, pos = vint(data, pos)
            nlen, pos = vint(data, pos)
            name = data[pos : pos + nlen].decode("utf-8", "replace")
            pos += nlen
        pos = hdr_start + size
        payload = data[pos : pos + data_size]
        pos += data_size
        if htype == 5:  # end
            break
        if htype == 2:
            print(f"file {name!r} method={method} unpacked={unpacked} packed={data_size}")
            out = dest / name.replace("\\", "/").lstrip("/")
            out.parent.mkdir(parents=True, exist_ok=True)
            if method == 0:
                out.write_bytes(payload[:unpacked] if unpacked else payload)
                files += 1
            else:
                # keep packed blob for inspection
                (out.parent / (out.name + f".method{method}.packed")).write_bytes(payload)
                print("  COMPRESSED — left packed blob")
    print(f"extracted {files} stored files -> {dest}")


def main() -> int:
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    extract(src, dst)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
