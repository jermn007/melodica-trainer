#!/usr/bin/env python
"""build_badge.py - embed the traced badge (tools/badge_paths.json from trace_badge.py) into index.html.
Replaces the block from the badge doc-comment through the end of `function badge(g){...}` so it is idempotent.
Run from the app folder:  python tools/build_badge.py
"""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_path = os.path.join(ROOT, 'index.html')
data = json.load(open(os.path.join(ROOT, 'tools', 'badge_paths.json')))
html = open(html_path, encoding='utf-8').read()

start = html.index('/* The "m-37C Plus')
fn = html.index('function badge(g){', start)
end = html.index('\n}\n', fn) + 3

block = (
'/* The "m-37C Plus = S SUZUKI =" badge on the low-F end cap: a vector TRACE of the owner\'s photo of the real\n'
'   badge (tools/badge_crop.png -> tools/trace_badge.py -> tools/badge_paths.json; regenerate with\n'
'   tools/build_badge.py). Canvas %sx%s units = the recessed panel, mapped to its true aspect (the photo was\n'
'   oblique). Drawn beside the keys, rotated -90 so it reads bottom-to-top in Flat view and upright in Held view,\n'
'   exactly as on the instrument. No font involved. */\n' % (data['w'], data['h']) +
'const BADGE={w:%s,h:%s,iou:%s,d:"%s"};\n' % (data['w'], data['h'], data.get('iou', 0), data['d']) +
'function badge(g){\n'
'  const k=150/BADGE.w, th=BADGE.h*k, px=g.nutX-6-th, py=(g.H-150)/2+150;   /* panel: 150 long, beside the keys */\n'
'  return \'<g transform="translate(\'+px+\' \'+py+\') rotate(-90) scale(\'+k+\')" style="pointer-events:none">\'\n'
'    +\'<rect x="-2" y="-2" width="\'+(BADGE.w+4)+\'" height="\'+(BADGE.h+4)+\'" rx="10" fill="\'+COL.blueDk+\'" stroke="#6b93c8" stroke-opacity=".55" stroke-width="1.6"/>\'\n'
'    +\'<rect x="0.5" y="0.5" width="\'+(BADGE.w-1)+\'" height="\'+(BADGE.h-1)+\'" rx="8" fill="\'+COL.blue+\'"/>\'\n'
'    +\'<path d="\'+BADGE.d+\'" fill="#e8edf3" fill-rule="evenodd"/></g>\';\n'
'}\n')
html = html[:start] + block + html[end:]
open(html_path, 'w', encoding='utf-8', newline='\n').write(html)
print('embedded badge: %d contours, %d points, %d chars, IoU %s' % (data['contours'], data['points'], len(data['d']), data.get('iou')))
