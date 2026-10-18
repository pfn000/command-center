import { chromium } from 'playwright'
import fs from 'node:fs'
// v6 r4 proof (light-mode tool logos, Cuddle Cove hero crop, old email removed): headline work (Emmi_Official, EmmiCO, worlds), tap-to-explain glass panels, résumé logos, companies, /plex docs page, big legal badge bottom-right; 1600x900 + 390x844, dark + light
const [base, out] = process.argv.slice(2)
const B = base.replace(/\/$/, '')
const report = { shots: [], errors: [], checks: {} }
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] })
const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
async function audit(page) {
  return page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    broken: [...document.images].filter((i) => i.complete && i.naturalWidth === 0 && i.style.display !== 'none').map((i) => i.getAttribute('src')).slice(0, 8),
    badLinks: [...document.querySelectorAll('a[href]')].map((a) => a.getAttribute('href')).filter((h) => /tiktok|twitch|youtube|emmiofficial|vr_emmi|notion\.site|instagram|beacons|linkedin|\/arch$|\/nos$/i.test(h)).slice(0, 8),
    oldNos: [...document.images].map((i) => i.getAttribute('src') || '').filter((s) => /nos-|arch-demo|explore-terminal|dev-mama|takeover/.test(s)).slice(0, 8),
    peter: /peter/i.test(document.body.innerText || ''),
    oldEmail: /official_emmi|emmi@outlook/i.test(document.documentElement.outerHTML),
    mailto: [...document.querySelectorAll('a[href^="mailto:"]')].map((a) => a.getAttribute('href')).slice(0, 4),
    monoLogos: [...document.querySelectorAll('img[src$=".svg"]')].filter((i) => /unity|blender|vrchat|github|git\.svg/.test(i.getAttribute('src'))).map((i) => getComputedStyle(i).filter).slice(0, 3),
  })).catch((e) => ({ err: String(e).slice(0, 200) }))
}
async function snap(page, name, opts = {}) {
  await page.screenshot({ path: `${out}/${name}.jpg`, type: 'jpeg', quality: 80, ...opts })
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
for (const [kind, theme] of [['d', 'dark'], ['p', 'dark'], ['d', 'light'], ['p', 'light']]) {
  const full = theme === 'dark'
  const { c, p } = await ctx(kind, theme)
  const k = `${kind}-${theme}`
  await go(p, '/', theme)
  await snap(p, `${k}-01-home`)
  await lazyAll(p)
  if (full) await snap(p, `${k}-00-home-full`, { fullPage: true, quality: 55 })
  for (const [n, sel] of [['02-emmi-official', '#emmi-official'], ['03-emmico', '#emmico'], ['04-worlds', '#worlds'], ['04b-talks', '#talks'], ['05-ncom', '#ncom'], ['05b-ncom-demos', '#nos'], ['06-jena', '#jena'], ['06b-focals', '#focals'], ['06c-moments', '#moments'], ['07-resume-preview', '#resume'], ['07b-resume-preview-2', '.pf-cv-grid'], ['08-projects', '#projects'], ['09-companies', '#companies'], ['09b-writing', '#writing']]) {
    if (!full && !['03-emmico', '06b-focals', '07-resume-preview', '09-companies', '09b-writing'].includes(n)) continue
    await to(p, sel, 10)
    await snap(p, `${k}-${n}`)
  }
  // tap-to-explain: open the first EmmiCO shot's panel
  await to(p, '#emmico .pf-shot', 30)
  const btn = await p.$('#emmico .pf-shot .pf-shot-img')
  if (btn) { await btn.click(); await p.waitForTimeout(900) }
  const panel = await p.evaluate(() => { const el = document.querySelector('#emmico .pf-shot.open .pf-shot-panel > div'); if (!el) return null; const r = el.getBoundingClientRect(); return { h: Math.round(r.height), text: el.innerText.slice(0, 120) } })
  report.checks[`${k}-panel`] = panel
  await to(p, '#emmico .pf-shot', 30)
  await snap(p, `${k}-10-panel-open`)
  // footer badge at the bottom-right
  await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); await p.waitForTimeout(1000)
  report.checks[`${k}-badge`] = await p.evaluate(() => { const i = document.querySelector('.pf-badge'); if (!i) return null; const r = i.getBoundingClientRect(); return { w: Math.round(r.width), right_gap: Math.round(window.innerWidth - r.right), bottom: Math.round(r.bottom), vh: window.innerHeight, docBottomGap: Math.round(document.documentElement.scrollHeight - (r.bottom + window.scrollY)) } })
  await snap(p, `${k}-11-footer-badge`)
  // résumé page
  await go(p, '/resume', theme)
  await snap(p, `${k}-12-resume`)
  await to(p, '.pf-job:nth-of-type(2)', 10)
  await snap(p, `${k}-13-resume-logos`)
  if (full) { await lazyAll(p); await snap(p, `${k}-12b-resume-full`, { fullPage: true, quality: 55 }) }
  report.checks[`${k}-resume-logos`] = await p.evaluate(() => [...document.querySelectorAll('.pf-job-logos img')].map((i) => [i.getAttribute('src'), i.naturalWidth]))
  // plex page
  if (full) {
    await go(p, '/plex', theme, 4000)
    await snap(p, `${k}-14-plex`)
    await to(p, '#docs', 10)
    await snap(p, `${k}-15-plex-docs`)
    // redirects
    await to(p, '.pf-plex-note', 80)
    await snap(p, `${k}-14b-plex-note`)
    for (const slug of ['ai-being-used-wrong', 'future-of-ads']) {
      await go(p, `/writing/${slug}`, theme, 2500)
      await snap(p, `${k}-16-article-${slug}`)
      await p.evaluate(() => window.scrollTo(0, 1400)); await p.waitForTimeout(800)
      await snap(p, `${k}-16b-article-${slug}`)
    }
    await go(p, '/writing', theme, 2000)
    await snap(p, `${k}-17-writing`)
    await go(p, '/arch', theme, 800)
    report.checks[`${k}-arch-redirect`] = p.url()
  }
  await c.close()
}
fs.writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1))
console.log('DONE', report.shots.length, 'shots', report.errors.length, 'errors')
await browser.close()
