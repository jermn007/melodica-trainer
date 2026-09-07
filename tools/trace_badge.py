#!/usr/bin/env python
r"""
trace_badge.py - vector-trace the "m-37C Plus = S SUZUKI =" badge from a photo crop.

Input : a crop of the badge panel (light lettering on blue). Oblique photos foreshorten the panel's short
        axis, so the crop is mapped anisotropically onto the panel's true aspect (--aspect, length:thickness).
Output: badge_paths.json  {"w":300,"h":H,"d":"M...Z M...Z", "contours":n, "points":n, "iou":x}
        badge_preview.svg  the trace at 4x over the original crop (stretched the same way) for eyeballing
Method: whiteness score -> 6x Lanczos upscale -> Gaussian blur -> Otsu threshold -> component cleanup ->
        marching squares on the blurred score (sub-pixel contours) -> Douglas-Peucker -> evenodd path.
Requires numpy, scipy, Pillow (no OpenCV/skimage needed).
"""
import argparse, json, math, os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

def otsu(v):
    h, edges = np.histogram(v, bins=256); h = h.astype(float); mids = (edges[:-1] + edges[1:]) / 2
    w0 = np.cumsum(h); w1 = w0[-1] - w0; m0 = np.cumsum(h * mids) / np.maximum(w0, 1e-9)
    m1 = (np.cumsum((h * mids)[::-1])[::-1]) / np.maximum(w1, 1e-9)
    var = w0[:-1] * w1[1:] * (m0[:-1] - m1[1:]) ** 2
    return mids[int(np.argmax(var))]

def marching_squares(f, level):
    """Iso-contours of 2-D array f at `level`; returns list of (N,2) arrays of (x,y) in pixel coords (cell corners)."""
    H, W = f.shape
    b = f >= level
    segs = []
    def interp(p, q, fp, fq):
        t = (level - fp) / (fq - fp) if fq != fp else 0.5
        return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
    for y in range(H - 1):
        for x in range(W - 1):
            tl, tr, br, bl = b[y, x], b[y, x + 1], b[y + 1, x + 1], b[y + 1, x]
            idx = tl * 8 + tr * 4 + br * 2 + bl
            if idx == 0 or idx == 15: continue
            ftl, ftr, fbr, fbl = f[y, x], f[y, x + 1], f[y + 1, x + 1], f[y + 1, x]
            top = interp((x, y), (x + 1, y), ftl, ftr); right = interp((x + 1, y), (x + 1, y + 1), ftr, fbr)
            bottom = interp((x, y + 1), (x + 1, y + 1), fbl, fbr); left = interp((x, y), (x, y + 1), ftl, fbl)
            table = {1: [(left, bottom)], 2: [(bottom, right)], 3: [(left, right)], 4: [(top, right)],
                     5: [(left, top), (bottom, right)], 6: [(top, bottom)], 7: [(left, top)], 8: [(top, left)],
                     9: [(top, bottom)], 10: [(top, right), (left, bottom)], 11: [(top, right)], 12: [(left, right)],
                     13: [(bottom, right)], 14: [(left, bottom)]}
            if idx in (5, 10):  # saddle: use the centre value
                c = (ftl + ftr + fbr + fbl) / 4 >= level
                if idx == 5: table[5] = [(left, top), (bottom, right)] if c else [(left, bottom), (top, right)]
                else: table[10] = [(top, right), (left, bottom)] if c else [(top, left), (bottom, right)]
            segs.extend(table[idx])
    # link segments into closed polylines
    key = lambda p: (round(p[0], 4), round(p[1], 4))
    adj = {}
    for a, c in segs:
        adj.setdefault(key(a), []).append((key(a), key(c))); adj.setdefault(key(c), []).append((key(a), key(c)))
    used = set(); contours = []
    for a, c in segs:
        s = (key(a), key(c))
        if s in used: continue
        used.add(s); path = [s[0], s[1]]
        cur = s[1]
        while True:
            nxt = None
            for e in adj.get(cur, []):
                if e in used: continue
                other = e[1] if e[0] == cur else e[0]
                used.add(e); nxt = other; break
            if nxt is None or nxt == path[0]: break
            path.append(nxt); cur = nxt
        if len(path) >= 3: contours.append(np.array(path, dtype=float))
    return contours

def dp(points, eps):
    """Douglas-Peucker on a closed polyline."""
    pts = points
    if len(pts) < 4: return pts
    def rec(p):
        if len(p) < 3: return p
        a, b = p[0], p[-1]; ab = b - a; n = np.hypot(*ab) + 1e-12
        d = np.abs((p[:, 0] - a[0]) * ab[1] - (p[:, 1] - a[1]) * ab[0]) / n
        i = int(np.argmax(d))
        if d[i] > eps: return np.vstack([rec(p[:i + 1])[:-1], rec(p[i:])])
        return np.array([a, b])
    # split at the farthest point from p0 so the closed loop becomes two open runs
    far = int(np.argmax(np.hypot(*(pts - pts[0]).T)))
    r = np.vstack([rec(pts[:far + 1])[:-1], rec(np.vstack([pts[far:], pts[:1]]))[:-1]])
    return r

def inside(pt, poly):
    x, y = pt; n = len(poly); c = False; j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi): c = not c
        j = i
    return c

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('image'); ap.add_argument('--out', default='.')
    ap.add_argument('--width', type=float, default=300, help='canvas length in units')
    ap.add_argument('--aspect', type=float, default=3.66, help='true panel aspect (length / thickness)')
    ap.add_argument('--up', type=int, default=6); ap.add_argument('--blur', type=float, default=1.0)
    ap.add_argument('--eps', type=float, default=0.22, help='simplification tolerance in canvas units')
    ap.add_argument('--min-area', type=float, default=18, help='drop blobs smaller than this (canvas units^2)')
    ap.add_argument('--inset', type=float, default=0.0, help='fraction of crop height to ignore at top/bottom (panel bevel)')
    ap.add_argument('--sharpen', type=float, default=0.0, help='unsharp-mask amount applied to the score before thresholding (opens tiny counters)')
    ap.add_argument('--sharpen-radius', type=float, default=1.2, help='unsharp radius in source pixels')
    ap.add_argument('--level', type=float, default=0.0, help='offset added to the Otsu threshold (positive = thinner strokes, opener counters)')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    im = Image.open(a.image).convert('RGB'); W0, H0 = im.size
    rgb = np.asarray(im).astype(float)
    score = 0.5 * (rgb[..., 0] + rgb[..., 1]) - 0.35 * rgb[..., 2]          # silver high, blue low
    score = (score - score.min()) / (score.max() - score.min() + 1e-9)
    if a.inset > 0:
        k = int(round(H0 * a.inset)); score[:k, :] = 0; score[H0 - k:, :] = 0
    if a.sharpen > 0:
        score = np.clip(score + a.sharpen * (score - ndi.gaussian_filter(score, a.sharpen_radius)), 0, 1)
    up = Image.fromarray((score * 255).astype(np.uint8)).resize((W0 * a.up, H0 * a.up), Image.LANCZOS)
    f = np.asarray(up).astype(float) / 255.0
    f = ndi.gaussian_filter(f, a.blur)
    thr = float(np.clip(otsu(f.ravel()) + a.level, 0.05, 0.95))
    mask = f >= thr
    mask = ndi.binary_opening(mask, structure=np.ones((3, 3)))
    lab, n = ndi.label(mask)
    canvas_h = a.width / a.aspect
    sx, sy = a.width / (W0 * a.up), canvas_h / (H0 * a.up)
    keep = np.zeros_like(mask)
    for i in range(1, n + 1):
        blob = lab == i; ys, xs = np.nonzero(blob)
        area = blob.sum() * sx * sy
        wfrac = (xs.max() - xs.min()) / (W0 * a.up); touches = ys.min() <= 1 or ys.max() >= H0 * a.up - 2
        if area < a.min_area: continue
        if touches and wfrac > 0.5: continue        # panel bevel highlight running along the edge
        keep |= blob
    # contours on the smoothed score, masked to kept blobs (dilated a little so edges stay sub-pixel)
    fm = np.where(ndi.binary_dilation(keep, iterations=2), f, 0.0)
    fm = np.pad(fm, 1)
    contours = marching_squares(fm, thr)
    polys = []
    for c in contours:
        c = (c - 1.0) * np.array([sx, sy])
        c = dp(c, a.eps)
        if len(c) >= 3 and abs(np.cross(c[1:] - c[0], c[:-1] - c[0]).sum()) / 2 >= a.min_area * 0.4:
            polys.append(c)
    # rasterise for an IoU check against the mask (holes = contours inside another contour)
    outer = [i for i, p in enumerate(polys) if not any(j != i and inside(p[0], q) for j, q in enumerate(polys))]
    R = 4; test = Image.new('L', (int(a.width * R), int(canvas_h * R)), 0); d = ImageDraw.Draw(test)
    for i, p in enumerate(polys):
        d.polygon([(x * R, y * R) for x, y in p], fill=255 if i in outer else 0)
    ref = Image.fromarray((keep * 255).astype(np.uint8)).resize(test.size, Image.BILINEAR)
    A = np.asarray(test) > 127; B = np.asarray(ref) > 127
    iou = float((A & B).sum() / max(1, (A | B).sum()))
    test.save(os.path.join(a.out, 'badge_trace.png'))
    parts = []
    for p in polys:
        parts.append('M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in p) + 'Z')
    dstr = ' '.join(parts)
    json.dump({'w': a.width, 'h': round(canvas_h, 2), 'd': dstr, 'contours': len(polys), 'points': int(sum(len(p) for p in polys)),
               'iou': round(iou, 4), 'threshold': round(float(thr), 4), 'source': os.path.basename(a.image)},
              open(os.path.join(a.out, 'badge_paths.json'), 'w'), indent=1)
    # preview: crop stretched to the canvas aspect, trace overlaid in red outline + solid fill beneath
    b64 = None
    import base64, io
    st = im.resize((int(a.width * R), int(canvas_h * R)), Image.LANCZOS); buf = io.BytesIO(); st.save(buf, 'PNG'); b64 = base64.b64encode(buf.getvalue()).decode()
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {a.width} {canvas_h * 2 + 6}" width="{a.width * R}">'
           f'<rect width="{a.width}" height="{canvas_h * 2 + 6}" fill="#0b0f17"/>'
           f'<image href="data:image/png;base64,{b64}" x="0" y="0" width="{a.width}" height="{canvas_h}"/>'
           f'<path d="{dstr}" fill="none" stroke="#ff3355" stroke-width="0.5"/>'
           f'<g transform="translate(0 {canvas_h + 6})"><rect width="{a.width}" height="{canvas_h}" fill="#1f5fa8"/>'
           f'<path d="{dstr}" fill="#e8edf3" fill-rule="evenodd"/></g></svg>')
    open(os.path.join(a.out, 'badge_preview.svg'), 'w', encoding='utf-8').write(svg)
    print(f'contours {len(polys)}  points {sum(len(p) for p in polys)}  path chars {len(dstr)}  IoU vs mask {iou:.3f}  canvas {a.width}x{canvas_h:.1f}  thr {thr:.3f}')

if __name__ == '__main__':
    main()
