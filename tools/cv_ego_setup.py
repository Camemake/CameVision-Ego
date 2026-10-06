#!/usr/bin/env python3
"""CameVision Ego host installer — packs that ship in this folder.

    python tools/cv_ego_setup.py --gui
    python tools/cv_ego_setup.py --pack usb
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_ego_driver import driver_installed, install_linux, install_windows, is_windows  # noqa: E402
from cv_ego_host_setup import (  # noqa: E402
    STAMP,
    ensure_linux_executables,
    extract_linux_python,
    install_libusb_linux,
    install_python_linux,
    unblock_windows,
    verify,
)
from cv_ego_packages import packages  # noqa: E402
from cv_ego_paths import adb_exe, bundled_python, repo_root, upgrade_tool  # noqa: E402

ROOT = repo_root()


def log(msg: str) -> None:
    print(msg, flush=True)


def pack_python() -> None:
    if is_windows():
        py = bundled_python()
        if py is None or not Path(py).is_file():
            raise SystemExit("Python runtime missing from this package (host/python)")
        log(f"python {py}")
        return
    extract_linux_python()
    ensure_linux_executables()
    if bundled_python() is None:
        install_python_linux()
    py = bundled_python()
    if py is None or not Path(py).is_file():
        raise SystemExit("Python runtime missing from this package")
    log(f"python {py}")


def pack_host() -> None:
    if not is_windows():
        ensure_linux_executables()
    adb = adb_exe()
    ut = upgrade_tool()
    if not Path(adb).is_file() and adb == "adb":
        raise SystemExit("ADB missing from this package")
    if not Path(ut).is_file() and ut == "upgrade_tool":
        raise SystemExit("flash tool missing from this package")
    log(f"adb {adb}")
    log(f"upgrade_tool {ut}")


def pack_files() -> None:
    if is_windows():
        unblock_windows()
    else:
        ensure_linux_executables()
    log(f"root {ROOT}")


def pack_usb() -> None:
    if is_windows():
        if driver_installed():
            log("USB driver present")
            return
        code = install_windows()
        if code:
            raise SystemExit(f"USB driver exit {code}")
        return
    if driver_installed():
        log("udev rule present")
    else:
        code = install_linux()
        if code:
            raise SystemExit(f"udev exit {code}")
    install_libusb_linux()


def pack_images() -> None:
    pkgs = packages()
    ready = [p for p in pkgs if p.get("ready")]
    if not ready:
        miss = pkgs[0]["missing"] if pkgs else ["images"]
        raise SystemExit("board images missing: " + ", ".join(miss))
    for p in pkgs:
        log(f"package {p['name']} {'ready' if p['ready'] else 'missing'}")


def pack_finish() -> None:
    missing = verify()
    if missing:
        raise SystemExit("missing " + ", ".join(missing))
    STAMP.parent.mkdir(parents=True, exist_ok=True)
    STAMP.write_text("ok\n", encoding="ascii")
    log("host ready")


PACKS = (
    ("python", "Python runtime", pack_python),
    ("host", "ADB and flash tool", pack_host),
    ("files", "Package files", pack_files),
    ("usb", "USB access", pack_usb),
    ("images", "Board images", pack_images),
    ("finish", "Finish", pack_finish),
)


def run_pack(pack_id: str) -> int:
    for pid, _name, fn in PACKS:
        if pid == pack_id:
            log(f"=== { _name } ===")
            fn()
            log("ok")
            return 0
    raise SystemExit(f"unknown pack {pack_id}")


def run_all() -> int:
    for pid, name, fn in PACKS:
        log(f"=== {name} ===")
        fn()
        log("ok")
    return 0


def _python() -> str:
    found = bundled_python()
    return str(found) if found is not None else sys.executable


def launch_tool() -> None:
    env = os.environ.copy()
    env["CAMEVISION_EGO_ROOT"] = str(ROOT)
    studio = ROOT / "tools" / "cv_ego_studio.py"
    creation = 0
    if is_windows():
        creation = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen([_python(), str(studio)], cwd=str(ROOT), env=env, creationflags=creation)


def gui() -> int:
    try:
        import tkinter as tk
        from tkinter import font as tkfont
    except Exception:
        return _gui_zenity() if not is_windows() else run_all()

    CAME = "#1a6f7c"
    PINK = "#e84b8a"
    BG = "#f4efe8"
    INK = "#222222"
    MUTED = "#5c5c5c"
    CARD = "#ffffff"

    root = tk.Tk()
    root.title("CameVision Ego · Camemake")
    root.configure(bg=BG)
    root.geometry("520x620")
    root.minsize(480, 560)

    header = tk.Frame(root, bg=CARD, height=72)
    header.pack(fill="x")
    header.pack_propagate(False)
    logo_path = ROOT / "tools" / "camemake-logo.png"
    if not logo_path.is_file():
        logo_path = ROOT / "docs" / "assets" / "camemake-logo.png"
    if logo_path.is_file():
        try:
            img = tk.PhotoImage(file=str(logo_path))
            if img.width() > 160:
                img = img.subsample(max(1, img.width() // 160))
            tk.Label(header, image=img, bg=CARD).pack(side="left", padx=18, pady=16)
            root._logo = img  # noqa: SLF001
        except Exception:
            tk.Label(header, text="Camemake", fg=CAME, bg=CARD, font=("Segoe UI", 14, "bold")).pack(
                side="left", padx=18
            )
    titles = tk.Frame(header, bg=CARD)
    titles.pack(side="left", padx=8)
    tk.Label(titles, text="CameVision Ego", fg=INK, bg=CARD, font=("Segoe UI", 16, "bold")).pack(anchor="w")
    tk.Label(titles, text="Camemake installer", fg=CAME, bg=CARD, font=("Segoe UI", 11)).pack(anchor="w")

    body = tk.Frame(root, bg=BG)
    body.pack(fill="both", expand=True, padx=28, pady=18)
    tk.Label(
        body,
        text="This installs every pack that ships in this folder.",
        fg=MUTED,
        bg=BG,
        font=("Segoe UI", 11),
        wraplength=440,
        justify="left",
    ).pack(anchor="w")

    rows = tk.Frame(body, bg=CARD, highlightbackground="#e4ddd4", highlightthickness=1)
    rows.pack(fill="x", pady=16)
    status: dict[str, tk.Label] = {}
    for pid, name, _fn in PACKS:
        row = tk.Frame(rows, bg=CARD)
        row.pack(fill="x", padx=14, pady=7)
        tk.Label(row, text=name, fg=INK, bg=CARD, font=("Segoe UI", 11)).pack(side="left")
        lab = tk.Label(row, text="Waiting", fg=MUTED, bg=CARD, font=("Segoe UI", 10))
        lab.pack(side="right")
        status[pid] = lab

    log_box = tk.Text(
        body,
        height=10,
        bg=CARD,
        fg=INK,
        relief="flat",
        highlightbackground="#e4ddd4",
        highlightthickness=1,
        font=("Consolas", 10),
    )
    log_box.pack(fill="both", expand=True)
    log_box.insert("end", "Ready.\n")

    btn_row = tk.Frame(body, bg=BG)
    btn_row.pack(fill="x", pady=16)
    btn = tk.Button(
        btn_row,
        text="Install",
        bg=PINK,
        fg="#ffffff",
        activebackground="#d63d79",
        activeforeground="#ffffff",
        relief="flat",
        font=("Segoe UI", 12, "bold"),
        padx=22,
        pady=8,
        cursor="hand2",
    )
    btn.pack(side="left")
    busy = {"on": False}

    def write(line: str) -> None:
        log_box.insert("end", line + "\n")
        log_box.see("end")

    def set_st(pid: str, text: str, color: str) -> None:
        status[pid].configure(text=text, fg=color)

    def work() -> None:
        busy["on"] = True
        btn.configure(state="disabled")
        ok = True
        for pid, name, fn in PACKS:
            root.after(0, lambda p=pid: set_st(p, "Installing", CAME))
            root.after(0, lambda n=name: write("=== " + n + " ==="))
            try:
                fn()
                root.after(0, lambda p=pid: set_st(p, "Installed", CAME))
                root.after(0, lambda: write("ok"))
            except Exception as e:
                ok = False
                root.after(0, lambda p=pid: set_st(p, "Failed", "#c0392b"))
                root.after(0, lambda m=str(e): write(m))
                break
        if ok:
            root.after(0, lambda: write("Opening the offline tool…"))
            try:
                launch_tool()
            except Exception as e:
                root.after(0, lambda m=str(e): write(m))
            root.after(0, lambda: btn.configure(text="Open again", state="normal", command=launch_tool))
        else:
            root.after(0, lambda: btn.configure(state="normal"))
        busy["on"] = False

    def start() -> None:
        if busy["on"]:
            return
        threading.Thread(target=work, daemon=True).start()

    btn.configure(command=start)
    tk.Label(body, text="© Camemake · CV-EGO01-OS", fg=MUTED, bg=BG, font=("Segoe UI", 9)).pack(anchor="w")
    _ = tkfont
    root.mainloop()
    return 0


def _gui_zenity() -> int:
    zen = None
    for name in ("zenity", "qarma"):
        from shutil import which

        if which(name):
            zen = name
            break
    if zen is None:
        log("no installer window — installing from this package")
        code = run_all()
        if code == 0:
            launch_tool()
        return code
    total = len(PACKS)
    proc = subprocess.Popen(
        [zen, "--progress", "--title=CameVision Ego", "--text=Camemake installer", "--percentage=0", "--auto-close"],
        stdin=subprocess.PIPE,
        text=True,
    )
    assert proc.stdin is not None
    try:
        for i, (_pid, name, fn) in enumerate(PACKS, 1):
            proc.stdin.write(f"#{name}\n{int(i * 100 / total)}\n")
            proc.stdin.flush()
            fn()
    except Exception as e:
        proc.kill()
        log(str(e))
        return 1
    proc.stdin.close()
    proc.wait(timeout=10)
    launch_tool()
    return 0


def main() -> int:
    os.environ["CAMEVISION_EGO_ROOT"] = str(ROOT)
    args = sys.argv[1:]
    if "--gui" in args or not args:
        return gui()
    if "--list" in args:
        for pid, name, _fn in PACKS:
            print(f"{pid}\t{name}")
        return 0
    if "--launch" in args:
        launch_tool()
        return 0
    if len(args) >= 2 and args[0] == "--pack":
        return run_pack(args[1])
    if "--all" in args:
        return run_all()
    return gui()


if __name__ == "__main__":
    raise SystemExit(main())
