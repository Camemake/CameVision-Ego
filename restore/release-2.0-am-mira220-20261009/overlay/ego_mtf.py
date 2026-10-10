#!/usr/bin/env python3
"""ISO 12233 slanted-edge MTF50 for CameVision Ego focus.

Runs on the live 1920x1200 Y plane. Hold the chart at 50 cm.
MTF50 is the spatial frequency where SFR drops to 0.5 (cycles/pixel).
"""
from __future__ import annotations

import json
import os
import threading
import time

W, H = 1920, 1200
FOCUS_PATH = "/userdata/ego_focus.json"
DISTANCE_MM = 500
OVERSAMPLE = 4
# Soft / usable / good for this global-shutter module (cycles/pixel).
SOFT = 0.18
GOOD = 0.28


def _y(nv12, w: int = W, h: int = H):
    import numpy as np

    n = w * h
    buf = nv12[:n] if not isinstance(nv12, memoryview) else nv12[:n]
    return np.frombuffer(buf, dtype=np.uint8, count=n).reshape(h, w)


def _centroids(roi, vertical: bool):
    import numpy as np

    img = roi.astype(np.float64)
    h, w = img.shape
    ys = []
    xs = []
    if vertical:
        axis = np.arange(w - 1, dtype=np.float64) + 0.5
        for y in range(h):
            d = np.diff(img[y])
            mag = np.abs(d)
            s = mag.sum()
            if s < 12.0:
                continue
            xs.append(float(np.dot(axis, mag) / s))
            ys.append(float(y))
    else:
        axis = np.arange(h - 1, dtype=np.float64) + 0.5
        for x in range(w):
            d = np.diff(img[:, x])
            mag = np.abs(d)
            s = mag.sum()
            if s < 12.0:
                continue
            ys.append(float(np.dot(axis, mag) / s))
            xs.append(float(x))
    if len(xs) < 16:
        return None
    return np.asarray(ys), np.asarray(xs)


def mtf50_roi(roi) -> dict | None:
    """Slanted-edge SFR (ISO 12233). Returns cycles/pixel and LW/PH."""
    import numpy as np

    if roi is None or roi.size < 400:
        return None
    h, w = roi.shape
    p5, p95 = np.percentile(roi, (5, 95))
    if (p95 - p5) < 40:
        return None
    gx = np.abs(np.diff(roi.astype(np.float32), axis=1)).sum()
    gy = np.abs(np.diff(roi.astype(np.float32), axis=0)).sum()
    vertical = gx >= gy
    pair = _centroids(roi, vertical)
    if pair is None:
        return None
    ys, xs = pair
    if vertical:
        b, a = np.polyfit(ys, xs, 1)
        angle = abs(float(np.degrees(np.arctan(b))))
        nx, ny = 1.0, -b
    else:
        b, a = np.polyfit(xs, ys, 1)
        angle = abs(float(np.degrees(np.arctan(b))))
        nx, ny = -b, 1.0
    if angle < 2.0 or angle > 18.0:
        return None
    nlen = float(np.hypot(nx, ny)) or 1.0
    nx /= nlen
    ny /= nlen
    yy, xx = np.indices(roi.shape)
    t = xx * nx + yy * ny
    t0 = float(t.min())
    span = float(t.max() - t0)
    if span < 8.0:
        return None
    osamp = OVERSAMPLE
    nb = int(span * osamp)
    if nb < 32:
        return None
    nb = min(nb, 1024)
    idx = np.clip(((t - t0) * osamp).astype(np.int32), 0, nb - 1)
    acc = np.bincount(idx.ravel(), weights=roi.astype(np.float64).ravel(), minlength=nb)
    cnt = np.bincount(idx.ravel(), minlength=nb).astype(np.float64)
    ok = cnt > 0
    if ok.sum() < 24:
        return None
    esf = np.zeros(nb, dtype=np.float64)
    esf[ok] = acc[ok] / cnt[ok]
    # fill empty bins
    if (~ok).any():
        good = np.flatnonzero(ok)
        esf[~ok] = np.interp(np.flatnonzero(~ok), good, esf[ok])
    kernel = np.array([1.0, 2.0, 1.0])
    kernel /= kernel.sum()
    esf = np.convolve(esf, kernel, mode="same")
    lo, hi = float(np.min(esf)), float(np.max(esf))
    if (hi - lo) < 25:
        return None
    p10 = lo + 0.10 * (hi - lo)
    p90 = lo + 0.90 * (hi - lo)
    c10 = np.where((esf[:-1] - p10) * (esf[1:] - p10) <= 0)[0]
    c90 = np.where((esf[:-1] - p90) * (esf[1:] - p90) <= 0)[0]
    if c10.size == 0 or c90.size == 0:
        return None
    rise_px = abs(int(c90[0]) - int(c10[0])) / float(osamp)
    if rise_px < 1.3 or rise_px > 40:
        return None
    lsf = np.diff(esf)
    lsf -= lsf.mean()
    win = np.hamming(len(lsf))
    spec = np.fft.rfft(lsf * win)
    mtf = np.abs(spec)
    if mtf[0] <= 1e-9:
        return None
    mtf = mtf / mtf[0]
    freq = np.fft.rfftfreq(len(lsf), d=1.0 / osamp)
    below = np.where(mtf <= 0.5)[0]
    if below.size == 0 or below[0] == 0:
        cy = float(freq[-1]) if mtf[-1] >= 0.5 else 0.0
    else:
        i = int(below[0])
        y0, y1 = float(mtf[i - 1]), float(mtf[i])
        x0, x1 = float(freq[i - 1]), float(freq[i])
        if y1 == y0:
            cy = x1
        else:
            cy = x0 + (0.5 - y0) * (x1 - x0) / (y1 - y0)
    cy = float(max(0.0, min(0.49, cy)))
    if cy >= 0.48:
        return None
    return {
        "mtf50_cy": round(cy, 4),
        "mtf50_lwph": int(round(2.0 * cy * H)),
        "angle_deg": round(angle, 2),
        "contrast": int(p95 - p5),
        "vertical": int(vertical),
    }


def _window(y, cx: int, cy: int, hw: int = 90, hh: int = 90):
    x0 = max(0, cx - hw)
    y0 = max(0, cy - hh)
    x1 = min(y.shape[1], cx + hw)
    y1 = min(y.shape[0], cy + hh)
    if x1 - x0 < 40 or y1 - y0 < 40:
        return None, None
    return y[y0:y1, x0:x1], {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


def _isolate_edge(crop):
    import numpy as np

    gx = np.abs(np.diff(crop.astype(np.float32), axis=1)).sum(axis=0)
    gy = np.abs(np.diff(crop.astype(np.float32), axis=0)).sum(axis=1)
    if gx.max() >= gy.max():
        c = int(np.argmax(gx))
        x0 = max(0, c - 28)
        x1 = min(crop.shape[1], c + 28)
        return crop[:, x0:x1], x0, 0
    r = int(np.argmax(gy))
    y0 = max(0, r - 28)
    y1 = min(crop.shape[0], r + 28)
    return crop[y0:y1, :], 0, y0


def _score_at(y, cx: int, cy: int, hw: int, hh: int):
    crop, box = _window(y, cx, cy, hw, hh)
    if crop is None:
        return None
    strip, dx, dy = _isolate_edge(crop)
    rec = mtf50_roi(strip)
    if rec is None:
        rec = mtf50_roi(crop)
        dx = dy = 0
    if rec is None or box is None:
        return None
    rec["box"] = {
        "x": box["x"] + dx,
        "y": box["y"] + dy,
        "w": strip.shape[1] if dx or dy else box["w"],
        "h": strip.shape[0] if dx or dy else box["h"],
    }
    return rec


def _best_in(y, x0: int, y0: int, x1: int, y1: int, hw: int = 88) -> dict | None:
    import numpy as np

    best = None
    xs = np.unique(np.concatenate((
        np.linspace(x0, x1, 3, dtype=int),
        np.array([(x0 + x1) // 2], dtype=int),
    )))
    ys = np.unique(np.concatenate((
        np.linspace(y0, y1, 3, dtype=int),
        np.array([(y0 + y1) // 2], dtype=int),
    )))
    for cy in ys:
        for cx in xs:
            rec = _score_at(y, int(cx), int(cy), hw, hw)
            if rec is None:
                continue
            if best is None or rec["mtf50_cy"] > best["mtf50_cy"]:
                best = rec
    return best


def find_chart(y):
    """Find the ISO 12233 sheet (large high-contrast rectangle)."""
    import numpy as np

    h, w = y.shape
    try:
        import cv2
    except Exception:
        cv2 = None
    if cv2 is None:
        return None
    sw, sh = 480, 300
    small = cv2.resize(y, (sw, sh), interpolation=cv2.INTER_AREA)
    blur = cv2.GaussianBlur(small, (5, 5), 0)
    paper = (blur > np.percentile(blur, 42)).astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 17))
    paper = cv2.morphologyEx(paper, cv2.MORPH_CLOSE, k)
    paper = cv2.morphologyEx(paper, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)))
    cnts, _ = cv2.findContours(paper, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    for c in cnts:
        area = cv2.contourArea(c)
        if area < sw * sh * 0.16:
            continue
        x, yy, bw, bh = cv2.boundingRect(c)
        ar = bw / float(max(bh, 1))
        if ar < 1.15 or ar > 2.35:
            continue
        fill = area / float(max(bw * bh, 1))
        if fill < 0.55:
            continue
        if best is None or area > best[0]:
            best = (area, x, yy, bw, bh)
    if best is None:
        edges = cv2.Canny(blur, 40, 130)
        edges = cv2.dilate(edges, None, iterations=2)
        cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            area = cv2.contourArea(c)
            if area < sw * sh * 0.18:
                continue
            x, yy, bw, bh = cv2.boundingRect(c)
            ar = bw / float(max(bh, 1))
            if ar < 1.15 or ar > 2.35:
                continue
            if best is None or area > best[0]:
                best = (area, x, yy, bw, bh)
    if best is None:
        return None
    _, x, yy, bw, bh = best
    sx, sy = w / float(sw), h / float(sh)
    box = {
        "x": int(x * sx),
        "y": int(yy * sy),
        "w": int(bw * sx),
        "h": int(bh * sy),
    }
    if box["w"] < w * 0.28 or box["h"] < h * 0.28:
        return None
    return box


def measure_eye(y) -> dict:
    empty = {
        "ok": False,
        "mtf50_cy": None,
        "mtf50_lwph": None,
        "corner_cy": None,
        "n_edges": 0,
        "center": None,
        "corners": [],
        "chart": None,
    }
    chart = find_chart(y)
    if chart is None:
        return empty
    x0, y0, bw, bh = chart["x"], chart["y"], chart["w"], chart["h"]
    center = _best_in(
        y,
        x0 + bw // 3,
        y0 + bh // 3,
        x0 + (2 * bw) // 3,
        y0 + (2 * bh) // 3,
        max(56, min(bw, bh) // 8),
    )
    if center is not None:
        center["name"] = "C"
    sites = (
        ("TL", x0 + bw // 5, y0 + bh // 5),
        ("TR", x0 + (4 * bw) // 5, y0 + bh // 5),
        ("BL", x0 + bw // 5, y0 + (4 * bh) // 5),
        ("BR", x0 + (4 * bw) // 5, y0 + (4 * bh) // 5),
    )
    hw = max(48, min(bw, bh) // 10)
    rois = []
    corners = []
    if center is not None:
        rois.append(center)
    for name, cx, cy in sites:
        rec = _score_at(y, cx, cy, hw, hw)
        if rec is None:
            continue
        rec["name"] = name
        rois.append(rec)
        corners.append(rec)
    cy_val = None
    if center is not None:
        cy_val = center["mtf50_cy"]
    elif rois:
        cy_val = sum(r["mtf50_cy"] for r in rois) / len(rois)
    corner_cy = None
    if corners:
        corner_cy = sum(r["mtf50_cy"] for r in corners) / len(corners)
    return {
        "ok": cy_val is not None,
        "mtf50_cy": None if cy_val is None else round(float(cy_val), 4),
        "mtf50_lwph": None if cy_val is None else int(round(2.0 * float(cy_val) * H)),
        "corner_cy": None if corner_cy is None else round(float(corner_cy), 4),
        "n_edges": len(rois),
        "center": center,
        "corners": corners,
        "chart": chart,
    }


def _smooth(prev: float | None, cur: float | None, a: float = 0.38) -> float | None:
    if cur is None:
        return None
    if prev is None:
        return cur
    return prev * (1.0 - a) + cur * a


def _grade(cy: float | None) -> str:
    if cy is None:
        return "none"
    if cy < SOFT:
        return "soft"
    if cy < GOOD:
        return "ok"
    return "good"


def _hint(left: dict, right: dict) -> tuple[str, str]:
    lc = left.get("mtf50_cy")
    rc = right.get("mtf50_cy")
    lp = left.get("peak_cy") or 0.0
    rp = right.get("peak_cy") or 0.0
    saw_l = left.get("chart") is not None
    saw_r = right.get("chart") is not None
    if not saw_l and not saw_r:
        return (
            "no_chart",
            "This test needs the ISO 12233 resolution chart (black frame, slanted squares, center circles). Hold that printed chart at 50 cm so it fills both views.",
        )
    if lc is None and rc is None:
        return (
            "no_edge",
            "Chart seen. Center a slanted black square so an edge fills the teal box, then turn the lens.",
        )
    if lc is None or rc is None:
        miss = "left" if lc is None else "right"
        return (
            "one_eye",
            "Chart seen on one eye only. Center it so both cameras see the same slanted edge (%s missing)."
            % miss,
        )
    l_off = (lp - lc) / lp if lp > 0.05 else 0.0
    r_off = (rp - rc) / rp if rp > 0.05 else 0.0
    near = l_off < 0.08 and r_off < 0.08
    if near and lc >= GOOD and rc >= GOOD:
        return (
            "in_focus",
            "Peak focus. Lock the lens ring on both eyes. MTF50 L %.2f  R %.2f cy/px."
            % (lc, rc),
        )
    if l_off > 0.10 or r_off > 0.10:
        which = []
        if l_off > 0.10:
            which.append("left")
        if r_off > 0.10:
            which.append("right")
        return (
            "turn_back",
            "Softer than the peak on %s. Turn the lens back a little."
            % " and ".join(which),
        )
    if lc < SOFT or rc < SOFT:
        return (
            "soft",
            "Soft. Loosen the lock ring and turn the M12 lens slowly. Watch the number climb, then lock at the peak.",
        )
    return (
        "improving",
        "Keep turning slowly. Stop when both numbers stop rising, then lock.",
    )


class FocusMeter:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.running = False
        self.distance_mm = DISTANCE_MM
        self.left: dict = {}
        self.right: dict = {}
        self.hint = ""
        self.verdict = "idle"
        self.t = 0.0
        self._ema_l = None
        self._ema_r = None
        self._peak_l = 0.0
        self._peak_r = 0.0
        self._prev_l = None
        self._prev_r = None

    def status(self) -> dict:
        with self.lock:
            return {
                "running": self.running,
                "chart": "ISO12233",
                "method": "slanted-edge SFR",
                "distance_mm": self.distance_mm,
                "cap_w": W,
                "cap_h": H,
                "left": dict(self.left),
                "right": dict(self.right),
                "hint": self.hint,
                "verdict": self.verdict,
                "t": self.t,
                "soft": SOFT,
                "good": GOOD,
            }

    def start(self) -> dict:
        with self.lock:
            self.running = True
            self._ema_l = self._ema_r = None
            self._peak_l = self._peak_r = 0.0
            self._prev_l = self._prev_r = None
            self.left = {}
            self.right = {}
            self.verdict = "no_chart"
            self.hint = (
                "Hold the ISO 12233 chart at 50 cm. It looks like the picture "
                "on the left: black frame, slanted squares, circles in the center."
            )
        return self.status()

    def stop(self) -> dict:
        st = self.status()
        with self.lock:
            self.running = False
        try:
            tmp = FOCUS_PATH + ".tmp"
            with open(tmp, "w") as fh:
                json.dump(st, fh, indent=2)
            os.replace(tmp, FOCUS_PATH)
            st["saved"] = FOCUS_PATH
        except OSError:
            st["saved"] = ""
        st["running"] = False
        return st

    def update(self, nv_left, nv_right) -> dict:
        if not self.running:
            return self.status()
        try:
            yl = _y(nv_left)
            yr = _y(nv_right)
            raw_l = measure_eye(yl)
            raw_r = measure_eye(yr)
        except Exception as exc:
            with self.lock:
                self.hint = "MTF error: %s" % exc
                self.verdict = "error"
            return self.status()
        with self.lock:
            self._ema_l = _smooth(self._ema_l, raw_l.get("mtf50_cy"))
            self._ema_r = _smooth(self._ema_r, raw_r.get("mtf50_cy"))
            if self._ema_l is not None:
                self._peak_l = max(self._peak_l, self._ema_l)
            if self._ema_r is not None:
                self._peak_r = max(self._peak_r, self._ema_r)
            left = dict(raw_l)
            right = dict(raw_r)
            left["mtf50_cy"] = None if self._ema_l is None else round(self._ema_l, 4)
            right["mtf50_cy"] = None if self._ema_r is None else round(self._ema_r, 4)
            if left["mtf50_cy"] is not None:
                left["mtf50_lwph"] = int(round(2.0 * left["mtf50_cy"] * H))
            if right["mtf50_cy"] is not None:
                right["mtf50_lwph"] = int(round(2.0 * right["mtf50_cy"] * H))
            left["peak_cy"] = round(self._peak_l, 4)
            right["peak_cy"] = round(self._peak_r, 4)
            left["grade"] = _grade(left["mtf50_cy"])
            right["grade"] = _grade(right["mtf50_cy"])
            left["rising"] = int(
                self._prev_l is not None
                and left["mtf50_cy"] is not None
                and left["mtf50_cy"] > self._prev_l + 0.004
            )
            right["rising"] = int(
                self._prev_r is not None
                and right["mtf50_cy"] is not None
                and right["mtf50_cy"] > self._prev_r + 0.004
            )
            self._prev_l = left["mtf50_cy"]
            self._prev_r = right["mtf50_cy"]
            self.left = left
            self.right = right
            self.verdict, self.hint = _hint(left, right)
            self.t = time.monotonic()
        return self.status()
