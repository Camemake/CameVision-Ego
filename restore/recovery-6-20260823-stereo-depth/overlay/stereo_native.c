/* Fast stereo + NV12 overlay for RV1126B. Built as libego_stereo.so */
#include <stdint.h>
#include <string.h>

void ego_y_down(const uint8_t *y, int w, int h, uint8_t *out, int bw, int bh) {
    const int xs = w / bw;
    const int ys = h / bh;
    for (int j = 0; j < bh; j++) {
        const uint8_t *row = y + (j * ys) * w;
        uint8_t *dst = out + j * bw;
        for (int i = 0; i < bw; i++) {
            int acc = 0;
            const uint8_t *p = row + i * xs;
            acc += p[0] + p[1];
            acc += p[w] + p[w + 1];
            dst[i] = (uint8_t)(acc >> 2);
        }
    }
}

void ego_stereo_bm(const uint8_t *L, const uint8_t *R, uint8_t *disp,
                   int w, int h, int nd, int thresh) {
    memset(disp, 0, (size_t)w * (size_t)h);
    if (nd < 2) {
        return;
    }
    for (int y = 1; y < h - 1; y++) {
        const uint8_t *l0 = L + (y - 1) * w;
        const uint8_t *l1 = L + y * w;
        const uint8_t *l2 = L + (y + 1) * w;
        const uint8_t *r0 = R + (y - 1) * w;
        const uint8_t *r1 = R + y * w;
        const uint8_t *r2 = R + (y + 1) * w;
        uint8_t *drow = disp + y * w;
        for (int x = nd + 1; x < w - 1; x++) {
            int best = 1 << 30;
            int second = 1 << 30;
            int bd = 0;
            for (int d = 0; d < nd; d++) {
                const int rx = x - d;
                int s = 0;
                int t;
                t = l0[x - 1] - r0[rx - 1]; s += t < 0 ? -t : t;
                t = l0[x]     - r0[rx];     s += t < 0 ? -t : t;
                t = l0[x + 1] - r0[rx + 1]; s += t < 0 ? -t : t;
                t = l1[x - 1] - r1[rx - 1]; s += t < 0 ? -t : t;
                t = l1[x]     - r1[rx];     s += t < 0 ? -t : t;
                t = l1[x + 1] - r1[rx + 1]; s += t < 0 ? -t : t;
                t = l2[x - 1] - r2[rx - 1]; s += t < 0 ? -t : t;
                t = l2[x]     - r2[rx];     s += t < 0 ? -t : t;
                t = l2[x + 1] - r2[rx + 1]; s += t < 0 ? -t : t;
                if (s < best) {
                    second = best;
                    best = s;
                    bd = d;
                } else if (s < second) {
                    second = s;
                }
            }
            if (best < thresh && (second <= best || (second - best) > 6)) {
                drow[x] = (uint8_t)bd;
            }
        }
    }
}

void ego_paint_nv12(uint8_t *nv12, int w, int h, const uint8_t *disp,
                    int bw, int bh, const uint8_t *lut_y, const uint8_t *lut_u,
                    const uint8_t *lut_v, int nd) {
    const int ysize = w * h;
    uint8_t *y = nv12;
    uint8_t *uv = nv12 + ysize;
    const int uw = w / 2;
    const int xs = w / bw;
    const int ys = h / bh;
    for (int j = 0; j < bh; j++) {
        for (int i = 0; i < bw; i++) {
            const int d = disp[j * bw + i];
            if (d < 2 || d >= nd) {
                continue;
            }
            const uint8_t yy = lut_y[d];
            const uint8_t uu = lut_u[d];
            const uint8_t vv = lut_v[d];
            const int y0 = j * ys * w + i * xs;
            for (int dy = 0; dy < ys; dy++) {
                uint8_t *row = y + y0 + dy * w;
                for (int dx = 0; dx < xs; dx++) {
                    row[dx] = (uint8_t)((row[dx] * 3 + yy) >> 2);
                }
            }
            const int urow = (j * ys / 2) * uw + (i * xs / 2);
            for (int dy = 0; dy < ys / 2; dy++) {
                uint8_t *p = uv + (urow + dy * uw) * 2;
                for (int dx = 0; dx < xs / 2; dx++) {
                    p[dx * 2] = uu;
                    p[dx * 2 + 1] = vv;
                }
            }
        }
    }
}

void ego_render_xyz(uint8_t *out, int xw, int xh, const uint8_t *disp,
                    int bw, int bh, const uint8_t *lut_y, const uint8_t *lut_u,
                    const uint8_t *lut_v, int nd) {
    const int ysize = xw * xh;
    memset(out, 16, (size_t)ysize);
    uint8_t *uv = out + ysize;
    const int uvn = ysize / 2;
    for (int i = 0; i < uvn; i += 2) {
        uv[i] = 128;
        uv[i + 1] = 110;
    }
    const int uw = xw / 2;
    uint8_t *y = out;
    for (int j = 0; j < bh; j++) {
        for (int i = 0; i < bw; i++) {
            const int d = disp[j * bw + i];
            if (d < 2 || d >= nd) {
                continue;
            }
            const int u = 24 + i * (xw - 48) / bw + ((i - bw / 2) * d) / 16;
            const int v = 8 + j * (xh - 24) / bh + d * 2;
            if (u < 1 || v < 1 || u >= xw - 2 || v >= xh - 2) {
                continue;
            }
            const uint8_t yy = lut_y[d];
            const uint8_t uu = lut_u[d];
            const uint8_t vv = lut_v[d];
            y[v * xw + u] = yy;
            y[v * xw + u + 1] = yy;
            y[(v + 1) * xw + u] = yy;
            y[(v + 1) * xw + u + 1] = yy;
            const int up = (v / 2) * uw + (u / 2);
            uv[up * 2] = uu;
            uv[up * 2 + 1] = vv;
        }
    }
}
