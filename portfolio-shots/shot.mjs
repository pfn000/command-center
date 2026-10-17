import { chromium } from 'playwright'
import fs from 'node:fs'
import { execSync } from 'node:child_process'
// v5.3 proof (nav in its own row, sketch letterhead cropped, no old avatar as a first image, /arch back link in the menubar, MP4 scroll-throughs; white light theme, phone line-first hero, clean desktop hero band, wrapped multi-page résumé PDF rendered to PNG, /arch Résumé -> /resume): open-layout portfolio (no windows/dock in normal view), 1600x900 desktop + 402x874 phone, light + dark
const [base, out] = process.argv.slice(2)
const B = base.replace(/\/$/, '')
const report = { shots: [], errors: [] }
const T0 = Date.now()
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] })
const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
async function audit(page) {
  return page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    broken: [...document.images].filter((i) => i.complete && i.naturalWidth === 0 && i.style.display !== 'none').map((i) => i.getAttribute('src')).slice(0, 8),
    peter: /peter/i.test(document.body.innerText || ''),
    dock: !!document.querySelector('.nos-dock'),
    windows: document.querySelectorAll('.nwin').length,
    navResume: [...document.querySelectorAll('.pf-nav a')].filter((a) => /résumé/i.test(a.textContent || '')).length,
  })).catch((e) => ({ err: String(e).slice(0, 200) }))
}
async function snap(page, name, opts = {}) {
  await page.screenshot({ path: `${out}/${name}.jpg`, type: 'jpeg', quality: 82, ...opts })
  const a = await audit(page)
  report.shots.push({ name, ...a })
  console.log('shot', name, JSON.stringify(a))
}
async function ctxFor(kind, theme) {
  const c = kind === 'phone'
    ? await browser.newContext({ viewport: { width: 402, height: 874 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, userAgent: IPHONE, colorScheme: theme })
    : await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1, colorScheme: theme })
  const p = await c.newPage()
  p.on('console', (m) => m.type() === 'error' && report.errors.push(`${kind}-${theme}: ${m.text().slice(0, 200)}`))
  p.on('pageerror', (e) => report.errors.push(`${kind}-${theme} pageerror: ${String(e).slice(0, 300)}`))
  return { c, p }
}
async function go(p, path, theme, wait = 3500) {
  const sep = path.includes('?') ? '&' : '?'
  await p.goto(`${B}${path}${sep}nocoach=1&theme=${theme}`, { waitUntil: 'networkidle', timeout: 45000 }).catch((e) => report.errors.push('goto ' + path + ' ' + String(e).slice(0, 120)))
  await p.waitForTimeout(wait)
}
async function at(p, sel, dy = 0) {
  await p.evaluate(([s, d]) => { const el = document.querySelector(s); if (el) window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 20 + d) }, [sel, dy])
  await p.waitForTimeout(1800)
}
const PLAN = {
  'desk-dark': [['1-home', null], ['2-work', '#work'], ['2b-work-pairs', '#work', 900], ['3-now', '#now'], ['3b-now-more', '#now', 1200], ['4-projects', '#projects'], ['4b-projects-more', '#projects', 1400], ['5-plex', '#plex'], ['5b-plex-code', '#plex', 600], ['6-emmi', '#emmi'], ['7-resume-sec', '#resume'], ['8-contact', '#contact']],
  'desk-light': [['1-home', null], ['2-work', '#work'], ['3-now', '#now'], ['4-projects', '#projects'], ['5-plex', '#plex'], ['8-contact', '#contact']],
  'phone-dark': [['1-home', null], ['2-work', '#work'], ['2b-work-pairs', '#work', 700], ['3-now', '#now'], ['4-projects', '#projects'], ['4b-projects-more', '#projects', 900], ['5-plex', '#plex'], ['5b-plex-code', '#plex', 700], ['6-emmi', '#emmi'], ['8-contact', '#contact']],
  'phone-light': [['1-home', null], ['3-now', '#now'], ['4-projects', '#projects'], ['8-contact', '#contact']],
}
for (const key of Object.keys(PLAN)) {
  const [kind, theme] = key.split('-')
  const { c, p } = await ctxFor(kind, theme)
  await go(p, '/', theme)
  const tag = kind === 'phone' ? 'p' : 'd'
  for (const [name, sel, dy] of PLAN[key]) {
    if (sel) await at(p, sel, dy || 0)
    else { await p.evaluate(() => window.scrollTo(0, 0)); await p.waitForTimeout(600) }
    await snap(p, `${tag}-${theme}-${name}`)
  }
  await go(p, '/resume', theme)
  await snap(p, `${tag}-${theme}-9-resume-page`)
  if (theme === 'dark') {
    await go(p, '/arch', theme, 5000)
    await snap(p, `${tag}-dark-10-arch-demo`)
    // the résumé opened from the demo's menu must be its own page, never stacked over About
    try {
      const btn = p.locator(kind === 'phone' ? 'button:has-text("Read my résumé")' : 'header.nos-menubar button:has-text("Résumé")').first()
      await btn.click({ timeout: 8000 })
      await p.waitForURL('**/resume**', { timeout: 15000 })
      await p.waitForTimeout(2500)
      report.archResume = report.archResume || {}
      report.archResume[kind] = { url: p.url(), windows: await p.evaluate(() => document.querySelectorAll('.nwin').length) }
      await snap(p, `${tag}-dark-11-arch-menu-resume`)
      await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); await p.waitForTimeout(1200)
      await snap(p, `${tag}-dark-11b-arch-menu-resume-bottom`)
    } catch (e) { report.errors.push(`${kind} arch résumé click: ${String(e).slice(0, 200)}`) }
  }
  await c.close()
}

// MP4 scroll-throughs of the home page (Saidie asked for videos of the final): record, trim the warm-up, H.264
async function scrollVideo(kind, theme) {
  const dir = `/tmp/vid-${kind}-${theme}`
  fs.mkdirSync(dir, { recursive: true })
  const size = kind === 'phone' ? { width: 804, height: 1748 } : { width: 1600, height: 900 }
  const opts = kind === 'phone'
    ? { viewport: { width: 402, height: 874 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, userAgent: IPHONE, colorScheme: theme }
    : { viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1, colorScheme: theme }
  const t0 = Date.now()
  const c = await browser.newContext({ ...opts, recordVideo: { dir, size } })
  const p = await c.newPage()
  try {
    await go(p, '/', theme, 3000)
    // warm-up pass so every lazy image is loaded before the take
    const H0 = await p.evaluate(() => document.documentElement.scrollHeight - window.innerHeight)
    for (let y = 0; y <= H0; y += 700) { await p.evaluate((v) => window.scrollTo(0, v), y); await p.waitForTimeout(120) }
    await p.evaluate(() => window.scrollTo(0, 0)); await p.waitForTimeout(2500)
    const tStart = (Date.now() - t0) / 1000
    await p.waitForTimeout(1500)
    const H = await p.evaluate(() => document.documentElement.scrollHeight - window.innerHeight)
    const steps = 185
    for (let k = 1; k <= steps; k++) {
      const e = k / steps, ease = e < 0.5 ? 2 * e * e : 1 - Math.pow(-2 * e + 2, 2) / 2
      await p.evaluate((v) => window.scrollTo(0, v), Math.round(H * ease))
      await p.waitForTimeout(60)
    }
    await p.waitForTimeout(1200)
    const tEnd = (Date.now() - t0) / 1000
    await c.close()
    const raw = await p.video().path()
    const tag = kind === 'phone' ? 'p' : 'd'
    const mp4 = `${out}/video-${tag}-${theme}-home-scroll.mp4`
    execSync(`ffmpeg -y -loglevel error -ss ${Math.max(0, tStart).toFixed(2)} -to ${tEnd.toFixed(2)} -i ${raw} -c:v libx264 -preset medium -crf ${kind === 'phone' ? 26 : 24} -pix_fmt yuv420p -movflags +faststart -an ${mp4}`, { timeout: 240000 })
    const bytes = fs.statSync(mp4).size
    const dur = execSync(`ffprobe -v error -show_entries format=duration -of csv=p=0 ${mp4}`).toString().trim()
    report.videos = report.videos || []
    report.videos.push({ file: mp4.split('/').pop(), bytes, duration: Number(dur), size })
    console.log('video', mp4, bytes, dur)
  } catch (e) { report.errors.push(`video ${kind}-${theme}: ${String(e).slice(0, 300)}`); try { await c.close() } catch {} }
}
try { execSync('command -v ffmpeg') } catch { try { execSync('sudo apt-get install -y -q ffmpeg || (sudo apt-get update -q && sudo apt-get install -y -q ffmpeg)', { stdio: 'inherit', timeout: 240000, shell: '/bin/bash' }) } catch (e) { report.errors.push('ffmpeg install ' + String(e).slice(0, 200)) } }
for (const [k, t] of [['desk', 'dark'], ['phone', 'dark'], ['desk', 'light'], ['phone', 'light']]) {
  if (Date.now() - T0 > 430000) { report.errors.push(`video ${k}-${t} skipped: time`); continue }
  await scrollVideo(k, t)
}
try {
  const pdf = await fetch(`${B}/resume/download`)
  const buf = Buffer.from(await pdf.arrayBuffer())
  report.resume = { status: pdf.status, type: pdf.headers.get('content-type'), bytes: buf.byteLength }
  fs.writeFileSync(`${out}/resume.pdf`, buf)
  try {
    try { execSync('command -v pdftoppm') } catch { execSync('sudo apt-get install -y -q poppler-utils || (sudo apt-get update -q && sudo apt-get install -y -q poppler-utils)', { stdio: 'inherit', timeout: 300000, shell: '/bin/bash' }) }
    execSync(`pdftoppm -r 110 -png ${out}/resume.pdf ${out}/resume-pdf-page`, { timeout: 60000 })
    report.resume.info = execSync(`pdfinfo ${out}/resume.pdf`).toString()
    report.resume.text = execSync(`pdftotext -layout ${out}/resume.pdf -`).toString().slice(0, 6000)
    report.resume.pages = fs.readdirSync(out).filter((f) => f.startsWith('resume-pdf-page'))
  } catch (e) { report.errors.push('pdf render ' + String(e).slice(0, 300)) }
} catch (e) { report.errors.push('api ' + String(e).slice(0, 200)) }
await browser.close()
fs.writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1))
console.log('ERRORS', JSON.stringify(report.errors))
