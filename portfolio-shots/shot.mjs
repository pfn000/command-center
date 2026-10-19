import { chromium } from 'playwright'
import fs from 'node:fs'
import { execSync } from 'node:child_process'
const T0 = Date.now()
// v7 r13c SUPPLEMENT (phone light + videos only; r13b run 39184778125 has the rest) (PleX slate + genie video; solid slates/sheet, no donate links, transparent 404 chibi): multi-page restructure (home / work / emmico / worlds / writing / resume / about / companies / plex), glass nav, slates, aura shader, asset pipeline; 1600x900 + 390x844, dark + light
const [base, out] = process.argv.slice(2)
const B = base.replace(/\/$/, '')
const report = { shots: [], errors: [], checks: {} }
const LAUNCH = () => chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'] })
let browser = await LAUNCH()
const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
async function audit(page) {
  return page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    broken: [...document.images].filter((i) => i.complete && i.naturalWidth === 0 && i.style.display !== 'none').map((i) => i.getAttribute('src')).slice(0, 8),
    badLinks: [...document.querySelectorAll('a[href]')].map((a) => a.getAttribute('href')).filter((h) => /tiktok|twitch|youtube|emmiofficial|vr_emmi|notion\.site|instagram|beacons|linkedin|liberapay|\/arch$|\/nos$/i.test(h) || (/vrchat\.com/i.test(h) && !/vrchat\.com\/home\/(launch\?worldId=|world\/)wrld_(383e8b28-9a2c-46de-b7db-2a8ea30f9469|358ffb01-26fc-4566-b2fb-67b099ed3a00)/.test(h))).slice(0, 8),
    launch: [...document.querySelectorAll('a[href*="vrchat.com/home/launch"]')].map((a) => a.getAttribute('href')),
    dupImgs: (() => { const seen = {}; for (const i of document.querySelectorAll('main img')) { const s = (i.getAttribute('src') || ''); if (!s || i.closest('.pf-box')) continue; seen[s] = (seen[s] || 0) + 1 } return Object.entries(seen).filter(([, n]) => n > 1) })(),
    navH: (() => { const b = document.querySelector('.pf-nav7-bar'); return b ? Math.round(b.getBoundingClientRect().height) : null })(),
    whiteTiles: [...document.querySelectorAll('img')].filter((i) => { const cs = getComputedStyle(i); return /rgb\(255, 255, 255\)/.test(cs.backgroundColor) && i.naturalWidth > 0 }).map((i) => i.getAttribute('src')).slice(0, 6),
    oldNos: [...document.images].map((i) => i.getAttribute('src') || '').filter((s) => /nos-|arch-demo|explore-terminal|dev-mama|takeover/.test(s)).slice(0, 8),
    peter: /peter/i.test(document.body.innerText || ''),
    notMine: [...new Set(((document.body.innerText || '') + ' ' + [...document.querySelectorAll('a[href]')].map((a) => a.getAttribute('href')).join(' ')).match(/auravt|lite ?vtuber|localllm|local llm|outlook mcp|ms-outlook|torvalds|pfn000\/(linux|openclaw|claude-code|airi|vitrine)\b|\bvitrine\b/gi) || [])],
    counts: ((document.body.innerText || '').match(/[0-9]+\s+(public\s+)?(repos|repositories|projects)/gi) || []).slice(0, 6),
    oldEmail: /official_emmi|emmi@outlook/i.test(document.documentElement.outerHTML),
    mailto: [...document.querySelectorAll('a[href^="mailto:"]')].map((a) => a.getAttribute('href')).slice(0, 4),
    cutLogos: [...document.images].map((i) => i.getAttribute('src') || '').filter((x) => /\/logos\/(unity|vrchat|vscode)\.svg/.test(x)).length,
    liberapay: (() => { const D = /liberapay|ko-?fi\.com|\bko-fi\b|patreon|buymeacoffee|buy me a coffee|github\.com\/sponsors|opencollective|paypal\.me/i; return D.test(document.body.innerText || '') || [...document.images].some((i) => D.test(i.src)) || [...document.querySelectorAll('a[href]')].some((a) => D.test(a.getAttribute('href') || '')) })(),
    sheetBg: (() => { const s = document.querySelector('.pf-sheet'); return s && !s.hidden ? getComputedStyle(s).backgroundColor + ' | ' + getComputedStyle(s).backdropFilter : null })(),
    slateBg: [...document.querySelectorAll('.pf-main > .pf-slate')].slice(0, 2).map((e) => getComputedStyle(e).backgroundColor),
    navBg: (() => { const b = document.querySelector('.pf-nav7-bar'); return b ? getComputedStyle(b).backgroundColor : null })(),
    monoLogos: [...document.querySelectorAll('img[src$=".svg"]')].filter((i) => /unity|blender|vrchat|github|git\.svg/.test(i.getAttribute('src'))).map((i) => getComputedStyle(i).filter).slice(0, 3),
  })).catch((e) => ({ err: String(e).slice(0, 200) }))
}
async function snap(page, name, opts = {}) {
  try { await page.screenshot({ path: `${out}/${name}.jpg`, type: 'jpeg', quality: 80, timeout: 45000, ...opts }) }
  catch (e) {
    report.errors.push(`shot ${name} try1: ${String(e).slice(0, 140)}`)
    try { await page.waitForTimeout(1500); await page.screenshot({ path: `${out}/${name}.jpg`, type: 'jpeg', quality: 80, timeout: 60000, animations: 'disabled', ...opts }) }
    catch (e2) { report.errors.push(`shot ${name} FAILED: ${String(e2).slice(0, 140)}`); console.log('shot FAILED', name); return }
  }
  const a = await audit(page)
  report.shots.push({ name, ...a })
  console.log('shot', name, JSON.stringify(a))
}
async function ctx(kind, theme) {
  const c = kind === 'p'
    ? await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, userAgent: IPHONE, colorScheme: theme })
    : await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1, colorScheme: theme })
  const p = await c.newPage()
  p.on('console', (m) => m.type() === 'error' && report.errors.push(`${kind}-${theme}: ${m.text().slice(0, 200)}`))
  p.on('pageerror', (e) => report.errors.push(`${kind}-${theme} pageerror: ${String(e).slice(0, 300)}`))
  return { c, p }
}
async function go(p, path, theme, wait = 2500) {
  const sep = path.includes('?') ? '&' : '?'
  const [pth, hash] = path.split('#')
  await p.goto(`${B}${pth}${sep}theme=${theme}${hash ? '#' + hash : ''}`, { waitUntil: 'networkidle', timeout: 45000 }).catch((e) => report.errors.push('goto ' + path + ' ' + String(e).slice(0, 120)))
  await p.waitForTimeout(wait)
}
async function to(p, sel, off = 0) {
  await p.evaluate(([s, o]) => { const el = document.querySelector(s); if (el) window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - o) }, [sel, off])
  await p.waitForTimeout(900)
}
async function lazyAll(p) {
  await p.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 700) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 120)) } window.scrollTo(0, 0) })
  await p.waitForTimeout(1500)
}


const ROUTES = [['01', '/'], ['02', '/work'], ['03', '/emmico'], ['04', '/worlds'], ['05', '/writing'], ['06', '/resume'], ['07', '/about'], ['08', '/companies'], ['09', '/plex']]
const slug = (r) => (r === '/' ? 'home' : r.slice(1))
async function weigh(p, route) {
  return p.evaluate(async () => {
    const res = performance.getEntriesByType('resource')
    const js = res.filter((r) => r.initiatorType === 'script' || /\.js(\?|$)/.test(r.name)).reduce((n, r) => n + (r.transferSize || r.encodedBodySize || 0), 0)
    const all = res.reduce((n, r) => n + (r.transferSize || r.encodedBodySize || 0), 0)
    const imgs = [...document.querySelectorAll('img')].filter((i) => i.complete && i.naturalWidth > 0)
    let before = 0, after = 0
    const size = async (u) => { try { const r = await fetch(u, { cache: 'force-cache' }); return (await r.arrayBuffer()).byteLength } catch { return 0 } }
    for (const i of imgs) { const o = i.getAttribute('src'); const c = i.currentSrc || o; before += await size(o); after += await size(c) }
    return { jsKB: Math.round(js / 1024), allKB: Math.round(all / 1024), imgs: imgs.length, imgOrigKB: Math.round(before / 1024), imgShippedKB: Math.round(after / 1024), opt: imgs.filter((i) => /\/_opt\//.test(i.currentSrc)).length }
  }).catch((e) => ({ err: String(e).slice(0, 120) }))
}
for (const [kind, theme] of [['p', 'light'], ['d', 'dark'], ['p', 'dark'], ['d', 'light']]) {
  if (!browser.isConnected()) browser = await LAUNCH()
  const { c, p } = await ctx(kind, theme)
  const FULL = kind === 'p' && theme === 'light'
  try {
  const k = `${kind}-${theme}`
  const deep = theme === 'dark'
  console.log('ctx', k, Math.round((Date.now() - T0) / 1000))
  for (const [n, route] of (FULL ? ROUTES : [])) {
    await go(p, route, theme, 2600)
    await snap(p, `${k}-${n}-${slug(route)}`)
    if (deep) await lazyAll(p)
    if (route === '/' ) report.checks[`${k}-weight-home`] = await weigh(p, route)
    else if (deep && route === '/work') report.checks[`${k}-weight-${slug(route)}`] = await weigh(p, route)
    const slates = await p.evaluate(() => [...document.querySelectorAll('.pf-slate')].map((s) => Math.round(s.getBoundingClientRect().top + window.scrollY)))
    if (deep || ['/work', '/emmico'].includes(route)) {
      let j = 0
      for (const y of slates.slice(0, deep ? (route === '/work' ? 8 : 3) : (route === '/work' ? 3 : 1))) {
        j++
        await p.evaluate((v) => window.scrollTo(0, v - 70), y); await p.waitForTimeout(700)
        await snap(p, `${k}-${n}b-${slug(route)}-slate${j}`)
        if (route === '/work' && j <= (deep ? 3 : 2)) { await p.evaluate((v) => window.scrollTo(0, v + Math.round(window.innerHeight * 0.55)), y); await p.waitForTimeout(600); await snap(p, `${k}-${n}c-${slug(route)}-slate${j}-mid`) }
      }
    }
    if (route === '/' && deep) {
      await p.evaluate(() => window.scrollTo(0, 400)); await p.waitForTimeout(600)
      await snap(p, `${k}-${n}d-home-nav-scrolled`, { clip: { x: 0, y: 0, width: kind === 'p' ? 390 : 1600, height: 110 } })
      await p.evaluate(() => window.scrollTo(0, 0)); await p.waitForTimeout(500)
      await snap(p, `${k}-${n}e-home-nav`, { clip: { x: 0, y: 0, width: kind === 'p' ? 390 : 1600, height: 110 } })
      await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); await p.waitForTimeout(900)
      await snap(p, `${k}-${n}f-home-footer`)
    }
    if (deep && kind === 'd' && ['/', '/work'].includes(route)) { await p.evaluate(() => window.scrollTo(0, 0)); await snap(p, `${k}-${n}z-${slug(route)}-full`, { fullPage: true, quality: 45 }) }
  }
  // r13 additions: PleX Code slate and the genie-minimize video (on /work and on /emmico)
  try {
    await go(p, '/work', theme, 2200)
    await to(p, '#ncom .pf-genie', kind === 'p' ? 90 : 120); await p.waitForTimeout(1200)
    await snap(p, `${k}-02g-work-genie`)
    if (FULL) { await go(p, '/work', theme, 1800); await to(p, '#plexcode', kind === 'p' ? 70 : 100); await p.waitForTimeout(500); await snap(p, `${k}-02p-work-plexcode`) }
    report.checks[`${k}-genie-work`] = await p.evaluate(() => { const v = document.querySelector('#ncom .pf-genie video'); return v ? { paused: v.paused, t: v.currentTime, muted: v.muted, loop: v.loop, w: v.videoWidth, ready: v.readyState } : null })
    if (FULL) await go(p, '/emmico', theme, 2200)
    if (FULL) await to(p, '#emmi-official .pf-genie', kind === 'p' ? 90 : 120); await p.waitForTimeout(1200)
    if (FULL) await snap(p, `${k}-03g-emmico-genie`)
    report.checks[`${k}-genie-emmico`] = await p.evaluate(() => { const v = document.querySelector('#emmi-official .pf-genie video'); return v ? { paused: v.paused, t: v.currentTime, ready: v.readyState } : null })
  } catch (e) { report.errors.push(`r13 extras ${k}: ${String(e).slice(0, 200)}`) }
  if (kind === 'p' && FULL) {
    await go(p, '/', theme, 2000)
    const btn = await p.$('.pf-menu-btn')
    if (btn) { await btn.tap().catch(() => btn.click()); await p.waitForTimeout(800) }
    await snap(p, `${k}-10-menu-open`)
  }
  if (FULL) { await go(p, '/this-page-does-not-exist', theme, 1500); await snap(p, `${k}-11-404`) }
  for (const r of ['/projects', '/arch', '/emmi', '/contact']) { if (k !== 'd-dark') break; await go(p, r, theme, 800); report.checks[`redirect-${r}`] = p.url().replace(B, '') }
  for (const r of ['AuraVT', 'LiteVtuber', 'LocalLLM-iOS', 'MS-Outlook-MCP', 'linux']) {
    if (k !== 'd-dark') break
    const resp = await p.goto(`${B}/vault/${r}`, { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => null)
    report.checks[`vault-${r}`] = resp ? resp.status() : 'noresp'
  }
  } catch (e) { report.errors.push(`ctx ${kind}-${theme} died: ${String(e).slice(0, 300)}`) }
  await c.close().catch(() => {})
  fs.writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1))
}
fs.writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1))
// MP4s for Saidie: home scroll-throughs (desktop 1600, phone 390) + a tap-to-explain demo. H.264, faststart, each kept under 1.9 MB.
function enc(raw, mp4, ss, to, vf, crf) {
  execSync(`ffmpeg -y -loglevel error -ss ${Math.max(0, ss).toFixed(2)} -to ${to.toFixed(2)} -i ${raw} -vf "${vf},fps=24" -c:v libx264 -preset slow -crf ${crf} -pix_fmt yuv420p -movflags +faststart -an ${mp4}`, { timeout: 240000 })
  return fs.statSync(mp4).size
}
function encFit(raw, mp4, ss, to, vf) {
  let crf = 30, bytes = enc(raw, mp4, ss, to, vf, crf)
  while (bytes > 1.9e6 && crf < 44) { crf += 3; bytes = enc(raw, mp4, ss, to, vf, crf) }
  const dur = Number(execSync(`ffprobe -v error -show_entries format=duration -of csv=p=0 ${mp4}`).toString().trim())
  report.videos = report.videos || []
  report.videos.push({ file: mp4.split('/').pop(), bytes, duration: dur, crf })
  console.log('video', mp4, bytes, dur, crf)
}
async function recCtx(kind, dir) {
  fs.mkdirSync(dir, { recursive: true })
  const opts = kind === 'p'
    ? { viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true, hasTouch: true, userAgent: IPHONE, colorScheme: 'dark', recordVideo: { dir, size: { width: 390, height: 844 } } }
    : { viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1, colorScheme: 'dark', recordVideo: { dir, size: { width: 1600, height: 900 } } }
  const c = await browser.newContext(opts)
  return { c, p: await c.newPage() }
}
async function scrollVideo(kind) {
  const t0 = Date.now()
  const { c, p } = await recCtx(kind, `/tmp/vid-${kind}`)
  try {
    await go(p, '/', 'dark', 3500)
    const tHome = (Date.now() - t0) / 1000
    await p.waitForTimeout(2200)
    await p.evaluate(() => window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' })); await p.waitForTimeout(1800)
    const tHomeEnd = (Date.now() - t0) / 1000
    await go(p, '/work', 'dark', 3000)
    const H0 = await p.evaluate(() => document.documentElement.scrollHeight - window.innerHeight)
    for (let y = 0; y <= H0; y += 800) { await p.evaluate((v) => window.scrollTo(0, v), y); await p.waitForTimeout(90) }
    await p.evaluate(() => window.scrollTo(0, 0)); await p.waitForTimeout(2000)
    const tStart = (Date.now() - t0) / 1000
    await p.waitForTimeout(1200)
    const H = Math.min(await p.evaluate(() => document.documentElement.scrollHeight - window.innerHeight), kind === 'p' ? 16000 : 14000)
    const steps = 340
    for (let k = 1; k <= steps; k++) {
      const e = k / steps, ease = e < 0.5 ? 2 * e * e : 1 - Math.pow(-2 * e + 2, 2) / 2
      await p.evaluate((v) => window.scrollTo(0, v), Math.round(H * ease))
      await p.waitForTimeout(65)
    }
    await p.waitForTimeout(1000)
    const tEnd = (Date.now() - t0) / 1000
    await c.close()
    const raw = await p.video().path()
    // two pieces: home (hero + tiles), then the Work page scrolling through the stacked slates
    execSync(`ffmpeg -y -loglevel error -ss ${tHome.toFixed(2)} -to ${tHomeEnd.toFixed(2)} -i ${raw} -c:v libx264 -preset ultrafast -crf 18 -an /tmp/a-${kind}.mp4 && ffmpeg -y -loglevel error -ss ${tStart.toFixed(2)} -to ${tEnd.toFixed(2)} -i ${raw} -c:v libx264 -preset ultrafast -crf 18 -an /tmp/b-${kind}.mp4 && printf "file /tmp/a-${kind}.mp4\nfile /tmp/b-${kind}.mp4\n" > /tmp/l-${kind}.txt && ffmpeg -y -loglevel error -f concat -safe 0 -i /tmp/l-${kind}.txt -c copy /tmp/j-${kind}.mp4`, { timeout: 200000 })
    encFit(`/tmp/j-${kind}.mp4`, `${out}/video-${kind}-dark-home-work-scroll.mp4`, 0, 9999, kind === 'p' ? 'scale=390:844' : 'scale=1280:720:flags=lanczos')
  } catch (e) { report.errors.push(`video ${kind}: ${String(e).slice(0, 300)}`); try { await c.close() } catch {} }
}
async function menuVideo() {
  const t0 = Date.now()
  const { c, p } = await recCtx('p', '/tmp/vid-menu')
  try {
    await go(p, '/', 'dark', 3200)
    const tStart = (Date.now() - t0) / 1000
    await p.waitForTimeout(1200)
    for (const label of ['Work', 'EmmiCO', 'Worlds']) {
      const btn = await p.$('.pf-nav7 .pf-menu-btn')
      if (btn) { await btn.tap().catch(() => btn.click()); await p.waitForTimeout(1300) }
      const link = await p.$(`.pf-sheet-links a:has-text("${label}")`)
      if (link) { await link.tap().catch(() => link.click()); await p.waitForTimeout(2600) }
      await p.evaluate(() => window.scrollTo({ top: 900, behavior: 'smooth' })); await p.waitForTimeout(1600)
    }
    const tEnd = (Date.now() - t0) / 1000
    await c.close()
    const raw = await p.video().path()
    encFit(raw, `${out}/video-p-dark-menu-nav.mp4`, tStart, tEnd, 'scale=390:844')
  } catch (e) { report.errors.push(`video menu: ${String(e).slice(0, 300)}`); try { await c.close() } catch {} }
}
fs.writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1))
try { execSync('command -v ffmpeg') } catch { try { execSync('sudo apt-get install -y -q ffmpeg || (sudo apt-get update -q && sudo apt-get install -y -q ffmpeg)', { stdio: 'inherit', timeout: 240000, shell: '/bin/bash' }) } catch (e) { report.errors.push('ffmpeg install ' + String(e).slice(0, 200)) } }
for (const [name, job] of [['d', () => scrollVideo('d')], ['p', () => scrollVideo('p')], ['menu', () => menuVideo()]]) {
  if (Date.now() - T0 > 760000) { report.errors.push('video skipped: time'); continue }
  try { await browser.close() } catch {}
  browser = await LAUNCH()
  console.log('video job', name, Math.round((Date.now() - T0) / 1000))
  await Promise.race([job().catch((e) => report.errors.push(`video ${name} threw: ${String(e).slice(0, 200)}`)), new Promise((r) => setTimeout(() => { report.errors.push(`video ${name}: hard timeout 200s`); r() }, 200000))])
  fs.writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1))
}
try { await browser.close() } catch {}
browser = await LAUNCH()
fs.writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1))
// lighthouse last
// Lighthouse (phone) on home, if it fits
try {
  if (Date.now() - T0 < 780000) {
    const chrome = chromium.executablePath()
    execSync(`CHROME_PATH=${chrome} timeout -k 5 150 npx -y lighthouse@12 ${B}/ --only-categories=performance --form-factor=mobile --quiet --chrome-flags="--headless=new --no-sandbox" --output=json --output-path=/tmp/lh.json`, { stdio: 'ignore', timeout: 170000, shell: '/bin/bash' })
    const lh = JSON.parse(fs.readFileSync('/tmp/lh.json', 'utf8'))
    report.lighthouse = { perf: Math.round((lh.categories.performance.score || 0) * 100), lcp: lh.audits['largest-contentful-paint'].displayValue, cls: lh.audits['cumulative-layout-shift'].displayValue, tbt: lh.audits['total-blocking-time'].displayValue, fcp: lh.audits['first-contentful-paint'].displayValue, weight: lh.audits['total-byte-weight'].displayValue }
  } else report.lighthouse = 'skipped: time'
} catch (e) { report.lighthouse = 'failed: ' + String(e).slice(0, 160) }
fs.writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1))
console.log('DONE', report.shots.length, 'shots', report.errors.length, 'errors')
await browser.close()

// push 1792374059089599597
// push 1792374120972951987
