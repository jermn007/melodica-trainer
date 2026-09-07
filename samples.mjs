// Encodes the sample set for the web: recording/NN.wav (24-bit, with loop points; produced by
// tools/slice_samples.py) -> samples/NN.mp3 (96 kbps mono, LAME via ffmpeg) + samples/samples.json.
// (The source folder is not called "Samples": Windows treats that as the same folder as samples/.)
// The manifest carries loopStart/loopEnd in seconds and a per-note gain; index.html reads it at runtime.
// Loop regions are whole periods inside the steady part of each note, so the constant decoder offset an
// MP3 may introduce does not break the seam. Skips files whose mp3 is newer than the wav.
import { readFileSync, writeFileSync, existsSync, mkdirSync, statSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

const SRC = 'recording', OUT = 'samples';
if (!existsSync(SRC + '/samples.json')) { console.log('no recording/samples.json; skipping sample encode'); process.exit(0); }
mkdirSync(OUT, { recursive: true });
const man = JSON.parse(readFileSync(SRC + '/samples.json', 'utf8'));
const out = { sampleRate: man.sampleRate, lo: man.lo, hi: man.hi, format: 'mp3', notes: {} };
let enc = 0;
for (const [midi, n] of Object.entries(man.notes)) {
  const wav = `${SRC}/${n.file}`, mp3 = `${OUT}/${midi}.mp3`;
  if (!existsSync(mp3) || statSync(mp3).mtimeMs < statSync(wav).mtimeMs) {
    execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', wav, '-ac', '1', '-ar', String(man.sampleRate), '-c:a', 'libmp3lame', '-b:a', '96k', mp3]);
    enc++;
  }
  out.notes[midi] = { file: `${midi}.mp3`, note: n.note, loopStart: n.loopStart, loopEnd: n.loopEnd, gain: n.gain };
}
writeFileSync(OUT + '/samples.json', JSON.stringify(out));
console.log(`samples/: ${Object.keys(out.notes).length} notes, ${enc} re-encoded`);
