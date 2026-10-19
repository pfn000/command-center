import { chromium } from 'playwright'
import fs from 'node:fs'
// r13d: genie video PLAYBACK proof in real Google Chrome (H.264). Playwright's bundled Chromium has no H.264 decoder,
// so the earlier runs could only show the poster. Both placements: /work NCOM Arch slate and /emmico next to the growth video.
const [base, out] = process.argv.slice(2)
const B = base.replace(/\/$/, '')
const report = { errors: [], checks: {}, browser: null }
let browser
try { browser = await chromium.launch({ channel: 'chrome', args: ['--autoplay-policy=no-user-gesture-required'] }); report.browser = 'chrome ' + browser.version() }
catch (e) { report.errors.push('chrome channel: ' + String(e).slice(0, 200)); browser = await chromium.launch(); report.browser = 'chromium ' + browser.version() }
const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
const stat = (p, sel) => p.evaluate((s) => { const v = document.querySelector(s); if (!v) return null; const r = v.getBoundingClientRect(); return { src: v.currentSrc, videoWidth: v.videoWidth, videoHeight: v.videoHeight, readyState: v.readyState, currentTime: +v.currentTime.toFixed(2), paused: v.paused, muted: v.muted, loop: v.loop, autoplay: v.autoplay, playsInline: v.playsInline, inView: r.top < innerHeight && r.bottom > 0, error: v.error ? v.error.code : null } }, sel)
for (const [kind, theme] of [['d', 'dark'], ['p', 'dark'], ['d', 'light']]) {
  const c = kind === 'p'
    ? await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, userAgent: IPHONE, colorScheme: theme })
    : await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1, colorScheme: theme })
  const p = await c.newPage()
  p.on('pageerror', (e) => report.errors.push(`${kind}-${theme} pageerror: ${String(e).slice(0, 200)}`))
  for (const [path, sel, name] of [['/work', '#ncom .pf-genie video', '02g-work-genie'], ['/emmico', '#emmi-official .pf-genie video', '03g-emmico-genie']]) {
    const k = `${kind}-${theme}-${name}`
    try {
      await p.goto(`${B}${path}?theme=${theme}`, { waitUntil: 'networkidle', timeout: 45000 })
      await p.waitForTimeout(1500)
      await p.evaluate((s) => { const v = document.querySelector(s); if (v) { const fig = v.closest('figure'); const r = fig.getBoundingClientRect(); window.scrollTo(0, r.top + window.scrollY - Math.max(80, (innerHeight - r.height) / 2)) } }, sel)
      await p.waitForTimeout(2500)
      const a = await stat(p, sel)
      await p.screenshot({ path: `${out}/${kind}-${theme}-${name}-playing.jpg`, type: 'jpeg', quality: 80, timeout: 45000 })
      await p.waitForTimeout(1200)
      const b = await stat(p, sel)
      report.checks[k] = { at2_5s: a, at3_7s: b, plays: !!(b && b.videoWidth > 0 && b.readyState >= 3 && !b.paused && (b.currentTime > 0.5 || b.currentTime !== a.currentTime)) }
      console.log(k, JSON.stringify(report.checks[k]))
    } catch (e) { report.errors.push(`${k}: ${String(e).slice(0, 200)}`) }
  }
  await c.close().catch(() => {})
}
fs.writeFileSync(`${out}/report-play.json`, JSON.stringify(report, null, 1))
console.log('DONE', report.browser)
await browser.close()
