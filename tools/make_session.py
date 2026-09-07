#!/usr/bin/env python
r"""
make_session.py - build the guided REAPER recording session for the 37 melodica samples.

Creates:
  <project dir>/Melodica Samples.rpp   REAPER 7 project: 60 BPM, 44.1 kHz, 24-bit, two tracks
                                       (Guide: cue audio, not armed; Melodica: armed, input 1, no monitoring),
                                       a marker + region per note (regions named 53..89 for $region rendering),
                                       render preset = project regions -> Rendered\<region>.wav
  <project dir>/Media/Guide.wav        the cue track: reference tone (0-1.6 s), three count ticks (1, 2, 3 s),
                                       play on beat 4 (silent), release tick at 7 s; 8 s per note, 4 s lead-in
  <project dir>/RECORDING.md           copied from tools/RECORDING.md if present

Timeline constants are shared with slice_samples.py (LEAD=4, SLOT=8, play at +4).
Reference tones use a WAV per note named NN.wav from --ref (e.g. the Forest Melodica samples, private use
only) and fall back to a plain sine if a file is missing.
"""
import argparse, math, os, shutil, struct, sys, uuid
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slice_samples import read_wav, resample, write_wav24, note_name, SR, LO, HI, LEAD, SLOT, PLAY_AT, SEARCH

TOTAL = LEAD + (HI - LO + 1) * SLOT  # 300 s

def guid():
    return '{' + str(uuid.uuid4()).upper() + '}'

def loop_points(path):
    d = open(path, 'rb').read(); pos = 12
    while pos + 8 <= len(d):
        cid, sz = d[pos:pos + 4], struct.unpack('<I', d[pos + 4:pos + 8])[0]
        if cid == b'smpl':
            b = d[pos + 8:pos + 8 + sz]; n = struct.unpack('<I', b[28:32])[0]
            if n:
                s, e = struct.unpack('<IIIIII', b[36:60])[2:4]
                return s, e
        pos += 8 + sz + (sz & 1)
    return None

def ref_tone(midi, refdir, dur=1.6, level_db=-14.0):
    """A sustained reference of the target pitch: the sample looped to `dur`, else a sine."""
    n = int(dur * SR)
    out = None
    p = os.path.join(refdir, f'{midi}.wav') if refdir else None
    if p and os.path.exists(p):
        x, sr = read_wav(p); x = resample(x, sr)
        lp = loop_points(p) if sr == SR else None
        if lp and lp[1] > lp[0] + 32 and lp[1] < len(x):
            s, e = lp
            head = x[:e + 1]
            cyc = x[s:e + 1]
            reps = int(math.ceil((n - len(head)) / len(cyc))) + 1
            out = np.concatenate([head] + [cyc] * max(reps, 0))[:n]
        else:
            out = np.resize(x, n) if len(x) < n else x[:n]
    if out is None:
        t = np.arange(n) / SR
        f = 440.0 * 2 ** ((midi - 69) / 12)
        out = 0.6 * np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t) + 0.1 * np.sin(6 * np.pi * f * t)
    out = out.astype(np.float32)
    fade = int(0.02 * SR)
    out[:fade] *= np.linspace(0, 1, fade, dtype=np.float32)
    out[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)
    out *= (10 ** (level_db / 20)) / (np.max(np.abs(out)) + 1e-9)
    return out

def tick(freq=1000.0, dur=0.03, level_db=-10.0):
    n = int(dur * SR); t = np.arange(n) / SR
    env = np.exp(-t * 60)
    return (np.sin(2 * np.pi * freq * t) * env * 10 ** (level_db / 20)).astype(np.float32)

def build_guide(refdir):
    g = np.zeros(int(TOTAL * SR), dtype=np.float32)
    def put(t, y):
        a = int(t * SR); g[a:a + len(y)] += y[:len(g) - a]
    # lead-in: three soft ticks at 1, 2, 3 s so the first slot doesn't surprise
    for t in (1.0, 2.0, 3.0):
        put(t, tick(700, level_db=-20))
    for midi in range(LO, HI + 1):
        T = LEAD + (midi - LO) * SLOT
        put(T, ref_tone(midi, refdir))
        put(T + 1.0, tick(900, level_db=-14)); put(T + 2.0, tick(900, level_db=-14)); put(T + 3.0, tick(1400, level_db=-8))
        put(T + 7.0, tick(600, dur=0.05, level_db=-22))  # release cue
    return np.clip(g, -1, 1)

TEMPLATE_HEAD = """<REAPER_PROJECT 0.1 "7.79/win64" 1788728847 0
  <NOTES 0 2
{notes}
  >
  RIPPLE 0 0
  GROUPOVERRIDE 0 0 0 0
  AUTOXFADE 129
  ENVATTACH 3
  POOLEDENVATTACH 0
  TCPUIFLAGS 0
  MIXERUIFLAGS 11 48 0
  ENVFADESZ10 40
  PEAKGAIN 1
  FEEDBACK 0
  PANLAW 1
  PROJOFFS 0 0 0
  MAXPROJLEN 0 0
  GRID 3199 8 1 8 1 0 0 0
  TIMEMODE 1 5 -1 30 0 0 -1 0
  VIDEO_CONFIG 0 0 65792
  PANMODE 3
  PANLAWFLAGS 3
  CURSOR 0
  ZOOM 4 0 0
  VZOOMEX 6 0
  USE_REC_CFG 0
  RECMODE 1
  SMPTESYNC 0 30 100 40 1000 300 0 0 1 0 0
  LOOP 0
  LOOPGRAN 0 4
  RECORD_PATH "Media" ""
  <RECORD_CFG
    ZXZhdxgAAQ==
  >
  <APPLYFX_CFG
  >
  RENDER_FILE "{render_dir}"
  RENDER_PATTERN $region
  RENDER_FMT 0 1 44100
  RENDER_1X 0
  RENDER_RANGE 3 0 0 18 1000
  RENDER_RESAMPLE 3 0 1
  RENDER_ADDTOPROJ 0
  RENDER_STEMS 0
  RENDER_DITHER 0
  RENDER_TRIM 0.000001 0.000001 0 0
  TIMELOCKMODE 1
  TEMPOENVLOCKMODE 1
  ITEMMIX 1
  DEFPITCHMODE 589824 0
  TAKELANE 1
  SAMPLERATE 44100 0 0
  <RENDER_CFG
    ZXZhdxgAAQ==
  >
  LOCK 1
  <METRONOME 6 2
    VOL 0.25 0.125
    BEATLEN 4
    FREQ 1760 880 1
    SAMPLES "" "" "" ""
    SPLIGNORE 0 0
    SPLDEF 2 660 "" 0 ""
    SPLDEF 3 440 "" 0 ""
    PATTERN 0 169
    PATTERNSTR ABBB
    MULT 1
  >
  GLOBAL_AUTO -1
  TEMPO 60 4 4 0
  PLAYRATE 1 0 0.25 4
  SELECTION 0 0
  SELECTION2 0 0
  MASTERAUTOMODE 0
  MASTERTRACKHEIGHT 0 0
  MASTERPEAKCOL 16576
  MASTERMUTESOLO 0
  MASTERTRACKVIEW 0 0.6667 0.5 0.5 0 0 0 0 0 0 0 0 0 0 1
  MASTERHWOUT 0 0 1 0 0 0 0 -1
  MASTER_NCH 2 2
  MASTER_VOLUME 1 0 -1 -1 1
  MASTER_PANMODE 3
  MASTER_PANLAWFLAGS 3
  MASTER_FX 1
  MASTER_TRACKID {g_master}
  MASTER_SEL 0
  <MASTERPLAYSPEEDENV
    EGUID {g_speed}
    ACT 0 -1
    VIS 0 1 1
    LANEHEIGHT 0 0
    ARM 0
    DEFSHAPE 0 -1 -1
  >
  <TEMPOENVEX
    EGUID {g_tempo}
    ACT 0 -1
    VIS 1 0 1
    LANEHEIGHT 0 0
    ARM 0
    DEFSHAPE 1 -1 -1
  >
{markers}
  RULERHEIGHT 86 86
  RULERLANE 1 4 "" 0 -1 0
  RULERLANE 2 8 "" 0 -1 0
  <PROJBAY
  >
"""

TRACK_TMPL = """  <TRACK {tid}
    NAME {name}
    PEAKCOL {color}
    BEAT -1
    AUTOMODE 0
    PANLAWFLAGS 3
    VOLPAN {vol} 0 -1 -1 1
    MUTESOLO 0 0 0
    IPHASE 0
    PLAYOFFS 0 1
    ISBUS 0 0
    BUSCOMP 0 0 0 0 0
    SHOWINMIX 1 0.6667 0.5 1 0.5 0 0 0 0
    FIXEDLANES 9 0 0 0 0
    SEL {sel}
    REC {rec}
    VU 2
    TRACKHEIGHT {height} 0 0 0 0 0 0
    INQ 0 0 0 0.5 100 0 0 100
    NCHAN 2
    FX 1
    TRACKID {tid}
    PERF 0
    MIDIOUT -1 -1
    MAINSEND 1 0
{items}  >
"""

ITEM_TMPL = """    <ITEM
      POSITION 0
      SNAPOFFS 0
      LENGTH {length}
      LOOP 0
      ALLTAKES 0
      FADEIN 1 0.01 0 1 0 0 0
      FADEOUT 1 0.01 0 1 0 0 0
      MUTE 0 0
      SEL 0
      IGUID {ig}
      IID 1
      NAME Guide.wav
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {g}
      <SOURCE WAVE
        FILE "{file}"
      >
    >
"""

def color(r, g, b):
    return 0x1000000 | (r | (g << 8) | (b << 16))

def build_rpp(project_dir, guide_path, guide_len):
    notes = [
        'Melodica sample session - Suzuki M-37C Plus, F3..F6 (MIDI 53..89), 37 notes.',
        'Each note has an 8-second slot: hear the reference pitch, count 1-2-3 on the ticks,',
        'PLAY on beat 4 (no tick) and hold a steady mf note until the soft release tick, then stop.',
        'Recording: headphones on, mic on input 1, put the cursor at the start (Home), Ctrl+R, play along.',
        'Export: run tools/slice_samples.py --rpp on this project (see RECORDING.md), or File > Render',
        '(Bounds: Project regions, name $region) with the Guide track muted.',
    ]
    notes_txt = '\n'.join('    |' + n for n in notes)
    markers = []
    c1, c2 = color(45, 212, 191), color(31, 95, 168)
    for i, midi in enumerate(range(LO, HI + 1)):
        T = LEAD + (midi - LO) * SLOT
        markers.append(f'  MARKER {i + 1} {T:g} "{note_name(midi)} {midi}" 0 {c1 if i % 2 == 0 else c2} 1 R {guid()} 0')
    for i, midi in enumerate(range(LO, HI + 1)):
        T = LEAD + (midi - LO) * SLOT
        rid = 100 + i
        markers.append(f'  MARKER {rid} {T + SEARCH[0]:g} "{midi}" 1 {c1 if i % 2 == 0 else c2} 1 R {guid()} 0')
        markers.append(f'  MARKER {rid} {T + SLOT:g} "" 1')
    render_dir = os.path.join(project_dir, 'Rendered').replace('\\', '\\\\') if False else os.path.join(project_dir, 'Rendered')
    head = TEMPLATE_HEAD.format(notes=notes_txt, render_dir=render_dir, g_master=guid(), g_speed=guid(), g_tempo=guid(),
                                markers='\n'.join(markers))
    item = ITEM_TMPL.format(length=f'{guide_len:.6f}', ig=guid(), g=guid(), file=guide_path)
    guide = TRACK_TMPL.format(tid=guid(), name='Guide', color=color(31, 95, 168), vol=0.5, sel=0,
                              rec='0 -1 0 0 0 0 0 0', height=60, items=item)
    melo = TRACK_TMPL.format(tid=guid(), name='Melodica', color=color(200, 16, 46), vol=1, sel=1,
                             rec='1 0 0 0 0 0 0 0', height=180, items='')
    return head + guide + melo + '>\n'

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--project-dir', required=True)
    ap.add_argument('--ref', default=None, help='folder of NN.wav reference tones (optional)')
    a = ap.parse_args()
    pd = os.path.abspath(a.project_dir)
    os.makedirs(os.path.join(pd, 'Media'), exist_ok=True)
    os.makedirs(os.path.join(pd, 'Rendered'), exist_ok=True)
    g = build_guide(a.ref)
    guide_path = os.path.join(pd, 'Media', 'Guide.wav')
    write_wav24(guide_path, g)
    rpp = build_rpp(pd, guide_path, len(g) / SR)
    rpp_path = os.path.join(pd, 'Melodica Samples.rpp')
    open(rpp_path, 'w', encoding='utf-8', newline='\n').write(rpp)
    doc = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'RECORDING.md')
    if os.path.exists(doc):
        shutil.copy(doc, os.path.join(pd, 'RECORDING.md'))
    print('project :', rpp_path)
    print('guide   :', guide_path, f'({len(g) / SR:.0f} s)')
    print('regions :', HI - LO + 1, f'({LO}..{HI}), slot {SLOT:g} s, lead {LEAD:g} s, play at +{PLAY_AT:g} s')

if __name__ == '__main__':
    main()
