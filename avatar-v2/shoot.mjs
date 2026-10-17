
import { chromium } from 'playwright';
import fs from 'fs';
const [,, base, outDir] = process.argv;
const rep = JSON.parse(fs.readFileSync(outDir + '/build-report.json', 'utf8'));
fs.mkdirSync(outDir + '/proof/frames', { recursive: true });
const log = (...a) => { console.log(...a); fs.appendFileSync(outDir + '/proof/shoot-log.txt', a.join(' ') + '\n'); };
const b = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-webgl'] });
const page = await b.newPage({ viewport: { width: 1000, height: 1000 } });
page.on('console', m => log('console', m.type(), m.text().slice(0, 300)));
page.on('pageerror', e => log('pageerror', e.message));
await page.goto(base + '/view.html'); await page.waitForFunction(() => window.api && window.api.ready, null, { timeout: 60000 });
const save = (name, dataUrl) => { fs.writeFileSync(`${outDir}/proof/${name}`, Buffer.from(dataUrl.split(',')[1], 'base64')); log('saved', name); };
const compose = (cells, cols, cw, ch, title) => page.evaluate(async ({ cells, cols, cw, ch, title }) => {
  const rows = Math.ceil(cells.length / cols), th = title ? 56 : 0; const c = document.createElement('canvas'); c.width = cols * cw; c.height = rows * ch + th;
  const g = c.getContext('2d'); g.fillStyle = '#1f1f21'; g.fillRect(0, 0, c.width, c.height);
  if (title) { g.fillStyle = '#f2f2f2'; g.font = '600 26px sans-serif'; g.fillText(title, 18, 37); }
  for (let i = 0; i < cells.length; i++) { const im = new Image(); im.src = cells[i].src; await im.decode();
    const x = (i % cols) * cw, y = Math.floor(i / cols) * ch + th; g.drawImage(im, x, y, cw, ch);
    g.fillStyle = 'rgba(0,0,0,0.55)'; g.fillRect(x, y + ch - 40, cw, 40); g.fillStyle = '#fff'; g.font = '500 20px sans-serif'; g.fillText(cells[i].label, x + 12, y + ch - 13); }
  return c.toDataURL('image/png'); }, { cells, cols, cw, ch, title });
const info = {};
info.v2 = await page.evaluate(() => window.api.load('v2', './jena-v2.vrm', false)); log('v2', JSON.stringify(info.v2));
let meshy = fs.existsSync(outDir + '/meshy.glb');
if (meshy) { try { info.meshy = await page.evaluate(() => window.api.load('meshy', './meshy.glb', true)); log('meshy', JSON.stringify(info.meshy)); } catch (e) { log('meshy load failed', e.message); meshy = false; } }
const S = info.v2 ? 1.6 / info.v2.height_raw : 1;
const shot = (k, o) => page.evaluate(([k, o]) => window.api.shot(k, o), [k, o]);
const expr = (k, v) => page.evaluate(([k, v]) => window.api.setExpr(k, v), [k, v]);
await expr('v2', {});
// 1) turntable
const tt = [];
for (const [yaw, lab] of [[0, 'front'], [45, '3/4'], [90, 'side'], [180, 'back']]) { const d = await shot('v2', { yaw: -yaw, w: 900, h: 1400 }); save(`v2-${lab.replace('/', '')}.png`, d); tt.push({ src: d, label: `v2 ${lab}` }); }
save('turntable-v2.png', await compose(tt, 4, 600, 933, 'Jena v2 - Anime_StudioPaint .nude, 3-panel light (2 back 60% + 1 front 20%), WebGL2'));
for (let i = 0; i < 36; i++) { const d = await shot('v2', { yaw: -i * 10, w: 600, h: 932 }); fs.writeFileSync(`${outDir}/proof/frames/f${String(i).padStart(3,'0')}.png`, Buffer.from(d.split(',')[1], 'base64')); }
// 2) face: blink + visemes + ARKit samples
const headY = rep.landmarks_blender.eye[2] * S - 0.005;
const face = { target: [0, headY, 0], dist: 0.62, w: 480, h: 560, fov: 22 };
const states = [['neutral', {}], ['blink (both)', { blink: 1 }], ['blink_Eye_L (her left)', { blink_Eye_L: 1 }], ['blink_Eye_R (her right)', { blink_Eye_R: 1 }],
  ['viseme aa', { aa: 1 }], ['viseme ih', { ih: 1 }], ['viseme ou', { ou: 1 }], ['viseme ee', { ee: 1 }], ['viseme oh', { oh: 1 }],
  ['jawOpen + tongueOut', { jawOpen: 0.6, tongueOut: 1 }], ['mouthSmile L+R', { mouthSmileLeft: 1, mouthSmileRight: 1 }], ['browInnerUp', { browInnerUp: 1 }],
  ['cheekPuff', { cheekPuff: 1 }], ['eyeLookOut L+R', { eyeLookOutLeft: 1, eyeLookInRight: 1 }], ['mouthLeft', { mouthLeft: 1 }], ['happy (preset)', { happy: 1 }]];
const fc = [];
for (const [lab, v] of states) { await expr('v2', v); fc.push({ src: await shot('v2', face), label: lab }); }
await expr('v2', {});
save('face-blink-visemes.png', await compose(fc, 4, 480, 560, 'Jena v2 face - ARKit 52 + visemes + blink_Eye_L / blink_Eye_R (live VRM expressions)'));
// 3) logo on the LEFT thigh-high band
const bandY = rep.extra_points.band_mid_z * S;
const lg = [];
lg.push({ src: await shot('v2', { yaw: -90, target: [0, bandY, 0.08], dist: 0.5, w: 700, h: 700, fov: 22 }), label: 'her LEFT leg, outer band (close-up)' });
lg.push({ src: await shot('v2', { yaw: -50, target: [0.05, bandY + 0.05, 0.06], dist: 1.4, w: 700, h: 700, fov: 22 }), label: 'front-left 3/4' });
lg.push({ src: await shot('v2', { yaw: 90, target: [0, bandY, 0.08], dist: 0.5, w: 700, h: 700, fov: 22 }), label: 'her RIGHT leg band (no logo)' });
save('logo-left-thighhigh.png', await compose(lg, 3, 700, 700, 'NCOM // on the outer band of her LEFT thigh-high (her own logo image, shape unchanged)'));
// 4) side-by-side v2 vs Meshy
if (meshy) {
  const sb = [];
  for (const [yaw, lab] of [[0, 'front'], [45, '3/4'], [180, 'back']]) {
    sb.push({ src: await shot('v2', { yaw: -yaw, w: 700, h: 1100 }), label: `v2 (new) ${lab}` });
    sb.push({ src: await shot('meshy', { yaw: -yaw, w: 700, h: 1100 }), label: `Meshy (current) ${lab}` });
  }
  save('side-by-side-v2-vs-meshy.png', await compose(sb, 2, 560, 880, 'Same renderer, same .nude 3-panel light: v2 (left) vs current Meshy model (right)'));
  const mf = [{ src: await shot('v2', face), label: 'v2 face' }, { src: await shot('meshy', face), label: 'Meshy face' }];
  save('side-by-side-face.png', await compose(mf, 2, 480, 560, 'Face: v2 vs Meshy'));
}
fs.writeFileSync(outDir + '/proof/view-info.json', JSON.stringify(info, null, 1));
await b.close(); log('done');
