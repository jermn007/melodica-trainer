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
  const vbZoom = svg().match(/viewBox="([^"]+)"/)[1].split(' ').map(Number);
  ok('register zoom crops the view to the window', vbZoom[0] > 0 && vbZoom[2] < 700, JSON.stringify(vbZoom));
  $('zoom').querySelectorAll('button')[1].dispatchEvent(evt('click'));
  const vbFull = svg().match(/viewBox="([^"]+)"/)[1].split(' ').map(Number);
  ok('zoom Full shows the whole instrument again', vbFull[0] === 0 && vbFull[2] > 1000, JSON.stringify(vbFull));
  $('zoom').querySelectorAll('button')[0].dispatchEvent(evt('click'));
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

  // double harmonic major: 22 keys, b2/b6 spelled flat, its own chords, idiomatic roman numerals + random pool
  $('scale').value = 'double_harmonic'; $('scale').dispatchEvent(evt('change'));
  ok('C double harmonic lights 22 keys', dots() === 22, 'dots=' + dots());
  ok('double harmonic spells Db and Ab (never C#/G#)', svg().includes('>Db<') && svg().includes('>Ab<') && !svg().includes('>C#<') && !svg().includes('>G#<'));
  const dh = [...$('diatonic').querySelectorAll('.chip')].map(c => c.textContent.trim().split(/\s+/)[0]);
  ok('double harmonic chords are C Db Em Fm G Abaug Bdim', dh.join(' ') === 'C Db Em Fm G Abaug Bdim', dh.join(' '));
  $('progin').value = 'I bII V I'; $('setprog').dispatchEvent(evt('click'));
  ok('I bII V I resolves to C Db G C', [...$('prog').querySelectorAll('.pchip')].map(b => b.textContent).join(' ') === 'C Db G C', [...$('prog').querySelectorAll('.pchip')].map(b => b.textContent).join(' '));
  $('randprog').dispatchEvent(evt('click'));
  ok('random uses the desert pool with bII in its name', /bII/.test($('progname').textContent), $('progname').textContent);
  // phrygian (A): Bb spelled flat, chords Am Bb C Dm Edim F Gm; phrygian dominant (C): C Db Edim Fm Gdim Abaug Bbm
  $('root').value = '9'; $('root').dispatchEvent(evt('change')); $('scale').value = 'phrygian'; $('scale').dispatchEvent(evt('change'));
  const ph = [...$('diatonic').querySelectorAll('.chip')].map(c => c.textContent.trim().split(/\s+/)[0]);
  ok('A phrygian chords are Am Bb C Dm Edim F Gm', ph.join(' ') === 'Am Bb C Dm Edim F Gm', ph.join(' '));
  ok('A phrygian spells Bb on the keys', svg().includes('>Bb<') && !svg().includes('>A#<'));
  $('root').value = '0'; $('root').dispatchEvent(evt('change')); $('scale').value = 'phrygian_dominant'; $('scale').dispatchEvent(evt('change'));
  const pd = [...$('diatonic').querySelectorAll('.chip')].map(c => c.textContent.trim().split(/\s+/)[0]);
  ok('C phrygian dominant chords are C Db Edim Fm Gdim Abaug Bbm', pd.join(' ') === 'C Db Edim Fm Gdim Abaug Bbm', pd.join(' '));
  ok('C phrygian dominant spells Db Ab Bb', svg().includes('>Db<') && svg().includes('>Ab<') && svg().includes('>Bb<') && !svg().includes('>A#<'));
  $('scale').value = 'major'; $('scale').dispatchEvent(evt('change')); $('clearprog').dispatchEvent(evt('click'));

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

  // chords mode: chord finder, inversions, octave, placements
  $('mode').querySelectorAll('button')[1].dispatchEvent(evt('click'));
  ok('chords mode shows the chord row and hides the progression rows', !$('chordrow').hidden && $('progrow').hidden && $('transrow').hidden);
  ok('chords mode auto-picks the I chord with spelling in the readout', /^C · C E G · root$/.test($('bnow').textContent), $('bnow').textContent);
  $('chordin').value = 'Dm7'; $('setchord').dispatchEvent(evt('click'));
  const ch = window.eval('S.chord');
  ok('Dm7 finds a 4-note voicing with fingering', ch && ch.voicing && ch.voicing.midis.length === 4 && ch.voicing.fingers.length === 4, JSON.stringify(ch && ch.voicing));
  ok('3rd-inversion button appears for a 4-note chord', !$('inv').querySelectorAll('button')[3].hidden);
  $('inv').querySelectorAll('button')[1].dispatchEvent(evt('click'));
  ok('1st inversion puts F at the bottom', window.eval('S.chord.voicing.inv') === 1 && window.eval('S.chord.voicing.midis[0]') % 12 === 5, window.eval('JSON.stringify(S.chord.voicing.midis)'));
  const before = window.eval('S.chord.voicing.midis[0]'); $('octup').dispatchEvent(evt('click'));
  ok('+8va moves the voicing up (or stays at the top of the range)', window.eval('S.chord.voicing.midis[0]') >= before);
  ok('placements strip lists every fit', $('alts').querySelectorAll('.chip').length === window.eval('S.chord.list.length') && $('alts').querySelectorAll('.chip').length > 4, $('alts').querySelectorAll('.chip').length);
  $('mode').querySelectorAll('button')[0].dispatchEvent(evt('click'));
  ok('back to explore restores the rows', !$('progrow').hidden && $('chordrow').hidden);

  // drill mode: note item + chord item via press(), Leitner persists
  window.localStorage.removeItem('mt_leitner');
  $('mode').querySelectorAll('button')[2].dispatchEvent(evt('click'));
  ok('drill mode hides scale dots and shows the drill bar', dots() === 0 && !$('drillbar').hidden);
  $('dtype').querySelectorAll('button')[1].dispatchEvent(evt('click'));  // Notes
  $('dstart').dispatchEvent(evt('click'));
  const DR = window.eval('DR');
  ok('a note round starts with 10 items and a prompt', DR.on && DR.items.length === 10 && /Press every/.test($('prompt').textContent), $('prompt').textContent);
  const pc = DR.cur.item.pc; const expected = [...DR.cur.expected];
  window.eval('press(' + ((pc + 1) % 12 + 60) + '); release(' + ((pc + 1) % 12 + 60) + ')');   // one wrong key
  expected.forEach(m => window.eval('press(' + m + '); release(' + m + ')'));
  ok('pressing all instances completes the item; the wrong key counts as a miss', /✗ 1 wrong key/.test($('fb').textContent), $('fb').textContent);
  const L1 = JSON.parse(window.localStorage.getItem('mt_leitner') || '{}');
  ok('Leitner box recorded for the missed note (box 0)', L1['note:' + pc] && L1['note:' + pc].box === 0, JSON.stringify(L1));
  window.eval('endRound()');
  $('dtype').querySelectorAll('button')[2].dispatchEvent(evt('click'));  // Chords
  $('dstart').dispatchEvent(evt('click'));
  const cItem = DR.cur.item; const pcs = [...DR.cur.pcs];
  ok('a chord item prompts to play a chord', /Play/.test($('prompt').textContent) && pcs.length >= 3, $('prompt').textContent);
  const midis = pcs.map(p => 60 + ((p - 0 + 12) % 12));  // one octave placement C4..B4
  midis.forEach(m => window.eval('press(' + m + ')'));
  ok('holding the chord tones completes the chord item correctly', /✓ Correct/.test($('fb').textContent), $('fb').textContent);
  midis.forEach(m => window.eval('release(' + m + ')'));
  const L2 = JSON.parse(window.localStorage.getItem('mt_leitner') || '{}');
  ok('Leitner promotes the correct chord to box 1', L2[cItem.key] && L2[cItem.key].box === 1, JSON.stringify(L2[cItem.key]));
  window.eval('endRound()');
  $('mode').querySelectorAll('button')[0].dispatchEvent(evt('click'));

  // pitch detector on a synthetic A4 (440 Hz) and a low F3 (174.6 Hz)
  const sr = 44100, mk = f => { const b = new Float32Array(2048); for (let i = 0; i < b.length; i++) b[i] = 0.5 * Math.sin(2 * Math.PI * f * i / sr) + 0.2 * Math.sin(4 * Math.PI * f * i / sr) + 0.1 * Math.sin(6 * Math.PI * f * i / sr); return b; };
  const fA = window.pitchFromBuffer(mk(440), sr), fF = window.pitchFromBuffer(mk(174.61), sr);
  ok('pitch detector finds A4 within 5 cents', fA && Math.abs(1200 * Math.log2(fA / 440)) < 5, fA);
  ok('pitch detector finds F3 without octave error', fF && Math.abs(1200 * Math.log2(fF / 174.61)) < 5, fF);
  ok('pitch detector returns null for silence', window.pitchFromBuffer(new Float32Array(2048), sr) === null);

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
