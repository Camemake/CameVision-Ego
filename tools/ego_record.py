#!/usr/bin/env python3
"""CameVision Ego session recorder — streams to the Windows host.

Does not write sessions on the camera. USB stays ADB. Host listens on
127.0.0.1:8091, or pulls through `adb forward tcp:8092 tcp:8091`.

Live stereo keeps rkaiq 3A. Record encodes the same live NV12 (trigger
unchanged) to HEVC on the PC so colour stays with the live JPEG.
"""
from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
import queue
import socket
import struct
import subprocess
import threading
import time
from ctypes import CDLL, POINTER, byref, c_int, c_ubyte
from pathlib import Path

HOST = ("127.0.0.1", 8091)
ENC = "/oem/usr/bin/mpi_enc_test"
HEVC = "16777220"
H264 = "7"
SRC_W, SRC_H = 1920, 1200
W, H = 1600, 1200
CROP_X = (SRC_W - W) // 2
SRC_FRAME = SRC_W * SRC_H * 3 // 2
FRAME = W * H * 3 // 2
# Keep the live trigger. Jumping 12.5 → 30 on Record shocks AWB (yellow
# clip) and overruns USB, which used to drop the bitstream after ~2 s.
TRIG_FPS = 15.0
FPS = 15
GOP = 30
BPS = 8_000_000
HOST_W, HOST_H, HOST_FPS, HOST_TRIG, HOST_GOP, HOST_BPS = W, H, FPS, TRIG_FPS, GOP, BPS
LOCAL_ROOT = Path("/userdata/recordings")
LOCAL_W, LOCAL_H, LOCAL_FPS = 1920, 1200, 50
KMPP = "/userdata/kmpp-rt52.ko"
ENC_INI = "/tmp/ego_enc.ini"
# Full-range BT.709 — RKAIQ HD output. BT.601 made playback look extra yellow.
ENC_INI_TEXT = (
    "[prep]\n"
    "range = 2\n"
    "colorprim = 1\n"
    "colortrc = 1\n"
    "colorspace = 1\n"
)
F_SETPIPE_SZ = 1031

T_MANIFEST = 1
T_SYNC = 2
T_VLEFT = 3
T_VRIGHT = 4
T_TSLEFT = 5
T_TSRIGHT = 6
T_IMUL = 7
T_IMUR = 8
T_COMPLETE = 9
T_LOG = 10
T_SID = 11

IMUS = (
    ("imu_left", Path("/sys/bus/iio/devices/iio:device2"), Path("/sys/bus/iio/devices/iio:device1"), 0),
    ("imu_right", Path("/sys/bus/iio/devices/iio:device4"), Path("/sys/bus/iio/devices/iio:device3"), 1),
)

CAM_DEV = {"left": "/dev/video24", "right": "/dev/video32"}
CAM_KEY = {"left": "cam0", "right": "cam1"}


def _read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return default


def device_serial() -> str:
    for p in (
        "/sys/class/android_usb/android0/iSerial",
        "/proc/device-tree/serial-number",
    ):
        s = _read_text(Path(p)).replace("\x00", "").strip()
        if s:
            return s.replace(" ", "_")
    return "ego"


def boot_count() -> int:
    p = Path("/userdata/boot_count")
    try:
        return int(_read_text(p, "0") or "0")
    except ValueError:
        return 0


def next_session_index() -> int:
    p = Path("/userdata/session_index")
    try:
        n = int(_read_text(p, "0") or "0") + 1
    except ValueError:
        n = 1
    p.write_text(str(n), encoding="ascii")
    return n


def ensure_kmpp() -> str:
    if os.path.exists("/dev/mpp_service") or os.path.exists("/dev/vcodec"):
        return "ok"
    if os.path.isfile(KMPP):
        subprocess.call(["insmod", KMPP], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists("/dev/mpp_service") or os.path.exists("/dev/vcodec"):
        return "loaded"
    return "missing"


def pack(kind: int, payload: bytes) -> bytes:
    return b"EGOR" + struct.pack(">BBHI", 1, kind, 0, len(payload)) + payload


def restore_host_geom() -> None:
    global W, H, CROP_X, FRAME, FPS, TRIG_FPS, GOP, BPS
    W, H = HOST_W, HOST_H
    CROP_X = (SRC_W - W) // 2
    FRAME = W * H * 3 // 2
    FPS = HOST_FPS
    TRIG_FPS = HOST_TRIG
    GOP = HOST_GOP
    BPS = HOST_BPS


_NV12 = None
_NV12_LOOP = None


def _load_nv12() -> None:
    global _NV12, _NV12_LOOP
    path = "/userdata/libego_stereo.so"
    if not os.path.exists(path):
        return
    try:
        lib = CDLL(path)
        fn = lib.ego_nv12_rot180_crop
        fn.argtypes = [POINTER(c_ubyte), c_int, c_int, POINTER(c_ubyte), c_int]
        fn.restype = None
        _NV12 = fn
        loop = lib.ego_nv12_prep_loop
        loop.argtypes = [c_int, c_int, c_int, c_int, c_int, POINTER(c_int), POINTER(c_int)]
        loop.restype = c_int
        _NV12_LOOP = loop
    except Exception as exc:
        _NV12_LOOP = None
        print("nv12 loop off:", exc, flush=True)


def _u8(buf, n: int):
    if isinstance(buf, memoryview):
        buf = buf.obj
    return (c_ubyte * n).from_buffer(buf)


def prep_nv12(src, dst: bytearray) -> None:
    """180° (live viewer) + center-crop 1920 -> 1600, height 1200 unchanged."""
    if _NV12 is not None:
        _NV12(_u8(src, SRC_FRAME), SRC_W, SRC_H, _u8(dst, FRAME), W)
        return
    import numpy as np

    y = np.frombuffer(src, dtype=np.uint8, count=SRC_W * SRC_H).reshape(SRC_H, SRC_W)
    uv = np.frombuffer(src, dtype=np.uint8, offset=SRC_W * SRC_H, count=SRC_W * (SRC_H // 2)).reshape(
        SRC_H // 2, SRC_W
    )
    yo = np.frombuffer(dst, dtype=np.uint8, count=W * H).reshape(H, W)
    uvo = np.frombuffer(dst, dtype=np.uint8, offset=W * H, count=W * (H // 2)).reshape(H // 2, W)
    yo[:, :] = y[::-1, CROP_X : CROP_X + W][:, ::-1]
    crop_uv = uv[::-1, CROP_X : CROP_X + W]
    uvo[:, :] = crop_uv.reshape(H // 2, W // 2, 2)[:, ::-1, :].reshape(H // 2, W)


_load_nv12()


class MppEnc:
    def __init__(self, side: str, codec: str) -> None:
        self.side = side
        self.codec = codec
        self.typ = HEVC if codec == "hevc" else H264
        self.proc: subprocess.Popen | None = None
        self.infd = -1
        self.out = None
        self.inf = "/tmp/ego_%s.nv12" % side
        self.outf = "/tmp/ego_%s.bit" % side
        self.frames = 0
        self.err = ""
        self.bytes_out = 0
        self._buf = bytearray(FRAME)
        self._scratch = bytearray(FRAME)
        self._have = threading.Event()
        self._wstop = threading.Event()
        self._wthr: threading.Thread | None = None
        self._pthr: threading.Thread | None = None
        self._free: queue.Queue = queue.Queue()
        self._work: queue.Queue = queue.Queue(maxsize=6)
        self.cstop = c_int(0)
        self.cframes = c_int(0)
        self.rawf = ""
        self._use_writer = True
        for _ in range(8):
            self._free.put(bytearray(SRC_FRAME))

    def start(self) -> None:
        for p in (self.inf, self.outf):
            try:
                os.remove(p)
            except OSError:
                pass
        os.mkfifo(self.inf)
        open(self.outf, "wb").close()
        try:
            Path(ENC_INI).write_text(ENC_INI_TEXT, encoding="ascii")
        except OSError:
            pass
        env = os.environ.copy()
        env["PATH"] = "/oem/usr/bin:" + env.get("PATH", "")
        env["LD_LIBRARY_PATH"] = "/oem/usr/lib:/oem/lib:" + env.get("LD_LIBRARY_PATH", "")
        base = [
            ENC, "-i", self.inf, "-o", self.outf,
            "-w", str(W), "-h", str(H),
            "-hstride", str(W), "-vstride", str(H),
            "-f", "0", "-t", self.typ, "-n", "1000000",
            "-g", "1:%d:0" % GOP, "-fps", "%d:%d" % (FPS, FPS),
            "-rc", "1", "-bps", str(BPS), "-v", "q",
        ]
        extras = [
            ["-qc", "24:18:42:18:42", "-atf", "2", "-sm", "1", "-ini", ENC_INI],
            ["-qc", "24:18:42:18:42"],
            [],
        ]
        self.proc = None
        last_err = "mpi_enc_test failed"
        log_path = "/tmp/ego_%s_enc.log" % self.side
        for extra in extras:
            if self.proc is not None:
                try:
                    self.proc.kill()
                    self.proc.wait(timeout=1)
                except Exception:
                    pass
            logf = open(log_path, "wb")
            self.proc = subprocess.Popen(
                base + extra, stdin=subprocess.DEVNULL, stdout=logf, stderr=subprocess.STDOUT, env=env
            )
            t0 = time.monotonic()
            fd = -1
            last_err = "encoder fifo not ready"
            while time.monotonic() - t0 < 4.0:
                if self.proc.poll() is not None:
                    last_err = "mpi_enc_test exited %s" % self.proc.returncode
                    fd = -1
                    break
                try:
                    fd = os.open(self.inf, os.O_WRONLY | os.O_NONBLOCK)
                    break
                except OSError:
                    time.sleep(0.05)
            if fd >= 0:
                break
        if fd < 0:
            raise RuntimeError(last_err)
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl & ~os.O_NONBLOCK)
        try:
            fcntl.fcntl(fd, F_SETPIPE_SZ, 1024 * 1024)
        except OSError:
            pass
        self.infd = fd
        self.out = open(self.outf, "rb")
        self._have.clear()
        self._wstop.clear()
        self.cstop.value = 0
        self.cframes.value = 0
        if self._use_writer:
            while not self._work.empty():
                try:
                    self._free.put_nowait(self._work.get_nowait())
                except Exception:
                    break
            self._wthr = threading.Thread(target=self._writer, daemon=True)
            self._wthr.start()

    def start_prep(self, raw_path: str) -> None:
        self.rawf = raw_path
        self.cstop.value = 0
        self.cframes.value = 0
        self._pthr = threading.Thread(target=self._prep, daemon=True)
        self._pthr.start()

    def _prep(self) -> None:
        infd = -1
        try:
            infd = os.open(self.rawf, os.O_RDONLY)
            if _NV12_LOOP is not None:
                _NV12_LOOP(infd, self.infd, SRC_W, SRC_H, W, byref(self.cstop), byref(self.cframes))
                return
            src = bytearray(SRC_FRAME)
            dst = bytearray(FRAME)
            while not self.cstop.value:
                got = 0
                mv = memoryview(src)
                while got < SRC_FRAME and not self.cstop.value:
                    chunk = os.read(infd, SRC_FRAME - got)
                    if not chunk:
                        return
                    mv[got : got + len(chunk)] = chunk
                    got += len(chunk)
                prep_nv12(src, dst)
                off = 0
                view = memoryview(dst)
                while off < FRAME and not self.cstop.value:
                    n = os.write(self.infd, view[off:FRAME])
                    if n <= 0:
                        return
                    off += n
                self.cframes.value += 1
        except Exception as exc:
            self.err = str(exc)
        finally:
            if infd >= 0:
                try:
                    os.close(infd)
                except OSError:
                    pass

    def _writer(self) -> None:
        while not self._wstop.is_set():
            try:
                buf = self._work.get(timeout=0.05)
            except queue.Empty:
                continue
            if self.infd < 0:
                self._free.put(buf)
                break
            try:
                prep_nv12(buf, self._scratch)
            except Exception as exc:
                self.err = str(exc)
                self._free.put(buf)
                continue
            off = 0
            view = memoryview(self._scratch)
            while off < FRAME and not self._wstop.is_set():
                try:
                    n = os.write(self.infd, view[off:FRAME])
                except OSError as exc:
                    self.err = str(exc)
                    break
                if n <= 0:
                    break
                off += n
            self._free.put(buf)

    def push(self, nv12) -> bool:
        if self.infd < 0 or self._wstop.is_set():
            return False
        try:
            buf = self._free.get_nowait()
        except queue.Empty:
            return False
        view = memoryview(nv12)
        if len(view) < SRC_FRAME:
            self._free.put(buf)
            return False
        try:
            buf[:SRC_FRAME] = view[:SRC_FRAME]
        except Exception as exc:
            self.err = str(exc)
            self._free.put(buf)
            return False
        try:
            self._work.put_nowait(buf)
        except queue.Full:
            self._free.put(buf)
            return False
        self.frames += 1
        return True

    def pull(self) -> bytes:
        if self.out is None:
            return b""
        try:
            blob = self.out.read1(256 * 1024) if hasattr(self.out, "read1") else self.out.read(65536)
        except Exception:
            return b""
        if blob:
            self.bytes_out += len(blob)
        return blob

    def finish(self) -> None:
        self.cstop.value = 1
        self._wstop.set()
        if self._pthr is not None:
            self._pthr.join(timeout=2.0)
            self._pthr = None
        if self._wthr is not None:
            self._wthr.join(timeout=2.0)
            self._wthr = None
        try:
            if self.infd >= 0:
                os.close(self.infd)
        except OSError:
            pass
        self.infd = -1
        if self.proc is not None:
            try:
                self.proc.wait(timeout=4)
            except Exception:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=1)
                except Exception:
                    self.proc.kill()
            self.proc = None

    def close(self) -> None:
        self.finish()
        if self.out is not None:
            try:
                self.out.close()
            except Exception:
                pass
            self.out = None
        for p in (self.inf, self.outf):
            try:
                os.remove(p)
            except OSError:
                pass


class LocalSink:
    """Write the session tree on eMMC: episode/ + synced/."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.ep = root / "episode"
        self.sy = root / "synced"
        self.fl = self.ep / "frames_left"
        self.fr = self.ep / "frames_right"
        self.ep.mkdir(parents=True, exist_ok=True)
        self.sy.mkdir(parents=True, exist_ok=True)
        self.fl.mkdir(parents=True, exist_ok=True)
        self.fr.mkdir(parents=True, exist_ok=True)
        self.files = {
            T_TSLEFT: (self.ep / "cam_left.timestamps.jsonl").open("ab"),
            T_TSRIGHT: (self.ep / "cam_right.timestamps.jsonl").open("ab"),
            T_IMUL: (self.ep / "imu_left.jsonl").open("ab"),
            T_IMUR: (self.ep / "imu_right.jsonl").open("ab"),
            T_LOG: (self.ep / "session.log").open("ab"),
        }
        self.raw = {
            T_VLEFT: (self.ep / "cam_left.annexb").open("ab"),
            T_VRIGHT: (self.ep / "cam_right.annexb").open("ab"),
        }
        self.bytes_out = 0

    def write(self, kind: int, payload: bytes) -> None:
        if kind in (T_VLEFT, T_VRIGHT):
            fh = self.raw[kind]
            fh.write(payload)
            fh.flush()
            self.bytes_out += len(payload)
            return
        if kind in self.files:
            self.files[kind].write(payload)
            self.files[kind].flush()
            self.bytes_out += len(payload)
            return
        if kind == T_MANIFEST:
            (self.ep / "manifest.json").write_text(
                json.dumps(json.loads(payload.decode()), indent=2) + "\n", encoding="utf-8"
            )
            return
        if kind == T_SYNC:
            (self.ep / "sync_point.json").write_text(
                json.dumps(json.loads(payload.decode()), indent=2) + "\n", encoding="utf-8"
            )

    def still(self, side: str, idx: int, jpeg: bytes) -> None:
        if not jpeg:
            return
        dest = (self.fl if side == "left" else self.fr) / ("%06d.jpg" % idx)
        dest.write_bytes(jpeg)

    def close(self) -> None:
        for fh in list(self.files.values()) + list(self.raw.values()):
            try:
                fh.flush()
                os.fsync(fh.fileno())
                fh.close()
            except Exception:
                pass

    def finish_sync(self) -> None:
        def load(path: Path) -> list:
            rows = []
            if not path.is_file():
                return rows
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return rows

        left = load(self.ep / "cam_left.timestamps.jsonl")
        right = load(self.ep / "cam_right.timestamps.jsonl")
        rm = {int(r.get("trigger_index") or -1): r for r in right}
        matched = 0
        dt = []
        out = []
        for L in left:
            ti = int(L.get("trigger_index") or -1)
            R = rm.get(ti)
            rec = {
                "trigger_index": ti,
                "left_frame": L.get("frame_index"),
                "right_frame": None if R is None else R.get("frame_index"),
                "t_left": L.get("timestamp_or_counter"),
                "t_right": None if R is None else R.get("timestamp_or_counter"),
            }
            if R is not None:
                matched += 1
                rec["dt_us"] = int((int(R["timestamp_or_counter"]) - int(L["timestamp_or_counter"])) / 1000)
                dt.append(abs(rec["dt_us"]))
            out.append(rec)
        with (self.sy / "frame_map.jsonl").open("w", encoding="utf-8") as fh:
            for rec in out:
                fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
        report = {
            "left_frames": len(left),
            "right_frames": len(right),
            "matched": matched,
            "unmatched": len(out) - matched,
            "dt_us_max": max(dt) if dt else 0,
            "dt_us_mean": int(sum(dt) / len(dt)) if dt else 0,
        }
        (self.sy / "sync_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    def file_list(self) -> list:
        rows = []
        for folder in (self.ep, self.sy):
            if not folder.is_dir():
                continue
            for p in sorted(folder.rglob("*")):
                if not p.is_file() or p.suffix == ".tmp":
                    continue
                h = hashlib.sha256()
                n = 0
                with p.open("rb") as fh:
                    while True:
                        chunk = fh.read(1 << 20)
                        if not chunk:
                            break
                        n += len(chunk)
                        h.update(chunk)
                rows.append({
                    "path": str(p.relative_to(self.root)).replace("\\", "/"),
                    "bytes": n,
                    "sha256": h.hexdigest(),
                })
        return rows


class Recorder:
    def __init__(self, shared: dict) -> None:
        self.shared = shared
        self.lock = threading.Lock()
        self.active = False
        self.sid = ""
        self.codec = "hevc"
        self.err = ""
        self.sock: socket.socket | None = None
        self.enc: dict[str, MppEnc] = {}
        self.t0 = 0.0
        self.n = {"cam0": 0, "cam1": 0}
        self.last_trig = {"cam0": -1, "cam1": -1}
        self.bytes_out = 0
        self._trig_base = 0
        self._imu_stop = threading.Event()
        self._send_stop = threading.Event()
        self._q: queue.Queue = queue.Queue(maxsize=128)
        self._send_thr: threading.Thread | None = None
        self.local = False
        self.local_root: Path | None = None
        self._sink: LocalSink | None = None
        self._stills_stop = threading.Event()

    def status(self) -> dict:
        with self.lock:
            rec_fps = 0.0
            if self.active and self.t0:
                dt = max(0.001, time.monotonic() - self.t0)
                rec_fps = (self.n["cam0"] + self.n["cam1"]) / 2.0 / dt
            return {
                "on": int(self.active),
                "session_id": self.sid,
                "codec": self.codec,
                "err": self.err,
                "fps": round(rec_fps, 2),
                "n_left": self.n.get("cam0", 0),
                "n_right": self.n.get("cam1", 0),
                "bytes": self.bytes_out,
                "local": int(self.local),
                "path": str(self.local_root) if self.local_root else "",
            }

    def _send(self, kind: int, payload: bytes) -> None:
        if self._sink is not None:
            self._sink.write(kind, payload)
            self.bytes_out = self._sink.bytes_out
            return
        blob = pack(kind, payload)
        keep = kind in (
            T_VLEFT, T_VRIGHT, T_MANIFEST, T_SYNC, T_SID, T_COMPLETE,
            T_TSLEFT, T_TSRIGHT, T_LOG,
        )
        while True:
            try:
                self._q.put(blob, timeout=0.5 if keep else 0.05)
                return
            except queue.Full:
                if keep and not self._send_stop.is_set():
                    continue
                return

    def _send_loop(self) -> None:
        while not self._send_stop.is_set() or not self._q.empty():
            try:
                blob = self._q.get(timeout=0.05)
            except queue.Empty:
                continue
            sock = self.sock
            if sock is None:
                break
            try:
                sock.sendall(blob)
                self.bytes_out += len(blob)
            except Exception:
                self._send_stop.set()
                break

    def _close_sock(self) -> None:
        self._send_stop.set()
        if self._send_thr is not None:
            self._send_thr.join(timeout=1.0)
            self._send_thr = None
        try:
            if self.sock is not None:
                self.sock.close()
        except Exception:
            pass
        self.sock = None

    def _connect(self) -> None:
        srv = socket.socket()
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind(("0.0.0.0", HOST[1]))
            srv.listen(1)
            srv.settimeout(20)
            conn, _addr = srv.accept()
        except OSError as exc:
            srv.close()
            raise OSError("Windows recorder not connected") from exc
        srv.close()
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.sock = conn

    def _begin_send(self, sid: str) -> None:
        self._send_stop.clear()
        self._imu_stop.clear()
        while not self._q.empty():
            try:
                self._q.get_nowait()
            except queue.Empty:
                break
        self._send_thr = threading.Thread(target=self._send_loop, daemon=True)
        self._send_thr.start()
        self.sid = sid
        self._send(T_SID, sid.encode())

    def start(self, local: bool = False) -> dict:
        global W, H, CROP_X, FRAME, FPS, TRIG_FPS, GOP, BPS
        with self.lock:
            if self.active:
                return self.status()
        self.err = ""
        self.local = bool(local)
        kmpp = ensure_kmpp()
        serial = device_serial()
        sid = "%s_%s_%s" % (serial, boot_count(), next_session_index())
        if kmpp == "missing":
            self.err = "kmpp missing — load kmpp-rt52.ko"
            return {"on": 0, "err": self.err, "session_id": ""}
        sides = [s for s, dev in CAM_DEV.items() if os.path.exists(dev)]
        if not sides:
            sides = ["left"]
        if self.local:
            W, H = LOCAL_W, LOCAL_H
            CROP_X = 0
            FRAME = W * H * 3 // 2
            FPS = LOCAL_FPS
            TRIG_FPS = float(LOCAL_FPS)
            GOP = LOCAL_FPS
            BPS = 10_000_000
            LOCAL_ROOT.mkdir(parents=True, exist_ok=True)
            root = LOCAL_ROOT / sid
            if root.exists():
                root = LOCAL_ROOT / ("%s_%d" % (sid, int(time.time())))
            self.local_root = root
            self._sink = LocalSink(root)
            self.sid = sid
            self._imu_stop.clear()
            self._stills_stop.clear()
        else:
            restore_host_geom()
            try:
                self._connect()
            except OSError:
                self.err = "Windows recorder not connected (start cv_ego_record_host.py)"
                return {"on": 0, "err": self.err, "session_id": sid}
            self._begin_send(sid)
        encs: dict[str, MppEnc] = {}
        codec = "hevc"
        last_err = ""
        for try_codec in ("hevc", "h264"):
            encs = {}
            ok = True
            for side in sides:
                enc = MppEnc(side, try_codec)
                enc._use_writer = not self.local
                try:
                    enc.start()
                except Exception as exc:
                    last_err = "%s %s: %s" % (try_codec, side, exc)
                    ok = False
                    enc.close()
                    for e in encs.values():
                        e.close()
                    break
                encs[side] = enc
            if ok:
                codec = try_codec
                break
        if not encs:
            self.err = last_err or "encoder failed"
            if self._sink is not None:
                self._sink.close()
                self._sink = None
            else:
                self._close_sock()
            restore_host_geom()
            return {"on": 0, "err": self.err, "session_id": sid}
        wall = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cams = {}
        if "left" in encs:
            cams["left"] = {"file": "cam_left.mp4", "dev": "/dev/video24", "role": "cam0", "imu": "imu0"}
        if "right" in encs:
            cams["right"] = {"file": "cam_right.mp4", "dev": "/dev/video32", "role": "cam1", "imu": "imu1"}
        manifest = {
            "session_id": sid,
            "device_serial": serial,
            "boot_count": boot_count(),
            "session_index": int(_read_text(Path("/userdata/session_index"), "0") or "0"),
            "wall_clock_utc": wall,
            "time_base": "CLOCK_MONOTONIC_ns",
            "storage": "emmc" if self.local else "host",
            "path": str(self.local_root) if self.local_root else "",
            "cameras": cams,
            "video": {
                "codec": codec,
                "profile": "main" if codec == "hevc" else "high",
                "width": W,
                "height": H,
                "src_width": SRC_W,
                "src_height": SRC_H,
                "crop": {"x": CROP_X, "y": 0, "w": W, "h": H},
                "rotate_deg": 180,
                "fps_target": TRIG_FPS,
                "gop": GOP,
                "bframes": 0,
                "rc": "cbr",
                "bitrate": BPS,
                "pixfmt": "nv12",
                "path": "v4l2 -> nv12 prep -> mpi_enc_test fifo",
                "flicker": "50Hz_iq",
                "ae": "rkaiq_3A",
                "color": {
                    "primaries": "bt709",
                    "transfer": "bt709",
                    "matrix": "bt709",
                    "range": "full",
                },
            },
            "session_complete": False,
        }
        sync_point = {
            "time_base": "CLOCK_MONOTONIC_ns",
            "epoch_unix_ns": time.clock_gettime_ns(time.CLOCK_REALTIME),
            "mono_ns": time.clock_gettime_ns(time.CLOCK_MONOTONIC),
            "trigger_fps": TRIG_FPS,
        }
        with self.lock:
            self.active = True
            self.sid = sid
            self.codec = codec
            self.enc = encs
            self.t0 = time.monotonic()
            self.n = {"cam0": 0, "cam1": 0}
            self.last_trig = {"cam0": -1, "cam1": -1}
        sync = self.shared.get("cam_sync")
        self._trig_base = int(getattr(sync, "pulses", 0) or 0) if sync is not None else 0
        self._send(T_MANIFEST, json.dumps(manifest, separators=(",", ":")).encode())
        self._send(T_SYNC, json.dumps(sync_point, separators=(",", ":")).encode())
        for side, enc in encs.items():
            kind = T_VLEFT if side == "left" else T_VRIGHT
            threading.Thread(target=self._pump_enc, args=(side, kind), daemon=True).start()
        dest = {}
        if self.local:
            for side, enc in encs.items():
                raw = "/tmp/ego_%s_raw.nv12" % side
                try:
                    os.remove(raw)
                except OSError:
                    pass
                os.mkfifo(raw)
                enc.start_prep(raw)
                dest[CAM_KEY[side]] = raw
            threading.Thread(target=self._ts_watch, daemon=True).start()
        self.shared["rec_dest"] = dest
        self.shared["rec_on"] = True
        self.shared["rec_fps_target"] = TRIG_FPS
        threading.Thread(target=self._imu_loop, daemon=True).start()
        return self.status()

    def stop(self) -> dict:
        with self.lock:
            was = self.active
            self.active = False
        self.shared["rec_on"] = False
        self.shared["rec_dest"] = {}
        if not was:
            return self.status()
        self._stills_stop.set()
        self._imu_stop.set()
        for enc in self.enc.values():
            enc.finish()
        time.sleep(0.4)
        for side in ("left", "right"):
            try:
                txt = Path("/tmp/ego_%s_enc.log" % side).read_text(encoding="utf-8", errors="replace")
                if txt.strip():
                    self._send(T_LOG, ("%s encoder\n%s" % (side, txt[-2500:])).encode())
            except OSError:
                pass
        st = self.status()
        actual = {}
        dt = max(0.001, time.monotonic() - self.t0) if self.t0 else 0.001
        for side, enc in self.enc.items():
            actual[side] = round(self.n[CAM_KEY[side]] / dt, 2)
        st["fps_actual"] = actual
        try:
            self._send(T_COMPLETE, json.dumps(st, separators=(",", ":")).encode())
        except Exception:
            pass
        self._send_stop.set()
        if self._send_thr is not None:
            self._send_thr.join(timeout=2.0)
        try:
            if self.sock is not None:
                self.sock.close()
        except Exception:
            pass
        self.sock = None
        for enc in self.enc.values():
            enc.close()
        self.enc = {}
        if self._sink is not None:
            sink = self._sink
            try:
                sink.finish_sync()
            except Exception:
                pass
            sink.close()
            try:
                man_path = sink.ep / "manifest.json"
                man = {}
                if man_path.is_file():
                    man = json.loads(man_path.read_text(encoding="utf-8"))
                man["session_complete"] = True
                man["fps_actual"] = actual
                man["closed_unix"] = time.time()
                man["files"] = sink.file_list()
                man_path.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
            except Exception:
                pass
            self._sink = None
        self.local = False
        self.local_root = None
        restore_host_geom()
        self.shared["rec_fps_target"] = HOST_TRIG
        return st

    def _ts_watch(self) -> None:
        last = {"left": 0, "right": 0}
        while self.active:
            sync = self.shared.get("cam_sync")
            trig = int(getattr(sync, "pulses", 0) or 0) if sync is not None else 0
            t_ns = int(getattr(sync, "last_t_ns", 0) or 0) if sync is not None else 0
            if not t_ns:
                t_ns = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
            for side, enc in list(self.enc.items()):
                n = int(enc.cframes.value)
                key = CAM_KEY[side]
                while last[side] < n and self.active:
                    last[side] += 1
                    enc.frames = last[side]
                    self.n[key] = last[side]
                    pts = max(0, (last[side] - 1) * (1_000_000_000 // FPS))
                    self._ts_line(key, trig, t_ns, {}, flags=0, frame_index=last[side] - 1, pts=pts)
            time.sleep(0.003)

    def on_frame(self, key: str, buf, trig: int, t_ns: int, meta: dict) -> None:
        if not self.active:
            return
        side = "left" if key == "cam0" else "right"
        enc = self.enc.get(side)
        if enc is None:
            return
        ok = enc.push(buf)
        if not ok:
            return
        idx = enc.frames
        self.n[key] = idx
        pts = max(0, (idx - 1) * (1_000_000_000 // FPS)) if idx else 0
        self._ts_line(key, trig, t_ns, meta, flags=0, frame_index=max(0, idx - 1), pts=pts)

    def _ts_line(self, key: str, trig: int, t_ns: int, meta: dict, flags: int, frame_index: int | None = None, pts: int = 0) -> None:
        if frame_index is None:
            frame_index = self.n[key]
        line = {
            "frame_index": frame_index,
            "frame_id": trig,
            "timestamp_or_counter": t_ns,
            "pts": pts,
            "trigger_index": trig,
            "exposure_us": int(meta.get("exposure_us") or 0),
            "again": float(meta.get("again") or 1.0),
            "dgain": float(meta.get("dgain") or 1.0),
            "awb_r_gain": float(meta.get("awb_r") or 1.0),
            "awb_b_gain": float(meta.get("awb_b") or 1.0),
            "flags": flags,
        }
        kind = T_TSLEFT if key == "cam0" else T_TSRIGHT
        try:
            self._send(kind, (json.dumps(line, separators=(",", ":")) + "\n").encode())
        except Exception:
            pass

    def _trig_loop(self) -> None:
        last = 0
        while self.active:
            sync = self.shared.get("cam_sync")
            pulses = int(getattr(sync, "pulses", 0) or 0) if sync is not None else 0
            if pulses > last:
                ring = getattr(sync, "pulse_ns", None) if sync is not None else None
                for trig in range(last + 1, pulses + 1):
                    flags = 0
                    t_ns = 0
                    if ring:
                        t_ns = int(ring[trig & 511] or 0)
                    if not t_ns:
                        t_ns = int(getattr(sync, "last_t_ns", 0) or 0)
                    pts = max(0, (trig - 1) * (1_000_000_000 // FPS))
                    for side, enc in list(self.enc.items()):
                        key = CAM_KEY[side]
                        self.n[key] = trig
                        self.last_trig[key] = trig
                        self._ts_line(key, trig, t_ns, {}, flags=flags, frame_index=trig - 1, pts=pts)
                last = pulses
            else:
                time.sleep(0.0004)

    def _pump_enc(self, side: str, kind: int) -> None:
        enc = self.enc.get(side)
        if enc is None:
            return
        idle = 0
        while True:
            blob = enc.pull()
            if blob:
                idle = 0
                try:
                    self._send(kind, blob)
                except Exception:
                    break
                continue
            if not self.active:
                idle += 1
                if idle > 80:
                    break
            time.sleep(0.002)

    def _imu_loop(self) -> None:
        handles = []
        for name, accel, gyro, cam in IMUS:
            if not accel.is_dir() or not (accel / "in_accel_x_raw").is_file():
                continue
            try:
                (accel / "sampling_frequency").write_text("480")
                (gyro / "sampling_frequency").write_text("480")
            except OSError:
                pass
            files = [
                open(accel / "in_accel_x_raw", "rb", buffering=0),
                open(accel / "in_accel_y_raw", "rb", buffering=0),
                open(accel / "in_accel_z_raw", "rb", buffering=0),
                open(gyro / "in_anglvel_x_raw", "rb", buffering=0),
                open(gyro / "in_anglvel_y_raw", "rb", buffering=0),
                open(gyro / "in_anglvel_z_raw", "rb", buffering=0),
            ]
            ascl = float((accel / "in_accel_scale").read_text())
            gscl = float((gyro / "in_anglvel_scale").read_text())
            kind = T_IMUL if name == "imu_left" else T_IMUR
            handles.append((name, files, ascl, gscl, kind))
        n = {h[0]: 0 for h in handles}
        batch = {h[0]: [] for h in handles}
        while not self._imu_stop.is_set():
            t_ns = time.clock_gettime_ns(time.CLOCK_MONOTONIC)
            for name, files, ascl, gscl, kind in handles:
                try:
                    vals = []
                    for f in files:
                        f.seek(0)
                        vals.append(int(f.read().strip() or b"0"))
                except Exception:
                    continue
                ax, ay, az = vals[0] * ascl, vals[1] * ascl, vals[2] * ascl
                gx, gy, gz = vals[3] * gscl, vals[4] * gscl, vals[5] * gscl
                rec = {
                    "sample_index": n[name],
                    "timestamp_or_counter": t_ns,
                    "ax": ax, "ay": ay, "az": az,
                    "gx": gx, "gy": gy, "gz": gz,
                    "flags": 0,
                }
                n[name] += 1
                batch[name].append(json.dumps(rec, separators=(",", ":")))
                if len(batch[name]) >= 16:
                    try:
                        self._send(kind, ("\n".join(batch[name]) + "\n").encode())
                    except Exception:
                        self._imu_stop.set()
                        break
                    batch[name] = []
            time.sleep(0.001)
        for name, files, ascl, gscl, kind in handles:
            if batch.get(name):
                try:
                    self._send(kind, ("\n".join(batch[name]) + "\n").encode())
                except Exception:
                    pass
            for f in files:
                try:
                    f.close()
                except Exception:
                    pass
