
// Shared status logic: reads Jena's public health, then the box through its tunnel. Returns only safe fields.
async function readStatus() {
  const t0 = Date.now();
  const out = { checkedAt: new Date().toISOString(), brain: { online: false, detail: 'unknown' },
    box: { reachable: false, detail: 'unknown' }, gateway: { ok: false, detail: 'unknown' }, site: {} };
  const get = async (url, ms) => {
    const c = new AbortController(); const tm = setTimeout(() => c.abort(), ms);
    try { const r = await fetch(url, { signal: c.signal, headers: { accept: 'application/json' }, cache: 'no-store' });
      let j = null; try { j = await r.json(); } catch (e) {}
      return { status: r.status, json: j };
    } catch (e) { return { status: 0, json: null, err: e.name === 'AbortError' ? 'timed out' : 'no answer' }; }
    finally { clearTimeout(tm); }
  };
  const h = await get('https://jena-magic-screen.vercel.app/api/health', 6000);
  if (!h.json) { out.brain.detail = 'health page ' + (h.err || ('answered ' + h.status)); return out; }
  const b = h.json.brain || {};
  out.brain = { name: b.name || 'JenaXI', online: !!b.online, detail: friendly(b.detail),
    lastSeen: b.checkedAt ? new Date(b.checkedAt).toISOString() : null };
  if (h.json.build) out.site = { commit: String(h.json.build.commit || '').slice(0, 7), env: h.json.build.env || '' };
  const boxUrl = b.box && b.box.url;
  if (b.box && b.box.announcedAt) out.box.announcedAt = new Date(b.box.announcedAt).toISOString();
  if (!boxUrl || !/^https:\/\/[a-z0-9-]+\.trycloudflare\.com$/.test(boxUrl)) { out.box.detail = 'no tunnel announced'; out.gateway.detail = 'box not reachable'; return out; }
  const [bh, gh] = await Promise.all([get(boxUrl + '/box/health', 5000), get(boxUrl + '/health', 5000)]);
  out.box = { ...out.box, reachable: !!(bh.json && bh.json.ok), detail: bh.json && bh.json.ok ? 'tunnel up' : friendly(bh.err || ('answered ' + bh.status)) };
  out.gateway = { ok: !!(gh.json && (gh.json.status === 'ok' || gh.json.ok === true)), detail: gh.json && (gh.json.status === 'ok' || gh.json.ok === true) ? 'answering' : friendly(gh.err || ('answered ' + gh.status)) };
  out.ms = Date.now() - t0;
  return out;
}
function friendly(d) {
  d = String(d || '');
  if (/530|1033|502|504/.test(d)) return 'tunnel down (' + d.replace(/[^0-9a-z ]/gi, '').slice(0, 20) + ')';
  return d.slice(0, 60) || 'ok';
}

module.exports = async (req, res) => {
  const s = await readStatus();
  res.setHeader('content-type', 'application/json'); res.setHeader('cache-control', 'no-store');
  res.status(200).send(JSON.stringify(s));
};
