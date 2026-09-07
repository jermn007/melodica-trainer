#!/usr/bin/env python
"""
slice_samples.py - turn a melodica recording into the app's sample set.

Produces, for every MIDI note 53..89 (F3..F6, the Suzuki M-37C Plus):
  <out>/NN.wav        24-bit mono 44.1 kHz, trimmed to the attack, peak-normalised,
                      with a seamless loop stored in the WAV 'smpl' chunk
  <out>/samples.json  manifest: file, loopStart/loopEnd (seconds + samples), gain, pitch check
  <out>/REPORT.md     per-note table: detected pitch vs expected, cents, level, loop length, warnings

Three input modes:
  --rpp  "<project>.rpp"   read the recorded take(s) on the 'Melodica' track from the REAPER project
                           (item position + source file), slice by the guided-session timeline
  --wav  take.wav [--offset S]   one long take that starts at project time S (default 0), same timeline
  --dir  folder/           already-separated files named NN.wav (e.g. REAPER "render project regions"
                           output, or an existing sample pack): trim/loop/normalise only

Timeline (must match make_guide.py and the project's regions):
  60 BPM, one 8-second slot per note, first slot starts at LEAD seconds.
  In each slot: reference tone 0-2 s, clicks at 2 s and 3 s, PLAY from 4 s and hold until 7 s.
  The note is searched for between slot+3.5 s and slot+6.0 s.

Requires numpy. ffmpeg is used only when the input is not a plain PCM WAV.
"""
import argparse, json, math, os, re, struct, subprocess, sys
import numpy as np

SR = 44100
LO, HI = 53, 89
LEAD = 4.0          # seconds before the first slot
SLOT = 8.0          # seconds per note
PLAY_AT = 4.0       # play cue inside the slot
SEARCH = (3.5, 6.0) # the region each note is expected in (used by make_session for the ruler regions)
WINDOW = (-0.5, 8.0) # where the slicer actually looks for the note: anywhere in the slot (notes are 8 s apart)
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def note_name(m):
    return NAMES[m % 12] + str(m // 12 - 1)

def slot_start(midi):
    return LEAD + (midi - LO) * SLOT

# ---------------------------------------------------------------- WAV I/O
def read_wav(path):
    """Return (float32 mono array, sample_rate). Handles 16/24/32-bit PCM and float WAVs; falls back to ffmpeg."""
    d = open(path, 'rb').read()
    if d[:4] != b'RIFF' or d[8:12] != b'WAVE':
        return read_via_ffmpeg(path)
    pos, fmt, fmt_body, data = 12, None, None, None
    while pos + 8 <= len(d):
        cid, sz = d[pos:pos + 4], struct.unpack('<I', d[pos + 4:pos + 8])[0]
        body = d[pos + 8:pos + 8 + sz]
        if cid == b'fmt ':
            fmt = struct.unpack('<HHIIHH', body[:16]); fmt_body = body
        elif cid == b'data':
            data = body
        pos += 8 + sz + (sz & 1)
    if fmt is None or data is None:
        return read_via_ffmpeg(path)
    tag, ch, sr, _, _, bits = fmt
    if tag == 0xFFFE and len(fmt_body) >= 26:  # WAVE_FORMAT_EXTENSIBLE: real tag = first two bytes of the subformat GUID
        tag = struct.unpack('<H', fmt_body[24:26])[0]
    if bits == 16:
        x = np.frombuffer(data[:len(data) // 2 * 2], dtype='<i2').astype(np.float32) / 32768.0
    elif bits == 24:
        a = np.frombuffer(data[:len(data) // 3 * 3], dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = a[:, 0] | (a[:, 1] << 8) | (a[:, 2] << 16)
        v = np.where(v & 0x800000, v - 0x1000000, v)
        x = v.astype(np.float32) / 8388608.0
    elif bits == 32 and tag == 3:
        x = np.frombuffer(data[:len(data) // 4 * 4], dtype='<f4').astype(np.float32)
    elif bits == 32:
        x = np.frombuffer(data[:len(data) // 4 * 4], dtype='<i4').astype(np.float32) / 2147483648.0
    else:
        return read_via_ffmpeg(path)
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr

def read_via_ffmpeg(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype='<f4').astype(np.float32), SR

def resample(x, sr):
    if sr == SR:
        return x
    n = int(round(len(x) * SR / sr))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)

def write_wav24(path, x, loop=None, root=60, info=None):
    """Write mono 24-bit PCM with an optional smpl loop (start, end inclusive, in samples), the root/unity
    MIDI note in the smpl chunk, and an optional INFO tag dict (INAM, IART, ICMT, IPRD, ISFT...)."""
    v = np.clip(np.round(x * 8388607.0), -8388608, 8388607).astype(np.int32)
    b = np.empty((len(v), 3), dtype=np.uint8)
    b[:, 0] = v & 0xFF; b[:, 1] = (v >> 8) & 0xFF; b[:, 2] = (v >> 16) & 0xFF
    data = b.tobytes()
    fmt = struct.pack('<HHIIHH', 1, 1, SR, SR * 3, 3, 24)
    chunks = [b'fmt ' + struct.pack('<I', len(fmt)) + fmt]
    if info:
        sub = b''
        for k, val in info.items():
            s = val.encode('utf-8') + b'\x00'
            sub += k.encode('ascii')[:4].ljust(4) + struct.pack('<I', len(s)) + s + (b'\x00' if len(s) & 1 else b'')
        chunks.append(b'LIST' + struct.pack('<I', 4 + len(sub)) + b'INFO' + sub)
    chunks.append(b'data' + struct.pack('<I', len(data)) + data + (b'\x00' if len(data) & 1 else b''))
    if loop:
        s, e = loop
        smpl = struct.pack('<IIIIIIIII', 0, 0, int(1e9 / SR), int(root), 0, 0, 0, 1, 0)
        smpl += struct.pack('<IIIIII', 0, 0, s, e, 0, 0)
        chunks.append(b'smpl' + struct.pack('<I', len(smpl)) + smpl)
    body = b''.join(chunks)
    with open(path, 'wb') as f:
        f.write(b'RIFF' + struct.pack('<I', 4 + len(body)) + b'WAVE' + body)

# ---------------------------------------------------------------- analysis
def db(v):
    return 20 * math.log10(max(v, 1e-9))

def envelope(x, win=256):
    n = len(x) // win * win
    e = np.sqrt((x[:n].reshape(-1, win) ** 2).mean(axis=1))
    return e, win

def find_onset(x, thresh_db=-30.0):
    """First envelope frame above thresh (relative to full scale), backed up to the frame where it began rising."""
    e, win = envelope(x, 128)
    if not len(e):
        return None
    peak = e.max()
    if db(peak) < -45:
        return None
    thr = max(10 ** (thresh_db / 20), peak * 0.08)
    idx = np.where(e > thr)[0]
    if not len(idx):
        return None
    i = idx[0]
    while i > 0 and e[i - 1] > thr * 0.25:
        i -= 1
    return i * win

def find_end(x, onset, floor_db=-42.0, max_len=2.5):
    e, win = envelope(x[onset:], 256)
    peak = e.max()
    thr = max(10 ** (floor_db / 20), peak * 0.02)
    below = np.where(e[int(0.2 * SR / win):] < thr)[0]
    end = (below[0] + int(0.2 * SR / win)) * win if len(below) else len(x) - onset
    return onset + min(end, int(max_len * SR))

def detect_pitch(seg, fmin=60.0, fmax=2000.0):
    """Autocorrelation pitch with octave-error guard: first peak that reaches 85% of the best peak."""
    seg = seg - seg.mean()
    n = len(seg)
    w = seg * np.hanning(n)
    ac = np.fft.irfft(np.abs(np.fft.rfft(w, 2 * n)) ** 2)[:n]
    ac = ac / (ac[0] + 1e-12)
    lo, hi = int(SR / fmax), min(int(SR / fmin), n - 2)
    if hi <= lo + 2:
        return None
    r = ac[:hi + 1].copy()
    # local maxima in [lo, hi]
    cand = [k for k in range(lo, hi) if r[k] > r[k - 1] and r[k] >= r[k + 1] and r[k] > 0.3]
    if not cand:
        return None
    best = max(r[k] for k in cand)
    k = next(k for k in cand if r[k] >= 0.85 * best)
    a, b, c = r[k - 1], r[k], r[k + 1]
    k = k + 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) else k
    return SR / k

def cents(f, midi):
    return 1200 * math.log2(f / (440.0 * 2 ** ((midi - 69) / 12)))

def find_loop(x, start, end, period, target=0.12):
    """Pick loopStart/loopEnd (inclusive end sample index) inside [start, end): a whole number of periods,
    about `target` seconds long, at the position where the waveform repeats most exactly."""
    P = period
    k = max(4, int(round(target * SR / P)))
    L = int(round(k * P))
    W = int(round(2 * P))  # comparison window
    lo_s = start
    hi_s = end - L - W - 1
    if hi_s <= lo_s:
        L = max(int(round(4 * P)), 64)
        hi_s = end - L - W - 1
        if hi_s <= lo_s:
            return None
    best = (1e18, None, None)
    step = max(1, (hi_s - lo_s) // 4000)
    for s in range(lo_s, hi_s, step):
        for dL in (-2, -1, 0, 1, 2):
            LL = L + dL
            d = x[s:s + W] - x[s + LL:s + LL + W]
            err = float(np.dot(d, d))
            # prefer positive-going zero crossings
            if not (x[s] <= 0 <= x[s + 1] or abs(x[s]) < 0.01):
                err *= 1.5
            if err < best[0]:
                best = (err, s, LL)
    _, s, LL = best
    if s is None:
        return None
    # refine around the best start at full resolution
    for s2 in range(max(lo_s, s - step), min(hi_s, s + step)):
        for dL in (-2, -1, 0, 1, 2):
            LL2 = L + dL
            d = x[s2:s2 + W] - x[s2 + LL2:s2 + LL2 + W]
            err = float(np.dot(d, d))
            if err < best[0]:
                best = (err, s2, LL2)
    _, s, LL = best
    rms = float(np.sqrt(np.mean(x[s:s + LL] ** 2)) + 1e-9)
    seam = float(np.sqrt(best[0] / W)) / rms
    return s, s + LL - 1, seam

# ---------------------------------------------------------------- processing
def existing_loop(path):
    """(start, end_inclusive) from the WAV smpl chunk, or None."""
    d = open(path, 'rb').read(); pos = 12
    while pos + 8 <= len(d):
        cid, sz = d[pos:pos + 4], struct.unpack('<I', d[pos + 4:pos + 8])[0]
        if cid == b'smpl':
            b = d[pos + 8:pos + 8 + sz]; n = struct.unpack('<I', b[28:32])[0]
            if n:
                s, e = struct.unpack('<IIIIII', b[36:60])[2:4]
                return (s, e) if e > s else None
        pos += 8 + sz + (sz & 1)
    return None

def process_note(x, midi, report, min_hold=0.6, keep=None):
    """x: mono float audio believed to contain the note (already windowed to the slot). Returns (out, loop, meta).
    keep: (start, end) loop points already present in the source (used instead of searching when given)."""
    onset = find_onset(x)
    if onset is None:
        report.append((midi, 'MISSING', 'no signal above -45 dBFS in the window'))
        return None
    end = find_end(x, onset)
    if (end - onset) / SR < min_hold:
        report.append((midi, 'SHORT', f'note held only {(end - onset) / SR:.2f}s'))
    pre = int(0.010 * SR)
    a = max(0, onset - pre)
    seg = x[a:end].astype(np.float32).copy()
    # fade in 3 ms so the cut is clickless
    fi = min(int(0.003 * SR), len(seg))
    seg[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)
    # pitch on the steady part
    st = int(0.25 * SR); en = min(len(seg) - int(0.05 * SR), st + int(0.5 * SR))
    if en - st < int(0.1 * SR):
        st, en = int(0.05 * SR), max(int(0.15 * SR), len(seg) - int(0.02 * SR))
    f = detect_pitch(seg[st:en])
    if f is None:
        report.append((midi, 'NOPITCH', 'could not detect a pitch'))
        f = 440.0 * 2 ** ((midi - 69) / 12)
    c = cents(f, midi)
    if abs(c) > 60:
        report.append((midi, 'WRONGNOTE', f'detected {f:.1f} Hz = {note_name(int(round(69 + 12 * math.log2(f / 440))))}, {c:+.0f} cents from {note_name(midi)}'))
    elif abs(c) > 25:
        report.append((midi, 'TUNING', f'{c:+.0f} cents'))
    period = SR / f
    # loop in the steady region: from 0.30 s after onset to 0.10 s before the end
    ls, le = int(0.30 * SR), len(seg) - int(0.10 * SR)
    if keep and keep[0] - a >= 0 and keep[1] - a < len(seg):
        s0, e0 = keep[0] - a, keep[1] - a
        W = int(round(2 * period)); L = e0 + 1 - s0
        d = seg[s0:s0 + W] - seg[s0 + L:s0 + L + W] if s0 + L + W <= len(seg) else np.zeros(1)
        rms0 = float(np.sqrt(np.mean(seg[s0:e0 + 1] ** 2)) + 1e-9)
        loop = (s0, e0, float(np.sqrt(np.dot(d, d) / max(W, 1))) / rms0)
    else:
        loop = find_loop(seg, ls, le, period) if le - ls > int(0.2 * SR) else None
    if loop is None:
        ls = int(0.12 * SR); loop = find_loop(seg, ls, len(seg) - int(0.02 * SR), period, target=0.05)
    if loop is None:
        report.append((midi, 'NOLOOP', 'not enough sustained material to loop'))
        lstart, lend, seam = None, None, None
    else:
        lstart, lend, seam = loop
        if seam > 0.25:
            report.append((midi, 'LOOPSEAM', f'loop seam mismatch {seam:.2f} (audible click likely; hold the note steadier)'))
        # keep only what the player needs: through the loop end plus 20 ms
        seg = seg[:min(len(seg), lend + 1 + int(0.02 * SR))]
    # normalise peak to -1 dBFS
    peak = float(np.max(np.abs(seg)) + 1e-9)
    seg *= (10 ** (-1 / 20)) / peak
    rms = float(np.sqrt(np.mean(seg[lstart:lend + 1] ** 2))) if loop else float(np.sqrt(np.mean(seg ** 2)))
    return seg, (lstart, lend) if loop else None, dict(hz=f, cents=c, peak_in=peak, rms=rms, seam=seam, length=len(seg) / SR)

def load_take_from_rpp(rpp):
    """Find audio items on the track named 'Melodica' (else the first armed track) and return [(pos, soffs, length, file)]."""
    txt = open(rpp, encoding='utf-8', errors='replace').read()
    base = os.path.dirname(os.path.abspath(rpp))
    items = []
    for tm in re.finditer(r'<TRACK\b.*?\n(.*?)\n  >\n', txt, re.S):
        body = tm.group(1)
        name = re.search(r'^\s*NAME "?(.*?)"?\s*$', body, re.M)
        name = name.group(1) if name else ''
        if name.lower() != 'melodica':
            continue
        for im in re.finditer(r'<ITEM\b(.*?)\n    >', body, re.S):
            ib = im.group(1)
            pos = float(re.search(r'\n\s*POSITION ([\d.]+)', ib).group(1))
            ln = float(re.search(r'\n\s*LENGTH ([\d.]+)', ib).group(1))
            so = re.search(r'\n\s*SOFFS ([\d.]+)', ib); so = float(so.group(1)) if so else 0.0
            fm = re.search(r'FILE "(.*?)"', ib)
            if not fm:
                continue
            f = fm.group(1)
            if not os.path.isabs(f):
                f = os.path.join(base, f)
            items.append((pos, so, ln, f))
    return items

def assemble_from_items(items):
    """Lay the take(s) onto a project-time canvas (mono float) so slot timing applies."""
    total = max(p + l for p, _, l, _ in items) + 1.0
    canvas = np.zeros(int(total * SR), dtype=np.float32)
    for pos, so, ln, f in items:
        x, sr = read_wav(f); x = resample(x, sr)
        a = int(so * SR); b = min(len(x), a + int(ln * SR))
        p = int(pos * SR)
        canvas[p:p + (b - a)] += x[a:b]
    return canvas

def main():
    global LEAD, SLOT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--rpp'); g.add_argument('--wav'); g.add_argument('--dir')
    ap.add_argument('--offset', type=float, default=0.0, help='project time (s) at which --wav starts')
    ap.add_argument('--out', required=True, help='output folder (NN.wav, samples.json, REPORT.md)')
    ap.add_argument('--lead', type=float, default=LEAD); ap.add_argument('--slot', type=float, default=SLOT)
    ap.add_argument('--keep-loops', action='store_true', help='--dir only: reuse loop points already stored in the source WAVs')
    ap.add_argument('--artist', default='Jeremy Terhune', help='IART tag written into each WAV')
    ap.add_argument('--product', default='Suzuki M-37C Plus melodica, single notes', help='IPRD tag written into each WAV')
    args = ap.parse_args()
    LEAD, SLOT = args.lead, args.slot
    os.makedirs(args.out, exist_ok=True)

    report, manifest = [], {}
    keep_for = {}
    if args.dir:
        source = 'separate files in ' + args.dir
        def get(midi):
            p = os.path.join(args.dir, f'{midi}.wav')
            if not os.path.exists(p):
                return None
            x, sr = read_wav(p)
            if args.keep_loops and sr == SR:
                keep_for[midi] = existing_loop(p)
            return resample(x, sr)
    else:
        if args.rpp:
            items = load_take_from_rpp(args.rpp)
            if not items:
                sys.exit("no audio items found on a track named 'Melodica' in " + args.rpp)
            canvas = assemble_from_items(items)
            source = f'{len(items)} item(s) from {args.rpp}'
        else:
            x, sr = read_wav(args.wav); x = resample(x, sr)
            canvas = np.zeros(int(args.offset * SR) + len(x), dtype=np.float32)
            canvas[int(args.offset * SR):] = x
            source = f'{args.wav} at project time {args.offset:.2f}s'
        def get(midi):
            t = slot_start(midi)
            a, b = max(0, int((t + WINDOW[0]) * SR)), int((t + WINDOW[1]) * SR)
            if a >= len(canvas):
                return None
            return canvas[a:min(b, len(canvas))]

    rms_all = []
    results = {}
    for midi in range(LO, HI + 1):
        x = get(midi)
        if x is None or not len(x):
            report.append((midi, 'MISSING', 'no audio for this note')); continue
        r = process_note(x, midi, report, keep=keep_for.get(midi))
        if r is None:
            continue
        seg, loop, meta = r
        results[midi] = (seg, loop, meta); rms_all.append(meta['rms'])

    target = float(np.median(rms_all)) if rms_all else 0.1
    for midi, (seg, loop, meta) in results.items():
        gain = target / max(meta['rms'], 1e-6)
        gain = float(min(2.0, max(0.5, gain)))  # +-6 dB of level matching, applied by the app, not baked in
        write_wav24(os.path.join(args.out, f'{midi}.wav'), seg, loop, root=midi,
                    info={'INAM': f'{note_name(midi)} ({midi})', 'IART': args.artist, 'IPRD': args.product,
                          'ICMT': f'root note {midi}; loop {loop[0]}-{loop[1]} samples' if loop else f'root note {midi}',
                          'ISFT': 'slice_samples.py'})
        manifest[str(midi)] = dict(file=f'{midi}.wav', note=note_name(midi),
                                   loopStart=(loop[0] / SR) if loop else None, loopEnd=((loop[1] + 1) / SR) if loop else None,
                                   loopStartSample=loop[0] if loop else None, loopEndSample=(loop[1] + 1) if loop else None,
                                   gain=round(gain, 3), hz=round(meta['hz'], 2), cents=round(meta['cents'], 1),
                                   length=round(meta['length'], 3))
    json.dump(dict(sampleRate=SR, lo=LO, hi=HI, source=source, notes=manifest),
              open(os.path.join(args.out, 'samples.json'), 'w'), indent=1)

    # report
    warn = {}
    for midi, kind, msg in report:
        warn.setdefault(midi, []).append(f'{kind}: {msg}')
    lines = ['# Sample set report', '', f'Source: {source}', f'Notes produced: {len(results)}/37', '',
             '| MIDI | note | Hz | cents | held s | loop ms | seam | gain | warnings |', '|---|---|---|---|---|---|---|---|---|']
    for midi in range(LO, HI + 1):
        if midi in results:
            seg, loop, m = results[midi]
            lms = ((loop[1] + 1 - loop[0]) / SR * 1000) if loop else 0
            lines.append(f"| {midi} | {note_name(midi)} | {m['hz']:.1f} | {m['cents']:+.0f} | {m['length']:.2f} | {lms:.0f} | "
                         f"{(m['seam'] if m['seam'] is not None else float('nan')):.2f} | {manifest[str(midi)]['gain']:.2f} | {'; '.join(warn.get(midi, []))} |")
        else:
            lines.append(f"| {midi} | {note_name(midi)} | - | - | - | - | - | - | {'; '.join(warn.get(midi, ['MISSING']))} |")
    bad = [m for m in range(LO, HI + 1) if m not in results or any(w.startswith(('WRONGNOTE', 'LOOPSEAM', 'SHORT')) for w in warn.get(m, []))]
    lines += ['', ('**Re-record these notes:** ' + ', '.join(f'{m} ({note_name(m)})' for m in bad)) if bad else '**All 37 notes look good.**']
    open(os.path.join(args.out, 'REPORT.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
