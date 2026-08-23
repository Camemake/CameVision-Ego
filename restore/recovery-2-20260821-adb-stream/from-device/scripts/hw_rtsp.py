#!/usr/bin/env python3
"""ISP NV12 bursts -> kmpp H.264 GOP -> RTSP interleaved TCP.
Marker bit only on the last packet of each access unit.
"""
import base64
import os
import signal
import socket
import struct
import subprocess
import sys
import threading
import time

ISP = "/dev/shm/isp.nv12"
OUT = "/tmp/hw_one.h264"
FRAME = 1920 * 1200 * 3 // 2
PORT = 8554
PATH = "/live"
PT = 96
FPS = 60
TS_STEP = 90000 // FPS
MAX_NAL = 1400
ENC = [
    "/oem/usr/bin/mpi_enc_test",
    "-i", ISP,
    "-o", OUT,
    "-w", "1920",
    "-h", "1200",
    "-hstride", "1920",
    "-vstride", "1200",
    "-f", "0",
    "-t", "7",
    "-n", "1",
    "-g", "1:30:0",
    "-fps", "60:60",
    "-bps", "12000000",
    "-rc", "1",
    "-sm", "1",
    "-atf", "1",
    "-v", "q",
]

os.environ["PATH"] = "/oem/usr/bin:/usr/bin:/bin:" + os.environ.get("PATH", "")
os.environ["LD_LIBRARY_PATH"] = "/oem/usr/lib:/oem/lib:" + os.environ.get(
    "LD_LIBRARY_PATH", ""
)
signal.signal(signal.SIGHUP, signal.SIG_IGN)
signal.signal(signal.SIGPIPE, signal.SIG_IGN)


class Latest:
    def __init__(self):
        self.frame = None
        self.idx = 0
        self.sps_pps = b""
        self.cv = threading.Condition()

    def set(self, frame, sps_pps):
        with self.cv:
            self.frame = frame
            self.sps_pps = sps_pps
            self.idx += 1
            self.cv.notify_all()

    def snapshot(self):
        with self.cv:
            return self.idx, self.frame, self.sps_pps

    def wait_new(self, last_idx, timeout):
        with self.cv:
            ok = self.cv.wait_for(lambda: self.idx != last_idx, timeout=timeout)
            if not ok:
                return last_idx, None
            return self.idx, self.frame


def split_nals(buf):
    starts = []
    i = 0
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
    nals = []
    for x, y in zip(starts, starts[1:] + [len(buf)]):
        nal = buf[x:y].rstrip(b"\x00")
        if nal:
            nals.append(nal)
    return nals


def sps_pps_of(nals):
    sps = pps = b""
    for nal in nals:
        t = nal[0] & 0x1F
        if t == 7:
            sps = nal
        elif t == 8:
            pps = nal
    return sps, pps


def rtp_h264_nal(nal, seq, ts, ssrc, marker_last):
    pkts = []
    if len(nal) <= MAX_NAL:
        marker = 0x80 if marker_last else 0x00
        hdr = struct.pack("!BBHII", 0x80, marker | PT, seq & 0xFFFF, ts & 0xFFFFFFFF, ssrc)
        pkts.append(hdr + nal)
        return pkts, (seq + 1) & 0xFFFF
    nri = nal[0] & 0x60
    ntype = nal[0] & 0x1F
    data = nal[1:]
    off = 0
    first = True
    while off < len(data):
        chunk = data[off : off + MAX_NAL - 2]
        off += len(chunk)
        last = off >= len(data)
        fu_ind = nri | 28
        fu_hdr = (0x80 if first else 0) | (0x40 if last else 0) | ntype
        marker = 0x80 if (last and marker_last) else 0x00
        hdr = struct.pack("!BBHII", 0x80, marker | PT, seq & 0xFFFF, ts & 0xFFFFFFFF, ssrc)
        pkts.append(hdr + bytes([fu_ind, fu_hdr]) + chunk)
        seq = (seq + 1) & 0xFFFF
        first = False
    return pkts, seq


def send_au(conn, au, seq, ts, ssrc):
    nals = split_nals(au)
    if not nals:
        return seq
    last = len(nals) - 1
    for i, nal in enumerate(nals):
        pkts, seq = rtp_h264_nal(nal, seq, ts, ssrc, i == last)
        for p in pkts:
            conn.sendall(b"$" + bytes([0]) + struct.pack("!H", len(p)) + p)
    return seq


def encoder_thread(latest):
    n = 0
    last_m = -1
    while True:
        try:
            st = os.stat(ISP)
            if st.st_size != FRAME:
                time.sleep(0.01)
                continue
            m = getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9))
            if m == last_m:
                time.sleep(0.005)
                continue
        except OSError:
            time.sleep(0.02)
            continue
        last_m = m
        try:
            subprocess.check_call(
                ENC, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            au = open(OUT, "rb").read()
        except Exception as e:
            sys.stderr.write("enc %s\n" % e)
            time.sleep(0.02)
            continue
        if len(au) < 20000 or au.find(b"\x00\x00\x00\x01") < 0:
            sys.stderr.write("skip au %d\n" % len(au))
            continue
        nals = split_nals(au)
        sps, pps = sps_pps_of(nals)
        n += 1
        latest.set(au, (sps, pps))
        if n == 1 or n % 10 == 0:
            sys.stderr.write("hw264 %d %d bytes\n" % (n, len(au)))


def handle(conn, addr, latest, session):
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    conn.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 512 * 1024)
    buf = b""
    playing = False
    seq = 0
    ts = 0
    last_idx = 0
    ssrc = 0x26401200
    print("client", addr, flush=True)
    try:
        while True:
            conn.settimeout(0.05 if playing else 20)
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
                    if len(buf) < 4:
                        break
                    ln = struct.unpack("!H", buf[2:4])[0]
                    need = 4 + ln
                    if len(buf) < need:
                        break
                    buf = buf[need:]
                    progressed = True
                    continue
                if b"\r\n\r\n" not in buf:
                    break
                raw, rest = buf.split(b"\r\n\r\n", 1)
                lines = raw.decode("utf-8", "replace").split("\r\n")
                first = lines[0] if lines else ""
                headers = {}
                for line in lines[1:]:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        headers[k.strip().lower()] = v.strip()
                clen = int(headers.get("content-length", "0") or 0)
                if len(rest) < clen:
                    break
                buf = rest[clen:]
                progressed = True
                print(first, flush=True)
                cseq = headers.get("cseq", "1")
                method = first.split(" ")[0] if first else ""
                extra = ""
                body = ""
                if method == "OPTIONS":
                    extra = "Public: OPTIONS, DESCRIBE, SETUP, PLAY, TEARDOWN, GET_PARAMETER\r\n"
                elif method == "DESCRIBE":
                    _, _, sp = latest.snapshot()
                    fmtp = "packetization-mode=1;profile-level-id=640032"
                    if sp and sp[0] and sp[1]:
                        fmtp += ";sprop-parameter-sets=%s,%s" % (
                            base64.b64encode(sp[0]).decode("ascii"),
                            base64.b64encode(sp[1]).decode("ascii"),
                        )
                    body = (
                        "v=0\r\n"
                        "o=- 0 0 IN IP4 0.0.0.0\r\n"
                        "s=camevision-h264\r\n"
                        "t=0 0\r\n"
                        "m=video 0 RTP/AVP 96\r\n"
                        "c=IN IP4 0.0.0.0\r\n"
                        "a=control:streamid=0\r\n"
                        "a=rtpmap:96 H264/90000\r\n"
                        "a=fmtp:96 %s\r\n"
                        "a=framerate:%d\r\n" % (fmtp, FPS)
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
                    extra = "Session: %s\r\nRange: npt=0.000-\r\n" % session
                    playing = True
                    last_idx, au, _ = latest.snapshot()
                    conn.sendall(
                        (
                            "RTSP/1.0 200 OK\r\nCSeq: %s\r\n%sContent-Length: 0\r\n\r\n"
                            % (cseq, extra)
                        ).encode()
                    )
                    if au:
                        seq = send_au(conn, au, seq, ts, ssrc)
                        ts = (ts + TS_STEP) & 0xFFFFFFFF
                    continue
                elif method == "GET_PARAMETER":
                    extra = "Session: %s\r\n" % session
                elif method == "TEARDOWN":
                    extra = "Session: %s\r\n" % session
                    conn.sendall(
                        (
                            "RTSP/1.0 200 OK\r\nCSeq: %s\r\n%sContent-Length: 0\r\n\r\n"
                            % (cseq, extra)
                        ).encode()
                    )
                    return
                conn.sendall(
                    (
                        "RTSP/1.0 200 OK\r\nCSeq: %s\r\n%sContent-Length: %d\r\n\r\n%s"
                        % (cseq, extra, len(body), body)
                    ).encode()
                )
            if playing:
                idx, au = latest.wait_new(last_idx, 0.1)
                if au is None:
                    _, au, _ = latest.snapshot()
                    if au is None:
                        continue
                else:
                    last_idx = idx
                seq = send_au(conn, au, seq, ts, ssrc)
                ts = (ts + TS_STEP) & 0xFFFFFFFF
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
