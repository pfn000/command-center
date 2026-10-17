import { chromium } from 'playwright'
import fs from 'node:fs'
const [base, out] = process.argv.slice(2)
const pages = [['home', '/'], ['about', '/about'], ['projects', '/projects'], ['plex', '/plex']]
const views = [['1600', { width: 1600, height: 900 }, 1, false], ['402', { width: 402, height: 874 }, 2, true]]
const report = []
console.log('start', new Date().toISOString())
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] })
for (const [vn, vp, dpr, mobile] of views) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: dpr, isMobile: mobile, hasTouch: mobile,
    userAgent: mobile ? 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1' : undefined })
  for (const [pn, path] of pages) {
    console.log('page', pn, vn, new Date().toISOString())
    const page = await ctx.newPage(); page.setDefaultTimeout(45000); const errors = []
    page.on('console', m => { if (m.type() === 'error') errors.push(m.text().slice(0, 200)) })
    page.on('pageerror', e => errors.push(String(e).slice(0, 200)))
    let status = null
    try {
      const r = await page.goto(base.replace(/\/$/, '') + path, { waitUntil: 'load', timeout: 45000 }); status = r && r.status()
    } catch (e) { errors.push('goto: ' + String(e).slice(0, 200)) }
    await page.waitForTimeout(2500)
    // walk down so lazy images load, then back to the top
    const h = await page.evaluate(() => document.documentElement.scrollHeight).catch(() => 0)
    for (let y = 0, n = 0; y < h && n < 40; y += vp.height * 0.8, n++) { await page.evaluate(v => window.scrollTo(0, v), y).catch(() => {}); await page.waitForTimeout(200) }
    await page.evaluate(() => window.scrollTo(0, 0)).catch(() => {}); await page.waitForTimeout(800)
    const title = await page.title().catch(() => '')
    const overflowX = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth).catch(() => null)
    const broken = await page.evaluate(() => [...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.getAttribute('src'))).catch(() => [])
    await page.screenshot({ path: `${out}/${pn}-${vn}.jpg`, type: 'jpeg', quality: 82 })
    await page.screenshot({ path: `${out}/${pn}-${vn}-full.jpg`, type: 'jpeg', quality: 60, fullPage: true, timeout: 60000 }).catch(e => errors.push('full: ' + String(e).slice(0, 120)))
    report.push({ page: pn, view: vn, url: page.url(), status, title, overflowX, broken, errors })
    console.log(pn, vn, status, title, 'overflowX=' + overflowX, 'broken=' + broken.length, 'errors=' + errors.length)
    await page.close()
  }
  // section close-ups on home: hero, sketch→built, now building, plex call-out
  try {
    const page = await ctx.newPage()
    await page.goto(base.replace(/\/$/, '') + '/', { waitUntil: 'load', timeout: 45000 })
    await page.waitForTimeout(3000)
    for (const id of ['sketches', 'now', 'plex']) {
      const el = page.locator('#' + id).first()
      await el.scrollIntoViewIfNeeded(); await page.waitForTimeout(1500)
      await el.screenshot({ path: `${out}/sec-${id}-${vn}.jpg`, type: 'jpeg', quality: 78, timeout: 60000 })
    }
    const feed = await page.evaluate(() => { const s = document.querySelector('#now'); return s ? s.innerText.slice(0, 900) : '' })
    console.log('NOW-FEED', vn, JSON.stringify(feed))
    await page.close()
  } catch (e) { console.log('section shot failed', String(e).slice(0, 200)) }
  await ctx.close()
}
await browser.close()
fs.writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1))
