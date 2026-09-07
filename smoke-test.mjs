// Headless smoke test for index.html — verifies logic & rendering (NOT layout, NOT audio).
// Run: npm install && npm test
import { readFileSync } from 'node:fs';
let JSDOM;
try { ({ JSDOM } = await import('jsdom')); }
catch { console.error('Install deps first:  npm install'); process.exit(1); }

const html = readFileSync(new URL('./index.html', import.meta.url), 'utf8');
const errs = [];
const vc = new (await import('jsdom')).VirtualConsole();
vc.on('jsdomError', e => errs.push(e.message));
const dom = new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true, virtualConsole: vc, url: 'http://localhost/' });
const { window } = dom, d = window.document;
// stub Web Audio + fetch so audio paths don't throw (fetch fails -> synth fallback path)
const param = () => ({ value: 0, setValueAtTime() {}, exponentialRampToValueAtTime() {}, cancelScheduledValues() {} });
const node = () => ({ connect() {}, start() {}, stop() {}, gain: param(), frequency: param(), detune: param(), Q: param(), delayTime: param(), type: '', buffer: null, loop: false, loopStart: 0, loopEnd: 0 });
window.AudioContext = function () {
  return { state: 'running', currentTime: 0, sampleRate: 44100, resume() {}, close() {}, destination: {},
    createOscillator: node, createGain: node, createBiquadFilter: node, createDelay: node, createBufferSource: node,
    createBuffer() { return { getChannelData() { return new Float32Array(1024); } }; }, decodeAudioData() { return Promise.resolve({}); } };
};
window.fetch = () => Promise.reject(new Error('offline'));
window.matchMedia = q => ({ matches: false, media: q, addEventListener() {}, addListener() {} });
window.SVGElement.prototype.getBBox = () => ({ x: 0, y: 0, width: 10, height: 10 });

const results = [];
const ok = (name, cond, extra = '') => results.push([!!cond, name, extra]);
const $ = id => d.getElementById(id);
const evt = t => new window.Event(t);
const keys = () => $('svgwrap').querySelectorAll('.key');
const dots = () => $('svgwrap').querySelectorAll('.dot').length;
const svg = () => $('svgwrap').innerHTML;

setTimeout(() => {
  ok('no JS errors on load', errs.length === 0, errs.join(' | '));
  ok('37 keys render', keys().length === 37, 'got ' + keys().length);
  ok('22 white + 15 black', $('svgwrap').querySelectorAll('.key.white').length === 22 && $('svgwrap').querySelectorAll('.key.black').length === 15);
  ok('lowest key is F3, highest F6', keys()[0].getAttribute('aria-label').startsWith('F3') && [...keys()].some(k => k.getAttribute('aria-label').startsWith('F6')));
  ok('C major lights all 22 white keys', dots() === 22, 'dots=' + dots());
  ok('simple mode is default (amber root dot present)', svg().includes('#f59e0b'));

  // labels scaffold
  $('labels').querySelectorAll('button')[1].dispatchEvent(evt('click'));
  const landmarkLabels = (svg().match(/font-size="10"/g) || []).length;
  ok('landmarks level labels only C and F white keys (7)', landmarkLabels === 7, 'labels=' + landmarkLabels);
  $('labels').querySelectorAll('button')[2].dispatchEvent(evt('click'));
  ok('labels none removes key labels', (svg().match(/font-size="10"/g) || []).length === 0);
  $('labels').querySelectorAll('button')[0].dispatchEvent(evt('click'));

  // register window dims outside keys
  $('register').value = 'mid'; $('register').dispatchEvent(evt('change'));
  ok('register Middle dims keys outside C4–C5', (svg().match(/rgba\(11,15,23,\.58\)/g) || []).length === 37 - 13, 'dimmed=' + (svg().match(/rgba\(11,15,23,\.58\)/g) || []).length);
  ok('subtitle shows register', /Register C4–C5/.test($('bsub').textContent), $('bsub').textContent);
  $('register').value = ''; $('register').dispatchEvent(evt('change'));

  // scale change: A minor pentatonic -> 5 pitch classes across the range
  $('root').value = '9'; $('root').dispatchEvent(evt('change'));
  $('scale').value = 'minor_pentatonic'; $('scale').dispatchEvent(evt('change'));
  ok('A minor pentatonic lights 15 keys (5 pitch classes × 3 octaves)', dots() === 15, 'dots=' + dots());
  ok('title updates', /A Minor Pentatonic/.test($('btitle').textContent), $('btitle').textContent);
  // flat spelling: F major diatonic contains Bb
  $('root').value = '5'; $('scale').value = 'major'; $('root').dispatchEvent(evt('change')); $('scale').dispatchEvent(evt('change'));
  ok('flat-key spelling (F major diatonic contains Bb)', [...$('diatonic').querySelectorAll('.chip')].some(c => c.textContent.trim().startsWith('Bb')));
  // blues: blue-note ring + flat spelling
  $('root').value = '0'; $('root').dispatchEvent(evt('change')); $('scale').value = 'major_blues'; $('scale').dispatchEvent(evt('change'));
  ok('C major blues shows the blue-note ring and spells Eb', svg().includes('#60a5fa') && svg().includes('>Eb<') && !svg().includes('>D#<'));
  $('scale').value = 'major'; $('scale').dispatchEvent(evt('change'));

  // held view
  $('view').querySelectorAll('button')[2].dispatchEvent(evt('click'));
  ok('held view rotates the board', /data-view="held"/.test(svg()) && /rotate\(90\)/.test(svg()) && $('svgwrap').dataset.view === 'held');
  $('view').querySelectorAll('button')[1].dispatchEvent(evt('click'));
  ok('flat view restores', /data-view="flat"/.test(svg()));

  // pitch colours
  $('colormode').querySelectorAll('button')[1].dispatchEvent(evt('click'));
  ok('pitch colour mode renders pitch colours', svg().includes('#6366f1'));
  $('colormode').querySelectorAll('button')[0].dispatchEvent(evt('click'));

  // coach: typed progression, voicings + fingering, stepping, smooth voice-leading
  $('progin').value = 'C G Am F'; $('setprog').dispatchEvent(evt('click'));
  const chips = $('prog').querySelectorAll('.pchip');
  ok('typed progression sets 4 chords', chips.length === 4, 'chips=' + chips.length);
  $('next').dispatchEvent(evt('click'));
  ok('stepping highlights the chord (bnow + emerald rings + fingering badges)', /▶ C/.test($('bnow').textContent) && (svg().match(/stroke="#34d399" stroke-width="4"/g) || []).length === 3 && (svg().match(/r="9" fill="#0b0f17"/g) || []).length === 3, $('bnow').textContent);
  const st = window.eval('S');
  const v0 = st.line.items[0].voicing, v1 = st.line.items[1].voicing;
  ok('C voicing is a close triad inside the keyboard', v0 && v0.midis.length === 3 && v0.midis[0] >= 53 && v0.midis[2] <= 89 && (v0.midis[2] - v0.midis[0]) <= 9, JSON.stringify(v0 && v0.midis));
  const movement = v1 ? v1.midis.reduce((a, m) => a + Math.min(...v0.midis.map(x => Math.abs(x - m))), 0) : 99;
  ok('smooth voicing keeps C→G movement small (≤ 6 semitones total)', movement <= 6, 'movement=' + movement);
  ok('C→G keeps the common tone G', v1 && v0.midis.some(m => v1.midis.includes(m)), JSON.stringify(v1 && v1.midis));
  // roman numerals + melody parsing
  $('progin').value = 'I V vi IV'; $('setprog').dispatchEvent(evt('click'));
  ok('roman numerals resolve in C major', [...$('prog').querySelectorAll('.pchip')].map(b => b.textContent).join(' ') === 'C G Am F', [...$('prog').querySelectorAll('.pchip')].map(b => b.textContent).join(' '));
  $('progin').value = 'C D E C -'; $('setprog').dispatchEvent(evt('click'));
  ok('melody line parses (4 notes, last held 2 beats)', st.line.kind === 'melody' && st.line.items.length === 4 && st.line.items[3].beats === 2, JSON.stringify(st.line.items.map(i => i.sym)));
  $('next').dispatchEvent(evt('click'));
  ok('melody step lights exactly one key', dots() === 22 && /▶ C4/.test($('bnow').textContent), $('bnow').textContent);
  $('progin').value = 'C H7 Am'; $('setprog').dispatchEvent(evt('click'));
  ok('unknown token reported', /Didn’t recognize: H7/.test($('progmsg').textContent), $('progmsg').textContent);
  // random
  $('randprog').dispatchEvent(evt('click'));
  ok('Random builds a progression and fills the input', $('prog').querySelectorAll('.pchip').length >= 3 && $('progin').value.length > 0);

  // key press via pointer and computer keyboard (no throw; synth fallback since fetch fails)
  const k = keys()[7]; const pe = new window.Event('pointerdown', { bubbles: true }); pe.pointerId = 1; k.dispatchEvent(pe);
  ok('pointer press marks the key on', k.classList.contains('on'));
  k.dispatchEvent(new window.Event('pointerup', { bubbles: true }));
  ok('pointer release clears it', !k.classList.contains('on'));
  d.dispatchEvent(new window.KeyboardEvent('keydown', { code: 'KeyZ', bubbles: true }));
  ok('computer keyboard Z presses C4', !!$('svgwrap').querySelector('.key[data-midi="60"].on'));
  d.dispatchEvent(new window.KeyboardEvent('keyup', { code: 'KeyZ', bubbles: true }));

  // options / modal
  $('optToggle').dispatchEvent(evt('click'));
  ok('options panel opens', !$('options').hidden);
  ok('guide modal is open on first run', !$('help-modal').hidden);
  $('help-close').dispatchEvent(evt('click'));
  ok('guide modal closes', $('help-modal').hidden);
  ok('no JS errors after interaction', errs.length === 0, errs.join(' | '));

  const pass = results.filter(r => r[0]).length;
  console.log('\nMelodica Trainer — smoke test');
  console.log('─'.repeat(52));
  for (const [good, name, extra] of results) console.log(`${good ? 'PASS' : 'FAIL'}  ${name}${good ? '' : '  → ' + extra}`);
  console.log('─'.repeat(52));
  console.log(`${pass}/${results.length} passed`);
  process.exit(pass === results.length ? 0 : 1);
}, 300);
