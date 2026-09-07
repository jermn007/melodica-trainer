# Melodica Trainer

Single-file interactive trainer for the **Suzuki M-37C Plus** alto melodica (37 keys, F3–F6). Type a chord
progression, a Roman-numeral pattern or a melody, pick a scale, and the keys to press light up with fingering;
tap a key to hear the real instrument (37 notes recorded from the owner's melodica, looped for sustain).
Everything is in **`index.html`** — no framework, no CDN, works offline once loaded.

Live: https://melodica.terhunelabs.com  ·  Cloudflare Pages project `melodica-trainer`.
Sibling of [fretboard-trainer](https://github.com/jermn007/fretboard-trainer), which it borrows its design system,
music theory and transport from.

## Develop
```
npm install     # jsdom, for the smoke test only
npm run dev     # http://localhost:5174
npm test        # headless smoke test (logic/render; not layout, not audio)
```

## Samples
`recording/` holds the recorded note set (`53.wav` … `89.wav`, 24-bit, loop points and root note in the WAV,
plus `samples.json` and `REPORT.md`). `npm run samples` (part of `npm run build`) encodes them into `samples/`
(96 kbps MP3 + manifest) for the web. To re-record, see `tools/RECORDING.md`: `tools/make_session.py` builds a
guided REAPER session and `tools/slice_samples.py` turns the take into the note set.

## Deploy (Cloudflare Pages)
```
npm run deploy  # samples.mjs -> samples/, build.mjs -> dist/, then wrangler pages deploy dist
```
Static page, no env vars. See **SPEC.md** for the analysis, learning design (GUIDE), technical spec and plan.
