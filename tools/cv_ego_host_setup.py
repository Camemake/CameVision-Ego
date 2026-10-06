#!/usr/bin/env python3
"""Install host pieces that ship inside this package.

Windows: portable Python is already in host/python. This step unblocks
files and installs the USB driver (Rockusb + ADB).

Linux: portable Python is in host/linux/python. This step marks the
host binaries executable, writes the udev rule, and installs libusb
when the package manager is present.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_ego_driver import driver_installed, install_linux, install_windows, is_windows  # noqa: E402
from cv_ego_paths import adb_exe, bundled_python, host_dir, repo_root, upgrade_tool  # noqa: E402

ROOT = repo_root()
STAMP = host_dir() / ".host-installed"


def log(msg: str) -> None:
    print(msg, flush=True)


def _chmod_exec(*paths: Path) -> None:
    for p in paths:
        if p.is_file():
            mode = p.stat().st_mode
            p.chmod(mode | 0o111)
            log(f"executable {p}")


def extract_linux_python() -> None:
    linux = host_dir() / "linux"
    dest = linux / "python"
    marker = dest / "bin" / "python3"
    if marker.is_file():
        return
    machine = os.uname().machine.lower() if hasattr(os, "uname") else "x86_64"
    tar = linux / (
        "python-aarch64.tar.gz" if machine in ("aarch64", "arm64") else "python-x86_64.tar.gz"
    )
    if not tar.is_file():
        log(f"python archive missing: {tar.name}")
        return
    if dest.exists():
        shutil.rmtree(dest)
    log(f"extract {tar.name}")
    subprocess.run(["tar", "-xzf", str(tar), "-C", str(linux)], check=True)
    if not marker.is_file():
        raise SystemExit(f"extract did not produce {marker}")


def install_python_linux() -> None:
    if bundled_python() is not None:
        return
    script = (
        "if command -v apt-get >/dev/null 2>&1; then "
        "apt-get install -y python3 libusb-1.0-0; "
        "elif command -v dnf >/dev/null 2>&1; then "
        "dnf install -y python3 libusb1; "
        "elif command -v pacman >/dev/null 2>&1; then "
        "pacman -S --noconfirm python libusb; "
        "fi"
    )
    for helper in (["pkexec", "sh", "-c", script], ["sudo", "sh", "-c", script]):
        if shutil.which(helper[0]) is None:
            continue
        log(f"install python3 via {helper[0]}")
        if subprocess.run(helper, timeout=300).returncode == 0:
            return


def ensure_linux_executables() -> None:
    host = host_dir()
    linux = host / "linux"
    _chmod_exec(
        linux / "adb",
        linux / "upgrade_tool",
        linux / "python" / "bin" / "python3",
        linux / "python" / "bin" / "python",
        linux / "python-aarch64" / "bin" / "python3",
        linux / "python-aarch64" / "bin" / "python",
        host / "python" / "bin" / "python3",
    )
    for sh in (ROOT / "CameVision-Ego", ROOT / "CameVision-Ego.sh", ROOT / "tools" / "CameVision-Ego.sh"):
        _chmod_exec(sh)


def unblock_windows() -> None:
    ps = (
        f"Get-ChildItem -LiteralPath {str(ROOT)!r} -Recurse -File -ErrorAction SilentlyContinue "
        "| Unblock-File -ErrorAction SilentlyContinue"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        timeout=120,
    )
    log("unblocked package files")


def install_libusb_linux() -> None:
    if shutil.which("ldconfig") is not None:
        r = subprocess.run(["ldconfig", "-p"], capture_output=True, text=True, timeout=20)
        text = (r.stdout or "") + (r.stderr or "")
        if "libusb-1.0.so" in text:
            log("libusb-1.0 present")
            return
    script = (
        "if command -v apt-get >/dev/null 2>&1; then "
        "apt-get install -y libusb-1.0-0; "
        "elif command -v dnf >/dev/null 2>&1; then "
        "dnf install -y libusb1; "
        "elif command -v pacman >/dev/null 2>&1; then "
        "pacman -S --noconfirm libusb; "
        "fi"
    )
    for helper in (["pkexec", "sh", "-c", script], ["sudo", "sh", "-c", script]):
        if shutil.which(helper[0]) is None:
            continue
        log(f"install libusb via {helper[0]}")
        if subprocess.run(helper, timeout=300).returncode == 0:
            return


def verify() -> list[str]:
    missing: list[str] = []
    py = bundled_python()
    if py is None or not Path(py).is_file():
        missing.append("python")
    adb = adb_exe()
    if not Path(adb).is_file() and shutil.which(adb) is None:
        missing.append("adb")
    ut = upgrade_tool()
    if not Path(ut).is_file() and shutil.which(ut) is None:
        missing.append("upgrade_tool")
    return missing


def setup(*, force: bool = False) -> int:
    log("=== host setup ===")
    log(f"root {ROOT}")
    if is_windows():
        unblock_windows()
        if force or not driver_installed():
            code = install_windows()
            if code:
                return code
        else:
            log("USB driver already present")
    else:
        extract_linux_python()
        ensure_linux_executables()
        install_python_linux()
        if force or not driver_installed():
            code = install_linux()
            if code:
                return code
        else:
            log("udev rule already present")
        install_libusb_linux()
    missing = verify()
    py = bundled_python()
    log(f"python {py or 'missing'}")
    log(f"adb {adb_exe()}")
    log(f"upgrade_tool {upgrade_tool()}")
    if missing:
        log("missing " + ", ".join(missing))
        return 1
    STAMP.parent.mkdir(parents=True, exist_ok=True)
    STAMP.write_text("ok\n", encoding="ascii")
    log("host ready")
    return 0


def main() -> int:
    force = "--force" in sys.argv
    return setup(force=force)


if __name__ == "__main__":
    raise SystemExit(main())
