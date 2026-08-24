#!/usr/bin/env python3
"""CameVision Ego stereo: live color + depth overlay + IMU. Depth stays on the NPU."""
from __future__ import annotations

import ctypes
import json
import os
import socket
import subprocess
import sys
import threading
import time

for _p in ("/userdata/pylib", "/userdata", os.path.dirname(os.path.abspath(__file__))):
    if _p and os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
from ctypes import (
    CDLL,
    POINTER,
    byref,
    c_int,
    c_ubyte,
    c_ulong,
    c_void_p,
    cast,
    string_at,
)

CAM_W, CAM_H = 1920, 1200
CAM_FRAME = CAM_W * CAM_H * 3 // 2
W, H = 640, 400
FRAME = W * H * 3 // 2
YSIZE = W * H
VIEW_W, VIEW_H = CAM_W, CAM_H
VIEW_FRAME = CAM_FRAME
PORT = 8081
CAM0, CAM1 = "/dev/video24", "/dev/video32"
# Physical left eye is CAM0 / video24 / IMU0. Right eye is CAM1 / video32 / IMU1.
LEFT_KEY, RIGHT_KEY = "cam0", "cam1"
LIB = "/userdata/libego_stereo.so"
TJ = "/oem/usr/lib/libturbojpeg.so"
CALIB_PATH = "/userdata/ego_calib.json"
CAL_HTML = "/userdata/ego_calib.html"
LOGO_PATH = "/userdata/camemake-logo.png"
BASELINE_MM = 75.0
DISTANCE_MM = 1000.0

# Fine grid is 640x400 (3 sensor pixels per match cell). At f=1260 px that
# is ~8 cells across 1 cm at 0.5 m, which is what makes a hand readable.
# SGBM stays on 160x100; two refine stages recover the rest.
CAP_FPS = 15
COLOR_PERIOD = 0.16
BW_FAST, BH_FAST, ND_FAST, TH_FAST = 640, 400, 96, 40
BW_SLOW, BH_SLOW, ND_SLOW, TH_SLOW = 320, 200, 32, 40
XW, XH = CAM_W, CAM_H
XFRAME = CAM_FRAME
MID_W, MID_H = 640, 400

NATIVE = None
BW = BW_FAST
BH = BH_FAST
ND = ND_FAST
TH = TH_FAST
_CV_BM = None


def _jet_rgb(i: int):
    x = i / 255.0
    r = max(0.0, min(1.0, 1.5 - abs(4.0 * x - 3.0)))
    g = max(0.0, min(1.0, 1.5 - abs(4.0 * x - 2.0)))
    b = max(0.0, min(1.0, 1.5 - abs(4.0 * x - 1.0)))
    return int(r * 255), int(g * 255), int(b * 255)


def _lut_yuv():
    yuv = []
    for i in range(256):
        r, g, b = _jet_rgb(i)
        y = (66 * r + 129 * g + 25 * b + 128) >> 8
        u = ((-38 * r - 74 * g + 112 * b + 128) >> 8) + 128
        v = ((112 * r - 94 * g - 18 * b + 128) >> 8) + 128
        yuv.append((max(0, min(255, y)), max(0, min(255, u)), max(0, min(255, v))))
    return yuv


LUT = _lut_yuv()


def _load_native():
    global NATIVE
    if not os.path.exists(LIB):
        return
    lib = CDLL(LIB)
    lib.ego_y_down.argtypes = [
        POINTER(c_ubyte), c_int, c_int, POINTER(c_ubyte), c_int, c_int
    ]
    lib.ego_stereo_bm.argtypes = [
        POINTER(c_ubyte), POINTER(c_ubyte), POINTER(c_ubyte),
        c_int, c_int, c_int, c_int,
    ]
    lib.ego_paint_nv12.argtypes = [
        POINTER(c_ubyte), c_int, c_int, POINTER(c_ubyte), c_int, c_int,
        POINTER(c_ubyte), POINTER(c_ubyte), POINTER(c_ubyte), c_int,
    ]
    lib.ego_render_xyz.argtypes = [
        POINTER(c_ubyte), c_int, c_int, POINTER(c_ubyte), c_int, c_int,
        POINTER(c_ubyte), POINTER(c_ubyte), POINTER(c_ubyte), c_int,
    ]
    NATIVE = lib


_load_native()
SCALE = max(1, 255 // ND)
LUT_Y = (c_ubyte * ND)(*[LUT[min(255, d * SCALE)][0] for d in range(ND)])
LUT_U = (c_ubyte * ND)(*[LUT[min(255, d * SCALE)][1] for d in range(ND)])
LUT_V = (c_ubyte * ND)(*[LUT[min(255, d * SCALE)][2] for d in range(ND)])

PAGE = b"""<!doctype html>
<html><head><meta charset="utf-8"><title>Camemake | CameVision Ego</title>
<link rel="icon" href="/brand.png">
<style>
 :root{--came:#1a6f7c;--pink:#e84b8a;--bg:#f4efe8;--ink:#222;--muted:#5c5c5c;--line:#e4ddd4}
 html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);
  font-family:Segoe UI,Helvetica Neue,Arial,sans-serif;overflow:hidden}
 .brand{height:72px;display:flex;align-items:center;gap:16px;padding:0 22px;
  background:#fff;border-bottom:1px solid var(--line)}
 .plate{background:transparent;padding:0}
 .plate img{height:28px;width:auto;display:block}
 .titles{display:flex;flex-direction:column;line-height:1.2}
 .titles b{font-size:20px;font-weight:800;color:#1a1a1a}
 .titles span{font-size:13px;color:var(--came)}
 .brand a{margin-left:auto;color:#fff;background:var(--pink);text-decoration:none;
  padding:10px 18px;border-radius:8px;font-size:14px;font-weight:700}
 .stage{height:calc(100% - 72px);padding:10px 12px 12px;box-sizing:border-box}
 .top{display:flex;height:58%;gap:10px}
 .pane{flex:1;position:relative;min-width:0;background:#111;border-radius:10px;overflow:hidden}
 .pane img.v{width:100%;height:100%;object-fit:contain;object-position:center;
  display:block;background:#111;transform:scale(-1,-1)}
 .bot{height:calc(42% - 10px);margin-top:10px;position:relative;background:#111;border-radius:10px;overflow:hidden}
 .bot img.v{width:100%;height:100%;object-fit:contain;object-position:center;
  display:block;background:#111;transform:scale(-1,-1)}
 .hud{position:absolute;left:10px;top:10px;background:rgba(255,255,255,.88);color:#222;padding:8px 10px;
      border-radius:8px;font:12px Consolas,monospace;white-space:pre;box-shadow:0 1px 4px rgba(0,0,0,.12)}
</style></head><body>
<div class="brand">
 <div class="plate"><img src="/brand.png" alt="Camemake"></div>
 <div class="titles"><b>CameVision Ego</b><span>Camemake stereo &middot; NPU</span></div>
 <a href="/cal">Calibrate</a>
</div>
<div class="stage">
<div class="top">
 <div class="pane"><img class="v" src="/ov1"><div class="hud" id="h0">LEFT CAM1 IMU1</div></div>
 <div class="pane"><img class="v" src="/ov0"><div class="hud" id="h1">RIGHT CAM0 IMU0</div></div>
</div>
<div class="bot"><img class="v" src="/xyz"><div class="hud" id="hz">3D depth</div></div>
</div>
<script>
function n(v,d){return (v===undefined||Number.isNaN(+v))?"-":Number(v).toFixed(d)}
function blk(l,i,d,s){
 if(!i) return l+"\\nno imu";
 return l+"  "+(i.bus||"")+"\\n"+(i.t_iso||d.t_iso||"")+
  "\\nIMU "+n(i.read_hz||d.read_hz,0)+" Hz   color "+n(s&&s.color_fps,1)+" fps"+
  "\\n|a| "+n(i.a_g,3)+" g   w "+n(i.gx,1)+" "+n(i.gy,1)+" "+n(i.gz,1)+
  "\\nbaseline 75.000 mm  "+((s&&s.w)||1920)+"x"+((s&&s.h)||1200);
}
async function t(){
 let d=null,s=null;
 try{ d=await (await fetch("/imu")).json(); }catch(e){}
 if(!d){ try{ d=await (await fetch("http://127.0.0.1:8083/")).json(); }catch(e){} }
 try{ s=await (await fetch("/stat")).json(); }catch(e){}
 h0.textContent=blk("LEFT   CAM1  IMU1",d&&d.imu1,d||{},s);
 h1.textContent=blk("RIGHT  CAM0  IMU0",d&&d.imu0,d||{},s);
 if(s) hz.textContent="3D depth  "+n(s.heat_fps||s.depth_fps,1)+" fps";
 setTimeout(t,40);
}
t();
</script></body></html>
"""

lock = threading.Lock()
latest = {
    "ov0": b"",
    "ov1": b"",
    "xyz": b"",
    "raw0": b"",
    "raw1": b"",
    "stat": b'{"color_fps":0,"depth_fps":0}',
}
shared = {
    "cam0": None,
    "cam1": None,
    "disp": bytearray(BW * BH),
    "want_raw": 0.0,
    "color_fps": 0.0,
    "trig_on": True,
    "cam0_t": 0.0,
    "cam1_t": 0.0,
}

try:
    from ego_cam_sync import start_thread as start_cam_sync, SYNC as CAM_SYNC
except Exception:
    CAM_SYNC = None

    def start_cam_sync(flag, key="trig_on", fps=CAP_FPS):
        return None


cal = {
    "running": False,
    "cols": 11,
    "rows": 8,
    "square_mm": 25.0,
    "distance_mm": DISTANCE_MM,
    "need": 15,
    "good": 0,
    "samples": [],
    "zones": {},
    "next_zone": "C",
    "hint": "",
    "last_ok": False,
    "last_dx": 0.0,
    "last_dy": 0.0,
    "last_l": [],
    "last_r": [],
    "last_t": 0.0,
    "msg": "live preview is on — press Start, then move the device",
    "result": None,
}


def load_calib() -> None:
    try:
        with open(CALIB_PATH, "r") as fh:
            cal["result"] = json.load(fh)
    except Exception:
        cal["result"] = None


def save_calib(result: dict) -> None:
    result["path"] = CALIB_PATH
    tmp = CALIB_PATH + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(result, fh, indent=2)
    os.replace(tmp, CALIB_PATH)
    cal["result"] = result


load_calib()


def load_logo() -> bytes:
    for path in (LOGO_PATH, os.path.join(os.path.dirname(__file__), "camemake-logo.png")):
        try:
            with open(path, "rb") as fh:
                data = fh.read()
            if data:
                return data
        except OSError:
            continue
    return b""


LOGO = load_logo()


def load_cal_page() -> bytes:
    for path in (CAL_HTML, os.path.join(os.path.dirname(__file__), "ego_calib.html")):
        try:
            with open(path, "rb") as fh:
                return fh.read().replace(b"\r\n", b"\n")
        except OSError:
            continue
    return b"<html><body><a href='/'>back</a> missing ego_calib.html</body></html>"


CAL_PAGE = load_cal_page()


def eyes():
    return shared.get(LEFT_KEY), shared.get(RIGHT_KEY)


def _median(vals):
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    if n % 2:
        return float(s[n // 2])
    return 0.5 * (s[n // 2 - 1] + s[n // 2])


def y_half(y) -> bytearray:
    out = bytearray(320 * 200)
    mv = memoryview(y)
    dst = 0
    for j in range(0, H, 2):
        row = mv[j * W : (j + 1) * W]
        out[dst : dst + 320] = row[::2]
        dst += 320
    return out


def _as_640_y(y):
    """Accept 1920x1200 or 640x400 Y and return 640x400."""
    if len(y) >= CAM_W * CAM_H:
        out = bytearray(YSIZE)
        mv = memoryview(y)
        for j in range(H):
            src = (j * 3) * CAM_W
            out[j * W : (j + 1) * W] = mv[src : src + CAM_W : 3]
        return bytes(out)
    return y


def find_chessboard(y, cols: int, rows: int):
    """Saddle-point inner corners. Returns 1920-space (x,y) or None."""
    need = cols * rows
    src_scale = 3.0 if len(y) >= CAM_W * CAM_H else 1.0
    y = _as_640_y(y)
    small = y_half(y)
    sw, sh = 320, 200
    r = 4
    step = 2
    cands = []
    for yy in range(r + 1, sh - r - 1, step):
        for xx in range(r + 1, sw - r - 1, step):
            tl = tr = bl = br = 0
            nq = r * r
            for dy in range(r):
                top = (yy - r + dy) * sw + xx
                bot = (yy + dy) * sw + xx
                for dx in range(r):
                    tl += small[top - r + dx]
                    tr += small[top + dx]
                    bl += small[bot - r + dx]
                    br += small[bot + dx]
            tl //= nq
            tr //= nq
            bl //= nq
            br //= nq
            diag = abs((tl + br) - (tr + bl))
            same = abs(tl - br) + abs(tr - bl)
            if diag < 28 or same > 46:
                continue
            if not ((tl < 128 and br < 128 and tr > 128 and bl > 128) or (
                tl > 128 and br > 128 and tr < 128 and bl < 128
            )):
                continue
            cands.append((diag - same * 0.35, xx, yy))
    if len(cands) < need:
        return None
    cands.sort(reverse=True)
    pts = []
    for _score, xx, yy in cands:
        if any((xx - px) * (xx - px) + (yy - py) * (yy - py) < 36 for px, py in pts):
            continue
        pts.append((xx, yy))
        if len(pts) >= need * 3:
            break
    if len(pts) < need:
        return None
    dists = []
    for i, (ax, ay) in enumerate(pts):
        best = 1e9
        for j, (bx, by) in enumerate(pts):
            if i == j:
                continue
            d = (ax - bx) * (ax - bx) + (ay - by) * (ay - by)
            if d < best:
                best = d
        dists.append(best ** 0.5)
    pitch = _median(dists)
    if pitch < 6:
        return None
    pts_y = sorted(pts, key=lambda p: p[1])
    bands = []
    for p in pts_y:
        if not bands or abs(p[1] - _median([q[1] for q in bands[-1]])) > pitch * 0.55:
            bands.append([p])
        else:
            bands[-1].append(p)
    bands = [sorted(b, key=lambda p: p[0]) for b in bands if len(b) >= cols]
    if len(bands) < rows:
        return None
    # pick the most regular rows-block
    best = None
    best_err = 1e18
    for start in range(0, len(bands) - rows + 1):
        block = bands[start : start + rows]
        err = 0.0
        ok = True
        chosen = []
        for band in block:
            if len(band) < cols:
                ok = False
                break
            if len(band) == cols:
                row = band
            else:
                # densest cols-run
                run = None
                run_e = 1e18
                for i in range(0, len(band) - cols + 1):
                    sl = band[i : i + cols]
                    spac = [sl[k + 1][0] - sl[k][0] for k in range(cols - 1)]
                    e = sum(abs(v - pitch) for v in spac)
                    if e < run_e:
                        run_e = e
                        run = sl
                row = run
                err += run_e
            chosen.append(row)
        if not ok or any(x is None for x in chosen):
            continue
        if err < best_err:
            best_err = err
            best = chosen
    if not best:
        return None
    out = []
    for row in best:
        for x, yv in row:
            out.append((x * 2.0 * src_scale, yv * 2.0 * src_scale))
    if len(out) != need:
        return None
    return out


def paint_corners(nv12, corners, out: bytearray, uv_u=32, uv_v=240) -> bytearray:
    out[:] = nv12
    y = memoryview(out)
    uv = memoryview(out)[YSIZE:]
    uw = W // 2
    for x, yv in corners:
        xi, yi = int(x), int(yv)
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                xx, yy = xi + dx, yi + dy
                if 0 <= xx < W and 0 <= yy < H:
                    y[yy * W + xx] = 255
        if 1 <= xi < W - 1 and 1 <= yi < H - 1:
            up = (yi // 2) * uw + (xi // 2)
            uv[up * 2] = uv_u
            uv[up * 2 + 1] = uv_v
    return out


def shift_y(y, dy: int) -> bytes:
    dy = int(round(dy))
    if dy == 0:
        return y
    out = bytearray(YSIZE)
    mv = memoryview(y)
    for j in range(H):
        sj = j - dy
        if 0 <= sj < H:
            out[j * W : (j + 1) * W] = mv[sj * W : (sj + 1) * W]
    return bytes(out)


REQUIRED_ZONES = ("C", "TL", "TR", "BL", "BR")
ZONE_HINT = {
    "C": "Move so the board sits in the CENTER of both live images.",
    "TL": "Move the device so the board is in the TOP-LEFT of the live frame.",
    "TR": "Move the device so the board is in the TOP-RIGHT of the live frame.",
    "BL": "Move the device so the board is in the BOTTOM-LEFT of the live frame.",
    "BR": "Move the device so the board is in the BOTTOM-RIGHT of the live frame.",
    "TC": "Raise the board toward the TOP edge, still at 1.00 m.",
    "BC": "Lower the board toward the BOTTOM edge, still at 1.00 m.",
    "ML": "Slide toward the LEFT edge of the live frame.",
    "MR": "Slide toward the RIGHT edge of the live frame.",
}


def display_xy(x: float, y: float):
    """Map full-res sensor pixels to the 180-rotated preview the user sees."""
    return (CAM_W - 1 - x, CAM_H - 1 - y)


def zone_of(corners) -> str:
    cx = sum(p[0] for p in corners) / len(corners)
    cy = sum(p[1] for p in corners) / len(corners)
    dx, dy = display_xy(cx, cy)
    col = 0 if dx < CAM_W * 0.38 else (2 if dx > CAM_W * 0.62 else 1)
    row = 0 if dy < CAM_H * 0.38 else (2 if dy > CAM_H * 0.62 else 1)
    return (("TL", "TC", "TR"), ("ML", "C", "MR"), ("BL", "BC", "BR"))[row][col]


def next_zone() -> str:
    have = cal.get("zones") or {}
    for z in REQUIRED_ZONES:
        if not have.get(z):
            return z
    return ""


def cal_status() -> dict:
    res = cal.get("result")
    have = cal.get("zones") or {}
    bu = bv = None
    corners = cal.get("last_l") or []
    if corners:
        cx = sum(p[0] for p in corners) / len(corners)
        cy = sum(p[1] for p in corners) / len(corners)
        dx, dy = display_xy(cx, cy)
        bu, bv = dx / float(CAM_W), dy / float(CAM_H)
    return {
        "running": cal["running"],
        "cols": cal["cols"],
        "rows": cal["rows"],
        "square_mm": cal["square_mm"],
        "distance_mm": cal["distance_mm"],
        "cap_w": CAM_W,
        "cap_h": CAM_H,
        "need": cal["need"],
        "good": cal["good"],
        "zones": have,
        "zone_n": sum(1 for z in REQUIRED_ZONES if have.get(z)),
        "next_zone": cal.get("next_zone") or next_zone(),
        "hint": cal.get("hint") or "",
        "board_u": bu,
        "board_v": bv,
        "last_ok": cal["last_ok"],
        "last_dx": cal["last_dx"],
        "last_dy": cal["last_dy"],
        "msg": cal["msg"],
        "corners_l": cal.get("last_l") or [],
        "corners_r": cal.get("last_r") or [],
        "npu": 1,
        "np": 1 if _np_ok() else 0,
        "cv": 1 if _cv_ok() else 0,
        "result": res,
    }


_CV = None
_NP = None


def _np_ok() -> bool:
    global _NP
    if _NP is None:
        try:
            import numpy  # noqa: F401
            _NP = True
        except Exception:
            _NP = False
    return _NP


def _cv_ok() -> bool:
    global _CV
    if _CV is None:
        try:
            import cv2
            import numpy  # noqa: F401

            # Two is as fast as four here and leaves cores for the encoders.
            cv2.setNumThreads(2)
            _CV = True
        except Exception:
            _CV = False
    return _CV


def accept_sample(cl, cr) -> dict:
    if not cal["running"]:
        return cal_status()
    if not cl or not cr or len(cl) < 8 or len(cr) < 8:
        cal["last_ok"] = False
        cal["hint"] = "Board not complete in both eyes. Fill more of the frame, keep 1.00 m."
        return cal_status()
    if len(cl) != len(cr):
        cl = [(sum(p[0] for p in cl) / len(cl), sum(p[1] for p in cl) / len(cl))]
        cr = [(sum(p[0] for p in cr) / len(cr), sum(p[1] for p in cr) / len(cr))]
    dxi = [a[0] - b[0] for a, b in zip(cl, cr)]
    dyi = [a[1] - b[1] for a, b in zip(cl, cr)]
    dx = _median(dxi)
    dy = _median(dyi)
    if dx <= 1.0 and -dx > 1.0:
        cl, cr = cr, cl
        dx, dy = -dx, -dy
    if dx <= 1.0:
        cal["last_ok"] = False
        cal["last_l"], cal["last_r"] = cl, cr
        cal["hint"] = "Board found, but stereo disparity is too small. Hold at 1.00 m."
        return cal_status()
    now = time.time()
    z = zone_of(cl)
    prev = cal["samples"][-1] if cal["samples"] else None
    if prev and prev.get("zone") == z and now - prev.get("t", 0) < 0.45:
        cal["last_ok"] = True
        cal["last_dx"], cal["last_dy"] = dx, dy
        cal["last_l"], cal["last_r"] = cl, cr
        return cal_status()
    cal["zones"][z] = cal["zones"].get(z, 0) + 1
    cal["samples"].append({"dx": dx, "dy": dy, "n": len(cl), "t": now, "zone": z})
    cal["good"] = len(cal["samples"])
    cal["next_zone"] = next_zone()
    zneed = sum(1 for k in REQUIRED_ZONES if cal["zones"].get(k))
    cal["last_ok"] = True
    cal["last_dx"], cal["last_dy"] = dx, dy
    cal["last_l"], cal["last_r"] = cl, cr
    cal["last_t"] = now
    cal["msg"] = "locked %s  d=%.1f px  %d frames  %d/5 zones" % (z, dx, cal["good"], zneed)
    nxt = cal["next_zone"]
    cal["hint"] = ZONE_HINT.get(nxt, "All five zones have a sample. Press Stop & save, or keep moving.")
    if cal["good"] >= cal["need"] and zneed >= 5:
        try:
            compute_calib()
            cal["running"] = False
            cal["hint"] = "Calibration saved on the NPU. You can go back to live stereo."
        except Exception as exc:
            cal["msg"] = "compute failed: %s" % exc
    return cal_status()


def compute_calib() -> dict:
    samples = cal["samples"]
    if len(samples) < 3:
        raise ValueError("need at least 3 good frames")
    dxs = [s["dx"] for s in samples]
    dys = [s["dy"] for s in samples]
    dx = _median(dxs)
    dy = _median(dys)
    if dx <= 1.0:
        raise ValueError("disparity at 1 m is too small or inverted (%.2f px)" % dx)
    dist = float(cal["distance_mm"])
    f_px = dx * dist / BASELINE_MM
    result = {
        "left": "cam0",
        "right": "cam1",
        "baseline_mm": BASELINE_MM,
        "distance_mm": dist,
        "cols": cal["cols"],
        "rows": cal["rows"],
        "square_mm": cal["square_mm"],
        "d_at_1m": dx,
        "dy": dy,
        "f_px": f_px,
        "samples": len(samples),
        "w": W,
        "h": H,
    }
    save_calib(result)
    cal["msg"] = "saved f=%.1f px  d@1m=%.2f  dy=%.2f" % (f_px, dx, dy)
    return result


def _gray1920(nv12):
    return bytes(nv12[: CAM_W * CAM_H])


def find_board_cv(gray, cols: int, rows: int):
    """On-board lock on 1920 Y. OpenCV first, numpy saddles as fallback."""
    try:
        import numpy as np
    except Exception:
        return find_chessboard(gray, cols, rows)
    img = np.frombuffer(gray, dtype=np.uint8).reshape(CAM_H, CAM_W)
    try:
        import cv2
    except Exception:
        cv2 = None
    sizes = ((cols, rows), (rows, cols))
    if cv2 is not None:
        flags = (
            cv2.CALIB_CB_ADAPTIVE_THRESH
            | cv2.CALIB_CB_NORMALIZE_IMAGE
            | cv2.CALIB_CB_FAST_CHECK
        )
        work = img
        if img.shape[1] > 1400:
            work = cv2.resize(img, (960, 600), interpolation=cv2.INTER_AREA)
        try:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            work = clahe.apply(work)
        except Exception:
            pass
        scale = img.shape[1] / float(work.shape[1])
        for c, r in sizes[:2]:
            ok, corners = cv2.findChessboardCorners(work, (c, r), flags)
            if not ok and hasattr(cv2, "findChessboardCornersSB"):
                ok, corners = cv2.findChessboardCornersSB(
                    work, (c, r), cv2.CALIB_CB_NORMALIZE_IMAGE
                )
            if ok and corners is not None:
                cv2.cornerSubPix(
                    work,
                    corners,
                    (5, 5),
                    (-1, -1),
                    (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.03),
                )
                pts = corners.reshape(-1, 2) * scale
                return [(float(p[0]), float(p[1])) for p in pts]
    return find_board_np(img, cols, rows)


def find_board_np(img, cols: int, rows: int):
    """Vectorized saddles on a 960-wide view. Accepts a partial grid."""
    try:
        import numpy as np
    except Exception:
        return None
    small = img[::2, ::2]
    sh, sw = small.shape
    r = 4
    tl = small[:-r, :-r].astype(np.int16)
    tr = small[:-r, r:].astype(np.int16)
    bl = small[r:, :-r].astype(np.int16)
    br = small[r:, r:].astype(np.int16)
    h = min(tl.shape[0], tr.shape[0], bl.shape[0], br.shape[0])
    w = min(tl.shape[1], tr.shape[1], bl.shape[1], br.shape[1])
    tl, tr, bl, br = tl[:h, :w], tr[:h, :w], bl[:h, :w], br[:h, :w]
    diag = np.abs((tl + br) - (tr + bl))
    same = np.abs(tl - br) + np.abs(tr - bl)
    score = diag.astype(np.int32) - same
    dark = (tl < 128) & (br < 128) & (tr > 128) & (bl > 128)
    light = (tl > 128) & (br > 128) & (tr < 128) & (bl < 128)
    ys, xs = np.where((diag > 28) & (same < 50) & (score > 8) & (dark | light))
    if len(xs) < 12:
        return None
    order = np.argsort(score[ys, xs])[::-1]
    pts = []
    for i in order[:220]:
        x, y = int(xs[i]), int(ys[i])
        if any((x - px) * (x - px) + (y - py) * (y - py) < 36 for px, py in pts):
            continue
        pts.append((x, y))
    if len(pts) < 12:
        return None
    # scale back to 1920
    out = [(p[0] * 2.0 + r, p[1] * 2.0 + r) for p in pts[: max(cols * rows, 24)]]
    return out


def cal_loop() -> None:
    """Checkerboard lock runs on the board from the live 1920 NV12 Y plane."""
    while True:
        if not cal["running"]:
            if not cal.get("result"):
                cal["hint"] = "Live preview is on. Press Start, then move the device around the board."
            time.sleep(0.08)
            continue
        left, right = eyes()
        if not left or not right:
            cal["hint"] = "Waiting for both cameras…"
            time.sleep(0.03)
            continue
        cl = find_board_cv(_gray1920(left), cal["cols"], cal["rows"]) or []
        cr = find_board_cv(_gray1920(right), cal["cols"], cal["rows"]) or []
        if cl and cr:
            accept_sample(cl, cr)
        elif time.time() - float(cal.get("last_t") or 0) > 1.4:
            cal["last_ok"] = False
            cal["hint"] = (
                "NPU is searching the whole frame. Hold the 11×8 board upright, "
                "facing both cameras, at 1.00 m, filling most of both images — not on the floor."
            )
        time.sleep(0.05)


class TurboEnc:
    def __init__(self, w: int, h: int, q: int = 70) -> None:
        self.w, self.h, self.q = w, h, q
        lib = CDLL(TJ)
        lib.tjInitCompress.restype = c_void_p
        lib.tjCompressFromYUVPlanes.restype = c_int
        lib.tjCompressFromYUVPlanes.argtypes = [
            c_void_p,
            POINTER(POINTER(c_ubyte)),
            c_int,
            POINTER(c_int),
            c_int,
            c_int,
            POINTER(c_void_p),
            POINTER(c_ulong),
            c_int,
            c_int,
        ]
        lib.tjDestroy.argtypes = [c_void_p]
        lib.tjFree.argtypes = [c_void_p]
        self.lib = lib
        self.hnd = lib.tjInitCompress()
        if not self.hnd:
            raise OSError("tjInitCompress")
        self.lk = threading.Lock()
        uvn = (w * h) // 4
        self._u = bytearray(uvn)
        self._v = bytearray(uvn)
        self._u_c = (c_ubyte * uvn).from_buffer(self._u)
        self._v_c = (c_ubyte * uvn).from_buffer(self._v)

    def encode(self, nv12) -> bytes:
        w, h = self.w, self.h
        ysz = w * h
        if isinstance(nv12, bytearray):
            src = nv12
        elif isinstance(nv12, memoryview) and not nv12.readonly:
            src = nv12
        else:
            src = bytearray(nv12)
        y = (c_ubyte * ysz).from_buffer(src)
        uv_len = ysz // 2
        try:
            import numpy as np

            uv = np.frombuffer(src, dtype=np.uint8, count=uv_len, offset=ysz)
            np.frombuffer(self._u, dtype=np.uint8)[:] = uv[0::2]
            np.frombuffer(self._v, dtype=np.uint8)[:] = uv[1::2]
            u = self._u_c
            v = self._v_c
        except Exception:
            uv = src[ysz : ysz + uv_len]
            self._u[:] = uv[0::2]
            self._v[:] = uv[1::2]
            u = self._u_c
            v = self._v_c
        planes = (POINTER(c_ubyte) * 3)(
            cast(y, POINTER(c_ubyte)),
            cast(u, POINTER(c_ubyte)),
            cast(v, POINTER(c_ubyte)),
        )
        strides = (c_int * 3)(w, w // 2, w // 2)
        jpeg_buf = c_void_p()
        jpeg_size = c_ulong(0)
        with self.lk:
            rc = self.lib.tjCompressFromYUVPlanes(
                self.hnd,
                planes,
                w,
                strides,
                h,
                2,
                byref(jpeg_buf),
                byref(jpeg_size),
                self.q,
                2048,
            )
        if rc != 0 or not jpeg_buf.value:
            return b""
        try:
            return string_at(jpeg_buf, jpeg_size.value)
        finally:
            self.lib.tjFree(jpeg_buf)


class FfmpegEnc:
    def __init__(self, w: int, h: int) -> None:
        self.proc = subprocess.Popen(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-fflags", "nobuffer", "-flags", "low_delay",
                "-f", "rawvideo", "-pix_fmt", "nv12",
                "-video_size", f"{w}x{h}", "-framerate", "30", "-i", "-",
                "-q:v", "8", "-f", "mjpeg", "-flush_packets", "1", "pipe:1",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        self.jpg = b""
        self.pending = None
        self.ev = threading.Event()
        self.lk = threading.Lock()
        threading.Thread(target=self._out, daemon=True).start()
        threading.Thread(target=self._in, daemon=True).start()

    def _out(self) -> None:
        buf = b""
        assert self.proc.stdout is not None
        while True:
            chunk = self.proc.stdout.read(8192)
            if not chunk:
                break
            buf += chunk
            while True:
                a = buf.find(b"\xff\xd8")
                bpos = buf.find(b"\xff\xd9")
                if a < 0 or bpos < 0 or bpos < a:
                    if a > 0:
                        buf = buf[a:]
                    if len(buf) > 2_000_000:
                        buf = buf[-200000:]
                    break
                jpg = buf[a : bpos + 2]
                buf = buf[bpos + 2 :]
                with self.lk:
                    self.jpg = jpg

    def _in(self) -> None:
        while True:
            self.ev.wait()
            self.ev.clear()
            with self.lk:
                raw = self.pending
                self.pending = None
            if not raw:
                continue
            try:
                assert self.proc.stdin is not None
                self.proc.stdin.write(raw)
                self.proc.stdin.flush()
            except Exception:
                return

    def push(self, raw) -> None:
        with self.lk:
            self.pending = bytes(raw) if not isinstance(raw, (bytes, bytearray)) else raw
        self.ev.set()

    def get(self) -> bytes:
        with self.lk:
            return self.jpg


def make_enc(w: int, h: int, q: int = 70):
    try:
        return TurboEnc(w, h, q)
    except Exception:
        return FfmpegEnc(w, h)


def scale_nv12(src, sw: int, sh: int, dw: int, dh: int) -> bytearray:
    xs, ys = sw // dw, sh // dh
    out = bytearray(dw * dh * 3 // 2)
    ysrc = memoryview(src)[: sw * sh]
    d = 0
    for j in range(0, sh, ys):
        out[d : d + dw] = ysrc[j * sw : (j + 1) * sw : xs]
        d += dw
    uv_in = memoryview(src)[sw * sh :].cast("H")
    uv_out = memoryview(out)[dw * dh :].cast("H")
    suw, duw = sw // 2, dw // 2
    od = 0
    for j in range(0, sh // 2, ys):
        uv_out[od : od + duw] = uv_in[j * suw : (j + 1) * suw : xs]
        od += duw
    return out


def _ps_has(name: str) -> bool:
    try:
        out = subprocess.check_output(["ps"], timeout=2)
        blob = out if isinstance(out, str) else out.decode("utf-8", "ignore")
        return name in blob
    except Exception:
        return False


def _isp_blocks_on() -> bool:
    try:
        txt = open("/proc/rkisp-vir0", "r").read()
    except Exception:
        return True
    return "AWBGAIN    ON" in txt


def _start_3a(env: dict) -> None:
    log = open("/userdata/rkaiq.log", "ab")
    subprocess.Popen(
        ["/oem/usr/bin/rkaiq_3A_server", "--silent"],
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        env=env,
        start_new_session=True,
    )
    shared["_isp_started_t"] = time.monotonic()


def ensure_companions() -> None:
    """Keep RKAIQ 3A and the IMU HUD alive. Reattach 3A if ISP blocks dropped."""
    env = os.environ.copy()
    env["PATH"] = "/oem/usr/bin:/usr/sbin:/sbin:/usr/bin:/bin:" + env.get("PATH", "")
    env["LD_LIBRARY_PATH"] = "/oem/usr/lib:/oem/lib:" + env.get("LD_LIBRARY_PATH", "")
    if not _ps_has("rkaiq_3A_server"):
        try:
            _start_3a(env)
            print("isp: started rkaiq_3A_server", flush=True)
        except Exception as exc:
            print("isp start", exc, flush=True)
    elif (
        shared.get("cam0")
        and shared.get("cam1")
        and not _isp_blocks_on()
        and time.monotonic() - float(shared.get("_isp_started_t") or 0) > 5.0
        and int(shared.get("_isp_kick") or 0) < 2
    ):
        try:
            subprocess.call(
                ["killall", "rkaiq_3A_server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.5)
            _start_3a(env)
            shared["_isp_kick"] = int(shared.get("_isp_kick") or 0) + 1
            print("isp: reattached rkaiq_3A_server", flush=True)
        except Exception as exc:
            print("isp reattach", exc, flush=True)
    elif _isp_blocks_on():
        shared["_isp_kick"] = 0
    if not _ps_has("ego_imu_hud"):
        try:
            env["TZ"] = "UTC-2"
            log = open("/tmp/ego-imu.log", "ab")
            subprocess.Popen(
                ["/usr/bin/python3", "/userdata/ego_imu_hud.py"],
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
            )
            print("imu: started ego_imu_hud", flush=True)
        except Exception as exc:
            print("imu start", exc, flush=True)


def companion_loop() -> None:
    while True:
        try:
            ensure_companions()
        except Exception as exc:
            print("companion", exc, flush=True)
        time.sleep(3)


def grab(dev: str, key: str) -> None:
    fifo = f"/tmp/{key}.nv12"
    try:
        os.remove(fifo)
    except OSError:
        pass
    os.mkfifo(fifo)
    ring = [bytearray(CAM_FRAME) for _ in range(5)]
    slot = 0
    # Two 1920x1200 NV12 streams saturate memory bandwidth long before the
    # encoders keep up, so ask for the rate we can actually deliver.
    rates = [CAP_FPS, 30]
    ri = 0
    while True:
        cmd = (
            f"v4l2-ctl -d {dev} --set-fmt-video=width={CAM_W},height={CAM_H},pixelformat=NV12 "
            f"--set-parm={rates[ri]} --stream-mmap=4 --stream-to={fifo} --stream-poll"
        )
        proc = subprocess.Popen(["sh", "-c", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        frames = 0
        time.sleep(0.3)
        try:
            if proc.poll() is None:
                with open(fifo, "rb") as fh:
                    while proc.poll() is None:
                        mv = memoryview(ring[slot])
                        got = 0
                        while got < CAM_FRAME:
                            n = fh.readinto(mv[got:])
                            if not n:
                                got = 0
                                break
                            got += n
                        if got != CAM_FRAME:
                            break
                        shared[key] = ring[slot]
                        shared[key + "_t"] = time.monotonic()
                        slot = (slot + 1) % 5
                        frames += 1
        finally:
            proc.kill()
        if not frames and ri + 1 < len(rates):
            ri += 1
            print("grab %s: %d fps refused, using %d" % (dev, rates[ri - 1], rates[ri]), flush=True)
        time.sleep(0.2)


def _c_u8(buf):
    if isinstance(buf, bytearray):
        return (c_ubyte * len(buf)).from_buffer(buf)
    mv = memoryview(buf)
    if mv.readonly:
        return (c_ubyte * len(buf)).from_buffer_copy(buf)
    return (c_ubyte * len(buf)).from_buffer(mv)


def y_down(y, src_w: int = 0, src_h: int = 0) -> bytearray:
    sw = src_w or (CAM_W if len(y) >= CAM_W * CAM_H else W)
    sh = src_h or (CAM_H if len(y) >= CAM_W * CAM_H else H)
    if sw == BW and sh == BH:
        return bytearray(y[: BW * BH])
    if _cv_ok():
        import cv2
        import numpy as np

        img = np.frombuffer(y, dtype=np.uint8, count=sw * sh).reshape(sh, sw)
        small = cv2.resize(img, (BW, BH), interpolation=cv2.INTER_AREA)
        return bytearray(np.ascontiguousarray(small).tobytes())
    try:
        import numpy as np

        img = np.frombuffer(y, dtype=np.uint8, count=sw * sh).reshape(sh, sw)
        xs, ys = max(1, sw // BW), max(1, sh // BH)
        small = np.ascontiguousarray(img[::ys, ::xs][:BH, :BW])
        return bytearray(small.tobytes())
    except Exception:
        out = bytearray(BW * BH)
        xs, ys = max(1, sw // BW), max(1, sh // BH)
        mv = memoryview(y)
        dst = 0
        for j in range(0, BH * ys, ys):
            row = mv[j * sw : (j + 1) * sw]
            out[dst : dst + BW] = row[::xs][:BW]
            dst += BW
        return out


def grid_y(nv12) -> bytearray:
    """1920x1200 NV12 → BWxBH luma for matching. Decimate then box-average."""
    if not _cv_ok():
        return y_down(nv12[: CAM_W * CAM_H], CAM_W, CAM_H)
    import cv2
    import numpy as np

    img = np.frombuffer(nv12, dtype=np.uint8, count=CAM_W * CAM_H).reshape(CAM_H, CAM_W)
    small = cv2.resize(img, (BW, BH), interpolation=cv2.INTER_AREA)
    # The sensors read out upside down; matching needs upright rows and a
    # left-to-right disparity axis.
    small = np.ascontiguousarray(small[::-1, ::-1])
    # Flat walls and blown highlights carry no matchable detail without this.
    clahe = shared.get("_clahe")
    if clahe is None:
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        shared["_clahe"] = clahe
    return bytearray(np.ascontiguousarray(clahe.apply(small)).tobytes())


def _quad_basis(x, y):
    import numpy as np

    return np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], axis=-1)


def fit_align(left, right) -> str:
    """Fit the vertical epipolar error across the frame from ORB matches.

    A quadratic surface absorbs offset, roll and the lens distortion that a
    single shift cannot, and only the vertical axis is touched so disparity
    stays valid. A fit is installed only when it beats the one in use.
    """
    import cv2
    import numpy as np

    # Fit at 320x200. The surface is smooth, and the 640 grid made the
    # pixel residuals look like a wild warp.
    fw, fh = min(320, left.shape[1]), min(200, left.shape[0])
    if left.shape[1] != fw:
        left = cv2.resize(left, (fw, fh), interpolation=cv2.INTER_AREA)
        right = cv2.resize(right, (fw, fh), interpolation=cv2.INTER_AREA)
    nd_fit = max(8, int(round(ND * fw / float(BW))))
    orb = cv2.ORB_create(nfeatures=1500, scaleFactor=1.25, nlevels=5, fastThreshold=6)
    k1, d1 = orb.detectAndCompute(left, None)
    k2, d2 = orb.detectAndCompute(right, None)
    if d1 is None or d2 is None or len(k1) < 40 or len(k2) < 40:
        return "few features"
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    pairs = bf.match(d1, d2)
    if len(pairs) < 40:
        return "few matches"
    p1 = np.float32([k1[m.queryIdx].pt for m in pairs])
    p2 = np.float32([k2[m.trainIdx].pt for m in pairs])
    # Disparity must be positive and inside the search range.
    ok = (p1[:, 0] - p2[:, 0] > 0.5) & (p1[:, 0] - p2[:, 0] < nd_fit * 1.5)
    ok &= np.abs(p1[:, 1] - p2[:, 1]) < fh * 0.12
    p1, p2 = p1[ok], p2[ok]
    if len(p1) < 20:
        return "few pairs %d" % len(p1)
    # The rig is rigid, so pairs seen in different scenes all constrain the
    # same surface. Pooling them makes the fit far steadier than one frame.
    buf = (shared.get("align_pts") or [])[-11:] + [(p1, p2)]
    shared["align_pts"] = buf
    P1 = np.concatenate([a for a, _ in buf])
    P2 = np.concatenate([b for _, b in buf])
    if len(P1) < 80:
        return "collecting %d" % len(P1)
    r = (P1[:, 1] - P2[:, 1]).astype(np.float64)
    xn, yn = P1[:, 0] / float(fw), P1[:, 1] / float(fh)
    A = np.stack([np.ones_like(r), xn, yn], axis=1)
    keep = np.ones(len(r), dtype=bool)
    coef = None
    for thr in (6.0, 3.0, 1.5, 1.0, 0.7):
        sol, *_ = np.linalg.lstsq(A[keep], r[keep], rcond=None)
        res = np.abs(A @ sol - r)
        nxt = res <= thr
        if int(nxt.sum()) < 30:
            break
        coef, keep = sol, nxt
    if coef is None:
        return "no consensus"
    inl = int(keep.sum())
    after = float(np.median(np.abs(A[keep] @ coef - r[keep])))
    before = float(np.median(np.abs(r)))
    best = shared.get("align_res")
    if best is not None and after >= best:
        return "ok %.2f" % best
    X, Y = np.meshgrid(np.arange(BW, dtype=np.float32), np.arange(BH, dtype=np.float32))
    shift = (coef[0] + coef[1] * (X / float(BW)) + coef[2] * (Y / float(BH)))
    shift = shift * (float(BH) / float(fh))
    shift = np.clip(shift, -12.0, 12.0)
    shared["align"] = (
        np.ascontiguousarray(X),
        np.ascontiguousarray((Y - shift).astype(np.float32)),
    )
    shared["align_res"] = after
    shared["align_px"] = "%.2f->%.2f" % (before, after)
    shared["align_n"] = inl
    return "ok"


def apply_align(R) -> bytearray:
    maps = shared.get("align")
    if maps is None:
        return R
    try:
        import cv2
        import numpy as np

        img = np.frombuffer(R, dtype=np.uint8, count=BW * BH).reshape(BH, BW)
        out = cv2.remap(img, maps[0], maps[1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return bytearray(np.ascontiguousarray(out).tobytes())
    except Exception:
        return R


def _box_sum(a, k: int = 5):
    """Separable box sum. `a` is 2D int16/int32."""
    import numpy as np

    r = k // 2
    p = np.pad(a, ((r, r), (r, r)), mode="edge")
    z = np.zeros((p.shape[0], 1), dtype=np.int32)
    c = np.concatenate([z, np.cumsum(p, axis=1, dtype=np.int32)], axis=1)
    h = c[:, k:] - c[:, :-k]
    z = np.zeros((1, h.shape[1]), dtype=np.int32)
    c = np.concatenate([z, np.cumsum(h, axis=0, dtype=np.int32)], axis=0)
    return c[k:] - c[:-k]


def _box_mean(a, k: int):
    """Separable box mean for float32 maps."""
    import numpy as np

    r = k // 2
    p = np.pad(a.astype(np.float32, copy=False), ((r, r), (r, r)), mode="edge")
    z = np.zeros((p.shape[0], 1), dtype=np.float32)
    c = np.concatenate([z, np.cumsum(p, axis=1, dtype=np.float32)], axis=1)
    h = c[:, k:] - c[:, :-k]
    z = np.zeros((1, h.shape[1]), dtype=np.float32)
    c = np.concatenate([z, np.cumsum(h, axis=0, dtype=np.float32)], axis=0)
    return (c[k:] - c[:-k]) / float(k * k)


def _cv_matcher(nd: int):
    """Semi-global matcher for dense output, block matcher when CPU is short."""
    global _CV_BM
    import cv2

    algo = shared.get("algo") or "sgbm"
    nd = max(16, (nd + 15) // 16 * 16)
    key = (nd, algo)
    if _CV_BM is not None and shared.get("_bm_key") == key:
        return _CV_BM
    if algo == "sgbm":
        bs = 3
        m = cv2.StereoSGBM_create(
            minDisparity=0,
            numDisparities=nd,
            blockSize=bs,
            P1=8 * bs * bs,
            P2=32 * bs * bs,
            disp12MaxDiff=2,
            uniquenessRatio=4,
            speckleWindowSize=0,
            speckleRange=0,
            preFilterCap=31,
            mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY,
        )
    else:
        m = cv2.StereoBM_create(numDisparities=nd, blockSize=15)
        m.setPreFilterType(cv2.STEREO_BM_PREFILTER_XSOBEL)
        m.setPreFilterSize(5)
        m.setPreFilterCap(31)
        m.setTextureThreshold(0)
        m.setUniquenessRatio(0)
        m.setSpeckleWindowSize(0)
        m.setSpeckleRange(0)
        m.setDisp12MaxDiff(-1)
        m.setMinDisparity(0)
    _CV_BM = m
    shared["_bm_key"] = key
    return m


def _disp16(left, right, nd: int):
    """Raw 1/16 px disparity, speckles removed."""
    import cv2

    t = time.monotonic()
    # Without padding the matcher writes off the first ND columns wholesale,
    # even though far detail there is visible to both eyes. Give it room to
    # evaluate the full range and cut the padding back off afterwards.
    pad = max(16, (nd + 15) // 16 * 16)
    lp = cv2.copyMakeBorder(left, 0, 0, pad, 0, cv2.BORDER_REPLICATE)
    rp = cv2.copyMakeBorder(right, 0, 0, pad, 0, cv2.BORDER_REPLICATE)
    raw = _cv_matcher(nd).compute(lp, rp)[:, pad:]
    shared["sgbm_ms"] = (time.monotonic() - t) * 1000
    try:
        cv2.filterSpeckles(raw, 0, 32, 48)
    except Exception:
        pass
    shared["spk_ms"] = (time.monotonic() - t) * 1000 - shared["sgbm_ms"]
    return raw


def _refine(left, right, d0, nd: int, span: int = 2, win: int = 3):
    """Search a few disparities around an estimate, at this grid resolution.

    The global pass stays coarse. This local search is what puts centimetre
    edges back: a 3-pixel window follows a finger instead of averaging it
    into the palm, and strong image edges are allowed to move off the
    estimate with less evidence than a flat wall.
    """
    import cv2
    import numpy as np

    h, w = left.shape
    grid = shared.get("_ref_grid")
    if grid is None or grid[0].shape != (h, w):
        xs = np.broadcast_to(np.arange(w, dtype=np.float32)[None, :], (h, w))
        ys = np.broadcast_to(np.arange(h, dtype=np.float32)[:, None], (h, w))
        grid = (
            np.ascontiguousarray(xs),
            np.ascontiguousarray(ys),
            np.ascontiguousarray(xs.astype(np.int16)),
        )
        shared["_ref_grid"] = grid
    mx = cv2.subtract(grid[0], d0.astype(np.float32))
    rw = cv2.remap(right, mx, grid[1], cv2.INTER_NEAREST, borderMode=cv2.BORDER_REPLICATE)
    rp = cv2.copyMakeBorder(rw, 0, 0, span, span, cv2.BORDER_REPLICATE)
    n = 2 * span + 1
    stack = shared.get("_ref_stack")
    if stack is None or stack.shape != (n, h, w):
        stack = np.empty((n, h, w), dtype=np.uint16)
        shared["_ref_stack"] = stack
    for i, k in enumerate(range(-span, span + 1)):
        sh = np.ascontiguousarray(rp[:, span - k : span - k + w])
        cv2.boxFilter(
            cv2.absdiff(left, sh), cv2.CV_16U, (win, win), dst=stack[i], normalize=False
        )
    take = np.argmin(stack, axis=0).astype(np.int16)
    cost = np.min(stack, axis=0)
    # Flat walls match every candidate equally, so they stay on the estimate.
    # Image edges (a finger, a 1 cm part) are allowed to move with less gain.
    gain = cv2.subtract(stack[span], cost)
    edge = cv2.convertScaleAbs(cv2.Sobel(left, cv2.CV_16S, 1, 0, ksize=3))
    need = np.where(edge > 24, win * win, win * win * 3)
    off = np.where(gain > need, take - np.int16(span), np.int16(0))
    pick = np.clip(d0 + off, 0, nd - 1)
    good = (cost <= win * win * 24) | (grid[2] < pick)
    return np.where(good, pick, np.int16(0)).astype(np.uint8)


def _fill_small(d, nd: int):
    """Close pinholes from a 3x3 neighbourhood. Do not smear valid edges."""
    import cv2
    import numpy as np

    valid = d >= 1
    if valid.all():
        return d
    num = cv2.boxFilter((d * valid).astype(np.float32), -1, (3, 3), normalize=False)
    den = cv2.boxFilter(valid.astype(np.float32), -1, (3, 3), normalize=False)
    fill = num / np.maximum(den, 1e-6)
    return np.where(valid, d, np.clip(np.rint(fill), 1, nd - 1).astype(np.uint8))


def _densify(d, nd: int = 0):
    """Fill unmatched pixels from a normalized pyramid of the valid ones.

    Coarse levels cover both small dropouts and the wide strip where the eyes
    do not overlap, at a fraction of the cost of iterated dilation.
    """
    import cv2
    import numpy as np

    nd = nd or ND
    bh, bw = d.shape
    valid = d >= 1
    inv = ~valid
    if not valid.any():
        return d
    if inv.any():
        num = (d * valid).astype(np.float32)
        den = valid.astype(np.float32)
        pyr = []
        for div in (4, 8, 16, 32, 64):
            w, h = max(2, bw // div), max(2, bh // div)
            pyr.append(
                (
                    cv2.resize(num, (w, h), interpolation=cv2.INTER_AREA),
                    cv2.resize(den, (w, h), interpolation=cv2.INTER_AREA),
                )
            )
        cur = None
        for n, m in reversed(pyr):
            got = m > 1e-6
            v = n / np.maximum(m, 1e-6)
            if cur is None:
                cur = np.where(got, v, 0.0)
            else:
                up = cv2.resize(cur, (m.shape[1], m.shape[0]), interpolation=cv2.INTER_LINEAR)
                cur = np.where(got, v, up)
        fill = cv2.resize(cur, (bw, bh), interpolation=cv2.INTER_LINEAR)
        d = np.where(inv, np.clip(fill, 1, nd - 1).astype(np.uint8), d)
    return cv2.medianBlur(d, 3)


def _fill_holes(disp):
    """numpy-only gap fill for boards without OpenCV."""
    import numpy as np

    z = disp.astype(np.float32)
    for k, need in ((5, 0.18), (9, 0.22)):
        w = (disp >= 1).astype(np.float32)
        if float(w.sum()) < 80:
            return
        sm = _box_mean(z * w, k)
        sw = _box_mean(w, k)
        miss = (disp < 1) & (sw > need)
        z = np.where(miss, sm / np.maximum(sw, 1e-4), z)
        disp[:] = np.clip(np.rint(z), 0, ND - 1).astype(np.uint8)
        disp[z < 0.75] = 0


def stereo_bm(L, R) -> bytearray:
    try:
        import numpy as np

        left = np.frombuffer(L, dtype=np.uint8, count=BW * BH).reshape(BH, BW)
        right = np.frombuffer(R, dtype=np.uint8, count=BW * BH).reshape(BH, BW)
        if _cv_ok():
            import cv2

            cw, chh = max(80, BW // 4), max(50, BH // 4)
            ndc = max(16, ((ND // 4) + 15) // 16 * 16)
            lc = cv2.resize(left, (cw, chh), interpolation=cv2.INTER_AREA)
            rc = cv2.resize(right, (cw, chh), interpolation=cv2.INTER_AREA)
            swap = shared.get("swap")
            if swap is None:
                a = _disp16(lc, rc, ndc)
                b = _disp16(rc, lc, ndc)
                fa = float(np.count_nonzero(a >= 16)) / float(a.size)
                fb = float(np.count_nonzero(b >= 16)) / float(b.size)
                swap = fb > fa * 1.25
                shared["swap"] = swap
                shared["orient_win"] = "%.2f/%.2f" % (fa, fb)
                raw = b if swap else a
            elif swap:
                raw = _disp16(rc, lc, ndc)
            else:
                raw = _disp16(lc, rc, ndc)
            dc = np.clip(raw >> 4, 0, ndc - 1).astype(np.uint8)
            dc[raw < 16] = 0
            shared["pts"] = int(np.count_nonzero(dc)) * (BW * BH // max(1, cw * chh))
            t_f = time.monotonic()
            dc = _densify(dc, ndc)
            mw, mh = max(160, BW // 2), max(100, BH // 2)
            lm = cv2.resize(left, (mw, mh), interpolation=cv2.INTER_AREA)
            rm = cv2.resize(right, (mw, mh), interpolation=cv2.INTER_AREA)
            d1 = cv2.resize(dc, (mw, mh), interpolation=cv2.INTER_LINEAR).astype(np.int16)
            d1 = (d1 * (mw // max(1, cw))).astype(np.int16)
            d1 = _refine(lm, rm, d1, max(ND // 2, 16), span=2, win=3)
            d0 = cv2.resize(d1, (BW, BH), interpolation=cv2.INTER_LINEAR).astype(np.int16)
            d0 = (d0 * (BW // max(1, mw))).astype(np.int16)
            d = _refine(left, right, d0, ND, span=1, win=3)
            shared["ref_ms"] = (time.monotonic() - t_f) * 1000
            shared["hit"] = int(np.count_nonzero(d))
            t_f = time.monotonic()
            d = _fill_small(d, ND)
            # Blend only still surfaces. A moving hand must keep its outline.
            prev = shared.get("_prev_d")
            if prev is not None and prev.shape == d.shape:
                calm = cv2.absdiff(d, prev) < 2
                d = np.where(calm, ((d.astype(np.uint16) + prev) >> 1).astype(np.uint8), d)
            shared["_prev_d"] = d
            shared["dens_ms"] = (time.monotonic() - t_f) * 1000
            # Back to sensor orientation; the page flips both views for display.
            d = np.ascontiguousarray(d[::-1, ::-1])
            shared["bm_kind"] = shared.get("algo") or "sgbm"
            return bytearray(d.tobytes())
        if NATIVE is not None:
            raw = bytearray(BW * BH)
            NATIVE.ego_stereo_bm(_c_u8(L), _c_u8(R), _c_u8(raw), BW, BH, ND, TH)
            disp = np.frombuffer(raw, dtype=np.uint8, count=BW * BH).reshape(BH, BW).copy()
            _fill_holes(disp)
            shared["bm_kind"] = "native"
            return bytearray(np.ascontiguousarray(disp).tobytes())
        best = np.full((BH, BW), 1 << 30, dtype=np.int32)
        disp = np.zeros((BH, BW), dtype=np.uint8)
        win = 7
        area = win * win
        for d in range(1, ND):
            sad = np.abs(
                left[:, d:].astype(np.int16) - right[:, : BW - d].astype(np.int16)
            )
            cost = _box_sum(sad, win) // area
            better = cost < best[:, d:]
            best[:, d:][better] = cost[better]
            disp[:, d:][better] = d
        disp[best >= TH] = 0
        _fill_holes(disp)
        shared["bm_kind"] = "np"
        return bytearray(np.ascontiguousarray(disp).tobytes())
    except Exception as exc:
        if shared.get("_bm_err") != type(exc).__name__:
            shared["_bm_err"] = type(exc).__name__
            print("stereo_bm", type(exc).__name__, exc, flush=True)
        disp = bytearray(BW * BH)
        mL = memoryview(L)
        mR = memoryview(R)
        for y in range(BH):
            row = y * BW
            for x in range(ND, BW):
                p = row + x
                lv = mL[p]
                best = 1 << 30
                bd = 0
                d = 0
                while d < ND:
                    s = lv - mR[p - d]
                    if s < 0:
                        s = -s
                    if s < best:
                        best = s
                        bd = d
                    d += 1
                if best < TH:
                    disp[p] = bd
        shared["bm_kind"] = "py"
        return disp


def paint_nv12(src, disp, out: bytearray) -> bytearray:
    out[:] = src
    if NATIVE is not None:
        NATIVE.ego_paint_nv12(
            _c_u8(out), W, H, _c_u8(disp), BW, BH, LUT_Y, LUT_U, LUT_V, ND
        )
        return out
    y = memoryview(out)
    uv = memoryview(out)[YSIZE:]
    uw = W // 2
    xs, ys = W // BW, H // BH
    for j in range(BH):
        for i in range(BW):
            d = disp[j * BW + i]
            if d < 2:
                continue
            yy, uu, vv = LUT[min(255, d * SCALE)]
            y0 = j * ys * W + i * xs
            y[y0] = (y[y0] * 2 + yy) // 3
            urow = (j * ys // 2) * uw + (i * xs // 2)
            p = urow * 2
            uv[p] = uu
            uv[p + 1] = vv
    return out


def _blur5(z):
    import numpy as np

    k = np.array([1.0, 4.0, 6.0, 4.0, 1.0], dtype=np.float32) / 16.0
    p = np.pad(z, ((0, 0), (2, 2)), mode="edge")
    h = k[0] * p[:, 0:-4] + k[1] * p[:, 1:-3] + k[2] * p[:, 2:-2] + k[3] * p[:, 3:-1] + k[4] * p[:, 4:]
    p = np.pad(h, ((2, 2), (0, 0)), mode="edge")
    return k[0] * p[0:-4] + k[1] * p[1:-3] + k[2] * p[2:-2] + k[3] * p[3:-1] + k[4] * p[4:]


def _up2(src):
    """2x bilinear upsample."""
    import numpy as np

    right = np.empty_like(src)
    right[:, :-1] = src[:, 1:]
    right[:, -1] = src[:, -1]
    h = np.empty((src.shape[0], src.shape[1] * 2), dtype=src.dtype)
    h[:, 0::2] = src
    h[:, 1::2] = (src + right) * 0.5
    down = np.empty_like(h)
    down[:-1] = h[1:]
    down[-1] = h[-1]
    out = np.empty((src.shape[0] * 2, src.shape[1] * 2), dtype=src.dtype)
    out[0::2] = h
    out[1::2] = (h + down) * 0.5
    return out


def _up3(src):
    """3x bilinear upsample."""
    import numpy as np

    right = np.empty_like(src)
    right[:, :-1] = src[:, 1:]
    right[:, -1] = src[:, -1]
    h = np.empty((src.shape[0], src.shape[1] * 3), dtype=src.dtype)
    h[:, 0::3] = src
    h[:, 1::3] = (src * 2.0 + right) / 3.0
    h[:, 2::3] = (src + right * 2.0) / 3.0
    down = np.empty_like(h)
    down[:-1] = h[1:]
    down[-1] = h[-1]
    out = np.empty((src.shape[0] * 3, src.shape[1] * 3), dtype=src.dtype)
    out[0::3] = h
    out[1::3] = (h * 2.0 + down) / 3.0
    out[2::3] = (h + down * 2.0) / 3.0
    return out


def _up_to(src, dw: int, dh: int):
    sh, sw = src.shape
    if sh == dh and sw == dw:
        return src
    if dw == sw * 2 and dh == sh * 2:
        return _up2(src)
    if dw == sw * 3 and dh == sh * 3:
        return _up3(src)
    if dw == sw * 6 and dh == sh * 6:
        return _up3(_up2(src))
    if dw == sw * 12 and dh == sh * 12:
        return _up3(_up2(_up2(src)))
    cur = src
    while cur.shape[1] * 2 <= dw and cur.shape[0] * 2 <= dh:
        cur = _up2(cur)
    while cur.shape[1] * 3 <= dw and cur.shape[0] * 3 <= dh:
        cur = _up3(cur)
    if cur.shape[0] == dh and cur.shape[1] == dw:
        return cur
    return _up2(cur)[:dh, :dw] if cur.shape[0] * 2 >= dh else cur[:dh, :dw]


def render_xyz(disp, left=None) -> bytearray:
    """1920x1200 jet depth map. Disparity is upscaled smoothly, no camera mix."""
    try:
        import numpy as np

        d = np.frombuffer(disp, dtype=np.uint8, count=BW * BH).reshape(BH, BW)
        # Spread the palette over the depth actually present, so the map keeps
        # its full colour range instead of saturating in one band.
        sub = d[::3, ::3]
        lo, hi = (float(x) for x in np.percentile(sub, (2, 98)))
        prev = shared.get("_span")
        if prev:
            lo = prev[0] * 0.8 + lo * 0.2
            hi = prev[1] * 0.8 + hi * 0.2
        shared["_span"] = (lo, hi)
        idx_s = np.clip(
            (d.astype(np.float32) - lo) * (255.0 / max(6.0, hi - lo)), 0, 255
        ).astype(np.uint8)
        cache = shared.get("_heat_lut")
        if cache is None:
            # Disparity already crowds distant detail into a narrow band, so
            # bend the ramp to give the far field usable colour separation.
            g = [min(255, int(round(255.0 * (i / 255.0) ** 0.7))) for i in range(256)]
            lut_y = np.array([[LUT[g[i]][0]] for i in range(256)], dtype=np.uint8)
            lut_u = np.array([[LUT[g[i]][1]] for i in range(256)], dtype=np.uint8)
            lut_v = np.array([[LUT[g[i]][2]] for i in range(256)], dtype=np.uint8)
            shared["_heat_lut"] = (lut_y, lut_u, lut_v)
        else:
            lut_y, lut_u, lut_v = cache
        uw, uh = XW // 2, XH // 2
        buf = shared.get("_heat_nv12")
        nv = shared.get("_heat_np")
        if buf is None or len(buf) != XFRAME or nv is None:
            buf = bytearray(XFRAME)
            nv = np.frombuffer(buf, dtype=np.uint8)
            shared["_heat_nv12"] = buf
            shared["_heat_np"] = nv
        if _cv_ok():
            import cv2

            big = cv2.resize(idx_s, (XW, XH), interpolation=cv2.INTER_CUBIC)
            half = cv2.resize(idx_s, (uw, uh), interpolation=cv2.INTER_CUBIC)
            y = cv2.LUT(big, lut_y)
            u = cv2.LUT(half, lut_u)
            v = cv2.LUT(half, lut_v)
        else:
            big = _up_to(idx_s.astype(np.float32), XW, XH).astype(np.uint8)
            half = big[::2, ::2]
            y = lut_y[big, 0]
            u = lut_u[half, 0]
            v = lut_v[half, 0]
        nv[: XW * XH] = y.reshape(-1)
        uv = nv[XW * XH :].reshape(-1, 2)
        uv[:, 0] = u.reshape(-1)
        uv[:, 1] = v.reshape(-1)
        shared["_heat_err"] = ""
        return buf
    except Exception as exc:
        if not shared.get("_heat_err"):
            print("render_xyz", type(exc).__name__, exc, flush=True)
        shared["_heat_err"] = type(exc).__name__
        out = bytearray(XFRAME)
        y = memoryview(out)
        uv = memoryview(out)[XW * XH :]
        xs, ys = max(1, XW // BW), max(1, XH // BH)
        uw = XW // 2
        for j in range(BH):
            for i in range(BW):
                dv = disp[j * BW + i]
                yy, uu, vv = (16, 128, 128) if dv < 1 else LUT[min(255, dv * SCALE)]
                y0 = j * ys * XW + i * xs
                y[y0 : y0 + xs] = bytes([yy]) * xs
                for r in range(1, ys):
                    y[y0 + r * XW : y0 + r * XW + xs] = y[y0 : y0 + xs]
                up = ((j * ys) // 2) * uw + ((i * xs) // 2)
                uv[up * 2] = uu
                uv[up * 2 + 1] = vv
        return out


def set_stat(**kw) -> None:
    parts = []
    for k, v in kw.items():
        if isinstance(v, float):
            parts.append('"%s":%.2f' % (k, v))
        elif isinstance(v, int):
            parts.append('"%s":%d' % (k, v))
        else:
            parts.append('"%s":"%s"' % (k, v))
    with lock:
        latest["stat"] = ("{" + ",".join(parts) + "}").encode()


def bm_loop(ex) -> None:
    n = 0
    t0 = time.monotonic()
    last_ms = 0.0
    seen = (None, None)
    while True:
        a, b = eyes()
        if not a or not b or (a is seen[0] and b is seen[1]):
            time.sleep(0.003)
            continue
        seen = (a, b)
        t_a = time.monotonic()
        res = cal.get("result") or {}
        L = grid_y(a)
        R = grid_y(b)
        t_down = (time.monotonic() - t_a) * 1000
        # Keep hunting for a better epipolar fit; a scene with more texture
        # than the one at startup gives a sharper result.
        if (
            _cv_ok()
            and float(shared.get("align_res") or 9.9) > 0.25
            and time.monotonic() - float(shared.get("align_t") or 0.0) > 6.0
        ):
            shared["align_t"] = time.monotonic()
            try:
                import numpy as np

                shared["align_msg"] = fit_align(
                    np.frombuffer(L, dtype=np.uint8, count=BW * BH).reshape(BH, BW),
                    np.frombuffer(R, dtype=np.uint8, count=BW * BH).reshape(BH, BW),
                )
            except Exception as exc:
                shared["align_msg"] = type(exc).__name__
        R = apply_align(R)
        t_m = time.monotonic()
        d = stereo_bm(L, R)
        match_ms = (time.monotonic() - t_m) * 1000
        shared["disp"] = d
        last_ms = (time.monotonic() - t_a) * 1000
        slow = shared.get("_slow", 0)
        if (shared.get("algo") or "sgbm") == "sgbm" and _cv_ok():
            if match_ms > 400.0:
                slow += 1
                if slow >= 20:
                    shared["algo"] = "bm"
                    print("stereo: sgbm too slow (%.0f ms), using bm" % match_ms, flush=True)
            else:
                slow = 0
            shared["_slow"] = slow
        n += 1
        now = time.monotonic()
        if now - t0 >= 1.0:
            fps = n / (now - t0)
            n = 0
            t0 = now
            set_stat(
                color_fps=shared.get("color_fps", 0.0),
                depth_fps=fps,
                heat_fps=float(shared.get("heat_fps") or 0.0),
                w=VIEW_W,
                h=VIEW_H,
                xw=XW,
                xh=XH,
                bm_ms=last_ms,
                down_ms=t_down,
                match_ms=match_ms,
                native=1 if NATIVE is not None else 0,
                kind=shared.get("bm_kind") or "",
                swap=1 if shared.get("swap") else 0,
                orient_win=shared.get("orient_win") or "",
                align=shared.get("align_msg") or "",
                align_px=shared.get("align_px") or "",
                align_n=int(shared.get("align_n") or 0),
                sgbm_ms=float(shared.get("sgbm_ms") or 0.0),
                ref_ms=float(shared.get("ref_ms") or 0.0),
                dens_ms=float(shared.get("dens_ms") or 0.0),
                hit=100.0 * float(shared.get("hit") or 0) / float(BW * BH),
                f_px=float(res.get("f_px") or 0.0),
                d_at_1m=float(res.get("d_at_1m") or 0.0),
                heat_err=shared.get("_heat_err") or "",
                bm_err=shared.get("_bm_err") or "",
                heat_ms=float(shared.get("heat_ms") or 0.0),
                fill=100.0 * float(shared.get("pts") or 0) / float(BW * BH),
                grid="%dx%d" % (BW, BH),
                cm50=(float(res.get("f_px") or 1260.0) * 0.01 / 0.50) * (float(BW) / float(CAM_W)),
                trig=1 if shared.get("trig_on") else 0,
            )
        leftover = 0.008 - (time.monotonic() - t_a)
        if leftover > 0:
            time.sleep(leftover)


def heat_loop(ex) -> None:
    last = None
    n = 0
    t0 = time.monotonic()
    while True:
        d = shared.get("disp")
        if not d or d is last:
            time.sleep(0.004)
            continue
        last = d
        t_r = time.monotonic()
        raw = render_xyz(d)
        shared["heat_ms"] = (time.monotonic() - t_r) * 1000
        if isinstance(ex, TurboEnc):
            jpg = ex.encode(raw)
            if jpg:
                with lock:
                    latest["xyz"] = jpg
        else:
            ex.push(raw)
        n += 1
        now = time.monotonic()
        if now - t0 >= 1.0:
            shared["heat_fps"] = n / (now - t0)
            n = 0
            t0 = now


class EncWorker:
    def __init__(self, enc, key: str) -> None:
        self.enc = enc
        self.key = key
        self.frame = None
        self.ev = threading.Event()
        self.done = threading.Event()
        self.done.set()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        while True:
            self.ev.wait()
            self.ev.clear()
            frame = self.frame
            jpg = self.enc.encode(frame) if frame is not None else b""
            if jpg:
                with lock:
                    latest[self.key] = jpg
            self.done.set()

    def submit(self, frame) -> None:
        self.done.wait()
        self.frame = frame
        self.done.clear()
        self.ev.set()

    def join(self) -> None:
        self.done.wait()


def color_loop(e0, e1, er0, er1) -> None:
    n = 0
    t0 = time.monotonic()
    last_enc = 0.0
    w0 = EncWorker(e0, "ov0") if isinstance(e0, TurboEnc) else None
    w1 = EncWorker(e1, "ov1") if isinstance(e1, TurboEnc) else None
    seen = (None, None)
    while True:
        a, b = eyes()
        if not a or not b or (a is seen[0] and b is seen[1]):
            time.sleep(0.002)
            continue
        seen = (a, b)
        t_a = time.monotonic()
        if w0 and w1:
            w0.submit(a)
            w1.submit(b)
            w0.join()
            w1.join()
        else:
            e0.push(a)
            e1.push(b)
        want = cal["running"] or (time.monotonic() - shared.get("want_raw", 0.0) < 5.0)
        if want:
            with lock:
                latest["raw0"] = latest.get("ov0") or b""
                latest["raw1"] = latest.get("ov1") or b""
        last_enc = (time.monotonic() - t_a) * 1000
        n += 1
        now = time.monotonic()
        if now - t0 >= 1.0:
            fps = n / (now - t0)
            n = 0
            t0 = now
            shared["color_fps"] = fps
            shared["enc_ms"] = last_enc
        # The depth map is the product here; leave the cores for it.
        leftover = COLOR_PERIOD - (time.monotonic() - t_a)
        if leftover > 0:
            time.sleep(leftover)


def pump_ff(enc, key: str) -> None:
    last = b""
    while True:
        jpg = enc.get()
        if jpg and jpg is not last:
            last = jpg
            with lock:
                latest[key] = jpg
        time.sleep(0.01)


def send_mjpeg(conn: socket.socket, key: str) -> None:
    try:
        conn.sendall(
            b"HTTP/1.1 200 OK\r\nCache-Control: no-cache\r\n"
            b"Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n"
        )
        last = b""
        while True:
            with lock:
                jpg = latest[key]
            if jpg and jpg is not last:
                last = jpg
                conn.sendall(
                    b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                    + str(len(jpg)).encode()
                    + b"\r\n\r\n"
                    + jpg
                    + b"\r\n"
                )
            time.sleep(0.008)
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _send(conn: socket.socket, ctype: bytes, body: bytes) -> None:
    conn.sendall(
        b"HTTP/1.1 200 OK\r\nContent-Type: " + ctype + b"\r\n"
        b"Cache-Control: no-store\r\nContent-Length: "
        + str(len(body)).encode()
        + b"\r\n\r\n"
        + body
    )


def _read_http(conn: socket.socket):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(4096)
        if not chunk:
            break
        data += chunk
        if len(data) > 400000:
            break
    head, _, rest = data.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    path = b"/"
    method = b"GET"
    if lines:
        parts = lines[0].split(b" ")
        if len(parts) >= 2:
            method = parts[0]
            path = parts[1].split(b"?", 1)[0]
    length = 0
    for line in lines[1:]:
        if line.lower().startswith(b"content-length:"):
            try:
                length = int(line.split(b":", 1)[1].strip() or b"0")
            except ValueError:
                length = 0
    body = rest
    while len(body) < length:
        chunk = conn.recv(min(4096, length - len(body)))
        if not chunk:
            break
        body += chunk
    return method, path, body


def _cal_json() -> bytes:
    return json.dumps(cal_status()).encode()


def handle(conn: socket.socket) -> None:
    try:
        method, path, body = _read_http(conn)
        if path in (b"/", b"/index.html"):
            _send(conn, b"text/html; charset=utf-8", PAGE)
            return
        if path in (b"/brand.png", b"/logo.png"):
            _send(conn, b"image/png", LOGO)
            return
        if path in (b"/cal", b"/cal/", b"/calib"):
            shared["want_raw"] = time.monotonic()
            _send(conn, b"text/html; charset=utf-8", CAL_PAGE)
            return
        if path == b"/stat":
            with lock:
                stat = latest["stat"]
            _send(conn, b"application/json", stat)
            return
        if path == b"/imu":
            body = b"{}"
            try:
                s = socket.create_connection(("127.0.0.1", 8083), 0.2)
                s.sendall(b"GET / HTTP/1.0\r\nHost: x\r\n\r\n")
                buf = b""
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    if len(buf) > 65536:
                        break
                s.close()
                i = buf.find(b"\r\n\r\n")
                if i >= 0:
                    body = buf[i + 4 :]
            except Exception:
                body = b"{}"
            _send(conn, b"application/json", body)
            return
        if path == b"/trig":
            body = {"trig_on": bool(shared.get("trig_on")), "pins": {}}
            if CAM_SYNC is not None:
                body.update(CAM_SYNC.status())
            _send(conn, b"application/json", json.dumps(body).encode())
            return
        if path == b"/align":
            shared["align"] = None
            shared["align_res"] = None
            shared["align_pts"] = []
            shared["align_t"] = 0.0
            shared["align_msg"] = "refitting"
            shared["swap"] = None
            _send(conn, b"application/json", b'{"ok":1}')
            return
        if path == b"/cal/stat":
            shared["want_raw"] = time.monotonic()
            _send(conn, b"application/json", _cal_json())
            return
        if path == b"/cal/start":
            payload = {}
            try:
                payload = json.loads(body.decode() or "{}")
            except Exception:
                payload = {}
            cal["cols"] = int(payload.get("cols") or 11)
            cal["rows"] = int(payload.get("rows") or 8)
            cal["square_mm"] = float(payload.get("square_mm") or 25)
            cal["distance_mm"] = float(payload.get("distance_mm") or DISTANCE_MM)
            cal["samples"] = []
            cal["zones"] = {}
            cal["good"] = 0
            cal["next_zone"] = "C"
            cal["last_ok"] = False
            cal["last_l"] = []
            cal["last_r"] = []
            cal["last_t"] = 0.0
            cal["msg"] = "recording — move the device, keep 1.00 m"
            cal["hint"] = ZONE_HINT["C"]
            cal["running"] = True
            shared["want_raw"] = time.monotonic()
            _send(conn, b"application/json", _cal_json())
            return
        if path == b"/cal/sample":
            payload = {}
            try:
                payload = json.loads(body.decode() or "{}")
            except Exception:
                payload = {}
            cl = list(zip(payload.get("xl") or [], payload.get("yl") or []))
            cr = list(zip(payload.get("xr") or [], payload.get("yr") or []))
            _send(conn, b"application/json", json.dumps(accept_sample(cl, cr)).encode())
            return
        if path == b"/cal/stop":
            cal["running"] = False
            try:
                if len(cal["samples"]) >= 3:
                    compute_calib()
                else:
                    cal["msg"] = "stopped — need 3 good frames, have %d" % len(cal["samples"])
            except Exception as exc:
                cal["msg"] = "stop failed: %s" % exc
            _send(conn, b"application/json", _cal_json())
            return
        if path == b"/cal/reset":
            cal["running"] = False
            cal["samples"] = []
            cal["zones"] = {}
            cal["good"] = 0
            cal["next_zone"] = "C"
            cal["last_ok"] = False
            cal["last_l"] = []
            cal["last_r"] = []
            cal["last_t"] = 0.0
            cal["result"] = None
            cal["hint"] = "Cleared. Live preview stays on. Press Start when the 11×8 board is at 1.00 m."
            cal["msg"] = "cleared"
            try:
                os.remove(CALIB_PATH)
            except OSError:
                pass
            _send(conn, b"application/json", _cal_json())
            return
        snap = {
            b"/snap0": "ov0",
            b"/snap1": "ov1",
            b"/snapx": "xyz",
            b"/snapr0": "raw0",
            b"/snapr1": "raw1",
        }.get(path)
        if snap:
            with lock:
                jpg = latest[snap]
            if not jpg:
                conn.sendall(b"HTTP/1.1 204 No Content\r\nContent-Length: 0\r\n\r\n")
            else:
                _send(conn, b"image/jpeg", jpg)
            return
        key = {
            b"/ov0": "ov0",
            b"/ov1": "ov1",
            b"/xyz": "xyz",
            b"/depth": "xyz",
            b"/raw0": "raw0",
            b"/raw1": "raw1",
        }.get(path)
        if key:
            if key in ("raw0", "raw1"):
                shared["want_raw"] = time.monotonic()
            send_mjpeg(conn, key)
            return
        conn.sendall(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def serve() -> None:
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", PORT))
    sock.listen(8)
    print(
        f"stereo :{PORT} color {VIEW_W}x{VIEW_H} bm {BW}x{BH} native={NATIVE is not None}",
        flush=True,
    )
    while True:
        conn, _ = sock.accept()
        threading.Thread(target=handle, args=(conn,), daemon=True).start()


def main() -> int:
    global CAL_PAGE, LOGO, BW, BH, ND, TH, SCALE, LUT_Y, LUT_U, LUT_V
    _np_ok()
    _cv_ok()
    CAL_PAGE = load_cal_page()
    LOGO = load_logo()
    if _cv_ok():
        BW, BH, ND, TH = 640, 400, 96, 40
    else:
        BW, BH, ND, TH = 320, 200, 32, 420
    SCALE = max(1, 255 // ND)
    LUT_Y = (c_ubyte * ND)(*[LUT[min(255, d * SCALE)][0] for d in range(ND)])
    LUT_U = (c_ubyte * ND)(*[LUT[min(255, d * SCALE)][1] for d in range(ND)])
    LUT_V = (c_ubyte * ND)(*[LUT[min(255, d * SCALE)][2] for d in range(ND)])
    shared["disp"] = bytearray(BW * BH)
    ensure_companions()
    e0, e1, ex = make_enc(VIEW_W, VIEW_H, 48), make_enc(VIEW_W, VIEW_H, 48), make_enc(XW, XH, 50)
    er0, er1 = make_enc(CAM_W, CAM_H, 55), make_enc(CAM_W, CAM_H, 55)
    threading.Thread(target=companion_loop, daemon=True).start()
    if start_cam_sync is not None:
        trig_fps = 12.5
        start_cam_sync(shared, "trig_on", trig_fps)
        print("cam sync armed continuous-trigger fps=%.2f (50 Hz)" % trig_fps, flush=True)
    threading.Thread(target=grab, args=(CAM0, "cam0"), daemon=True).start()
    threading.Thread(target=grab, args=(CAM1, "cam1"), daemon=True).start()
    threading.Thread(target=bm_loop, args=(ex,), daemon=True).start()
    threading.Thread(target=heat_loop, args=(ex,), daemon=True).start()
    threading.Thread(target=color_loop, args=(e0, e1, er0, er1), daemon=True).start()
    threading.Thread(target=cal_loop, daemon=True).start()
    if not isinstance(e0, TurboEnc):
        threading.Thread(target=pump_ff, args=(e0, "ov0"), daemon=True).start()
        threading.Thread(target=pump_ff, args=(e1, "ov1"), daemon=True).start()
        threading.Thread(target=pump_ff, args=(ex, "xyz"), daemon=True).start()
        threading.Thread(target=pump_ff, args=(er0, "raw0"), daemon=True).start()
        threading.Thread(target=pump_ff, args=(er1, "raw1"), daemon=True).start()
    serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
