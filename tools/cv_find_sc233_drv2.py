#!/usr/bin/env python3
import tarfile
from pathlib import Path

root = Path(r"C:\Users\stefa\Downloads")
for tgz in root.rglob("*.tgz"):
    if "RV1126" not in tgz.name:
        continue
    print("scan", tgz.name, flush=True)
    try:
        with tarfile.open(tgz, "r:gz") as tf:
            hits = [n for n in tf.getnames() if "sc233" in n.lower()]
    except Exception as e:
        print("  err", type(e).__name__)
        continue
    print("  hits", len(hits))
    for n in hits[:30]:
        print(" ", n)
