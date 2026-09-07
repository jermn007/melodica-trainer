# Recording the M-37C Plus sample set

One guided pass of about five minutes produces all 37 notes (F3 to F6, MIDI 53 to 89) in the exact
layout the app and `tools/slice_samples.py` expect.

## 1. Setup (two minutes)

- Open `Melodica Samples.rpp` (this folder) in REAPER. Two tracks: **Guide** (cue audio, plays through
  your headphones) and **Melodica** (record-armed, input 1, monitoring off).
- **Headphones on.** The Guide track plays reference pitches and count ticks; with speakers they would leak
  into the mic.
- Mic on **input 1** of the UMC204HD (if you use input 2, change the Melodica track's input). Aim it at the
  back or the keys from about 30 to 40 cm; the melodica is loud, so set gain so a firm note peaks around
  -12 dBFS on the track meter. Avoid the tube end (breath noise).
- Sample rate is fixed at 44.1 kHz, 24-bit. The WaveOut driver is fine for this session: the slicer finds
  each note by its own attack, so driver latency does not matter. ASIO is optional.
- Sit the way you normally play at the desk (tube, two hands is fine); you only need one finger per note.

## 2. The timeline

Tempo is 60 BPM, so one beat is one second and every note gets an 8-second slot (two bars). The ruler shows a
marker per note (`F3 53`, `F#3 54`, ...) and a region per note named by its MIDI number.

| within the slot | you hear | you do |
|---|---|---|
| 0 to 1.6 s | the **reference pitch** for this note | find the key |
| 1 s, 2 s, 3 s | tick, tick, **TICK** (the third is higher) | count |
| 4 s | nothing | **play**: one firm, steady mf note, no vibrato, no swell |
| 7 s | a soft low tick | **release** and breathe |
| 8 s | next reference pitch | next key |

The first slot starts after a 4-second lead-in (three soft ticks). Hold each note steadily for about three
seconds; the slicer only needs about 0.6 s of clean sustain, so an early release is fine, a wobbly one is not.

## 3. Record

1. Press **Home** (cursor to the start), then **Ctrl+R**. Play along until the last note (F6, slot 37,
   about 5:00), then **Space** to stop and **Save** when asked (keep the file).
2. Missed or fluffed a note? Just carry on. Afterwards you can either re-record the whole pass (five minutes)
   or punch in one note: double-click its region in the ruler to make it the time selection, set
   **Options > Record mode: Time selection auto-punch**, put the cursor a few seconds before it, Ctrl+R, play it
   when the cue comes, stop, then set the record mode back to Normal. The slicer uses whatever is on the Melodica
   track inside each region, newest take on top.

## 4. Export

Preferred, no rendering needed. From the app folder:

```bash
cd /w/Personal/Programming/Melodica
python tools/slice_samples.py --rpp "/w/Personal/Reaper Music/Claude Collab/Projects/Melodica Samples/Melodica Samples.rpp" --out recording
```

This reads the take(s) on the Melodica track straight from the project, cuts each note out of its slot,
trims to the attack, finds a seamless loop, normalises, writes `recording/53.wav` ... `recording/89.wav` with the
loop stored in the WAV, plus `recording/samples.json` (loop points and per-note gain for the app) and
`recording/REPORT.md`. (`npm run build` then encodes them into `samples/` for the web.)

Alternative, if you prefer REAPER to do the cutting: mute the Guide track, **File > Render**, check that
Bounds is *Project regions* and the file name is `$region` (the project is pre-set), render into `Rendered\`,
then run the same script with `--dir Rendered` instead of `--rpp ...`.

## 5. Check

Open `recording/REPORT.md`. Every row should show the detected pitch within about 25 cents of the expected
note, a loop of 50 to 150 ms, a seam value under 0.25 and no warnings. The last line lists any notes to
re-record; punch those in (section 3) and run the export again. Then the app's `npm run build` picks the set up.
