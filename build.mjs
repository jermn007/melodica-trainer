// Builds a clean dist/ for Cloudflare Pages: index.html + root static assets (favicon/icons/OG image)
// + the encoded sample set (samples/NN.mp3 + samples/samples.json, produced by samples.mjs).
// Run: npm run build   (npm run deploy calls this first)
import { rmSync, mkdirSync, copyFileSync, existsSync, readdirSync } from 'node:fs';

const ASSETS = ['index.html', 'favicon.svg', 'icon-512.png', 'apple-touch-icon.png', 'og.png'];

rmSync('dist', { recursive: true, force: true });
mkdirSync('dist');
let n = 0;
for (const f of ASSETS) if (existsSync(f)) { copyFileSync(f, 'dist/' + f); n++; } else console.warn('missing asset:', f);
if (existsSync('samples')) {
  mkdirSync('dist/samples');
  for (const f of readdirSync('samples')) { copyFileSync('samples/' + f, 'dist/samples/' + f); n++; }
}
console.log('Built dist/ with ' + n + ' files');
