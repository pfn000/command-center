
"""overlay.py - Tab's mocap overlay for Saidie / Jena (v4: real floor grid drawn by the caller, rigid 3D pelvis + gizmo, off-frame legs hidden, GLIDE feet; v3, matches her 8:22 AM Oct 15 sketch).
One function, draw(img, F) -> measurements. F is one frame record (see SCHEMA / overlay.schema.json).
Used for the reference-dance track videos; the same record shape can be filled from Jena's own bones
(self-view) or from Tab's training data, so all three draw the same way.
Colours (from her sketch, as seen when the dancer faces the camera): her RIGHT side BLUE (screen left), her LEFT side MAGENTA,
spine/head CYAN, chest ORANGE, hips GREEN, ground RED, her RIGHT foot YELLOW, her LEFT foot GREEN."""
import math, cv2, numpy as np
def C(h): h = h.lstrip('#'); return (int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16))
COL = {'R': C('#3d8bff'), 'L': C('#ff3df0'), 'spine': C('#22e5ff'), 'chest': C('#ff9a1f'), 'hips': C('#2fe36b'), 'ground': C('#ff2a2a'),
       'footR': C('#ffe02a'), 'footL': C('#2fe36b'), 'eye': C('#ff2a2a'), 'white': (255, 255, 255), 'front': C('#9ffcff'), 'back': C('#b06bff'),
       'planted': C('#7dff4f')}
FINGERS = [[0, 1, 2, 3, 4], [0, 5, 6, 7, 8], [0, 9, 10, 11, 12], [0, 13, 14, 15, 16], [0, 17, 18, 19, 20]]
SCHEMA = {
  "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Tab mocap overlay frame (v3)", "type": "object",
  "required": ["size", "body"],
  "properties": {
    "size": {"description": "[W, H] of the image in px", "type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2},
    "body": {"description": "33 joints in MediaPipe Pose order, [x_px, y_px, visibility 0..1]; null when not tracked", "type": ["array", "null"], "minItems": 33, "maxItems": 33},
    "world": {"description": "33 joints in metres, hip-centred, x = her left->right on screen when facing camera, y up, z toward camera", "type": ["array", "null"]},
    "proj": {"description": "4x2 affine camera: [x, y, z, 1] @ proj = [u_px, v_px]; lets 3D directions be drawn", "type": ["array", "null"]},
    "hands": {"description": "her own LEFT/RIGHT hand, 21 MediaPipe hand points each [x_px, y_px]", "type": "object",
              "properties": {"L": {"type": ["array", "null"]}, "R": {"type": ["array", "null"]}}},
    "jaw": {"description": "optional jaw-line points [x_px, y_px] from the face mesh (chin first)", "type": ["array", "null"]},
    "face": {"description": "optional face contour polylines [[x,y],...] drawn thin", "type": ["array", "null"]},
    "floor": {"description": "ground estimate: y_px of the floor line, x_px centre under the feet, scale px", "type": ["object", "null"],
              "properties": {"y": {"type": "number"}, "x": {"type": "number"}}},
    "contact": {"description": "foot planted flags", "type": "object", "properties": {"L": {"type": "boolean"}, "R": {"type": "boolean"}}},
    "hip_bounce_cm": {"description": "hip height minus its 2 s rolling median, cm (caller computes over time)", "type": ["number", "null"]},
    "px_per_m": {"description": "image scale at the body, px per metre", "type": ["number", "null"]},
    "markers": {"description": "her sphere markers: name -> {px:[x,y], side: front|back, camera_facing: bool}", "type": ["object", "null"]},
    "hud": {"description": "title, lines, beat (bool), beat_no, hit (text or null)", "type": ["object", "null"]}}}

def ip(p): return (int(round(float(p[0]))), int(round(float(p[1]))))
def nrm(v): n = np.linalg.norm(v); return v / n if n > 1e-9 else v * 0
def blend_poly(img, pts, col, a):
    pts = np.array(pts, np.int32); x, y, w, h = cv2.boundingRect(pts); H, W = img.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0: return
    roi = img[y0:y1, x0:x1]; m = np.zeros(roi.shape[:2], np.uint8); cv2.fillPoly(m, [pts - [x0, y0]], 255)
    roi[m > 0] = (roi[m > 0] * (1 - a) + np.array(col) * a).astype(np.uint8)
def text(img, s, org, sc, col, th=1, bg=True):
    (tw, tht), bl = cv2.getTextSize(s, cv2.FONT_HERSHEY_SIMPLEX, sc, th); x, y = ip(org)
    if bg: cv2.rectangle(img, (x - 2, y - tht - 3), (x + tw + 2, y + bl), (0, 0, 0), -1)
    cv2.putText(img, s, (x, y), cv2.FONT_HERSHEY_SIMPLEX, sc, col, th, cv2.LINE_AA)
def line(img, a, b, col, w): cv2.line(img, ip(a), ip(b), col, w, cv2.LINE_AA)
def jellipse(img, c, along, r, col, w):
    ang = math.degrees(math.atan2(along[1], along[0])) if np.linalg.norm(along) > 1e-6 else 0
    cv2.ellipse(img, ip(c), (max(3, int(r * 0.75)), max(3, int(r * 1.25))), ang, 0, 360, col, w, cv2.LINE_AA)
def cone(img, o, d2, L, col, w, half=20):
    n = np.linalg.norm(d2)
    if n < 0.18:  # pointing (mostly) straight at / away from the camera
        cv2.circle(img, ip(o), int(L * 0.22), col, w, cv2.LINE_AA); cv2.circle(img, ip(o), max(2, w + 1), col, -1, cv2.LINE_AA); return
    d = d2 / n; Lr = L * min(1.0, n)
    pts = [o]
    for s in (-1, 1):
        a = math.radians(half * s); r = np.array([d[0] * math.cos(a) - d[1] * math.sin(a), d[0] * math.sin(a) + d[1] * math.cos(a)]); pts.append(o + r * Lr)
    blend_poly(img, pts, col, 0.28); cv2.polylines(img, [np.array(pts, np.int32)], True, col, w, cv2.LINE_AA)
    cv2.arrowedLine(img, ip(o), ip(o + d * Lr * 1.08), col, w, cv2.LINE_AA, tipLength=0.18)
def arrow(img, o, d2, L, col, w):
    n = np.linalg.norm(d2)
    if n < 0.18: cv2.circle(img, ip(o), max(3, int(L * 0.18)), col, w, cv2.LINE_AA); return
    cv2.arrowedLine(img, ip(o), ip(o + d2 / n * L * min(1.0, n)), col, w, cv2.LINE_AA, tipLength=0.3)
def rbox(img, pts, col, w, label=None, sc=0.5, pad=0.0, fill=0.12):
    pts = np.array([p for p in pts if np.all(np.isfinite(p))], np.float32)
    if len(pts) < 2: return None
    (cx, cy), (bw, bh), ang = cv2.minAreaRect(pts); box = cv2.boxPoints(((cx, cy), (bw + 2 * pad, bh + 2 * pad), ang))
    blend_poly(img, box, col, fill); cv2.polylines(img, [box.astype(np.int32)], True, col, w, cv2.LINE_AA)
    if label: top = box[np.argmin(box[:, 1])]; text(img, label, (top[0] + 2, top[1] - 4), sc, col)
    return box

def draw(img, F, style=None):
    H, W = img.shape[:2]; st = style or {}; out = {}
    B = F.get('body')
    if B is None: return out
    B = np.array(B, float); P = B[:, :2]; V = B[:, 2] if B.shape[1] > 2 else np.ones(33)
    def seen(j): return V[j] >= 0.5 and -2 <= P[j, 0] <= W + 2 and -2 <= P[j, 1] <= H - 3
    # v4.1 (Oct 15 checker): hips/legs off-frame or low confidence -> no hip box, pelvis gizmo, floor quad or feet; upper_only clips never draw them
    upper_only = bool(F.get('upper_only'))
    hips_ok = (not upper_only) and seen(23) and seen(24)
    feet_ok = (not upper_only) and any(seen(j) for j in (27, 28, 29, 30, 31, 32))
    arm_min = float(F.get('arm_min_vis') or 0.0)
    A = np.array(F['proj'], float) if F.get('proj') is not None else None; Wd = np.array(F['world'], float) if F.get('world') is not None else None
    bh = max(40.0, np.linalg.norm(P[0] - (P[27] + P[28]) / 2) * 1.12)
    lw = max(2, int(round(min(W, H) / 400))); sc = max(0.42, min(W, H) / 1080 * 0.55)
    proj = (lambda p: np.r_[p, 1.0] @ A) if A is not None else None
    sL, sR, hL, hR = P[11], P[12], P[23], P[24]; smid, hmid = (sL + sR) / 2, (hL + hR) / 2; earm = (P[7] + P[8]) / 2
    down = nrm(hmid - smid); torso = np.linalg.norm(hmid - smid)
    # world frames
    fr = None
    if Wd is not None:
        wsL, wsR, whL, whR = Wd[11], Wd[12], Wd[23], Wd[24]; wpel, wch = (whL + whR) / 2, (wsL + wsR) / 2; up = nrm(wch - wpel)
        def frame3(u, side): y = nrm(u); x = nrm(side - y * np.dot(side, y)); return x, y, np.cross(x, y)
        px, py, pz = frame3(up, whL - whR); cx, cy, cz = frame3(up, wsL - wsR)
        hf = nrm(Wd[0] - (Wd[7] + Wd[8]) / 2); fr = dict(pel=wpel, ch=wch, pz=pz, py=py, cz=cz, hf=hf, up=up)
    ppm = F.get('px_per_m')
    def dir2(p3, v3):
        if fr is None or proj is None or not ppm: return None
        return (proj(p3 + v3 * 0.2) - proj(p3)) / (0.2 * ppm)   # unit length when the vector lies in the image plane
    # ---------- ground ----------
    flo = F.get('floor') if feet_ok else None; contact = F.get('contact') or {}
    feet_x = (P[29, 0] + P[30, 0] + P[31, 0] + P[32, 0]) / 4
    if flo and flo.get('y') is not None and flo.get('grid'):
        fy = float(flo['y'])            # the perspective floor grid itself is drawn by the caller (locked to the floor plane)
    elif flo and flo.get('y') is not None:
        fy = float(flo['y']); xc = float(flo.get('x', feet_x)); w = 0.42 * bh
        quad = [(xc - 0.62 * w, fy - 0.07 * bh), (xc + 0.62 * w, fy - 0.07 * bh), (xc + w, fy + 0.09 * bh), (xc - w, fy + 0.09 * bh)]
        blend_poly(img, quad, COL['ground'], 0.10); cv2.polylines(img, [np.array(quad, np.int32)], True, COL['ground'], lw, cv2.LINE_AA)
        for k in range(1, 4):  # perspective grid
            t = k / 4; line(img, (quad[0][0] * (1 - t) + quad[1][0] * t, quad[0][1]), (quad[3][0] * (1 - t) + quad[2][0] * t, quad[3][1]), COL['ground'], 1)
        line(img, ((quad[0][0] + quad[3][0]) / 2, (quad[0][1] + quad[3][1]) / 2), ((quad[1][0] + quad[2][0]) / 2, (quad[1][1] + quad[2][1]) / 2), COL['ground'], 1)
        cv2.rectangle(img, ip((quad[1][0] - 6, quad[1][1] - 6)), ip((quad[1][0] + 6, quad[1][1] + 6)), COL['ground'], -1)
        text(img, 'floor', (quad[3][0] + 4, quad[3][1] - 6), sc, COL['ground'])
        out['floor_quad'] = [list(map(float, q)) for q in quad]
    else: fy = None
    if hips_ok:
        # ---------- floating hip reference box (anchored to the ground) + white bounce line ----------
        hipw = np.linalg.norm(hL - hR); bxs = 0.07 * bh
        bx = min(hL[0], hR[0]) - max(0.22 * bh, hipw * 1.1); by = hmid[1]
        bx = float(np.clip(bx, bxs, W - bxs))
        blend_poly(img, [(bx - bxs / 2, by - bxs / 2), (bx + bxs / 2, by - bxs / 2), (bx + bxs / 2, by + bxs / 2), (bx - bxs / 2, by + bxs / 2)], COL['hips'], 0.25)
        cv2.rectangle(img, ip((bx - bxs / 2, by - bxs / 2)), ip((bx + bxs / 2, by + bxs / 2)), COL['hips'], lw, cv2.LINE_AA)
        for k in range(0, int(abs(min(hL[0], hR[0]) - (bx + bxs / 2))), 14):  # dashed link hips -> box
            x0 = bx + bxs / 2 + k; line(img, (x0, by), (min(x0 + 7, min(hL[0], hR[0])), by), COL['white'], 1)
        text(img, 'HIP REF', (bx - bxs / 2, by - bxs / 2 - 5), sc * 0.85, COL['hips'])
        gy = fy if fy is not None else H - 4
        line(img, (bx, by + bxs / 2), (bx, gy), COL['white'], lw)
        cv2.ellipse(img, ip((bx, gy)), (int(bxs * 0.9), max(3, int(bxs * 0.28))), 0, 0, 360, COL['white'], lw, cv2.LINE_AA)
        if fy is not None and out.get('floor_quad'): line(img, (bx + bxs / 2, by + bxs / 2), out['floor_quad'][2], COL['ground'], 1)
        hh_px = (gy - hmid[1]) if fy is not None else None; out['hip_height_px'] = None if hh_px is None else round(float(hh_px), 1)
        lab = []
        if hh_px is not None:
            lab.append(f'{hh_px:.0f}px'); 
            if ppm: out['hip_height_cm'] = round(float(hh_px / ppm * 100), 1); lab.append(f'~{hh_px / ppm * 100:.0f}cm')
        else: lab.append('floor off-frame')
        if F.get('hip_bounce_cm') is not None: lab.append(f'bounce {F["hip_bounce_cm"]:+.1f}cm')
        for k, s in enumerate(lab): text(img, s, (bx + 6, (by + gy) / 2 + k * 22 * sc / 0.55), sc * 0.8, COL['white'])
    # ---------- face / head ----------
    if F.get('face'):
        for pl in F['face']: cv2.polylines(img, [np.array(pl, np.int32)], False, (225, 225, 225), 1, cv2.LINE_AA)
    for e in (2, 5): cv2.circle(img, ip(P[e]), max(3, lw + 1), COL['eye'], -1, cv2.LINE_AA)
    mouth = (P[9] + P[10]) / 2; eyem = (P[2] + P[5]) / 2
    chin = np.array(F['jaw'][0]) if F.get('jaw') else mouth + (mouth - eyem) * 0.7
    jw = 0.045 * bh; cv2.rectangle(img, ip(chin - jw / 2), ip(chin + jw / 2), COL['eye'], max(1, lw - 1), cv2.LINE_AA); text(img, 'jaw', (chin[0] + jw * 0.7, chin[1] + jw * 0.4), sc * 0.75, COL['eye'])
    neck = smid + (earm - smid) * 0.3; cv2.circle(img, ip(neck), int(0.03 * bh), COL['spine'], lw, cv2.LINE_AA)
    hd = dir2(fr['ch'] + (Wd[7] + Wd[8]) / 2 - fr['ch'], fr['hf']) if fr is not None else None
    cone(img, P[0], hd if hd is not None else nrm(P[0] - earm) * 0.6, 0.16 * bh, COL['spine'], lw)
    # ---------- spine ----------
    sp = [earm, neck] + [smid + (hmid - smid) * t for t in (0.15, 0.35, 0.6, 0.82)] + [hmid]
    for a, b in zip(sp, sp[1:]): line(img, a, b, COL['spine'], lw)
    for p in sp[1:-1]: cv2.circle(img, ip(p), max(4, int(0.016 * bh)), COL['spine'], lw, cv2.LINE_AA)
    # ---------- chest box + cone ----------
    cb = [sL + (sL - sR) * 0.08, sR + (sR - sL) * 0.08, sR + (sR - sL) * 0.08 + down * torso * 0.34, sL + (sL - sR) * 0.08 + down * torso * 0.34]
    blend_poly(img, cb, COL['chest'], 0.14); cv2.polylines(img, [np.array(cb, np.int32)], True, COL['chest'], lw, cv2.LINE_AA)
    ctop = cb[0] if cb[0][1] < cb[1][1] else cb[1]; text(img, 'CHEST', (min(cb[0][0], cb[1][0]), min(cb[0][1], cb[1][1]) - 5), sc * 0.85, COL['chest'])
    cc = smid + down * torso * 0.17
    cd = dir2(fr['ch'], fr['cz']) if fr is not None else None
    cone(img, cc, cd if cd is not None else np.zeros(2), 0.17 * bh, COL['chest'], lw)
    # ---------- hips triangle + cone ----------
    pv = F.get('pelvis') if hips_ok else None
    if pv:   # v4: rigid 3D pelvis (L hip/glute, R hip/glute, pelvis point) + small 3-axis gizmo; clinical, thin lines only
        tri = [np.array(q, float) for q in pv['tri_px']]; ctr = np.array(pv['center_px'], float)
        cv2.polylines(img, [np.array(tri, np.int32)], True, COL['hips'], lw, cv2.LINE_AA); blend_poly(img, tri, COL['hips'], 0.12)
        for p in tri: cv2.circle(img, ip(p), max(3, int(0.012 * bh)), COL['hips'], -1, cv2.LINE_AA)
        for k, c in (('L', COL['L']), ('up', COL['spine']), ('fwd', COL['white'])):
            e = np.array(pv['axes_px'][k], float); cv2.arrowedLine(img, ip(ctr), ip(e), (0, 0, 0), lw + 2, cv2.LINE_AA, tipLength=0.25)
            cv2.arrowedLine(img, ip(ctr), ip(e), c, lw, cv2.LINE_AA, tipLength=0.25); text(img, k, (e[0] + 3, e[1] - 3), sc * 0.6, c, bg=False)
        text(img, 'PELVIS', (max(hL[0], hR[0]) + 0.03 * bh, hmid[1] - 0.03 * bh), sc * 0.8, COL['hips'])
        out['pelvis_rpy_deg'] = pv.get('rpy')
    crotch = proj(fr['pel'] - fr['py'] * 0.13) if (fr is not None and proj is not None) else hmid + down * torso * 0.2
    tri = [hL, hR, crotch]
    if pv: tri = None
    if tri is not None and hips_ok:
      blend_poly(img, tri, COL['hips'], 0.22); blend_poly(img, tri, COL['hips'], 0.22); cv2.polylines(img, [np.array(tri, np.int32)], True, COL['hips'], lw, cv2.LINE_AA)
      for p in (hL, hR, crotch): cv2.circle(img, ip(p), max(4, int(0.018 * bh)), COL['hips'], lw, cv2.LINE_AA)
      text(img, 'HIPS', (max(hL[0], hR[0]) + 0.03 * bh, hmid[1]), sc * 0.85, COL['hips'])
      hdir = dir2(fr['pel'], fr['pz']) if fr is not None else None
      cone(img, (hL + hR + crotch) / 3, hdir if hdir is not None else np.zeros(2), 0.17 * bh, COL['hips'], lw)
    # ---------- limbs (her RIGHT = blue, her LEFT = magenta) ----------
    jr = 0.022 * bh
    for side, (s, e, w, h, k, a) in (('R', (12, 14, 16, 24, 26, 28)), ('L', (11, 13, 15, 23, 25, 27))):
        c = COL[side]
        for x, y in ((s, e), (e, w), (h, k), (k, a)):
            if x in (h, k) and not (seen(x) and seen(y)): continue          # v4: never draw a guessed leg that is off-frame / unseen
            if x in (s, e) and arm_min and (V[x] < arm_min or V[y] < arm_min): continue   # v4.1: hide low-confidence arm bones
            line(img, P[x], P[y], (0, 0, 0), lw + 2); line(img, P[x], P[y], c, lw)
        cv2.circle(img, ip(P[s]), int(jr), c, lw, cv2.LINE_AA)
        if not (arm_min and (V[e] < arm_min or V[w] < arm_min)): jellipse(img, P[e], P[w] - P[e], jr, c, lw)
        if seen(k) and seen(a): jellipse(img, P[k], P[a] - P[k], jr * 1.1, c, lw); jellipse(img, P[a], P[k] - P[a], jr * 0.9, c, lw)
        cv2.circle(img, ip(P[w]), int(jr * 0.7), c, lw, cv2.LINE_AA)
        # thin labelled part boxes (self-view look)
        if not (arm_min and (V[e] < arm_min or V[w] < arm_min)): rbox(img, [P[s], P[e], P[w]], c, 1, f'{side} arm', sc * 0.7, pad=jr, fill=0.04)
        if seen(k) and seen(a): rbox(img, [P[h], P[k], P[a]], c, 1, f'{side} leg', sc * 0.7, pad=jr, fill=0.04)
        elif seen(k) and hips_ok: rbox(img, [P[h], P[k]], c, 1, f'{side} thigh', sc * 0.7, pad=jr, fill=0.04)
        # facing arrows on upper/lower arm, thigh, shin (3D body-forward made orthogonal to the bone)
        if fr is not None:
            for (x, y, fwd) in ((s, e, fr['cz']), (e, w, fr['cz']), (h, k, fr['pz']), (k, a, fr['pz'])):
                if x in (h, k) and not (seen(x) and seen(y)): continue
                if x in (s, e) and arm_min and (V[x] < arm_min or V[y] < arm_min): continue
                bone = nrm(Wd[y] - Wd[x]); f3 = nrm(fwd - bone * np.dot(fwd, bone)); d = dir2((Wd[x] + Wd[y]) / 2, f3)
                if d is not None: arrow(img, (P[x] + P[y]) / 2, d, 0.07 * bh, c, max(1, lw - 1))
    # ---------- hands: palm box, fingers, wrist box, pointing arrow ----------
    hands = F.get('hands') or {}
    for side, wi in (('R', 16), ('L', 15)):
        c = COL[side]; Hh = hands.get(side)
        cv2.rectangle(img, ip(P[wi] - jr * 0.55), ip(P[wi] + jr * 0.55), c, 1, cv2.LINE_AA)
        if Hh is None: continue
        Hh = np.array(Hh, float); lc = tuple(int(min(255, v * 0.55 + 115)) for v in c)
        for ch in FINGERS:
            for a, b in zip(ch, ch[1:]): line(img, Hh[a], Hh[b], lc, max(1, lw - 1))
        for t in (4, 8, 12, 16, 20): cv2.circle(img, ip(Hh[t]), max(2, lw), (255, 255, 255), -1, cv2.LINE_AA)
        for q in Hh: cv2.circle(img, ip(q), max(1, lw - 1), c, -1, cv2.LINE_AA)
        rbox(img, Hh[[0, 1, 5, 9, 13, 17]], c, lw, 'palm', sc * 0.65, pad=2, fill=0.18)
        arrow(img, Hh[9], nrm(Hh[9] - Hh[0]) * 1.0, 0.06 * bh, c, max(1, lw - 1))
    # ---------- feet: 3D shoe boxes + facing arrows + planted ----------
    for side, (an, he, to), key in (('R', (28, 30, 32), 'footR'), ('L', (27, 29, 31), 'footL')):
        c = COL[key]; h, t, a = P[he], P[to], P[an]; f = t - h; fl = np.linalg.norm(f)
        if fl < 2 or not (seen(he) and seen(to) and seen(an)): continue
        n = np.array([-f[1], f[0]]) / fl * fl * 0.22; upv = (a - h) * 0.85
        b0 = [h - n, h + n, t + n, t - n]; t0 = [b0[0] + upv, b0[1] + upv, b0[2] + upv * 0.35, b0[3] + upv * 0.35]
        planted = bool(contact.get(side)); gl = bool(contact.get(side + '_glide')); ww = lw + (2 if planted else 0)
        if planted: blend_poly(img, b0, COL['planted'], 0.35)
        for q in (b0, t0): cv2.polylines(img, [np.array(q, np.int32)], True, c, ww, cv2.LINE_AA)
        for u, v in zip(b0, t0): line(img, u, v, c, ww)
        text(img, f'{side} foot' + (' PLANTED' if planted else (' GLIDE' if gl else '')), (max(q[0] for q in b0) + 4, max(q[1] for q in b0)), sc * 0.7, COL['planted'] if planted else c)
        arrow(img, (h + t) / 2, nrm(f), 0.06 * bh, c, max(1, lw - 1))
    # ---------- sphere markers (front / back inferred) ----------
    mk = F.get('markers') or {}
    rr = max(4, int(0.012 * bh))
    for name, m in mk.items():
        if not hips_ok and any(k_ in name.lower() for k_ in ('hip', 'glute', 'thigh', 'knee', 'foot', 'feet', 'ankle', 'shin', 'leg')): continue   # v4.1
        c = COL['front'] if m['side'] == 'front' else COL['back']; p = m['px']
        if m.get('camera_facing', True):
            cv2.circle(img, ip(p), rr + 1, (0, 0, 0), -1, cv2.LINE_AA); cv2.circle(img, ip(p), rr, c, -1, cv2.LINE_AA)
            cv2.circle(img, ip((p[0] - rr / 3, p[1] - rr / 3)), max(1, rr // 3), (255, 255, 255), -1, cv2.LINE_AA)
        else:
            cv2.circle(img, ip(p), rr, c, max(1, lw - 1), cv2.LINE_AA)
    # ---------- HUD ----------
    hud = F.get('hud') or {}
    y = 30 * sc / 0.55
    if hud.get('title'): text(img, hud['title'], (10, y), sc * 0.9, COL['white']); y += 26 * sc / 0.55
    for s in hud.get('lines', []): text(img, s, (10, y), sc * 0.62, (230, 230, 230)); y += 20 * sc / 0.55
    if hud.get('beat'):
        cv2.rectangle(img, (0, 0), (W - 1, H - 1), COL['white'], lw * 3); text(img, f"BEAT {hud.get('beat_no', '')}", (W - 170 * sc / 0.55, 60 * sc / 0.55), sc * 1.2, COL['white'])
    if hud.get('hit'): text(img, hud['hit'], (W - 300 * sc / 0.55, 100 * sc / 0.55), sc * 0.85, COL['planted'] if 'on beat' in hud['hit'] else (80, 180, 255))
    out['hip_ref_box_px'] = [round(bx, 1), round(by, 1)] if hips_ok else None
    return out

def hand_insets(img, hands, sc=None):
    """Two finger close-up panels at the top corners: screen-left = her RIGHT hand (blue), screen-right = her LEFT hand (magenta)."""
    H, W = img.shape[:2]; sc = sc or max(0.42, min(W, H) / 1080 * 0.55); lw = max(2, int(round(min(W, H) / 400)))
    pw = int(W * 0.2); ph = int(pw * 0.95); y0 = int(H * 0.11)
    for side, x0, nm in (('R', 8, 'her RIGHT hand'), ('L', W - pw - 8, 'her LEFT hand')):
        c = COL[side]; roi = img[y0:y0 + ph, x0:x0 + pw]; roi[:] = (roi * 0.25 + np.array((28, 20, 16)) * 0.75).astype(np.uint8)
        cv2.rectangle(img, (x0, y0), (x0 + pw, y0 + ph), c, lw, cv2.LINE_AA); text(img, nm, (x0 + 6, y0 + 22 * sc / 0.55), sc * 0.75, c, bg=False)
        Hh = (hands or {}).get(side)
        if Hh is None: text(img, 'not visible', (x0 + 8, y0 + ph // 2), sc * 0.7, (170, 170, 170), bg=False); continue
        Hh = np.array(Hh, float); mn, mx = Hh.min(0), Hh.max(0); s_ = 0.7 * min(pw, ph) / max(1, max(mx - mn)); Q = (Hh - (mn + mx) / 2) * s_ + [x0 + pw / 2, y0 + ph / 2 + 10]
        fc = [C('#ff6b6b'), C('#ffd93d'), C('#6bcb77'), C('#4d96ff'), C('#c77dff')]
        for fi, ch in enumerate(FINGERS):
            for a, b in zip(ch, ch[1:]): line(img, Q[a], Q[b], fc[fi], lw + 1)
        for q in Q: cv2.circle(img, ip(q), lw + 1, (255, 255, 255), -1, cv2.LINE_AA)
        rbox(img, Q[[0, 1, 5, 9, 13, 17]], c, 1, None, pad=3, fill=0.1)
