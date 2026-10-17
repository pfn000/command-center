import { chromium } from 'playwright'
import fs from 'node:fs'
const [base, out] = process.argv.slice(2)
const B = base.replace(/\/$/, '')
const report = { shots: [], errors: [] }
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] })
const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
async function audit(page) {
  return page.evaluate(() => ({
    overflowX: document.documentElement.scrollWidth - window.innerWidth,
    broken: [...document.images].filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.getAttribute('src')).slice(0, 8),
    peter: /peter/i.test(document.body.innerText || ''),
    offsite: [...document.querySelectorAll('a[href^="http"]')].filter((a) => a.closest('.nwin:not(.min)')).map((a) => a.getAttribute('href')).slice(0, 12),
    dockRadius: getComputedStyle(document.querySelector('.nos-dock') || document.body).borderRadius,
    wins: [...document.querySelectorAll('.nwin:not(.min)')].map((w) => w.getAttribute('data-app')),
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
    ? await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, userAgent: IPHONE, colorScheme: theme })
    : await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1, colorScheme: theme })
  const p = await c.newPage()
  p.on('console', (m) => m.type() === 'error' && report.errors.push(`${kind}-${theme}: ${m.text().slice(0, 200)}`))
  p.on('pageerror', (e) => report.errors.push(`${kind}-${theme} pageerror: ${String(e).slice(0, 300)}`))
  return { c, p }
}
async function go(p, q, wait = 3500) {
  await p.goto(`${B}/?nocoach=1&theme=${q.theme}${q.app ? '&app=' + q.app : ''}`, { waitUntil: 'networkidle', timeout: 45000 }).catch((e) => report.errors.push('goto ' + String(e).slice(0, 120)))
  await p.waitForTimeout(wait)
}
for (const theme of ['dark', 'light']) {
  const { c, p } = await ctxFor('desk', theme)
  await go(p, { theme })
  await snap(p, `d-${theme}-1-about`)
  if (theme === 'dark') {
    // close-ups: the hat (window top-right), the menu bar, the dock
    const w = await p.locator('[data-app=about]').first().boundingBox()
    if (w) await snap(p, 'z-hat', { clip: { x: w.x + w.width - 190, y: w.y - 6, width: 196, height: 80 } })
    await snap(p, 'z-menubar', { clip: { x: 0, y: 0, width: 800, height: 60 } })
    const dk = await p.locator('.nos-dock').first().boundingBox()
    if (dk) await snap(p, 'z-dock', { clip: { x: Math.max(0, dk.x - 20), y: dk.y - 20, width: Math.min(1600, dk.width + 40), height: dk.height + 36 } })
    await p.locator('[data-app=about] .nwin-body').first().evaluate((el) => el.scrollTo(0, 700)).catch(() => {})
    await p.waitForTimeout(800)
    await snap(p, 'd-dark-1b-about-scrolled')
  }
  for (const [i, app] of ['projects', 'plex', 'now', 'emmi', 'resume', 'contact', 'jena'].entries()) {
    if (theme === 'light' && !['projects', 'plex', 'now'].includes(app)) continue
    await go(p, { theme, app }, 5000)
    await snap(p, `d-${theme}-${i + 2}-${app}`)
    if (theme === 'dark' && (app === 'projects' || app === 'plex')) {
      await p.locator(`[data-app=${app}] .nwin-body`).first().evaluate((el) => el.scrollTo(0, 900)).catch(() => {})
      await p.waitForTimeout(1500)
      await snap(p, `d-dark-${i + 2}b-${app}-scrolled`)
    }
    if (theme === 'dark' && app === 'plex') {
      await p.getByRole('button', { name: 'Language spec' }).first().click().catch(() => {})
      await p.waitForTimeout(800)
      await p.locator('[data-app=plex] .nwin-body').first().evaluate((el) => el.scrollTo(0, 600)).catch(() => {})
      await p.waitForTimeout(800)
      await snap(p, 'd-dark-3c-plex-docs')
    }
    if (theme === 'dark' && app === 'projects') {
      await p.getByRole('button', { name: /AuraVT/ }).first().click().catch(() => {})
      await p.waitForTimeout(2500)
      await p.locator('[data-app=projects] .nwin-body').first().evaluate((el) => el.scrollTo(0, 0)).catch(() => {})
      await snap(p, 'd-dark-2c-projects-auravt')
    }
  }
  await c.close()
}
for (const theme of ['dark', 'light']) {
  const { c, p } = await ctxFor('phone', theme)
  await go(p, { theme })
  await snap(p, `p-${theme}-1-about`)
  if (theme === 'dark') {
    for (const [i, app] of ['projects', 'plex', 'now', 'resume', 'emmi'].entries()) {
      await go(p, { theme, app }, 5000)
      await snap(p, `p-dark-${i + 2}-${app}`)
    }
  }
  await c.close()
}
try {
  const pdf = await fetch(`${B}/resume/download`)
  report.resume = { status: pdf.status, type: pdf.headers.get('content-type'), bytes: (await pdf.arrayBuffer()).byteLength }
  const gh = await fetch(`${B}/data/gh.json`)
  report.gh = { status: gh.status, bytes: (await gh.arrayBuffer()).byteLength }
} catch (e) { report.errors.push('api ' + String(e).slice(0, 200)) }
await browser.close()
fs.writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1))
console.log('ERRORS', JSON.stringify(report.errors))
