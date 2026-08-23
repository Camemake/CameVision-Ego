#!/usr/bin/env python3
import tarfile
from pathlib import Path

root = Path(r"C:\Users\stefa\Downloads")
tgzs = list(root.rglob("*.tgz")) + list(root.rglob("*.tar.gz"))
print("tgz count", len(tgzs))
for t in tgzs:
    if "RV1126" in t.name or "1126" in t.name:
        print("CAND", t.name, flush=True)

target = None
for t in tgzs:
    if "RV1126B_Linux_IPC_SDK_V1.2.1" in t.name:
        target = t
        break
if not target:
    raise SystemExit("sdk tgz not found")
print("using name ok", flush=True)
with tarfile.open(target, "r:gz") as tf:
    hits = [n for n in tf.getnames() if "sc233hgs" in n.lower()]
    print("hits", len(hits))
    for n in hits:
        print(n)
    out = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\sc233hgs.c")
    for n in hits:
        if n.endswith("sc233hgs.c"):
            src = tf.extractfile(n)
            out.write_bytes(src.read())
            print("wrote", out, "from", n)
            break
