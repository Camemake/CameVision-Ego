#!/usr/bin/env python3
"""Assemble recovery-3 overlay from recovery-2 binaries + live UVC/RKAIQ files."""
import hashlib
import shutil
from pathlib import Path

REC2 = Path(r"C:\Users\stefa\Desktop\CameVision Single\restore\recovery-2-20260821-adb-stream")
REC3 = Path(r"C:\Users\stefa\Desktop\CameVision Single\restore\recovery-3-20260822-uvc-wifi-rkaiq")
LIVE = Path(r"C:\Users\stefa\Desktop\CameVision Single\build\live")
OV2 = REC2 / "overlay"
OV3 = REC3 / "overlay"

TEXT = {
    "S20linkmount": OV2 / "S20linkmount",
    "S21appinit": OV2 / "S21appinit",
    "S40network": OV2 / "S40network",
    "S50usbdevice.adb": OV2 / "S50usbdevice",
    "S99camevision": OV2 / "S99camevision",
    "camevision.sh": OV2 / "camevision.sh",
    "camevision-wifi.sh": OV2 / "camevision-wifi.sh",
    "camevision-imu.sh": OV2 / "camevision-imu.sh",
    "camevision-led.sh": OV2 / "camevision-led.sh",
    "camevision-aiq.sh": OV2 / "camevision-aiq.sh",
    "camevision-uvc-cam.sh": OV2 / "camevision-uvc-cam.sh",
    "camevision-uvc-mjpg.py": OV2 / "camevision-uvc-mjpg.py",
    "camevision-uvc-live.sh": OV2 / "camevision-uvc-live.sh",
    "camevision-stream.sh": OV2 / "camevision-stream.sh",
    "swt6621.sh": OV2 / "swt6621.sh",
    "imu-live.sh": OV2 / "imu-live.sh",
    "wifi-ble-test.sh": OV2 / "wifi-ble-test.sh",
    "wpa_camevision.conf": OV2 / "wpa_camevision.conf",
    "insmod_wifi.sh": OV2 / "insmod_wifi.sh",
    "hw_rtsp.py": OV2 / "hw_rtsp.py",
}

OV3.mkdir(parents=True, exist_ok=True)
(OV3 / "iqfiles").mkdir(exist_ok=True)

# UVC S50 is the boot gadget (no dwc3).
src_s50 = LIVE / "S50usbdevice.uvc-rk"
if not src_s50.exists():
    src_s50 = OV2 / "S50usbdevice.uvc-rk"
shutil.copy2(src_s50, OV3 / "S50usbdevice")

for name, src in TEXT.items():
    if not src.exists():
        print("MISSING", src)
        continue
    shutil.copy2(src, OV3 / name)

iq = OV2 / "iqfiles" / "sc233hgs_efference-sc233hgs_default.json"
if iq.exists():
    shutil.copy2(iq, OV3 / "iqfiles" / iq.name)

shutil.copy2(OV2 / "kmpp-rt52.ko", OV3 / "kmpp-rt52.ko")
for dirname in ("swt6621_fw", "swt6621-rt52"):
    dst = OV3 / dirname
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(OV2 / dirname, dst)

boot = REC2 / "camevision_boot_wifi_imu.img"
if boot.exists():
    shutil.copy2(boot, REC3 / "camevision_boot_wifi_imu.img")

# Unix newlines for scripts
for p in OV3.rglob("*"):
    if p.is_file() and p.suffix.lower() not in {".ko", ".bin", ".img", ".json"}:
        if p.suffix.lower() in {".sh", ".py", ".conf"} or p.name.startswith("S"):
            data = p.read_bytes()
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
            unix = text.replace("\r\n", "\n").replace("\r", "\n")
            p.write_bytes(unix.encode("utf-8"))

# Manifest of this package (not huge from-device dumps)
lines = []
for p in sorted(REC3.rglob("*")):
    if not p.is_file():
        continue
    if p.name in {"MANIFEST.sha256", "SHA256SUMS.txt"}:
        continue
    if "from-device" in p.parts:
        continue
    rel = p.relative_to(REC3).as_posix()
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    lines.append(f"{h}  {rel}")
(REC3 / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="ascii")
(REC3 / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="ascii")
print("files", len(lines))
print("S50", (OV3 / "S50usbdevice").stat().st_size)
print("done", REC3)
