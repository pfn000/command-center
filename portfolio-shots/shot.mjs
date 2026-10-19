import { chromium } from 'playwright'
import fs from 'node:fs'
import { execSync } from 'node:child_process'
// v7 r14 proof (portfolio-v6 leftovers): PleX slate dim fix, Emmi_Official logo once on /emmico, Medium links on /writing,
// stills of /work /emmico /writing at 1600x900 + 390x844, dark + light; then the desktop home->Work scroll video,
// recorded as a screenshot sequence (frame by frame, so a slow runner can't stretch it) and encoded at 24 fps, <=1.9 MB.
const T0 = Date.now()
const [base, out] = process.argv.slice(2)
const B = base.replace(/\/$/, '')
const report = { shots: [], errors: [], checks: {}, videos: [] }
const LAUNCH = () => chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'] })
let browser = await LAUNCH()
const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
const save = () => fs.writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1))
async function audit(page) {
  return page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    broken: [...document.images].filter((i) => i.complete && i.naturalWidth === 0 && i.style.display !== 'none').map((i) => i.getAttribute('src')).slice(0, 8),
    badLinks: [...document.querySelectorAll('a[href]')].map((a) => a.getAttribute('href')).filter((h) => /tiktok|twitch|youtube|emmiofficial|vr_emmi|notion\.site|instagram|beacons|linkedin|liberapay|ko-fi|patreon|buymeacoffee/i.test(h)).slice(0, 8),
    emmiLogos: [...document.querySelectorAll('main img')].filter((i) => /emmico-vtuber-logo/.test(i.getAttribute('src') || '') && i.getBoundingClientRect().width > 0).length,
    under: [...document.querySelectorAll('.pf-main > .pf-slate')].map((e) => (e.id || '?') + ':' + (e.style.getPropertyValue('--under') || '0')).join(' '),
  })).catch((e) => ({ err: String(e).slice(0, 200) }))
}
async function snap(page, name, opts = {}) {
  try { await page.screenshot({ path: `${out}/${name}.jpg`, type: 'jpeg', quality: 82, timeout: 45000, ...opts }) }
  catch (e) {
    report.errors.push(`shot ${name} try1: ${String(e).slice(0, 140)}`)
    try { await page.waitForTimeout(1500); await page.screenshot({ path: `${out}/${name}.jpg`, type: 'jpeg', quality: 82, timeout: 60000, animations: 'disabled', ...opts }) }
    catch (e2) { report.errors.push(`shot ${name} FAILED: ${String(e2).slice(0, 140)}`); return }
  }
  const a = await audit(page)
  report.shots.push({ name, ...a }); save()
  console.log('shot', name, Math.round((Date.now() - T0) / 1000), JSON.stringify(a))
}
async function ctx(kind, theme, br = browser) {
  const c = kind === 'p'
    ? await br.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, userAgent: IPHONE, colorScheme: theme })
    : await br.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1, colorScheme: theme })
  const p = await c.newPage()
  p.on('pageerror', (e) => report.errors.push(`${kind}-${theme} pageerror: ${String(e).slice(0, 300)}`))
  return { c, p }
}
async function go(p, path, theme, wait = 2500) {
  const sep = path.includes('?') ? '&' : '?'
  await p.goto(`${B}${path}${sep}theme=${theme}`, { waitUntil: 'networkidle', timeout: 45000 }).catch((e) => report.errors.push('goto ' + path + ' ' + String(e).slice(0, 120)))
  await p.waitForTimeout(wait)
}
async function lazyAll(p) {
  await p.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 700) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 110)) } window.scrollTo(0, 0) })
  await p.waitForTimeout(1200)
}
const absTop = (p, sel) => p.evaluate((s) => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().top + window.scrollY) : null }, sel)
const scrollTo = async (p, y, w = 900) => { await p.evaluate((v) => window.scrollTo(0, v), Math.max(0, Math.round(y))); await p.waitForTimeout(w) }

for (const [kind, theme] of [['d', 'dark'], ['d', 'light'], ['p', 'dark'], ['p', 'light']]) {
  if (!browser.isConnected()) browser = await LAUNCH()
  const k = `${kind}-${theme}`
  const { c, p } = await ctx(kind, theme)
  try {
    // /work
    await go(p, '/work', theme, 2600)
    await snap(p, `${k}-02-work`)
    await lazyAll(p)
    // PleX Code slate: same framing as r13 (top of the slate 100px / 70px from the top, the next slate entering below it)
    const off = kind === 'p' ? 70 : 100
    let y = await absTop(p, '#plexcode')
    if (y != null) {
      await scrollTo(p, y - off)
      await snap(p, `${k}-02p-work-plexcode`)
      report.checks[`${k}-plexcode-r13-framing`] = await p.evaluate(() => { const e = document.querySelector('#plexcode'); const n = e.nextElementSibling; const r = e.getBoundingClientRect(); return { under: e.style.getPropertyValue('--under'), filter: getComputedStyle(e).filter, slateBottom: Math.round(r.bottom), nextTop: n ? Math.round(n.getBoundingClientRect().top) : null } })
      // the next slate 1/3 of the way over it: the dim still works once it is actually covered
      const st = await p.evaluate(() => { const e = document.querySelector('#plexcode'); return { h: e.offsetHeight, stick: parseFloat(e.style.getPropertyValue('--stick')) || 0 } })
      const nextY = await p.evaluate(() => { const n = document.querySelector('#plexcode').nextElementSibling; return n ? Math.round(n.getBoundingClientRect().top + window.scrollY) : null })
      if (nextY != null) {
        await scrollTo(p, nextY - (st.stick + st.h * 0.62))
        await snap(p, `${k}-02q-work-plexcode-covered`)
        report.checks[`${k}-plexcode-covered`] = await p.evaluate(() => { const e = document.querySelector('#plexcode'); return { under: e.style.getPropertyValue('--under'), filter: getComputedStyle(e).filter } })
      }
    }
    // /emmico
    await go(p, '/emmico', theme, 2400)
    await snap(p, `${k}-03-emmico`)
    await lazyAll(p)
    report.checks[`${k}-emmico-logo-count`] = await p.evaluate(() => [...document.querySelectorAll('main img')].filter((i) => /emmico-vtuber-logo/.test(i.getAttribute('src') || '')).map((i) => i.closest('section') ? i.closest('section').id : '?'))
    let j = 0
    for (const sel of ['#emmi-official', '#emmico']) {
      j++
      const t = await absTop(p, sel)
      if (t != null) { await scrollTo(p, t - (kind === 'p' ? 70 : 90), 1000); await snap(p, `${k}-03b-emmico-slate${j}`) }
    }
    if (kind === 'p') {
      const t = await absTop(p, '#emmico .pf-three')
      if (t != null) { await scrollTo(p, t - 120, 1000); await snap(p, `${k}-03c-emmico-vtubing-logo`) }
    }
    // /writing
    await go(p, '/writing', theme, 2400)
    await snap(p, `${k}-05-writing`)
    report.checks[`${k}-writing-cards`] = await p.evaluate(() => [...document.querySelectorAll('.pf-art-card')].map((c) => ({ title: (c.querySelector('b') || {}).textContent, internal: (c.querySelector('.pf-art-in') || {}).getAttribute?.('href'), medium: (c.querySelector('.pf-art-ext') || {}).getAttribute?.('href'), mediumText: (c.querySelector('.pf-art-ext') || {}).textContent })))
    if (kind === 'p') { await p.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight)); await p.waitForTimeout(900); await snap(p, `${k}-05c-writing-cards-end`) }
    if (theme === 'dark') {
      await go(p, '/writing/ai-being-used-wrong', theme, 2200)
      await p.evaluate(() => { const m = document.querySelector('.pf-art .pf-meta'); if (m) window.scrollTo(0, m.getBoundingClientRect().top + window.scrollY - 300) }); await p.waitForTimeout(800)
      await snap(p, `${k}-05b-writing-article-ai`)
      report.checks[`${k}-article-medium-link`] = await p.evaluate(() => { const a = document.querySelector('.pf-art .pf-meta a'); return a ? a.getAttribute('href') : null })
    }
  } catch (e) { report.errors.push(`ctx ${k} died: ${String(e).slice(0, 300)}`) }
  await c.close().catch(() => {})
  save()
}
console.log('stills done', Math.round((Date.now() - T0) / 1000))

// Desktop home -> Work scroll video, frame by frame. Real Google Chrome when the runner has it (plays the H.264 genie clip).
async function desktopVideo() {
  let br = null
  try { br = await chromium.launch({ channel: 'chrome', args: ['--autoplay-policy=no-user-gesture-required', '--disable-dev-shm-usage'] }); report.checks.videoBrowser = 'chrome ' + br.version() }
  catch (e) { report.errors.push('video chrome: ' + String(e).slice(0, 160)); br = await LAUNCH(); report.checks.videoBrowser = 'chromium' }
  const dir = '/tmp/vf'; fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir)
  const { c, p } = await ctx('d', 'dark', br)
  let n = 0
  const DEADLINE = T0 + 870 * 1000
  const shoot = async () => { await p.screenshot({ path: `${dir}/f${String(n).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 90, timeout: 30000 }); n++ }
  const hold = (frames) => { const last = `${dir}/f${String(n - 1).padStart(5, '0')}.jpg`; for (let i = 0; i < frames; i++) { fs.copyFileSync(last, `${dir}/f${String(n).padStart(5, '0')}.jpg`); n++ } }
  const ease = (e) => (e < 0.5 ? 2 * e * e : 1 - Math.pow(-2 * e + 2, 2) / 2)
  const t0 = Date.now(); const seg = {}
  try {
    // segment 1: home hero, then a short scroll down the home page
    await go(p, '/', 'dark', 3500)
    await lazyAll(p); await p.waitForTimeout(800)
    await shoot(); hold(29)
    const Hh = await p.evaluate(() => document.documentElement.scrollHeight - window.innerHeight)
    const homeSteps = 40
    for (let i = 1; i <= homeSteps && Date.now() < DEADLINE; i++) { await p.evaluate((v) => window.scrollTo(0, v), Math.round(Hh * ease(i / homeSteps))); await p.waitForTimeout(45); await shoot() }
    hold(12); seg.home = n
    // segment 2: the Work page, top to bottom through the stacked slates
    await go(p, '/work', 'dark', 3000)
    await lazyAll(p); await p.waitForTimeout(1500)
    await shoot(); hold(23)
    const H = Math.min(await p.evaluate(() => document.documentElement.scrollHeight - window.innerHeight), 16000)
    const steps = 300
    for (let i = 1; i <= steps; i++) {
      if (Date.now() > DEADLINE) { report.errors.push(`video: deadline at work step ${i}/${steps}`); break }
      await p.evaluate((v) => window.scrollTo(0, v), Math.round(H * ease(i / steps))); await p.waitForTimeout(45); await shoot()
    }
    hold(18); seg.work = n - seg.home
  } catch (e) { report.errors.push(`video capture: ${String(e).slice(0, 300)}`) }
  await c.close().catch(() => {}); await br.close().catch(() => {})
  report.checks.videoCapture = { frames: n, seconds: Math.round((Date.now() - t0) / 1000), seg }
  console.log('video frames', n, Math.round((Date.now() - t0) / 1000))
  if (n < 48) return
  const mp4 = `${out}/video-d-dark-home-work-scroll.mp4`
  const enc = (crf) => { execSync(`ffmpeg -y -loglevel error -framerate 24 -i ${dir}/f%05d.jpg -vf "scale=1280:720:flags=lanczos,format=yuv420p" -c:v libx264 -preset slow -profile:v high -crf ${crf} -movflags +faststart -an ${mp4}`, { timeout: 300000 }); return fs.statSync(mp4).size }
  let crf = 26, bytes = enc(crf)
  while (bytes > 1.9e6 && crf < 44) { crf += 2; bytes = enc(crf) }
  const dur = Number(execSync(`ffprobe -v error -show_entries format=duration -of csv=p=0 ${mp4}`).toString().trim())
  report.videos.push({ file: 'video-d-dark-home-work-scroll.mp4', bytes, duration: dur, crf, frames: n })
  // contact sheet of the video for a quick look
  execSync(`ffmpeg -y -loglevel error -i ${mp4} -vf "fps=12/${dur.toFixed(2)},scale=400:-2,tile=4x3" -frames:v 1 ${out}/video-d-dark-sheet.jpg`, { timeout: 120000 })
  fs.rmSync(dir, { recursive: true, force: true })
}
await desktopVideo().catch((e) => report.errors.push('video: ' + String(e).slice(0, 300)))
save()
console.log('DONE', Math.round((Date.now() - T0) / 1000))
await browser.close().catch(() => {})
