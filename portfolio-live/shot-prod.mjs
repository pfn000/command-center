import { chromium } from 'playwright'
import fs from 'node:fs'
// Prod check for Saidie's live portfolio: every route at 1600x900 + 390x844 (dark; home also light), phone menu open, 404,
// genie video playback in real Chrome (H.264), banned-string audit on rendered text + raw HTML.
const [base, out] = process.argv.slice(2)
const B = base.replace(/\/$/, '')
const report = { base: B, shots: [], errors: [], play: {}, browser: null }
const ROUTES = [['01', '/'], ['02', '/work'], ['03', '/emmico'], ['04', '/worlds'], ['05', '/writing'], ['06', '/resume'], ['07', '/about'], ['08', '/companies'], ['09', '/plex']]
const slug = (r) => (r === '/' ? 'home' : r.slice(1))
const BANNED = /liberapay|ko-fi|ko‑fi|patreon|buymeacoffee|buy me a coffee|github sponsors|emmiofficial|official_emmi|tiktok_emmi|peternewara8|724[ .)-]*831[ .-]*3809/i
const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
let browser
try { browser = await chromium.launch({ channel: 'chrome', args: ['--autoplay-policy=no-user-gesture-required'] }); report.browser = 'chrome ' + browser.version() }
catch (e) { report.errors.push('chrome channel: ' + String(e).slice(0, 200)); browser = await chromium.launch(); report.browser = 'chromium ' + browser.version() }
async function ctx(kind, theme) {
  const c = kind === 'p'
    ? await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, userAgent: IPHONE, colorScheme: theme })
    : await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1, colorScheme: theme })
  const p = await c.newPage()
  p.on('pageerror', (e) => report.errors.push(`${kind}-${theme} pageerror: ${String(e).slice(0, 200)}`))
  return { c, p }
}
async function go(p, path, theme, wait = 2500) {
  let st = null
  try { const r = await p.goto(`${B}${path}${path.includes('?') ? '&' : '?'}theme=${theme}`, { waitUntil: 'networkidle', timeout: 45000 }); st = r && r.status() }
  catch (e) { report.errors.push('goto ' + path + ' ' + String(e).slice(0, 120)) }
  await p.waitForTimeout(wait); return st
}
async function audit(p) {
  return p.evaluate((bannedSrc) => {
    const re = new RegExp(bannedSrc, 'i'); const t = document.body.innerText || ''; const h = document.documentElement.outerHTML
    const hits = (s) => { const m = s.match(new RegExp(bannedSrc, 'gi')); return m ? [...new Set(m)].slice(0, 6) : [] }
    return { title: document.title, url: location.href, overflowX: document.documentElement.scrollWidth - window.innerWidth,
      bannedText: hits(t), bannedHtml: hits(h), email: /saidienewara@gmail\.com/.test(t), mailto: /mailto:/i.test(h),
      broken: [...document.images].filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.getAttribute('src')).slice(0, 8),
      login: /log in to vercel|vercel authentication/i.test(t), textLen: t.length, head: t.slice(0, 160) }
  }, BANNED.source)
}
async function snap(p, name, status, opts = {}) {
  try { await p.screenshot({ path: `${out}/${name}.jpg`, type: 'jpeg', quality: 80, timeout: 45000, ...opts }) }
  catch (e) { try { await p.screenshot({ path: `${out}/${name}.jpg`, type: 'jpeg', quality: 80, timeout: 60000, animations: 'disabled', ...opts }) } catch (e2) { report.errors.push(`shot ${name} FAILED ${String(e2).slice(0, 120)}`) } }
  const a = await audit(p).catch((e) => ({ err: String(e).slice(0, 120) }))
  report.shots.push({ name, status, ...a }); console.log('shot', name, status, JSON.stringify(a).slice(0, 260))
}
for (const [kind, theme] of [['d', 'dark'], ['p', 'dark'], ['d', 'light'], ['p', 'light']]) {
  const { c, p } = await ctx(kind, theme)
  const k = `${kind}-${theme}`
  const all = theme === 'dark'
  try {
    for (const [n, route] of (all ? ROUTES : [['01', '/'], ['02', '/work']])) {
      const st = await go(p, route, theme)
      await snap(p, `${k}-${n}-${slug(route)}`, st)
      if (all && (route === '/' || route === '/work')) {
        await p.evaluate(async () => { for (let y = 0; y < document.body.scrollHeight; y += 700) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 120)) } })
        await p.waitForTimeout(1500)
        await snap(p, `${k}-${n}z-${slug(route)}-full`, st, { fullPage: true, quality: 60 })
      }
    }
    if (kind === 'p') {
      await go(p, '/', theme, 2000)
      const btn = await p.$('.pf-menu-btn')
      if (btn) { await btn.tap().catch(() => btn.click()); await p.waitForTimeout(900) } else report.errors.push('no .pf-menu-btn ' + k)
      await snap(p, `${k}-10-menu-open`, 200)
    }
    if (all) { const st = await go(p, '/this-page-does-not-exist', theme, 1500); await snap(p, `${k}-11-404`, st) }
  } catch (e) { report.errors.push(`${k}: ${String(e).slice(0, 200)}`) }
  await c.close()
}
// genie playback
const stat = (p, sel) => p.evaluate((s) => { const v = document.querySelector(s); if (!v) return null; const r = v.getBoundingClientRect(); return { src: v.currentSrc, videoWidth: v.videoWidth, readyState: v.readyState, currentTime: +v.currentTime.toFixed(2), paused: v.paused, inView: r.top < innerHeight && r.bottom > 0, error: v.error ? v.error.code : null } }, sel)
for (const kind of ['d', 'p']) {
  const { c, p } = await ctx(kind, 'dark')
  for (const [path, sel, name] of [['/work', '#ncom .pf-genie video', '02g-work-genie'], ['/emmico', '#emmi-official .pf-genie video', '03g-emmico-genie']]) {
    const k = `${kind}-dark-${name}`
    try {
      await go(p, path, 'dark', 1500)
      await p.evaluate((s) => { const v = document.querySelector(s); if (v) { const f = v.closest('figure') || v; const r = f.getBoundingClientRect(); window.scrollTo(0, r.top + window.scrollY - Math.max(80, (innerHeight - r.height) / 2)) } }, sel)
      await p.waitForTimeout(2500); const a = await stat(p, sel)
      await snap(p, `${k}-playing`, 200)
      await p.waitForTimeout(1200); const b = await stat(p, sel)
      report.play[k] = { a, b, plays: !!(b && b.videoWidth > 0 && b.readyState >= 2 && !b.paused && a && b.currentTime !== a.currentTime) }
      console.log('play', k, JSON.stringify(report.play[k]))
    } catch (e) { report.errors.push(`play ${k}: ${String(e).slice(0, 200)}`) }
  }
  await c.close()
}
fs.writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1))
await browser.close()
console.log('DONE', report.errors.length, 'errors')
