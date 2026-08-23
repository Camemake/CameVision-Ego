#!/usr/bin/env python3
"""ISP NV12 -> kmpp hardware H.264 -> RTSP TCP interleaved.
Does not use ffmpeg or rockit. Each encode is mpi_enc_test -n 1 on /dev/shm/isp.nv12.
"""
import os
import signal
import socket
import struct
import subprocess
import sys
import threading
import time

ISP = "/dev/shm/isp.nv12"
FRAME = 1920 * 1200 * 3 // 2
PORT = 8554
PATH = "/live"
PT = 96
FPS = 10
TS_STEP = 90000 // FPS
MAX_PAYLOAD = 1200
ENC = [
    "mpi_enc_test",
    "-i", ISP,
    "-o", "/tmp/hw_one.h264",
    "-w", "1920", "-h", "1200",
    "-f", "0", "-t", "7",
    "-n", "1",
    "-fps", "10:10",
    "-bps", "2500000",
    "-rc", "1",
    "-v", "q",
]

os.environ["LD_LIBRARY_PATH"] = "/oem/usr/lib:/oem/lib:" + os.environ.get("LD_LIBRARY_PATH", "")
signal.signal(signal.SIGHUP, signal.SIG_IGN)
signal.signal(signal.SIGPIPE, signal.SIG_IGN)


class Latest:
    def __init__(self):
        self.frame = None
        self.idx = 0
        self.cv = threading.Condition()

    def set(self, frame):
        with self.cv:
            self.frame = frame
            self.idx += 1
            self.cv.notify_all()

    def wait_new(self, last_idx, timeout):
        with self.cv:
            ok = self.cv.wait_for(lambda: self.idx != last_idx, timeout=timeout)
            if not ok:
                return last_idx, None
            return self.idx, self.frame


def split_nals(buf):
    nals = []
    i = 0
    starts = []
    while True:
        a = buf.find(b"\x00\x00\x00\x01", i)
        b = buf.find(b"\x00\x00\x01", i)
        if a < 0 and b < 0:
            break
        if a < 0:
            pos, sc = b, 3
        elif b < 0 or a <= b:
            pos, sc = a, 4
        else:
            pos, sc = b, 3
        starts.append(pos + sc)
        i = pos + sc
    for x, y in zip(starts, starts[1:] + [len(buf)]):
        nal = buf[x:y]
        if nal:
            nals.append(nal)
    return nals


def rtp_h264_nal(nal, seq, ts, ssrc):
    pkts = []
    if len(nal) + 12 <= MAX_PAYLOAD + 12 and len(nal) < MAX_PAYLOAD:
        marker = 0x80
        hdr = struct.pack("!BBHII", 0x80, marker | PT, seq & 0xFFFF, ts & 0xFFFFFFFF, ssrc)
        pkts.append(hdr + nal)
        seq = (seq + 1) & 0xFFFF
        return pkts, seq
    nri_type = nal[0]
    nri = nri_type & 0x60
    ntype = nri_type & 0x1F
    data = nal[1:]
    off = 0
    first = True
    while off < len(data):
        chunk = data[off:off + MAX_PAYLOAD - 2]
        off += len(chunk)
        last = off >= len(data)
        fu_ind = nri | 28
        fu_hdr = (0x80 if first else 0) | (0x40 if last else 0) | ntype
        marker = 0x80 if last else 0
        hdr = struct.pack("!BBHII", 0x80, marker | PT, seq & 0xFFFF, ts & 0xFFFFFFFF, ssrc)
        pkts.append(hdr + bytes([fu_ind, fu_hdr]) + chunk)
        seq = (seq + 1) & 0xFFFF
        first = False
    return pkts, seq


def send_interleaved(conn, pkt, channel=0):
    conn.sendall(b"$" + bytes([channel]) + struct.pack("!H", len(pkt)) + pkt)


def skip_interleaved(data):
    if len(data) < 4 or data[0:1] != b"$":
        return data, False
    ln = struct.unpack("!H", data[2:4])[0]
    need = 4 + ln
    if len(data) < need:
        return data, False
    return data[need:], True


def parse_rtsp(buf):
    if b"\r\n\r\n" not in buf:
        return None, buf
    raw, rest = buf.split(b"\r\n\r\n", 1)
    text = raw.decode("utf-8", "replace")
    lines = text.split("\r\n")
    first = lines[0] if lines else ""
    headers = {}
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    clen = int(headers.get("content-length", "0") or 0)
    if len(rest) < clen:
        return None, buf
    return (first, headers, rest[:clen]), rest[clen:]


def encoder_thread(latest):
    n = 0
    while True:
        try:
            if os.path.getsize(ISP) != FRAME:
                time.sleep(0.02)
                continue
        except OSError:
            time.sleep(0.05)
            continue
        try:
            subprocess.check_call(
                ENC, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            with open("/tmp/hw_one.h264", "rb") as f:
                au = f.read()
        except Exception as e:
            sys.stderr.write("enc %s\n" % e)
            time.sleep(0.05)
            continue
        if len(au) < 8:
            continue
        n += 1
        latest.set(au)
        if n == 1 or n % 30 == 0:
            sys.stderr.write("hw264 %d %d bytes\n" % (n, len(au)))


def handle(conn, addr, latest, session):
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 256 * 1024)
    buf = b""
    playing = False
    seq = 0
    ts = 0
    last_idx = 0
    ssrc = 0x26401200
    print("client", addr, flush=True)
    try:
        while True:
            conn.settimeout(0.02 if playing else 20)
            try:
                data = conn.recv(4096)
                if not data:
                    return
                buf += data
            except socket.timeout:
                data = b""
            progressed = True
            while progressed and buf:
                progressed = False
                if buf[0:1] == b"$":
                    new, ok = skip_interleaved(buf)
                    if ok:
                        buf = new
                        progressed = True
                    break
                msg, new = parse_rtsp(buf)
                if msg is None:
                    break
                buf = new
                progressed = True
                first, headers, _body = msg
                print(first, flush=True)
                cseq = headers.get("cseq", "1")
                method = first.split(" ")[0] if first else ""
                extra = ""
                body = ""
                if method == "OPTIONS":
                    extra = "Public: OPTIONS, DESCRIBE, SETUP, PLAY, TEARDOWN, GET_PARAMETER\r\n"
                elif method == "DESCRIBE":
                    body = (
                        "v=0\r\n"
                        "o=- 0 0 IN IP4 0.0.0.0\r\n"
                        "s=camevision-h264\r\n"
                        "t=0 0\r\n"
                        "m=video 0 RTP/AVP 96\r\n"
                        "c=IN IP4 0.0.0.0\r\n"
                        "a=control:streamid=0\r\n"
                        "a=rtpmap:96 H264/90000\r\n"
                        "a=fmtp:96 packetization-mode=1;profile-level-id=640032\r\n"
                        "a=framerate:%d\r\n" % FPS
                    )
                    extra = (
                        "Content-Type: application/sdp\r\n"
                        "Content-Base: rtsp://127.0.0.1:%d%s/\r\n" % (PORT, PATH)
                    )
                elif method == "SETUP":
                    extra = (
                        "Transport: RTP/AVP/TCP;unicast;interleaved=0-1\r\n"
                        "Session: %s;timeout=60\r\n" % session
                    )
                elif method == "PLAY":
                    extra = "Session: %s\r\n" % session
                    playing = True
                    last_idx = latest.idx
                elif method == "GET_PARAMETER":
                    extra = "Session: %s\r\n" % session
                elif method == "TEARDOWN":
                    extra = "Session: %s\r\n" % session
                    conn.sendall(
                        ("RTSP/1.0 200 OK\r\nCSeq: %s\r\n%sContent-Length: 0\r\n\r\n" % (cseq, extra)).encode()
                    )
                    return
                resp = "RTSP/1.0 200 OK\r\nCSeq: %s\r\n%sContent-Length: %d\r\n\r\n%s" % (
                    cseq, extra, len(body), body)
                conn.sendall(resp.encode())
            if playing:
                idx, au = latest.wait_new(last_idx, 0.05)
                if au is not None and idx != last_idx:
                    for nal in split_nals(au):
                        pkts, seq = rtp_h264_nal(nal, seq, ts, ssrc)
                        for p in pkts:
                            send_interleaved(conn, p)
                    ts = (ts + TS_STEP) & 0xFFFFFFFF
                    last_idx = idx
    except Exception as e:
        print("client err", e, flush=True)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main():
    if not os.path.exists("/dev/mpp_service"):
        subprocess.call(["insmod", "/userdata/kmpp-rt52.ko"])
    print("hw h264 rtsp on :%d%s" % (PORT, PATH), flush=True)
    latest = Latest()
    threading.Thread(target=encoder_thread, args=(latest,), daemon=True).start()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", PORT))
    srv.listen(4)
    n = 0
    while True:
        c, a = srv.accept()
        n += 1
        threading.Thread(target=handle, args=(c, a, latest, str(n)), daemon=True).start()


if __name__ == "__main__":
    main()
