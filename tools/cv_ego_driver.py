#!/usr/bin/env python3
"""Install the USB access that ships in this package.

Windows: Rockchip Driver Assistant (bundled), plus rockusb + ADB INF.
Linux: udev rule for vendor 2207 (Maskrom / Loader / ADB).
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_ego_paths import driver_assistant_dir, host_dir, udev_rules_file  # noqa: E402


def is_windows() -> bool:
    return os.name == "nt"


def driver_present() -> bool:
    if is_windows():
        return driver_install_exe() is not None
    return udev_rules_file().is_file()


def driver_install_exe() -> Path | None:
    da = driver_assistant_dir()
    if da is None:
        return None
    exe = da / "DriverInstall.exe"
    return exe if exe.is_file() else None


def driver_installed() -> bool:
    if is_windows():
        return _windows_driver_present()
    return Path("/etc/udev/rules.d/99-camevision-rockusb.rules").is_file()


def _windows_driver_present() -> bool:
    try:
        r = subprocess.run(
            ["pnputil", "/enum-drivers"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        text = (r.stdout or "") + (r.stderr or "")
        low = text.lower()
        return "rockusb" in low or "rockchip" in low
    except Exception:
        return False


def _windows_infs() -> list[Path]:
    da = driver_assistant_dir()
    if da is None:
        return []
    arch = "x64" if platform.machine().lower() in ("amd64", "x86_64") else "x86"
    win = "win10"
    infs = [
        da / "Driver" / arch / win / "rockusb.inf",
        da / "ADBDriver" / "android_winusb.inf",
    ]
    return [p for p in infs if p.is_file()]


def _run_elevated_windows(command: str) -> int:
    ps = (
        "Start-Process -FilePath cmd.exe -ArgumentList @('/c', "
        + repr(command)
        + ") -Verb RunAs -Wait -WindowStyle Hidden"
    )
    r = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        timeout=300,
    )
    return int(r.returncode)


def install_windows() -> int:
    infs = _windows_infs()
    exe = driver_install_exe()
    if infs:
        cmd = " && ".join(f'pnputil /add-driver "{p}" /install' for p in infs)
        print(f"installing {len(infs)} driver package(s)", flush=True)
        code = _run_elevated_windows(cmd)
        print(f"pnputil exit {code}", flush=True)
        if code == 0:
            return 0
    if exe is None:
        raise SystemExit("USB driver is missing from this package (host/DriverAssitant)")
    print(f"opening {exe}", flush=True)
    os.startfile(str(exe))  # type: ignore[attr-defined]
    print("Driver Assistant is open — choose Install, then return here", flush=True)
    return 0


def install_linux() -> int:
    src = udev_rules_file()
    if not src.is_file():
        raise SystemExit(f"missing udev rule {src}")
    dest = Path("/etc/udev/rules.d/99-camevision-rockusb.rules")
    script = (
        f"cp {src.as_posix()!r} {dest.as_posix()!r} "
        f"&& chmod 644 {dest.as_posix()!r} "
        "&& udevadm control --reload-rules "
        "&& udevadm trigger"
    )
    for helper in (
        ["pkexec", "sh", "-c", script],
        ["sudo", "sh", "-c", script],
    ):
        if shutil.which(helper[0]) is None:
            continue
        print(">", " ".join(helper[:3]), "...", flush=True)
        r = subprocess.run(helper)
        if r.returncode == 0:
            print(f"wrote {dest}", flush=True)
            return 0
        print(f"{helper[0]} exit {r.returncode}", flush=True)
    dest_hint = dest.as_posix()
    print(f"copy {src} to {dest_hint} then run: udevadm control --reload-rules && udevadm trigger", flush=True)
    return 1


def main() -> int:
    print("=== USB driver ===", flush=True)
    if is_windows():
        return install_windows()
    return install_linux()


if __name__ == "__main__":
    raise SystemExit(main())
