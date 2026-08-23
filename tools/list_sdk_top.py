#!/usr/bin/env python3
"""List the largest / most interesting entries in the SDK tarball."""
from __future__ import annotations

import tarfile
import time
from pathlib import Path

DOWNLOADS = Path.home() / "Downloads"
candidates = sorted(DOWNLOADS.glob("RV1126B_Linux_IPC_SDK*/RV1126B_Linux_IPC_SDK_V*.tgz"))
SDK = candidates[-1]
print("using", SDK, flush=True)

entries: list[tuple[int, str]] = []
t0 = time.time()
with tarfile.open(SDK, "r|gz") as tf:
    for m in tf:
        entries.append((m.size, m.name))

print(f"total entries {len(entries)} in {time.time() - t0:.0f}s")
print("---- 40 largest ----")
for size, name in sorted(entries, reverse=True)[:40]:
    print(f"{size:>14,}  {name}")
print("---- first 40 by name ----")
for size, name in sorted(entries, key=lambda x: x[1])[:40]:
    print(f"{size:>14,}  {name}")

out = Path(r"C:\Users\stefa\Desktop\CameVision Single\sdk-dt\_toplevel.txt")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(f"{s}\t{n}" for s, n in sorted(entries, key=lambda x: x[1])), encoding="utf-8")
print("wrote", out)
