import { chromium } from 'playwright'
import fs from 'node:fs'
const [url, out] = process.argv.slice(2)
const report = { url, shots: [], errors: [] }
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] })
const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
for (const [kind, theme] of [['desktop','dark'],['desktop','light'],['phone','dark'],['phone','light']]) {
  const c = kind === 'phone'
    ? await browser.newContext({ viewport: { width: 402, height: 874 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, userAgent: IPHONE, colorScheme: theme })
    : await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1, colorScheme: theme })
  const p = await c.newPage()
  p.on('pageerror', (e) => report.errors.push(`${kind}-${theme}: ${String(e).slice(0, 200)}`))
  try {
    const r = await p.goto(url, { waitUntil: 'networkidle', timeout: 60000 })
    await p.waitForTimeout(3500)
    const name = `live-${kind}-${theme}`
    await p.screenshot({ path: `${out}/${name}.jpg`, type: 'jpeg', quality: 82 })
    const a = await p.evaluate(() => ({ title: document.title, finalUrl: location.href, overflowX: document.documentElement.scrollWidth - window.innerWidth,
      peter: /peter/i.test(document.body.innerText || ''), login: /log in to vercel|vercel authentication/i.test(document.body.innerText || ''),
      broken: [...document.images].filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.getAttribute('src')).slice(0, 8),
      text: (document.body.innerText || '').slice(0, 400) }))
    report.shots.push({ name, status: r && r.status(), ...a })
    console.log('shot', name, r && r.status(), JSON.stringify(a).slice(0, 300))
    if (theme === 'dark') { await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); await p.waitForTimeout(1500)
      await p.screenshot({ path: `${out}/live-${kind}-${theme}-full.jpg`, type: 'jpeg', quality: 70, fullPage: true }).catch((e) => report.errors.push('full ' + e)) }
  } catch (e) { report.errors.push(`${kind}-${theme} goto: ${String(e).slice(0, 200)}`) }
  await c.close()
}
fs.writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1))
await browser.close()
