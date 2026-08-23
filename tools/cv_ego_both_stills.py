#!/usr/bin/env python3
"""Capture Cam0 + Cam1 CIF frames and write a side-by-side PNG."""
from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ADB = r"C:\Users\stefa\Downloads\RKDevTool_Release_v3.37\RKDevTool_v3.37_for_window\bin\adb.exe"
STILLS = Path(r"C:\Users\stefa\Desktop\CameVision Ego\build\stills")
W, H, STRIDE, FRAME = 1920, 1200, 2048, 2457600


def serial() -> str:
    r = subprocess.run([ADB, "devices"], capture_output=True, text=True)
    for line in (r.stdout or "").splitlines():
        if "\tdevice" in line:
            return line.split()[0]
    raise SystemExit("no ADB device")


def sh(s: str, cmd: str, timeout: int = 40) -> str:
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=timeout)
    text = (r.stdout or "") + (r.stderr or "")
    print(text, end="")
    return text


def cif_id0(s: str, plat: str) -> str:
    cmd = (
        f"for d in /sys/devices/platform/{plat}/video4linux/video* "
        f"/sys/devices/platform/{plat}/*/video4linux/video*; do "
        f"[ -f $d/name ] || continue; "
        f"n=$(cat $d/name); "
        f"if [ \"$n\" = stream_cif_mipi_id0 ]; then echo /dev/$(basename $d); exit 0; fi; "
        f"done; exit 1"
    )
    r = subprocess.run([ADB, "-s", s, "shell", cmd], capture_output=True, text=True, timeout=15)
    dev = (r.stdout or "").strip().splitlines()
    if not dev:
        raise SystemExit(f"no stream_cif_mipi_id0 under {plat}\n{r.stdout}{r.stderr}")
    print(f"{plat} -> {dev[0]}")
    return dev[0]


def grab(s: str, name: str, dev: str) -> Path:
    remote = f"/userdata/{name}.raw"
    local = STILLS / f"{name}.raw"
    sh(
        s,
        f"rm -f {remote}; "
        f"v4l2-ctl -d {dev} --set-fmt-video=width=1920,height=1200,pixelformat=SBGGR10 --get-fmt-video; "
        f"timeout -k 2 12 v4l2-ctl -d {dev} --stream-mmap=4 --stream-count=3 --stream-to={remote} --stream-poll; "
        f"echo exit:$?; ls -l {remote}",
    )
    subprocess.run([ADB, "-s", s, "pull", remote, str(local)], capture_output=True)
    print(f"pulled {local} {local.stat().st_size if local.is_file() else 0} bytes")
    return local


def raw_to_image(path: Path) -> Image.Image:
    data = path.read_bytes()
    if len(data) < FRAME:
        raise SystemExit(f"{path} too small: {len(data)}")
    frame = data[:FRAME]
    print(f"{path.name} unique={len(set(frame))} min={min(frame)} max={max(frame)}")
    rgb = bytearray(W * H * 3)
    for y in range(H):
        row = frame[y * STRIDE : y * STRIDE + W]
        even = (y % 2) == 0
        for x in range(W):
            v = row[x]
            i = (y * W + x) * 3
            if even:
                if (x % 2) == 0:
                    rgb[i] = v
                else:
                    rgb[i + 1] = v
            else:
                if (x % 2) == 0:
                    rgb[i + 1] = v
                else:
                    rgb[i + 2] = v
        for x in range(W):
            i = (y * W + x) * 3
            if rgb[i] == 0 and rgb[i + 1] == 0 and rgb[i + 2] == 0:
                continue
            if rgb[i] == 0:
                rgb[i] = rgb[i + 1] or rgb[i + 2]
            if rgb[i + 1] == 0:
                rgb[i + 1] = rgb[i] or rgb[i + 2]
            if rgb[i + 2] == 0:
                rgb[i + 2] = rgb[i + 1] or rgb[i]
    return Image.frombytes("RGB", (W, H), bytes(rgb))


def label(im: Image.Image, text: str) -> Image.Image:
    im = im.copy()
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except OSError:
        font = ImageFont.load_default()
    draw.rectangle((0, 0, 360, 70), fill=(0, 0, 0))
    draw.text((16, 12), text, fill=(255, 255, 255), font=font)
    return im


def main() -> int:
    s = serial()
    STILLS.mkdir(parents=True, exist_ok=True)
    print("serial", s)
    cam0 = grab(s, "cam0", cif_id0(s, "rkcif-mipi-lvds"))
    cam1 = grab(s, "cam1", cif_id0(s, "rkcif-mipi-lvds2"))
    left = label(raw_to_image(cam0), "Cam 0")
    right = label(raw_to_image(cam1), "Cam 1")
    out = Image.new("RGB", (W * 2, H))
    out.paste(left, (0, 0))
    out.paste(right, (W, 0))
    png = STILLS / "cam0_cam1_side_by_side.png"
    out.save(png)
    print(f"wrote {png} {png.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
