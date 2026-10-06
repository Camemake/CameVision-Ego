/* Fast stereo + NV12 overlay for RV1126B. Built as libego_stereo.so */
#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

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

/* 180° (same as the live CSS scale(-1,-1)) and center-crop width src_w -> dst_w. */
void ego_nv12_rot180_crop(const uint8_t *src, int src_w, int src_h,
                          uint8_t *dst, int dst_w) {
    const int x0 = (src_w - dst_w) / 2;
    const uint8_t *sy = src;
    const uint8_t *suv = src + src_w * src_h;
    uint8_t *dy = dst;
    uint8_t *duv = dst + dst_w * src_h;
    for (int y = 0; y < src_h; y++) {
        const uint8_t *srow = sy + (src_h - 1 - y) * src_w + x0;
        uint8_t *drow = dy + y * dst_w;
        for (int x = 0; x < dst_w; x++) {
            drow[x] = srow[dst_w - 1 - x];
        }
    }
    const int ch = src_h / 2;
    for (int y = 0; y < ch; y++) {
        const uint8_t *srow = suv + (ch - 1 - y) * src_w + x0;
        uint8_t *drow = duv + y * dst_w;
        for (int x = 0; x < dst_w; x += 2) {
            const int sx = dst_w - 2 - x;
            drow[x] = srow[sx];
            drow[x + 1] = srow[sx + 1];
        }
    }
}

int ego_nv12_prep_loop(int in_fd, int out_fd, int src_w, int src_h, int dst_w,
                       volatile int *stop, volatile int *frames) {
    const size_t src_n = (size_t)src_w * (size_t)src_h * 3u / 2u;
    const size_t dst_n = (size_t)dst_w * (size_t)src_h * 3u / 2u;
    uint8_t *src = (uint8_t *)malloc(src_n);
    uint8_t *dst = (uint8_t *)malloc(dst_n);
    if (!src || !dst) {
        free(src);
        free(dst);
        return -1;
    }
    while (!stop || !*stop) {
        size_t got = 0;
        while (got < src_n) {
            if (stop && *stop) {
                goto done;
            }
            ssize_t n = read(in_fd, src + got, src_n - got);
            if (n < 0) {
                if (errno == EINTR) {
                    continue;
                }
                goto done;
            }
            if (n == 0) {
                goto done;
            }
            got += (size_t)n;
        }
        ego_nv12_rot180_crop(src, src_w, src_h, dst, dst_w);
        size_t put = 0;
        while (put < dst_n) {
            if (stop && *stop) {
                goto done;
            }
            ssize_t n = write(out_fd, dst + put, dst_n - put);
            if (n < 0) {
                if (errno == EINTR) {
                    continue;
                }
                goto done;
            }
            if (n == 0) {
                goto done;
            }
            put += (size_t)n;
        }
        if (frames) {
            __sync_add_and_fetch(frames, 1);
        }
    }
done:
    free(src);
    free(dst);
    return 0;
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
