#!/usr/bin/env python3
"""Snapshot live Recovery 3 files from the board over telnet."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

DST = Path(
    r"C:\Users\stefa\Desktop\CameVision Single\restore\recovery-3-20260822-uvc-wifi-rkaiq\from-device"
)
(DST / "init").mkdir(parents=True, exist_ok=True)
(DST / "scripts").mkdir(parents=True, exist_ok=True)
(DST / "logs").mkdir(parents=True, exist_ok=True)

text = run(
    r"""
echo '---FILE S50---'
cat /etc/init.d/S50usbdevice
echo '---FILE S99---'
cat /etc/init.d/S99camevision
echo '---FILE UVCLOG---'
cat /userdata/cv-uvc-live.log 2>/dev/null
echo '---FILE RKAIQ---'
grep sysctl /userdata/rkaiq.log | tail -8
echo '---FILE STATUS---'
echo -n product=; cat /sys/kernel/config/usb_gadget/rockchip/strings/0x409/product
echo -n pid=; cat /sys/kernel/config/usb_gadget/rockchip/idProduct
echo -n state=; cat /sys/class/udc/21500000.usb/state
ip -4 addr show wlan0 | grep inet
ps | grep -E 'rkaiq_3A|uvc-mjpg|v4l2-ctl|adbd' | grep -v grep
""",
    wait=10,
)

# Split marked files
parts = text.split("---FILE ")
mapping = {
    "S50---": DST / "init" / "S50usbdevice",
    "S99---": DST / "init" / "S99camevision",
    "UVCLOG---": DST / "logs" / "cv-uvc-live.log",
    "RKAIQ---": DST / "logs" / "rkaiq-sysctl.txt",
    "STATUS---": DST / "logs" / "live-status.txt",
}
for part in parts:
    for key, path in mapping.items():
        if part.startswith(key):
            body = part[len(key) :]
            # strip telnet prompts roughly
            lines = []
            for line in body.splitlines():
                if line.startswith("sh-") or line.startswith("__END"):
                    continue
                lines.append(line)
            path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
            print("wrote", path, "bytes", path.stat().st_size)

print("from-device done")
