#!/usr/bin/env python
"""make_icons.py - favicon.svg, icon-512.png, apple-touch-icon.png (180) and og.png (1200x630) for Melodica Trainer.
Draws the M-37C Plus motif (blue body, red rail, cream keys, black sharps, mouthpiece ring) with Pillow.
Run from the app folder:  python tools/make_icons.py
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BG, BLUE, BLUE_DK, RED, CREAM, BLACK, CHROME, CHROME_DK = '#0f1826', '#1f5fa8', '#17477e', '#c8102e', '#f3ead8', '#151515', '#cfd6dd', '#8a949f'
AMBER, GREEN, TEAL, INK, MUTED = '#f59e0b', '#22c55e', '#2dd4bf', '#e8eef6', '#94a4ba'

def font(size, bold=True):
    for p in (r'C:\Windows\Fonts\segoeuib.ttf' if bold else r'C:\Windows\Fonts\segoeui.ttf', r'C:\Windows\Fonts\arialbd.ttf', r'C:\Windows\Fonts\arial.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def melodica(d, x, y, w, h, keys=7, dots=None, scale=1.0):
    """Draw a small melodica: body rect, red rail, `keys` white keys with the black-key pattern for F..E."""
    r = int(22 * scale)
    d.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=BLUE)
    d.rounded_rectangle([x, y + h - int(10 * scale), x + w, y + h], radius=int(6 * scale), fill=BLUE_DK)
    cap = int(w * 0.13); kx0 = x + cap; kw_total = w - cap - int(w * 0.08)
    rail = int(h * 0.16)
    d.rectangle([kx0 - int(6 * scale), y, kx0 + kw_total + int(6 * scale), y + rail], fill=RED)
    d.rectangle([kx0 - int(3 * scale), y + rail, kx0 + kw_total + int(3 * scale), y + h - int(12 * scale)], fill=BLACK)
    kw = kw_total / keys; ky0 = y + rail + int(3 * scale); ky1 = y + h - int(14 * scale)
    gap = max(1, int(2 * scale))
    for i in range(keys):
        d.rounded_rectangle([kx0 + i * kw + gap, ky0, kx0 + (i + 1) * kw - gap, ky1], radius=int(5 * scale), fill=CREAM)
    # black keys after F G A, C D within an F-start octave pattern: positions between whites (0,1),(1,2),(2,3),(4,5),(5,6)
    bw = kw * 0.58; bh = (ky1 - ky0) * 0.62
    pattern = [0, 1, 2, 4, 5] if keys == 7 else [i for i in range(keys - 1) if i % 7 in (0, 1, 2, 4, 5)]
    for i in pattern:
        cx = kx0 + (i + 1) * kw
        d.rounded_rectangle([cx - bw / 2, ky0, cx + bw / 2, ky0 + bh], radius=int(3 * scale), fill=BLACK)
    # mouthpiece ring on the left cap
    cy = y + h * 0.62; rr = int(h * 0.075)
    d.ellipse([x + cap * 0.5 - rr, cy - rr, x + cap * 0.5 + rr, cy + rr], fill=CHROME, outline=CHROME_DK, width=max(2, int(3 * scale)))
    if dots:
        for i, col in dots:
            cx = kx0 + (i + 0.5) * kw; dy = ky1 - (ky1 - ky0) * 0.2; dr = kw * 0.3
            d.ellipse([cx - dr, dy - dr, cx + dr, dy + dr], fill=col, outline='#0b1220', width=max(1, int(2 * scale)))

def icon(size):
    im = Image.new('RGBA', (size, size), BG)
    d = ImageDraw.Draw(im)
    m = int(size * 0.06)
    d.rounded_rectangle([0, 0, size, size], radius=int(size * 0.22), fill=BG)
    d.rounded_rectangle([m, m, size - m, size - m], radius=int(size * 0.2), outline=TEAL + '59' if False else (45, 212, 191, 90), width=max(2, size // 90))
    melodica(d, int(size * 0.1), int(size * 0.29), int(size * 0.8), int(size * 0.42), keys=7, dots=[(2, AMBER), (4, GREEN)], scale=size / 512)
    return im

def og():
    W, H = 1200, 630
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)
    melodica(d, 70, 300, 1060, 250, keys=15, dots=[(3, AMBER), (5, CREAM), (7, GREEN), (10, AMBER)], scale=1.6)
    d.text((70, 70), 'Melodica Trainer', font=font(72), fill=INK)
    d.text((72, 165), 'Type a progression, pick a scale, see which keys to press.', font=font(34, bold=False), fill=MUTED)
    d.text((72, 212), 'Sampled Suzuki M-37C Plus · fingering · drills · melodica.terhunelabs.com', font=font(28, bold=False), fill=TEAL)
    return im

FAVICON_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" rx="14" fill="#0f1826"/>
  <rect x="7" y="20" width="50" height="26" rx="5" fill="#1f5fa8"/>
  <rect x="14" y="20" width="38" height="5" fill="#c8102e"/>
  <rect x="13" y="25" width="40" height="19" fill="#151515"/>
  <g fill="#f3ead8"><rect x="14" y="26" width="7" height="17" rx="1.2"/><rect x="22" y="26" width="7" height="17" rx="1.2"/><rect x="30" y="26" width="7" height="17" rx="1.2"/><rect x="38" y="26" width="7" height="17" rx="1.2"/><rect x="46" y="26" width="6" height="17" rx="1.2"/></g>
  <g fill="#151515"><rect x="19" y="26" width="4" height="10" rx="1"/><rect x="27" y="26" width="4" height="10" rx="1"/><rect x="43" y="26" width="4" height="10" rx="1"/></g>
  <circle cx="10.5" cy="37" r="2.4" fill="#cfd6dd" stroke="#8a949f" stroke-width="1"/>
  <circle cx="33.5" cy="40" r="2.6" fill="#f59e0b" stroke="#0b1220" stroke-width=".6"/>
  <circle cx="41.5" cy="40" r="2.6" fill="#22c55e" stroke="#0b1220" stroke-width=".6"/>
</svg>
'''

if __name__ == '__main__':
    icon(512).save(os.path.join(ROOT, 'icon-512.png'))
    icon(180).convert('RGB').save(os.path.join(ROOT, 'apple-touch-icon.png'))
    og().save(os.path.join(ROOT, 'og.png'))
    open(os.path.join(ROOT, 'favicon.svg'), 'w', encoding='utf-8').write(FAVICON_SVG)
    print('wrote icon-512.png, apple-touch-icon.png, og.png, favicon.svg')
