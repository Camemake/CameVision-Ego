#!/usr/bin/env python3
"""Serve the IMU overlay page only. Does not touch cameras or the IMU sampler."""
import os

os.environ.setdefault("PYTHONUNBUFFERED", "1")

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HTML_PATH = Path(r"C:\Users\stefa\Desktop\CameVision Ego\tools\ego_preview.html")
PORT = 8766


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        html = HTML_PATH.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)


if __name__ == "__main__":
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"page http://127.0.0.1:{PORT}", flush=True)
    httpd.serve_forever()
