#!/usr/bin/env python3
"""CameVision Ego offline installer.

Serves the local website: USB driver, package install (including GitHub
or file updates), ADB live page, and extended diagnostics.

    python tools/cv_ego_studio.py
    CameVision-Ego.exe
    ./CameVision-Ego
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_ego_driver import driver_installed, driver_present  # noqa: E402
from cv_ego_packages import packages, page_ready  # noqa: E402
from cv_ego_paths import (  # noqa: E402
    adb_exe,
    bundled_python,
    docs_dir,
    is_windows,
    repo_root,
    upgrade_tool,
)

ROOT = repo_root()
DOCS = docs_dir()
PORT = 8765
SRC_TREES = (
    ("tools/", ROOT / "tools"),
    ("device-tree/", ROOT / "device-tree"),
    ("overlay/", ROOT / "restore" / "release-0.2-20260902" / "overlay"),
)
SRC_TYPES = {
    ".py": "text/plain; charset=utf-8",
    ".sh": "text/plain; charset=utf-8",
    ".c": "text/plain; charset=utf-8",
    ".h": "text/plain; charset=utf-8",
    ".dts": "text/plain; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".conf": "text/plain; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
}
LOG: list[str] = []
LOG_LOCK = threading.Lock()
JOB: dict[str, object] = {"name": "", "running": False, "code": None}
JOB_LOCK = threading.Lock()
PROC: subprocess.Popen[str] | None = None
PROC_LOCK = threading.Lock()
USB_CACHE: dict[str, object] = {"t": 0.0, "data": {}}
USB_LOCK = threading.Lock()


def log(msg: str) -> None:
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with LOG_LOCK:
        LOG.append(line)
        if len(LOG) > 800:
            del LOG[:400]


def _run_text(args: list[str], timeout: int = 4) -> str:
    try:
        r = subprocess.run(args, capture_output=True, timeout=timeout)
    except Exception:
        return ""
    return ((r.stdout or b"") + (r.stderr or b"")).decode("utf-8", "replace")


def probe_usb() -> dict[str, object]:
    now = time.time()
    with USB_LOCK:
        cached_t = float(USB_CACHE["t"])
        if now - cached_t < 2.0 and USB_CACHE["data"]:
            return dict(USB_CACHE["data"])  # type: ignore[arg-type]
    ut = upgrade_tool()
    adb = adb_exe()
    rock = _run_text([ut, "ld"], timeout=4) if Path(ut).is_file() or ut == "upgrade_tool" else ""
    listing = _run_text([adb, "devices"], timeout=4) if Path(adb).is_file() or adb == "adb" else ""
    serials = []
    for line in listing.splitlines():
        if "\tdevice" in line:
            serials.append(line.split()[0])
    data = {
        "maskrom": "Maskrom" in rock,
        "loader": "Loader" in rock,
        "adb": serials,
        "rock": rock.strip()[:400],
    }
    with USB_LOCK:
        USB_CACHE["t"] = now
        USB_CACHE["data"] = data
    return data


def status() -> dict[str, object]:
    pkgs = packages()
    usb = probe_usb()
    with JOB_LOCK:
        job = dict(JOB)
    return {
        "root": str(ROOT),
        "os": "windows" if is_windows() else "linux",
        "python": str(bundled_python() or sys.executable),
        "adb": adb_exe(),
        "upgrade_tool": upgrade_tool(),
        "driver_present": driver_present(),
        "driver_installed": driver_installed() or bool(usb["maskrom"] or usb["loader"] or usb["adb"]),
        "packages": pkgs,
        "flash_ready": any(p["ready"] for p in pkgs),
        "page_ready": page_ready(),
        "usb": usb,
        "job": job,
    }


def run_job(name: str, args: list[str]) -> None:
    with JOB_LOCK:
        if JOB["running"]:
            log(f"busy — {JOB['name']} is still running")
            return
        JOB["name"] = name
        JOB["running"] = True
        JOB["code"] = None
    env = os.environ.copy()
    env["CAMEVISION_EGO_ROOT"] = str(ROOT)
    env["PYTHONUNBUFFERED"] = "1"
    log(f"=== {name} ===")
    log("> " + " ".join(args))

    def worker() -> None:
        global PROC
        try:
            proc = subprocess.Popen(
                args,
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            with PROC_LOCK:
                PROC = proc
            assert proc.stdout is not None
            for line in proc.stdout:
                log(line.rstrip("\n"))
            code = proc.wait()
            log(f"{name} exit {code}")
            with JOB_LOCK:
                JOB["running"] = False
                JOB["code"] = code
        except Exception as e:
            log(f"{name} failed: {e}")
            with JOB_LOCK:
                JOB["running"] = False
                JOB["code"] = 1
        finally:
            with PROC_LOCK:
                PROC = None

    threading.Thread(target=worker, daemon=True).start()


def stop_job() -> None:
    with PROC_LOCK:
        proc = PROC
    if proc is None or proc.poll() is not None:
        with JOB_LOCK:
            JOB["running"] = False
        log("no job to stop")
        return
    log(f"stopping {JOB.get('name') or 'job'}")
    try:
        proc.terminate()
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=4)
    except Exception as e:
        log(f"stop failed: {e}")
    with JOB_LOCK:
        JOB["running"] = False
        JOB["code"] = 1
    log("stopped")


def _python() -> str:
    found = bundled_python()
    return str(found) if found is not None else sys.executable


def start_driver() -> None:
    run_job("driver", [_python(), str(ROOT / "tools" / "cv_ego_driver.py")])


def start_flash(package_id: str = "camevision-ego") -> None:
    run_job(
        "install",
        [_python(), str(ROOT / "tools" / "cv_ego_flash.py"), "--prebuilt", "--package", package_id],
    )


def start_page() -> None:
    run_job("open", [_python(), str(ROOT / "tools" / "cv_ego_page.py")])


def start_autostart() -> None:
    run_job("autostart", [_python(), str(ROOT / "tools" / "cv_ego_autostart.py"), "--install"])


def start_diag() -> None:
    run_job("diagnostics", [_python(), str(ROOT / "tools" / "cv_ego_diag.py")])


def start_update_github() -> None:
    run_job("github update", [_python(), str(ROOT / "tools" / "cv_ego_update.py"), "--github"])


def start_update_file(path: str) -> None:
    run_job("file update", [_python(), str(ROOT / "tools" / "cv_ego_update.py"), "--file", path])


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        return

    def _json(self, payload: dict, code: int = 200) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            obj = json.loads(raw.decode("utf-8"))
        except Exception:
            return {}
        return obj if isinstance(obj, dict) else {}

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/status":
            st = status()
            with LOG_LOCK:
                st["log"] = list(LOG[-200:])
            self._json(st)
            return
        if path.startswith("/src/"):
            self._send_src(path[5:])
            return
        if path == "/" and (DOCS / "tool.html").is_file():
            self.path = "/tool.html"
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/update-file":
            saved = self._save_upload()
            if saved is None:
                self._json({"ok": False, "error": "no file"}, 400)
                return
            start_update_file(str(saved))
            self._json({"ok": True, "file": str(saved)})
            return
        body = self._body()
        if path == "/api/driver":
            start_driver()
            self._json({"ok": True})
            return
        if path in ("/api/flash", "/api/install"):
            start_flash(str(body.get("package") or "camevision-ego"))
            self._json({"ok": True})
            return
        if path == "/api/page":
            start_page()
            self._json({"ok": True})
            return
        if path == "/api/autostart":
            start_autostart()
            self._json({"ok": True})
            return
        if path == "/api/diag":
            start_diag()
            self._json({"ok": True})
            return
        if path == "/api/update-github":
            start_update_github()
            self._json({"ok": True})
            return
        if path == "/api/stop":
            stop_job()
            self._json({"ok": True})
            return
        self._json({"ok": False, "error": "unknown action"}, 404)

    def _send_src(self, rel: str) -> None:
        rel = rel.replace("\\", "/").lstrip("/")
        if ".." in rel.split("/"):
            self._json({"ok": False, "error": "bad path"}, 404)
            return
        found: Path | None = None
        for prefix, base in SRC_TREES:
            if not rel.startswith(prefix):
                continue
            path = (base / rel[len(prefix) :]).resolve()
            try:
                path.relative_to(base.resolve())
            except ValueError:
                break
            if path.is_file():
                found = path
            break
        if found is None:
            self.send_error(404, "file not in package")
            return
        data = found.read_bytes()
        ctype = SRC_TYPES.get(found.suffix.lower(), "text/plain; charset=utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _save_upload(self) -> Path | None:
        ctype = self.headers.get("Content-Type") or ""
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return None
        dest_dir = ROOT / "restore" / "updates"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "upload.zip"
        if "multipart/form-data" in ctype:
            data = self.rfile.read(length)
            marker = b"\r\n\r\n"
            idx = data.find(marker)
            if idx < 0:
                return None
            body = data[idx + 4 :]
            end = body.rfind(b"\r\n--")
            if end > 0:
                body = body[:end]
            dest.write_bytes(body)
            return dest
        dest.write_bytes(self.rfile.read(length))
        return dest


def main() -> int:
    port = PORT
    if len(sys.argv) >= 3 and sys.argv[1] == "--port":
        port = int(sys.argv[2])
    if not DOCS.is_dir():
        raise SystemExit(f"missing docs at {DOCS}")
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/tool.html"
    log(f"CameVision Ego offline tool at {url}")
    log(f"root {ROOT}")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
