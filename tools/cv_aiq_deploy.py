#!/usr/bin/env python3
"""Push SC233 ISP35 IQ + start rkaiq_3A_server and rkaiq_tool_server."""
import base64
import http.server
import shutil
import socket
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cv_telnet import run

ROOT = Path(r"C:\Users\stefa\Desktop\CameVision Single")
OVERLAY = ROOT / r"restore\recovery-2-20260821-adb-stream\overlay"
IQ_SRC = ROOT / r"restore\known-good-20260819-camera-adb\overlay\sc233hgs_efference-sc233hgs_default.json"
IQ_NAME = "sc233hgs_efference-sc233hgs_default.json"
HOST = "192.168.1.23"
HTTP_PORT = 8765


def pc_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((HOST, 2323))
        return s.getsockname()[0]
    finally:
        s.close()


def wait_board(seconds=180):
    t0 = time.time()
    while time.time() - t0 < seconds:
        try:
            s = socket.create_connection((HOST, 2323), 2)
            s.close()
            return True
        except OSError:
            print("waiting board %.0fs" % (time.time() - t0), flush=True)
            time.sleep(3)
    return False


def serve(directory: Path):
    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print("http", args[0] if args else fmt, flush=True)

    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), lambda *a: H(*a, directory=str(directory)))
    th = threading.Thread(target=httpd.serve_forever, daemon=True)
    th.start()
    return httpd


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def main() -> int:
    if not IQ_SRC.is_file():
        print("missing", IQ_SRC)
        return 1
    dest_iq = OVERLAY / "iqfiles" / IQ_NAME
    dest_iq.parent.mkdir(parents=True, exist_ok=True)
    if not dest_iq.exists() or dest_iq.stat().st_size != IQ_SRC.stat().st_size:
        shutil.copy2(IQ_SRC, dest_iq)
        print("copied IQ to", dest_iq, dest_iq.stat().st_size)

    print("wait board", HOST)
    if not wait_board():
        print("board still down; files staged, run this again after Wi-Fi")
        return 2

    ip = pc_ip()
    print("pc", ip, "iq", IQ_SRC.stat().st_size)
    httpd = serve(dest_iq.parent)
    time.sleep(0.3)

    aiq_b64 = b64(OVERLAY / "camevision-aiq.sh")
    s99_b64 = b64(OVERLAY / "S99camevision")
    stream_b64 = b64(OVERLAY / "camevision-stream.sh")

    cmd = f"""
mount -o remount,rw / 2>/dev/null
mkdir -p /userdata/iqfiles
if command -v wget >/dev/null 2>&1; then
  wget -q -O /userdata/iqfiles/{IQ_NAME} http://{ip}:{HTTP_PORT}/{IQ_NAME}
else
  python3 -c "import urllib.request; urllib.request.urlretrieve('http://{ip}:{HTTP_PORT}/{IQ_NAME}','/userdata/iqfiles/{IQ_NAME}')"
fi
ls -l /userdata/iqfiles/{IQ_NAME}
mount -o remount,rw /oem 2>/dev/null
cp -f /userdata/iqfiles/{IQ_NAME} /oem/usr/share/iqfiles/{IQ_NAME}
ln -sf {IQ_NAME} /oem/usr/share/iqfiles/sc233hgs_default_default.json
sync
ls -l /oem/usr/share/iqfiles/{IQ_NAME} /oem/usr/share/iqfiles/sc233hgs_default_default.json
echo {aiq_b64} | base64 -d > /userdata/camevision-aiq.sh
echo {s99_b64} | base64 -d > /etc/init.d/S99camevision
echo {stream_b64} | base64 -d > /userdata/camevision-stream.sh
chmod 755 /userdata/camevision-aiq.sh /etc/init.d/S99camevision /userdata/camevision-stream.sh
killall rkaiq_3A_server rkaiq_tool_server 2>/dev/null
sleep 1
/userdata/camevision-aiq.sh
"""
    text = run(cmd, wait=18)
    out = Path(__file__).with_name("cv_aiq_deploy.out.txt")
    out.write_text(text, encoding="utf-8", errors="replace")
    print(text)
    print("wrote", out)
    httpd.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
