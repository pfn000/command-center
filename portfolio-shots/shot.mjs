import { chromium } from 'playwright'
import fs from 'node:fs'
import { execSync } from 'node:child_process'
const [base, out] = process.argv.slice(2)
const B = base.replace(/\/$/, '')
const report = { shots: [], checks: {} }
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] })
const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
const CURSOR = `(() => { const d = document.createElement('div'); d.id = '__cur'; Object.assign(d.style, { position: 'fixed', left: '0', top: '0', width: '22px', height: '22px', marginLeft: '-11px', marginTop: '-11px', borderRadius: '11px', background: 'rgba(255,255,255,.55)', border: '2px solid rgba(20,20,40,.8)', zIndex: 99999, pointerEvents: 'none', transition: 'transform .08s, background .08s' }); document.addEventListener('DOMContentLoaded', () => document.body.appendChild(d)); addEventListener('pointermove', e => { d.style.left = e.clientX + 'px'; d.style.top = e.clientY + 'px' }, true); addEventListener('pointerdown', () => { d.style.transform = 'scale(.7)'; d.style.background = 'rgba(120,90,255,.7)' }, true); addEventListener('pointerup', () => { d.style.transform = ''; d.style.background = 'rgba(255,255,255,.55)' }, true) })()`

async function audit(page, name) {
  return page.evaluate(() => {
    const text = document.body.innerText || ''
    const alts = [...document.images].map((i) => i.alt || '').join(' | ')
    return {
      overflowX: document.documentElement.scrollWidth - window.innerWidth,
      broken: [...document.images].filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.getAttribute('src')),
      peter: /peter/i.test(text) || /peter/i.test(alts),
      cream: getComputedStyle(document.querySelector('.nos') || document.body).backgroundColor,
    }
  }).then((a) => ({ name, ...a })).catch((e) => ({ name, err: String(e).slice(0, 200) }))
}
async function snap(page, name, opts = {}) {
  await page.screenshot({ path: `${out}/${name}.jpg`, type: 'jpeg', quality: 84, ...opts })
  const a = await audit(page, name)
  report.shots.push(a)
  console.log('shot', name, JSON.stringify(a))
}
async function center(page, sel) {
  const b = await page.locator(sel).first().boundingBox()
  return { x: b.x + b.width / 2, y: b.y + b.height / 2, b }
}
async function drag(page, from, to, { hold = 0, steps = 18, keep = false } = {}) {
  await page.mouse.move(from.x, from.y)
  await page.mouse.down()
  if (hold) await page.waitForTimeout(hold)
  await page.mouse.move(to.x, to.y, { steps })
  if (!keep) await page.mouse.up()
}
const errors = []

async function desktop(theme) {
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1, colorScheme: theme })
  const page = await ctx.newPage()
  page.on('console', (m) => m.type() === 'error' && errors.push(`${theme}: ${m.text().slice(0, 200)}`))
  page.on('pageerror', (e) => errors.push(`${theme} pageerror: ${String(e).slice(0, 300)}`))
  page.on('response', (x) => x.status() >= 400 && errors.push(`${theme} HTTP ${x.status()} ${x.url().slice(0, 200)}`))
  const r = await page.goto(`${B}/?theme=${theme}`, { waitUntil: 'networkidle', timeout: 60000 })
  report.checks[`status_${theme}`] = r && r.status()
  await page.waitForTimeout(2200)
  await snap(page, `tour-1600-${theme}`)
  try {
    if (theme === 'light') {
      await page.locator('.coach').getByRole('button', { name: 'Next', exact: true }).click(); await page.waitForTimeout(500)
      await snap(page, 'tour2-1600-light')
      await page.locator('.coach').getByRole('button', { name: 'Next', exact: true }).click(); await page.waitForTimeout(500)
      await snap(page, 'tour3-1600-light')
      await page.locator('.coach').getByRole('button', { name: 'Got it', exact: true }).click()
    } else {
      await page.locator('.coach').getByRole('button', { name: 'Skip', exact: true }).click()
    }
    await page.waitForTimeout(500)
  } catch (e) { errors.push('tour: ' + String(e).slice(0, 200)) }
  report.checks[`coach_gone_${theme}`] = (await page.locator('.coach').count()) === 0
  await snap(page, `desk-1600-${theme}`)
  try {
    await page.locator('[data-app=about]').screenshot({ path: `${out}/hero-app-${theme}.jpg`, type: 'jpeg', quality: 86 })
  } catch (e) { errors.push('hero el shot ' + String(e).slice(0, 120)) }
  if (theme === 'light') {
    try {
      // open Projects from the dock, then hold ••• and move it (shot mid-move), then resize from the hidden corner (shot mid-resize)
      await page.getByRole('button', { name: 'Explore my work' }).click()
      await page.waitForTimeout(900)
      await snap(page, 'projects-open-1600-light')
      const d = await center(page, '[data-app=projects] .ctl-dots')
      await drag(page, d, { x: d.x - 260, y: d.y + 70 }, { hold: 420, keep: true })
      await page.waitForTimeout(150)
      await snap(page, 'window-moving-1600-light')
      await page.mouse.up()
      await page.waitForTimeout(600)
      const rz = await center(page, '[data-app=projects] .rz.br')
      await drag(page, rz, { x: rz.x - 230, y: rz.y - 160 }, { keep: true })
      await page.waitForTimeout(150)
      await snap(page, 'window-resizing-1600-light')
      await page.mouse.up()
      await page.waitForTimeout(700)
      // tap the pill = info popover
      await page.locator('[data-app=projects] .ctl-pill').click()
      await page.waitForTimeout(700)
      await snap(page, 'pill-info-1600-light')
      await page.keyboard.press('Escape')
      // ••• tap = program menu
      await page.locator('[data-app=projects] .ctl-dots').click()
      await page.waitForTimeout(500)
      await page.locator('[data-app=projects] .nmenu button.top').first().click()
      await page.waitForTimeout(500)
      await snap(page, 'dots-menu-1600-light')
      await page.keyboard.press('Escape')
      // lightbox
      await page.locator('[data-app=projects] .fig').first().click()
      await page.waitForTimeout(900)
      await snap(page, 'lightbox-1600-light')
      await page.keyboard.press('Escape')
    } catch (e) { errors.push('desktop gestures: ' + String(e).slice(0, 300)) }
  }
  try {
    await page.getByRole('button', { name: 'Open Contact' }).click()
    await page.waitForTimeout(1000)
    await snap(page, `contact-1600-${theme}`)
    await page.locator('[data-app=contact]').screenshot({ path: `${out}/contact-app-${theme}.jpg`, type: 'jpeg', quality: 86 })
  } catch (e) { errors.push('contact: ' + String(e).slice(0, 200)) }
  if (theme === 'dark') {
    try {
      await page.getByRole('button', { name: 'Open Now building' }).click()
      await page.waitForTimeout(2500)
      await snap(page, 'now-1600-dark')
      await page.getByRole('button', { name: 'Open Jena' }).click()
      await page.waitForTimeout(1500)
      await snap(page, 'jena-1600-dark')
      await page.getByRole('button', { name: 'Open PleX' }).click()
      await page.waitForTimeout(1500)
      await snap(page, 'plex-1600-dark')
    } catch (e) { errors.push('apps: ' + String(e).slice(0, 200)) }
  }
  await ctx.close()
}

async function phone(theme) {
  const ctx = await browser.newContext({ viewport: { width: 402, height: 874 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, userAgent: IPHONE, colorScheme: theme })
  const page = await ctx.newPage()
  page.on('pageerror', (e) => errors.push(`phone ${theme} pageerror: ${String(e).slice(0, 300)}`))
  page.on('console', (m) => m.type() === 'error' && errors.push(`phone ${theme}: ${m.text().slice(0, 200)}`))
  page.on('response', (x) => x.status() >= 400 && errors.push(`phone ${theme} HTTP ${x.status()} ${x.url().slice(0, 200)}`))
  await page.goto(`${B}/?theme=${theme}`, { waitUntil: 'networkidle', timeout: 60000 })
  await page.waitForTimeout(2200)
  await snap(page, `phone-home-402-${theme}`)
  try {
    await page.getByRole('button', { name: 'Explore my work' }).click()
    await page.waitForTimeout(1200)
    await snap(page, `phone-projects-402-${theme}`)
    // swipe the pill down = minimize -> back to the app home
    const p = await center(page, '[data-app=projects] .ctl-pill')
    await drag(page, p, { x: p.x, y: p.y + 120 })
    await page.waitForTimeout(900)
    await snap(page, `phone-back-402-${theme}`)
    await page.getByRole('button', { name: 'Open About Saidie' }).click()
    await page.waitForTimeout(1200)
    await snap(page, `phone-about-402-${theme}`)
    if (theme === 'dark') {
      const a = await center(page, '[data-app=about] .ctl-arc')
      await drag(page, a, { x: a.x, y: a.y + 220 })
      await page.waitForTimeout(900)
      await page.getByRole('button', { name: 'Open Contact' }).click()
      await page.waitForTimeout(1200)
      await snap(page, 'phone-contact-402-dark')
    }
  } catch (e) { errors.push('phone: ' + String(e).slice(0, 200)) }
  await ctx.close()
}

async function video() {
  fs.mkdirSync('/tmp/vid', { recursive: true })
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 760 }, recordVideo: { dir: '/tmp/vid', size: { width: 1280, height: 760 } }, colorScheme: 'light' })
  await ctx.addInitScript(CURSOR)
  const page = await ctx.newPage()
  try {
    await page.goto(`${B}/?theme=light`, { waitUntil: 'networkidle', timeout: 60000 })
    await page.waitForTimeout(1800)
    // the first-run window tour: Next, Next, Got it
    for (const n of ['Next', 'Next', 'Got it']) {
      try { const b = await center(page, `.coach button:has-text("${n}")`); await page.mouse.move(b.x, b.y, { steps: 14 }); await page.waitForTimeout(700); await page.mouse.click(b.x, b.y); await page.waitForTimeout(900) } catch (e) { errors.push('video tour ' + n) }
    }
    await page.mouse.move(640, 380, { steps: 10 })
    // open Projects from the labelled dock
    const dock = await center(page, '.nos-dock button[aria-label="Open Projects"]')
    await page.mouse.move(dock.x, dock.y, { steps: 20 }); await page.waitForTimeout(300); await page.mouse.click(dock.x, dock.y)
    await page.waitForTimeout(1200)
    // hold ••• and move
    let d = await center(page, '[data-app=projects] .ctl-dots')
    await page.mouse.move(d.x, d.y, { steps: 15 }); await drag(page, d, { x: d.x + 180, y: d.y + 40 }, { hold: 450, steps: 30 })
    await page.waitForTimeout(700)
    // resize from the hidden corner
    let rz = await center(page, '[data-app=projects] .rz.br')
    await page.mouse.move(rz.x, rz.y, { steps: 15 }); await page.waitForTimeout(300)
    await drag(page, rz, { x: rz.x - 200, y: rz.y - 120 }, { steps: 30 })
    await page.waitForTimeout(700)
    // pill swipe up = maximize, swipe down = restore
    let p = await center(page, '[data-app=projects] .ctl-pill')
    await page.mouse.move(p.x, p.y, { steps: 15 }); await drag(page, p, { x: p.x, y: p.y - 80 }, { steps: 10 })
    await page.waitForTimeout(1100)
    p = await center(page, '[data-app=projects] .ctl-pill')
    await page.mouse.move(p.x, p.y, { steps: 15 }); await drag(page, p, { x: p.x, y: p.y + 70 }, { steps: 10 })
    await page.waitForTimeout(1100)
    // tap the pill = info popover
    p = await center(page, '[data-app=projects] .ctl-pill')
    await page.mouse.move(p.x, p.y, { steps: 10 }); await page.mouse.click(p.x, p.y)
    await page.waitForTimeout(1600)
    await page.mouse.click(40, 600); await page.waitForTimeout(500)
    // ••• tap = menu
    d = await center(page, '[data-app=projects] .ctl-dots')
    await page.mouse.move(d.x, d.y, { steps: 10 }); await page.mouse.click(d.x, d.y); await page.waitForTimeout(600)
    const mb = await center(page, '[data-app=projects] .nmenu button.top >> nth=2')
    await page.mouse.move(mb.x, mb.y, { steps: 10 }); await page.mouse.click(mb.x, mb.y); await page.waitForTimeout(1300)
    await page.keyboard.press('Escape'); await page.waitForTimeout(400)
    // pill swipe down = minimize to the dock
    p = await center(page, '[data-app=projects] .ctl-pill')
    await page.mouse.move(p.x, p.y, { steps: 10 }); await drag(page, p, { x: p.x, y: p.y + 90 }, { steps: 10 })
    await page.waitForTimeout(1200)
    // drag the About window's top-right arc down = close
    const a = await center(page, '[data-app=about] .ctl-arc')
    await page.mouse.move(a.x, a.y, { steps: 15 }); await drag(page, a, { x: a.x + 20, y: a.y + 220 }, { steps: 30 })
    await page.waitForTimeout(1200)
    // theme toggle to dark
    const t = await center(page, '.nos-menubar button[aria-label^="Theme"]')
    await page.mouse.move(t.x, t.y, { steps: 15 }); await page.mouse.click(t.x, t.y); await page.waitForTimeout(400); await page.mouse.click(t.x, t.y)
    await page.waitForTimeout(1500)
  } catch (e) { errors.push('video: ' + String(e).slice(0, 300)) }
  const v = page.video()
  await ctx.close()
  try {
    const src = await v.path()
    fs.copyFileSync(src, `${out}/gestures.webm`)
    try { execSync('command -v ffmpeg') } catch { try { execSync('sudo apt-get update -qq && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg', { timeout: 240000, stdio: 'ignore' }) } catch (e2) { errors.push('apt ffmpeg: ' + String(e2).slice(0, 120)) } }
    execSync(`ffmpeg -y -loglevel error -i "${src}" -vf "fps=30,scale=1280:-2" -c:v libx264 -pix_fmt yuv420p -crf 26 -movflags +faststart ${out}/gestures.mp4`)
    console.log('video ok', fs.statSync(`${out}/gestures.mp4`).size)
    fs.rmSync(`${out}/gestures.webm`, { force: true })
  } catch (e) { errors.push('ffmpeg: ' + String(e).slice(0, 200)) }
}

async function api() {
  const post = (body) => fetch(`${B}/api/contact`, { method: 'POST', headers: { 'Content-Type': 'application/json', Origin: B }, body: JSON.stringify(body) }).then(async (r) => ({ status: r.status, body: await r.text() }))
  report.checks.contact_honeypot = await post({ name: 'Bot', email: 'b@x.io', message: 'spam spam spam', website: 'http://spam', elapsed: 9000 })
  report.checks.contact_too_fast = await post({ name: 'Fast', email: 'f@x.io', message: 'too fast message', elapsed: 300 })
  report.checks.contact_invalid = await post({ name: '', email: 'nope', message: 'x', elapsed: 9000 })
  report.checks.contact_real_no_key = await post({ name: 'Proof Run', email: 'proof@example.com', topic: 'Other', message: 'Automated proof message from CI', elapsed: 9000 })
  const rl = []
  for (let i = 0; i < 4; i++) rl.push((await post({ name: 'Rate', email: 'r@example.com', message: 'rate limit check ' + i, elapsed: 9000 })).status)
  report.checks.contact_rate_limit_statuses = rl
  const pdf = await fetch(`${B}/Saidie_Newara_Resume.pdf`)
  report.checks.resume = { status: pdf.status, type: pdf.headers.get('content-type'), bytes: (await pdf.arrayBuffer()).byteLength }
  for (const path of ['/about', '/projects', '/plex', '/contact']) report.checks['page' + path] = (await fetch(B + path)).status
}

for (const t of ['light', 'dark']) await desktop(t)
for (const t of ['light', 'dark']) await phone(t)
try { await api() } catch (e) { errors.push('api: ' + String(e).slice(0, 200)) }
try { await video() } catch (e) { errors.push('video outer: ' + String(e).slice(0, 200)) }
await browser.close()
report.errors = errors
fs.writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1))
console.log('ERRORS', JSON.stringify(errors))
