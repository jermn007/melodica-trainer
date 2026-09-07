# Melodica Trainer — Analysis, Plan & Scoped Spec (v0.2, 2026-09-07)

A sibling of **fretboard-trainer** for the **Suzuki M-37C Plus** alto melodica: an interactive on-screen
keyboard that looks and sounds like the real instrument, teaches exactly which keys to press for any
**chord progression, chord, scale, note or melody**, and drills the learner toward five concrete goals.

Status: **built through phase 3 on 2026-09-07** (keyboard + own-recorded sound, coach, chords, drills with mic, guide;
first deploy at melodica-trainer.pages.dev; repo jermn007/melodica-trainer). See `HANDOFF.md` for the as-built
architecture and the open items (custom domain, analytics token, device QA, GUIDE evaluate pass, self-pilot).

---

## 1. Up-front analysis

### 1.1 The instrument (verified against Suzuki + Thomann product pages and the owner's photo)

| Fact | Value |
|---|---|
| Model | Suzuki **M-37C Plus** (badge on the owner's instrument reads "M-37C Plus / SUZUKI"). Colour variant of the M-37C |
| Keys | **37** (22 white, 15 black), piano layout |
| Range | **F3 → F6** (Suzuki: "f–f3"), i.e. MIDI **53–89** inclusive, three octaves F-to-F |
| Register | Alto; phosphor-bronze reeds, aluminium cover |
| Look | **Red** aluminium rail along the back edge of the keys, **blue** end caps (the low-F cap carries the "M-37C Plus / SUZUKI" badge and the chrome mouthpiece port), **cream** white keys, glossy black sharps, black ribbed flexible tube (MP-161) plugging into the low end. Back: red body with a white hand strap on chrome fittings |
| Size | 470 × 110 × 55 mm, ~940 g |
| Playing modes | (a) **held**: left hand in the strap, mouthpiece in mouth, **right hand only**; (b) **table**: flat on the desk with the flexible tube, **both hands** (how the owner plays when sitting) |
| Owner's setup | Lives on the desk next to a split ergonomic computer keyboard (photo, 2026-09-07). Seen from above it lies with the **low-F/mouthpiece end at the top and the red rail on the right**, which is the product photo rotated 90° clockwise |

Design consequences:
- The keyboard model is trivial: `midi ∈ [53, 89]`; white/black from `pc % 12`. Everything (labels, colours,
  scales, chords) keys off pitch class exactly like the fretboard's `pcAt`.
- **Low end = mouthpiece end.** The SVG reproduces that (tube on the low side) so it maps 1:1 to the physical object.
- **v1 voicings are right-hand-only** (close position within an octave). **Two-hand/table voicings come right
  after v1** on the same engine (bass note or root in the left hand, chord in the right) — the data model leaves room (§5.3).
- Three octaves is small. Chords below ~C4 sound muddy on a melodica, so the voicing engine needs a
  **preferred register** (default around C4–C5) rather than "lowest available".
- Melodica is a **breath** instrument: sustain, dynamics and articulation come from air, not the key. The sample
  library's single "Air" control (§5.5) models exactly that; the guide and pattern player can cue breathing later (§5.7).
- The instrument has no MIDI out, so the app hears it only through the **microphone** (§4.3). Single-note pitch
  detection is reliable; chord verification is an experiment for v1.5.

### 1.2 What fretboard-trainer gives us (W:\Personal\Programming\Fretboard, in sync with origin/main @ 9bcb7d7)

**Reuse as-is (copy, rename identifiers):**
- **Infra:** `package.json` scripts (`dev`/`test`/`build`/`deploy`), `build.mjs` (copy to `dist/`),
  `.npmrc` (public registry), `.gitignore`, the jsdom `smoke-test.mjs` harness, Cloudflare Pages deploy via
  `wrangler pages deploy dist --project-name …`. Wrangler is authenticated on this machine; existing
  projects: `fretboard-trainer` (fretboard.terhunelabs.com), `lastly` (lastly.terhunelabs.com).
- **Design system:** the `:root` token palette (`#0b0f17` bg, teal accent `#2dd4bf`, amber root, emerald chord),
  `.bar/.grp/.seg/.btn/.chip/.pchip` controls, 44 px touch targets, `:focus-visible` rings, SVG-only icons,
  the collapsible **Options** panel, Full-screen button, the onboarding **Guide modal** (focus trap, `localStorage` "seen" flag).
- **Motion system:** `popIn` staggered spring pop, `ringIn` lock-on ring, `pulseN` tap pulse, `chordPop`
  chip, metronome pendulum/ping/countdown bar — all gated by `prefers-reduced-motion`.
- **Music theory:** `NOTES/FLAT`, `SCALES` (pentatonics, blues w/ blue note, major, natural minor), `DIA/ROMAN`,
  `CHORD_IV`, `usesFlats`, `noteName`, `degLabel`, `diatonic`, `chordTones`, `parseChord`, the curated
  `MAJ_PROG/MIN_PROG/BLUES_12BAR` random pools, flat-spelling rules (blue notes always flat).
- **Pitch-colour system** (`PITCH`, naturals solid / accidentals split) + "Simple" role mode + legend.
- **Transport + shared beat clock:** `playProg/stepTo/stopProg`, `clockTick/startClock/retimeClock`,
  metronome woodblock click, BPM field, Mute — chord changes phase-locked to ticks.
- **A11y pattern:** every playable element `role="button" tabindex="0" aria-label`, Enter/Space activates.

**Replace:**
- `INSTRUMENTS/TUNING/NS/FMAX/positions()` → a single `KB {lo:53, hi:89}` model. Fret positions have no
  analogue; the nearest concept is the **register window** and **hand span**.
- `buildBoard()` (fretboard SVG) → `buildKeys()` (melodica SVG). Same string-template → `innerHTML` render loop.
- Triangle-wave `tone()` → a **sample player** with a synth fallback (§5.5). Keep the `tone(freq,start,dur,gain)`
  shape so the transport code ports untouched, and add `noteOn/noteOff` for held keys.
- Guitar-specific easter eggs (Alvarez inlay, lightning bolts) → M-37C Plus livery (red rail, blue caps, badge, tube).
- The chord **builder hidden behind "Build"** → the progression input is **always visible** (§3.4); it is the owner's #1 use case.

**Add (new to this app):**
- **Voicing engine** (inversions, register targeting, smooth voice-leading) and **fingering overlay**.
- **Melody line** input and playback (note names stepping in time), plus a few public-domain tunes.
- **Drill mode** with spaced retrieval and **microphone listening** — the fretboard has no assessment loop at all.
- **Scaffolding levels** for labels (all → landmarks → none).

### 1.3 Learner analysis (GUIDE archetype 07, design mode)

- **Learner:** one adult, self-directed, plays fretted instruments, already fluent in the fretboard-trainer
  vocabulary (roots, scales, diatonic chords, Roman numerals, pitch colours). New to piano-style key geography
  and to the melodica's right-hand/breath technique. Plays held (right hand) standing and two-handed at the desk.
- **Performance gap:** cannot yet look at a chord symbol, note name or progression and land the right keys
  quickly enough to play through it in time.
- **Cause:** knowledge/skill gap (key geography, voicings, fingering), **not** environmental — an app is an
  appropriate intervention. Breath/tone technique is a motor skill the app can only cue, not train.
- **Constraints:** practice happens with the instrument in hand or on the desk → the app must work **on a
  tablet/phone, full-screen, at arm's length, mostly hands-off** (auto-stepping progressions, big keys, metronome),
  and on the desktop next to the split keyboard, where the **microphone** can listen.
- **Transfer bridge (ARCS Relevance):** reuse the *exact* colour system and terminology from fretboard-trainer so
  existing knowledge maps straight onto the keyboard; the sound is a sampled melodica so what you hear matches what you play.

### 1.4 Objectives (Mager format: behaviour · condition · criterion)

| # | Objective | Mode that teaches it | Drill that assesses it |
|---|---|---|---|
| O1 | Given a **note name**, press (or play) **every** key of that pitch class on the 37-key board within 3 s, 90 % over a set | Explore (scale highlighting, labels) | Note drill (screen or mic) |
| O2 | Given a **major/minor/dim triad symbol**, play a **root-position** voicing in the target register within 5 s, 90 % | Chords mode (fingering overlay) | Chord drill (screen) |
| O3 | Given a **chord progression** (typed or random), play it **in time at ≥ 60 BPM** using smooth (nearest-inversion) voicings with ≤ 1 miss per cycle | Progression coach + metronome | Progression drill (timed, screen) |
| O4 | Given a **short melody** (4–8 notes, shown as lit keys), play it back on the instrument at 60 BPM with ≤ 1 wrong note | Melody line playback | Melody drill (mic) |
| O5 | Given a **key**, play the **major scale one octave** up and down with standard right-hand fingering at 60 BPM | Scale view with fingering | Scale drill (mic, phase 4) |
| O6 | Given a **7th chord symbol** (7, m7, maj7), play a voicing within 5 s, 80 % | Chords mode | Chord drill (7ths tier) |

The **Guide modal lists these plainly** (Gagné event 2) and the drills report against their criteria (archetype 10:
objective ↔ strategy ↔ assessment coherence — this table *is* the alignment check). This is not a course; it is a
practice tool whose drills are short, self-chosen and always available (Knowles: self-direction, immediacy).

---

## 2. Product definition (decisions taken 2026-09-07)

- **Name:** Melodica Trainer. **Repo:** `jermn007/melodica-trainer` (new repo, shares no history with fretboard-trainer).
- **Hosting:** Cloudflare Pages project `melodica-trainer` → `melodica-trainer.pages.dev` + custom domain
  **`melodica.terhunelabs.com`**. Static, no env vars. One self-contained `index.html` plus root assets and a
  `samples/` folder; zero runtime dependencies; the only external request is the Cloudflare Web Analytics beacon.
- **Sound:** a **sampled melodica** (§5.5). The app must still work with no samples (synth fallback) so `index.html` stays self-sufficient.
- **Input:** on-screen keys (mouse/touch/multi-touch), computer-keyboard piano map, and the **microphone** for drills. **No Web MIDI.**
- **Posture:** right-hand-only voicings in v1; two-hand/table voicings immediately after v1.
- **Non-goals for v1:** staff notation, two-hand voicings, song library beyond a handful of public-domain melodies,
  accounts/sync, other melodica models. All listed in §6 so the data model doesn't paint us into a corner.

---

## 3. UI spec

### 3.1 Layout (same skeleton as fretboard-trainer)

```
┌ top bar ───────────────────────────────────────────────────────────────┐
│ Mode [Explore|Chords|Drill]  Root ▾  Scale ▾  Register ▾  BPM [96] ⏱  … Options ⤢ ? │
├ options (collapsed) ───────────────────────────────────────────────────┤
│ Labels [All|Landmarks|None]  Names [Notes|Degrees]  Colour [Simple|Pitch] │
│ Fingering [On|Off]  Voicing [Root|Smooth]  View [Flat|Held]  Sound [Melodica|Simple|Off]  Air ──●── │
├ coach strip (Explore) ─────────────────────────────────────────────────┤
│ [ Type a progression or melody: Am F C G  ▸ ]  Set  Clear  Random   ·  In this key: C Dm Em F G Am B° │
│ ◀ ▶ Play  Mute   ·  Pattern: I – V – vi – IV        [ C ] [ G ] [ Am ] [ F ]                          │
├ stage ─────────────────────────────────────────────────────────────────┤
│  C Major · now: G (1st inv · fingers 1-2-5)                                          ▶ G            │
│  ╔══ red rail ════════════════════════════════════════════════════╗                                 │
│ ⊂═tube═[blue cap] ▮▯▮▯▯▮▯▮▯▮▯▯ … 37 keys … ▯▮▯ [blue cap]                                       │
│  legend: ● root  ○ scale  ◎ chord tone  1 2 3 fingering                                             │
└────────────────────────────────────────────────────────────────────────┘
```

- **Stage** (the keyboard) is the hero; same `.svgwrap` absolute-fill + `preserveAspectRatio="xMidYMid meet"`
  technique so it fits the viewport with no page scroll on desktop/tablet-landscape; portrait hugs the aspect ratio.
- The melodica is **much wider than tall** (keyboard ≈ 5:1, wider than the fretboard's 2.9:1). On phones in
  portrait the keys would be tiny, so **Held view (rotated 90°)** is the natural portrait layout (§3.3) and ships in v1.
- The **coach strip** replaces the fretboard's collapsed builder: the text input is always visible because "type a
  progression, get taught where to press" is the primary job. The diatonic chips sit beside it as a palette.

### 3.2 Keyboard SVG (`buildKeys()`)

- Geometry: 22 white keys of width `W`, black keys `0.6 W` wide × `0.62` height, offset by the standard piano
  pattern (F–G, G–A, A–B, C–D, D–E have blacks). ViewBox roughly `(22·W + chrome) × (keyH + chrome)`.
- Livery: red rail (`#c8102e`-ish) along the back edge, blue end caps (`#1f5fa8`-ish) with an "M-37C Plus / SUZUKI"
  badge and a chrome mouthpiece ring on the low-F cap, cream whites (`#f3ead8`), glossy black sharps (`#151515` with a
  highlight), thin key gaps, subtle drop shadow under blacks, the black ribbed tube curling off the low cap.
  Literal hex only in SVG presentation attributes (the `var(--x)` gotcha).
- **Each key** = `<g class="key" role="button" tabindex="0" data-midi="…" aria-label="C4, degree 1, root">`.
  Pressed state = fill shift + 2 px translateY (spring easing), plus the pitch dot/label overlay used for
  highlighting. Multi-touch: `pointerdown/up/cancel` per key so chords can be held with several fingers; a held
  key sustains (looped sample) until release.
- **Overlays** (drawn on the key face, bottom third for whites / lower part for blacks):
  - Label (note name or degree) per the scaffolding level: **All** · **Landmarks** (only C's and F's) · **None**.
  - Pitch colour dot (default **Simple** = amber root / light scale / dim; **Pitch** = the shared 12-colour system).
  - Root ring (white), blue-note ring, chord-tone emerald ring, exactly as on the fretboard.
  - **Fingering numeral** (1–5) for chord/scale keys when Fingering is on.
  - **Next-up ghost**: during progression playback, the upcoming chord's keys show a faint outline one beat early
    (Mayer signalling; gives the hand time to move).
- **Register window:** a highlighted span (e.g. C4–C5) that dims keys outside it; "Full range" is the default;
  presets: Low (F3–F4), Middle (C4–C5), High (C5–F6), plus Auto (follows the voicing).
- Tap/click/Enter plays the key; the tap pulse animation carries over.

### 3.3 Views

- **Flat** (default on landscape/desktop): instrument as in the product photo, low F left, tube left, red rail on top.
- **Held** (default on portrait phones, toggle otherwise): the Flat SVG rotated **90° clockwise**, so the keyboard runs
  top-to-bottom with **low F at the top and the red rail on the right** — exactly the owner's desk photo and what the
  player sees looking down while holding the strap. Labels stay upright (counter-rotate text).

### 3.4 Modes

**Explore** (default) — the **progression / melody coach**.
- Type anything into the coach input: a **progression** (`Am F C G`, `Dm7 | G7 | Cmaj7`, Roman numerals `I V vi IV`
  in the current key) or a **melody** (`C4 D4 E4 C4`, or bare names `C D E C` placed in the register window; `-` holds,
  `.` rests). The parser decides which it is (chord symbols vs. single notes); mixed lines are rejected with a clear message.
- Or tap **In this key** chips to build a progression, or **Random** for a curated pattern (12-bar blues when a blues scale is on).
- **Play / ◀ ▶ step**: each chord (or note) lights its keys with fingering; chords advance on the beat clock; the
  **now** readout names the chord, inversion and fingers; the next chord ghosts one beat early. Smooth voicing on by default.
- Root + scale still light the scale across all three octaves, as on the fretboard, so the coach always shows the key context.

**Chords** — chord finder: type or pick any chord → best voicing lit with fingering; controls: **Inversion**
(root/1st/2nd/3rd), **Octave** (±), **Voicing** (Root-position vs Smooth), and a strip of the **alternate placements**
across the range. Shows the chord's spelling ("G B D") and what each key is (1·3·5).

**Drill** — retrieval practice toward the objectives (§4.2). The stage shows an unlabelled (or landmark-labelled)
keyboard and a prompt card; the learner answers by pressing keys on screen, on the computer keyboard, or by
**playing the real melodica into the microphone**; feedback is immediate and per key.

### 3.5 Guide modal (Gagné events 1–3, ARCS)

Welcome card in the fretboard style: a small melodica logo, one paragraph "what this is", the **six objectives** in
plain language, a map of the three modes, the computer-keyboard map, and a **"Try this first"** recipe:
> Explore · type `C G Am F` · Play at 60 BPM and press along. Then Drill → Notes with Landmarks labels.
Shown once (`localStorage` flag), reopenable from the `?` button.

---

## 4. Learning design (GUIDE, design mode)

Archetypes applied as forward criteria; each item names the dimension it satisfies so the later evaluate-mode
pass (archetype 10 gate) has something to check against. Deliberately **not a course**: no mandatory sequence,
no lessons — a coach (Explore/Chords) plus short, self-selected drills that measure progress against §1.4.

### 4.1 Sequence & scaffolding (03 Sequencing, 09 Cognitive Neuroscience)

Four tiers, recommended (not enforced) in order:

1. **Geography** — C landmarks, then all naturals, then sharps/flats; one octave, then all three.
2. **Triads** — diatonic triads in C, then G/F, then all keys; root position → inversions.
3. **Progressions & melodies** — curated pools (I–V–vi–IV, ii–V–I, 12-bar blues) and short tunes at 60 BPM; tempo ladder.
4. **Extensions** — 7ths, scale fingerings.

Gradual release inside every tier = the **label levels**: All → Landmarks → None (fade the cue, keep the task).
Retrieval practice, spacing and interleaving are built into Drill (§4.2). Attention management: one prompt at a
time, no timers on the first pass, the stage never shows more than the current task.

### 4.2 Drill mode (02 Assessment, 09)

| Item type | Objective | Prompt | Answer channel | Correct when |
|---|---|---|---|---|
| Find note | O1 | "Press every **C**" | screen / keys / **mic** (mic: any octave, one at a time) | all instances pressed (screen) or the pitch class sounded (mic) |
| Play chord | O2/O6 | "Play **Dm**" | screen / keys | pressed set = any allowed voicing in the register |
| Play progression | O3 | four chords on the beat clock | screen / keys | each chord correct on its beat, ≤ 1 miss per cycle |
| Play melody | O4 | 4–8 keys light in sequence, then "your turn" | **mic** / screen | each note detected in order within the beat window |
| Play scale | O5 | "C major, up and down" | mic / screen | notes in order with the fingering shown *(phase 4)* |

- **Item pool** is generated from theory (no hand-authored bank): 12 pitch classes × label levels; diatonic triads
  per key; progressions from the random pools; melodies from the coach input history plus a few public-domain tunes
  (Ode to Joy, Twinkle, Mary Had a Little Lamb, Frère Jacques, Amazing Grace, Happy Birthday — all transposed to fit F3–F6).
- **Scoring:** correctness per the table; time-to-answer recorded. Criteria from §1.4 drive the session verdict.
- **Spacing:** Leitner boxes per item key (`"note:C"`, `"chord:Dm"`, `"prog:I-V-vi-IV:C"`, `"mel:ode-to-joy"`) in
  `localStorage`; misses demote, hits promote; the next item is drawn weighted toward low boxes and interleaved across
  types. A session is short by design (10 items) and ends with a summary: accuracy, median time, what's due.
- **Feedback:** per key on release (green/red flash + the correct keys shown after a miss), never blocking; a
  "show me" button reveals the answer with fingering (worked example, then retry).

### 4.3 Microphone listening (new; needs HTTPS — fine on Pages and on localhost)

- `getUserMedia({audio:{echoCancellation:false, noiseSuppression:false}})` → `AnalyserNode` → **monophonic pitch
  detection** (McLeod/autocorrelation, ~2048-sample window, 40 ms hop) → pitch class + octave with a confidence gate;
  a note "counts" after ~80 ms of stable pitch. The melodica's bright, steady tone detects well; F3–F6 is comfortably
  inside the algorithm's range.
- Mic is **opt-in per session** (a Listen toggle in Drill), with a live "hearing: G4" readout so the learner can trust it
  and a level meter for mic placement. Mute the app's own sound while listening to avoid feedback.
- **Chord verification** by mic (chroma/FFT check that the expected pitch classes are present and others aren't) is an
  experiment for **v1.5**, gated behind Options; not required for v1.
- Nothing is recorded or uploaded; audio stays in the page.

### 4.4 Multimedia & accessibility (04, 05)

- Signalling over decoration: the livery is subdued (opacity/desaturation) whenever an overlay is active so highlights
  dominate. Fingering numerals sit on the key they refer to (spatial contiguity). No redundant text narration.
- Colour is never the only cue: labels, rings and aria-labels carry the same information (UDL / WCAG 1.4.1).
- Keys are keyboard-operable buttons with names; the SVG has an accessible name and `<title>`; contrast ≥ 4.5:1
  for text on keys; `prefers-reduced-motion` disables all animation.
- Sound and mic are optional; every drill can be completed on screen.

### 4.5 Formative evaluation (06) — self-pilot

Five practice sessions with the real instrument beside the tablet and at the desk with the mic. Log: time to first
chord, frictions, mic false positives/negatives, any mismatch between screen and instrument (orientation, key size,
register). Revise before the polish phase.

### 4.6 Alignment gate (10)

The §1.4 table is the artefact. Before Phase 3 ships, run the GUIDE skill in **evaluate mode** on the Guide text +
drill design (archetypes 03, 02, 10) and fix anything under 4.

---

## 5. Technical spec

### 5.1 Files (mirrors fretboard-trainer)

```
Melodica/
├ index.html          the whole app (CSS + markup + one <script>); works with or without samples/
├ samples/            NN.mp3 for MIDI 53–89 + samples.json (loop points, per-note gain)  [generated, see 5.5]
├ samples.mjs         WAV → MP3 + manifest builder (ffmpeg, already installed via winget)
├ build.mjs           copies index.html + root assets + samples/ → dist/
├ smoke-test.mjs      jsdom: renders, 37 keys, parser, voicing engine, drill scoring, Leitner
├ package.json        dev/test/build/deploy (deploy → wrangler pages deploy dist --project-name melodica-trainer)
├ .npmrc .gitignore   (gitignore: dist/, node_modules/, and any sample set we may not redistribute)
├ favicon.svg icon-512.png apple-touch-icon.png og.png   (new artwork: red/blue melodica motif)
├ README.md  HANDOFF.md  SPEC.md (this)
```

### 5.2 Data model

```js
const KB = { lo:53, hi:89 };                       // Suzuki M-37C Plus: F3–F6
const isBlack = m => [1,3,6,8,10].includes(m%12);
const S = { mode:'explore', root:0, scale:'major', labels:'all', names:'name', color:'role',
            register:null /* or {lo,hi} */, voicing:'smooth', inversion:0, octave:0, fingering:true,
            hands:'right' /* 'both' after v1 */, view:'flat', sound:'melodica', air:0.8,
            line:{kind:'prog'|'melody', items:[], idx:-1}, listen:false };
```
`KB` is the only instrument-specific constant (a future 32/44-key selector is a data change). `line` replaces the
fretboard's `prog` so chords and melodies share one transport.

### 5.3 Voicing engine (new)

```
voicings(rootPC, qual, KB, hands)  → all close-position voicings (root pos + inversions) fitting [lo,hi];
                                     hands:'both' (post-v1) adds a LH root/5th below the RH shape
pickVoicing(list, {mode, register, prev})
   mode 'root'   : root position nearest the register centre (default centre = 66 ≈ F#4)
   mode 'smooth' : minimise total semitone movement from `prev` (common tones held), tie → lower
fingering(voicing)                 → RH numerals: triad root 1-3-5 · 1st inv 1-2-5 · 2nd inv 1-3-5;
                                     7ths root 1-2-3-5 · inversions 1-2-4-5 (rule table, overridable)
parseLine(text, key)               → {kind:'prog', items:[{sym,rootPC,qual}]} | {kind:'melody', items:[{midi|rest|hold}]}
                                     accepts chord symbols, Roman numerals in the key, note names with/without octave
```

### 5.4 Input

- Pointer (mouse/touch, multi-touch) on keys; keyboard focus + Enter/Space.
- **Computer-keyboard piano map:** `Z S X D C V G B H N J M` = C4…B4, `Q 2 W 3 E R 5 T 6 Y 7 U` = C5…B5,
  `,` `.` shift octave. Match on `event.code` (physical position) so the owner's split ergonomic keyboard and any
  remapped layout still work; the map is shown in the Guide.
- **Microphone** (§4.3) for Drill.
- No Web MIDI (owner decision).

### 5.5 Audio — sampled melodica

**Library assessed: "Forest Melodica" by Severák (Pianobook, May 2023)**, local copy at
`W:\Personal\Reaper Music\Claude Collab\Samples\DecentSampler\Forest melodica\`.

| Property | Finding |
|---|---|
| Coverage | **37 samples, one per key, MIDI 53–89 = F3–F6 — exactly the M-37C Plus.** No pitch-shifting needed |
| Format | 44.1 kHz, mono, 24-bit WAV; 0.42–0.97 s each; 23 s / 4.0 MB total |
| Loops | every file carries a `smpl` loop (a few hundred to a few thousand samples, i.e. a handful of waveform cycles); the preset loops them for sustain and masks the short loops with a light chorus |
| Preset behaviour | attack 0, release 0.16 s, volume −3 dB; per-note gain taper 0.9→0.6 from MIDI 81 up; **"Air"** knob = master gain (0.5–0.7) + low-pass (2–8 kHz) — one control, like breath |
| Web size | MP3 96 kbps whole set ≈ **370 KB** (64 kbps ≈ 250 KB) — trivial to ship |
| Character | author notes slight mistuning in the bass and harshness on chords "as in the real instrument"; the owner already auditioned it in REAPER (`Renders/Mallet Audition/Melodica demo - Forest then Soprano.wav`) |
| **Licence** | Pianobook terms: free for **compositions**, but "it is forbidden to sell or redistribute the sample libraries that you do not own the copyright to". Serving the notes from a public website is redistribution → **not shippable as-is** |

So the pack **works perfectly for the alto**, and the runtime is designed around it, but the public build uses the
**owner's own M-37C Plus recording** (decided 2026-09-07). Forest stays the **dev-only** sound until then: `Samples/`
currently holds the Forest notes with their loop points plus `SOURCE.txt` marking them dev-only, and `Samples/` is
git-ignored until the own recording replaces it.

**Recording workflow (built 2026-09-07, `tools/`):**
- `tools/make_session.py` generates the guided REAPER session `Claude Collab\Projects\Melodica Samples\Melodica Samples.rpp`
  (60 BPM, 44.1 kHz/24-bit; Guide track with reference pitch + count ticks, Melodica track armed; a marker and a
  region per note, regions named `53`..`89`; render preset = project regions → `$region`). Guide audio uses the Forest
  notes as reference pitches (private use only). One pass is 5 minutes. Instructions: `tools/RECORDING.md`.
- `tools/slice_samples.py --rpp <project> --out Samples` reads the take from the project, cuts each note out of its
  8 s slot by onset, trims, finds a seamless loop (whole periods, best seam), peak-normalises, writes `NN.wav` with the
  loop in the `smpl` chunk, `samples.json` (loop points in seconds and samples, per-note gain within ±6 dB, pitch check)
  and `REPORT.md` listing notes to re-record. `--dir` accepts rendered region files; `--keep-loops` reuses existing loops.
  Validated on the Forest set (37/37, pitch within ±13 cents).
- The app's `samples.mjs` then only encodes `Samples/NN.wav` → `samples/NN.mp3` and copies the manifest.

**Runtime (`Sound = Melodica`):** on first user gesture fetch `samples.json`, then lazily fetch+`decodeAudioData` each
`NN.mp3` (all 37 preloaded in the background after the first note). `noteOn(midi)` = `AudioBufferSourceNode` with
`loop=true`, `loopStart/loopEnd` from the manifest → per-note gain (taper) → **Air** chain (gain + low-pass) → light chorus
(two short modulated delays, wet 0.12) → destination. `noteOff` = 160 ms exponential release then stop. Transport
notes use the same path with a fixed duration. **Fallback** (`Simple`, or while samples load/offline): the fretboard
triangle synth with a 35 ms attack. `Off` mutes.

Gotcha to design around: MP3 decoders prepend a constant delay (~1100 samples), which would shift loop points. Encode
each note with its loop region **repeated to an exact multiple of the period** (so any constant offset lands on the
same phase) or use OGG/Vorbis where supported; verify by ear in the self-pilot.

### 5.6 Deploy

```
npm run deploy   # samples.mjs (if raw WAVs present) → build.mjs → dist/, then wrangler pages deploy dist --project-name melodica-trainer
```
Then in the Cloudflare dashboard: Pages → melodica-trainer → Custom domains → `melodica.terhunelabs.com`; Web Analytics →
add site → paste the new beacon token into `index.html`. Post-deploy check (fretboard gotcha): the live URL returns real
HTML, and `/`, `/og.png`, `/favicon.svg`, `/samples/60.mp3` all load. Mic needs HTTPS — Pages provides it.

### 5.7 Deferred technique cues

Breath bar under the stage during Play (fills for the chord's duration, "breathe" gap between bars) and an
articulation hint ("tongue each chord") — after v1; cheap once the beat clock is in.

### 5.8 Tests (`npm test`, jsdom)

Renders with no JS errors · exactly **37** `.key` elements (22 white/15 black) · C major lights 22 keys ·
`parseLine` distinguishes `Am F C G` / `I V vi IV` / `C4 D4 E4` and rejects mixed lines · `voicings('C','')` count
within range and `pickVoicing` root/smooth choices for C→G→Am→F · fingering table · drill scoring accepts any allowed
inversion and rejects a wrong key · Leitner promote/demote · label levels change overlay text · Held view rotates ·
sample manifest loads and the synth fallback engages when fetch fails (mocked).

---

## 6. Backlog (explicitly after v1)

- **Two-hand / table mode** voicings (LH root or root+5th, RH chord) — first thing after v1; engine already takes `hands`.
- **Mic chord verification** (chroma check), then scale drills by mic (O5).
- **Staff notation** strip above the keyboard (treble clef) — melodica repertoire is mostly sheet music.
- Breath/articulation cues (§5.7), PWA manifest for install-to-home-screen, light theme.
- Bigger melody library, arpeggios, scale fingerings for all 12 keys.
- Other melodica models via `KB` presets (32-key Hohner, 44-key Yamaha).

---

## 7. Plan & phases

| Phase | Deliverable | Reuses | Exit check |
|---|---|---|---|
| **0 · Scaffold** | New repo + `index.html` shell (theme, top bar, Options, Guide stub, full-screen); infra files; `samples.mjs` + manifest from the Forest WAVs (dev-only, git-ignored); Pages project created; hello-world live at `melodica-trainer.pages.dev` | infra, CSS, modal | `npm test` green; deploy serves real HTML |
| **1 · Keyboard & sound** | `buildKeys()` with M-37C Plus livery; sampled sound with loop/sustain, Air, synth fallback; labels (3 levels), colours, root/scale highlighting, register window, Flat/Held views, responsive fit, computer-keyboard map | theory, colours, motion | 37 keys; held chords sustain; fits desktop/tablet/phone; a11y pass |
| **2 · Coach** | `parseLine` (progressions, Roman numerals, melodies), diatonic chips, Random, **voicing engine + fingering + next-up ghost**, transport + beat clock + metronome, Chords mode | transport, clock, prog pools | type `C G Am F` → play at 60 BPM with correct inversions; melody `C D E C` steps in time; tests |
| **3 · Drills & Guide** | Drill mode (note / chord / progression / melody items, Leitner, session summary); **mic listening** for note + melody drills; Guide modal with objectives + "try this first"; GUIDE evaluate pass (03/02/10) | modal, localStorage | drill round-trip works offline; mic detects F3–F6 on the real instrument; rubric ≥ 4 |
| **4 · Ship** | Record the owner's own samples (or obtain permission) and swap in; OG/favicon art; analytics token; custom domain; real-browser layout QA; HANDOFF.md; self-pilot logged | build/deploy | live at melodica.terhunelabs.com with legally clean sound |
| **5 · Post-v1** | Two-hand voicings; mic chord verification; breath cues | engine | — |

Rough effort: phases 0–1 one session each, phase 2 one to two sessions (voicing engine + parser are the new logic),
phase 3 two sessions (pitch detection needs real-instrument tuning), phase 4 one session plus the recording.

---

## 8. Decisions

Resolved 2026-09-07 with the owner:
1. Model: Suzuki M-37C Plus, 37 keys F3–F6 (confirmed by photo).
2. Name/repo/domain: Melodica Trainer · `melodica-trainer` · melodica.terhunelabs.com.
3. Right-hand voicings in v1; two-hand/table voicings straight after v1.
4. No Web MIDI. Sampled melodica sound (Forest Melodica fits the alto exactly; licence handled per §5.5).
5. Staff notation stays in the backlog.
6. Not a course: a coach plus short drills toward the objectives, with **microphone listening** for drills, and a
   **freeform progression input that teaches where/what to press** as the primary mode.
7. Both note-finding and simple melody drills in v1.

8. Sample licence route: **record the M-37C Plus** with the guided session in `tools/` (ready 2026-09-07); Forest is dev-only.

Still open:
- **Melody starter set:** the six public-domain tunes in §4.2, or different ones?
- **Mic in phase 3 vs 4:** proposed phase 3 (note + melody drills need it to be meaningful at the desk).
