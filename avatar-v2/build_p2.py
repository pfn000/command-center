
# ---------- thigh-highs: cylindrical UVs, sheer leg, opaque band, NCOM // logo on the LEFT band ----------
tc = coords(thigh); band_lo = th_top - 0.065
def leg_axis(zv, s):
    if zv > kneez: a = L['knee'].lerp(L['leg'], (zv-kneez)/(legz-kneez))
    else: a = L['ankle'].lerp(L['knee'], max(0.0,(zv-L['ankle'].z))/(kneez-L['ankle'].z))
    return a.x*s, a.y
me = thigh.data
while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
uvl = me.uv_layers.new(name='UVMap')
for p in me.polygons:
    s = 1 if tc[list(p.vertices)].mean(0)[0] > 0 else -1
    us = []
    for li in p.loop_indices:
        v = tc[me.loops[li].vertex_index]; ax_, ay_ = leg_axis(v[2], s)
        us.append(0.5 + math.atan2(v[1]-ay_, (v[0]-ax_)*s)/(2*math.pi))   # u=0.5 is the OUTER side of that leg
    m_ = float(np.median(us))
    for k_, li in enumerate(p.loop_indices):
        u = us[k_]
        if u - m_ > 0.5: u -= 1
        if m_ - u > 0.5: u += 1
        zv = tc[me.loops[li].vertex_index][2]
        uvl.data[li].uv = (u, (zv - band_lo)/(th_top - band_lo) if zv >= band_lo - 0.004 else zv*12.0)
    cz = tc[list(p.vertices)].mean(0)[2]
    p.material_index = 0 if cz < band_lo else (2 if s > 0 else 1)
mid = (band_lo+th_top)/2
lb = tc[(tc[:,0]>0) & (np.abs(tc[:,2]-mid) < 0.008)]; ax_, ay_ = leg_axis(mid, 1)
r_ = float(np.hypot(lb[:,0]-ax_, lb[:,1]-ay_).mean()) if len(lb) else 0.075
C_band = 2*math.pi*r_; H_band = th_top - band_lo
REP['band'] = {'circumference_m': round(C_band,4), 'height_m': round(H_band,4)}
S = 256; yy, xx = np.mgrid[0:S,0:S]/S
d_ = np.abs(((xx*18 + yy*18) % 1) - 0.5) + np.abs(((xx*18 - yy*18) % 1) - 0.5)
alpha = 0.80 + 0.15*ss(0.86, 0.98, d_)
sheer_img = make_img('ThighHigh_Sheer', np.stack([np.full((S,S),0.045), np.full((S,S),0.035), np.full((S,S),0.03), alpha], 2))
TW, TH = 2048, 256
band = np.zeros((TH, TW, 4), np.float32); band[...,:3] = 0.02; band[...,3] = 1
band[int(TH*0.06):int(TH*0.10),:, :3] = 0.06; band[int(TH*0.90):int(TH*0.94),:, :3] = 0.06
plain_img = make_img('ThighHigh_Band', band)
logo = bpy.data.images.load(LOGO); lw, lh = logo.size
lp = np.array(logo.pixels[:], np.float32).reshape(lh, lw, 4)[::-1]
lum = lp[...,:3].mean(2); bg = float(np.median(lum))
mask = ss(bg - 0.012, bg - 0.035, lum)          # her logo card: the bars read slightly darker (shaded glass) than the card
ys, xs = np.where(mask > 0.5); mask = mask[ys.min():ys.max()+1, xs.min():xs.max()+1]; mh, mw = mask.shape
crop = lp[ys.min():ys.max()+1, xs.min():xs.max()+1, :3]
edge = (np.abs(np.diff(mask > 0.5, axis=0, prepend=0)) + np.abs(np.diff(mask > 0.5, axis=1, prepend=0))) > 0
ov = crop.copy(); ov[edge] = [1.0, 0.1, 0.1]
mk = np.repeat(mask[...,None], 3, 2)*0.96 + (1-np.repeat(mask[...,None], 3, 2))*0.02
make_img('proof_logo_overlay', np.concatenate([crop, ov, mk], 1))
REP['logo_source_px'] = {'w': int(mw), 'h': int(mh), 'aspect_w_over_h': round(mw/mh, 4), 'bg_lum': round(bg,3)}
logo_h_m = 0.62*H_band; logo_w_m = logo_h_m*mw/mh
px_w = int(round(logo_w_m / C_band * TW)); px_h = int(round(logo_h_m / H_band * TH))
REP['logo_on_band'] = {'w_m': round(logo_w_m,4), 'h_m': round(logo_h_m,4), 'tex_px': [px_w, px_h], 'aspect_in_3d': round(logo_w_m/logo_h_m,4)}
m2 = mask[(np.arange(px_h)*mh/px_h).astype(int)][:, (np.arange(px_w)*mw/px_w).astype(int)]
band_l = band.copy(); cy, cx = TH//2, TW//2
reg = band_l[cy-px_h//2:cy-px_h//2+px_h, cx-px_w//2:cx-px_w//2+px_w]
reg[..., :3] = reg[..., :3]*(1-m2[...,None]) + 0.96*m2[...,None]
logo_img = make_img('ThighHigh_Band_L_NCOM', band_l)
thigh.data.materials.append(make_mat('ThighHigh_Sheer', img=sheer_img, alpha=True, rough=0.7))
thigh.data.materials.append(make_mat('ThighHigh_Band', img=plain_img, rough=0.75))
thigh.data.materials.append(make_mat('ThighHigh_Band_L_NCOM', img=logo_img, rough=0.75))
for o in (tee, shorts, thigh, bra): add_armature(o)
# ---------- 4. hair: Jena's OWN procedural hair (VRoid strands deleted): short messy layered cut, side-swept bangs over her right eye,
#                black roots -> white ends (refs), small messy bun at the back. Strand cards weighted to new spring chains.
neckz, eyez, headz = L['neck'].z, L['eye'].z, L['head'].z
dg = bpy.context.evaluated_depsgraph_get()
FBV = BVHTree.FromObject(face, dg); SBV = BVHTree.FromObject(hairback, dg)
hb = coords(hairback); fv_ = coords(face)
crown = np.vstack([hb, fv_[fv_[:,2] > eyez - 0.01]])
Hc = (crown.min(0) + crown.max(0)) / 2; Hc[0] = 0.0; Hr = (crown.max(0) - crown.min(0)) / 2
chinz = float(fv_[:,2].min()) + 0.012
note('head centre', [round(float(x),3) for x in Hc], 'radii', [round(float(x),3) for x in Hr], 'chin', round(chinz,3))
def push_out(p, off):
    p = Vector(p)
    for bv in (FBV, SBV):
        loc, nrm, _i, dist = bv.find_nearest(p)
        if loc is None: continue
        if (p - loc).dot(nrm) < off: p = loc + nrm*off
    q = (np.array(p) - Hc) / (Hr*np.array([0.97, 0.97, 0.97]))
    r = float(np.linalg.norm(q))
    if r < 1.0 and p.z > eyez - 0.02: p = Vector(Hc + (np.array(p) - Hc)/max(r,1e-6))
    return p
def nrmz(v): v = np.asarray(v, float); return v/ (np.linalg.norm(v)+1e-9)
def grow(p0, d0, target_z, off0, off1, curl, nseg=10, grav=0.22):
    L_est = max(0.03, (p0[2] - target_z)*1.2 + 0.025); step = L_est/nseg
    pts = [Vector(p0)]; d = nrmz(d0); p = Vector(p0)
    for i in range(nseg):
        t = (i+1)/nseg
        rad = nrmz(np.array(p) - Hc); radh = nrmz([rad[0], rad[1], 0.0])
        d = nrmz(d*(1-grav) + np.array([0,0,-1.0])*grav + radh*0.05 + curl*t*t)
        p = push_out(p + Vector(d*step), off0 + (off1-off0)*t)
        pts.append(p)
        if p.z < target_z: break
    return pts
CARDS = []   # (pts, width, column, kind)
rng = np.random.default_rng(11)
def add_card(pts, w, kind):
    if len(pts) >= 3: CARDS.append((pts, w, int(rng.integers(0, 8)), kind))
# roots: area-weighted samples on the scalp cap
bm = bmesh.new(); bm.from_mesh(hairback.data); bmesh.ops.triangulate(bm, faces=bm.faces[:]); bm.faces.ensure_lookup_table()
mw_ = hairback.matrix_world
tris = [[mw_ @ v.co for v in f.verts] for f in bm.faces]; bm.free()
areas = np.array([((t[1]-t[0]).cross(t[2]-t[0])).length/2 for t in tris]); areas /= areas.sum()
def sample_roots(n):
    out = []
    for k in rng.choice(len(tris), n, p=areas):
        a, b = rng.random(2)
        if a + b > 1: a, b = 1-a, 1-b
        t = tris[k]; out.append(np.array(t[0] + (t[1]-t[0])*a + (t[2]-t[0])*b))
    return out
front_y = Hc[1] - 0.55*Hr[1]
for p0 in sample_roots(480):
    rad = nrmz(p0 - Hc); radh = nrmz([rad[0], rad[1], 0.0])
    if p0[2] < eyez - 0.005 and rad[1] < 0.2: continue          # no roots on the cheeks/temples below the eye line
    front = p0[1] < front_y and p0[2] > eyez + 0.02
    side = abs(rad[0]) > 0.55
    if front:
        # bangs: swept from her left to her right (-X), ending at brow/eye level, some across her right eye
        sweep = np.array([-0.75, -0.45, -0.55]) + rng.normal(0, 0.12, 3)
        tz = eyez + rng.uniform(-0.022, 0.018) - (0.015 if p0[0] < 0 else 0.0)
        pts = grow(p0, sweep, tz, 0.004, 0.010, np.array([0.0, -0.15, 0.05]), nseg=9, grav=0.18)
        add_card(pts, rng.uniform(0.016, 0.024), 'bang')
    else:
        back = rad[1] > 0.35
        if back: tz = neckz + rng.uniform(-0.005, 0.04)
        elif side: tz = chinz + rng.uniform(-0.03, 0.02)
        else: tz = chinz + rng.uniform(0.0, 0.05)
        d0 = radh*0.45 + np.array([0,0,0.15])*max(rad[2], 0) + np.array([0,0,-0.35]) + rng.normal(0, 0.06, 3)
        curl = radh*rng.uniform(0.0, 0.18) + rng.normal(0, 0.05, 3)          # messy flicks outward at the ends
        layer = rng.random()
        off0, off1 = (0.003, 0.006) if layer < 0.5 else (0.006, 0.012)
        pts = grow(p0, d0, tz, off0, off1, curl, nseg=10, grav=0.30)
        add_card(pts, rng.uniform(0.028, 0.040) if layer < 0.5 else rng.uniform(0.020, 0.030), 'main')
# side locks in front of the ears, a little longer (refs)
for s in (1,-1):
    for k in range(5):
        p0 = Hc + np.array([s*Hr[0]*rng.uniform(0.70, 0.85), -Hr[1]*rng.uniform(0.15, 0.40), Hr[2]*rng.uniform(0.25, 0.55)])
        p0 = np.array(push_out(p0, 0.004))
        pts = grow(p0, [s*0.25, -0.35, -1.0], chinz - rng.uniform(0.00, 0.03), 0.005, 0.012, np.array([s*0.05, -0.08, 0]), nseg=10, grav=0.3)
        add_card(pts, rng.uniform(0.012, 0.017), 'lock')
note('hair cards', len(CARDS), {k: sum(1 for c in CARDS if c[3]==k) for k in ('bang','main','lock')})
# --- bun at the back top (messy loops) ---
top_z = float(hb[:,2].max())
ring = hb[(hb[:,2] > top_z - 0.10) & (hb[:,2] < top_z - 0.06)]
back_y = float(ring[:,1].max()) if len(ring) else Hc[1] + Hr[1]
bun_c = Vector((0.0, back_y + 0.012, top_z - 0.055)); head_c = Vector(Hc.tolist())
dirv = (bun_c - head_c).normalized(); REP['bun_center'] = [round(x,3) for x in bun_c]
BUNC = []
for k in range(16):
    ax = nrmz(rng.normal(0, 1, 3)); u_ = nrmz(np.cross(ax, [0.3, 0.5, 0.8])); v_ = np.cross(ax, u_)
    r_ = rng.uniform(0.016, 0.030); a0 = rng.uniform(0, 2*math.pi); span = rng.uniform(4.0, 6.6)
    pts = [Vector(np.array(bun_c) + np.array(dirv)*0.012 + r_*(math.cos(a)*u_ + math.sin(a)*v_)) for a in np.linspace(a0, a0+span, 12)]
    BUNC.append((pts, rng.uniform(0.010, 0.016), int(rng.integers(0, 8)), 'bun'))
# gather strands into the bun from the nape/back crown
for k in range(14):
    ang = rng.uniform(-1.2, 1.2); p0 = Hc + np.array([Hr[0]*0.9*math.sin(ang), Hr[1]*0.9*math.cos(ang), Hr[2]*rng.uniform(-0.1, 0.35)])
    p0 = np.array(push_out(p0, 0.004)); tgt = np.array(bun_c)
    pts = [push_out(p0 + (tgt - p0)*t + nrmz(p0 - Hc)*0.01*math.sin(math.pi*t), 0.005) for t in np.linspace(0, 1, 8)]
    BUNC.append((pts, rng.uniform(0.012, 0.018), int(rng.integers(0, 8)), 'gather'))
# --- texture: 8 strand columns, black roots -> white ends at a different height per column, combed alpha tips ---
TW_, TH_ = 512, 1024
uu = (np.arange(TW_)[None,:] + 0.5)/TW_; vv = 1.0 - (np.arange(TH_)[:,None] + 0.5)/TH_   # make_img flips rows: array row 0 = top = v 1 (tip)
col_ = np.floor(uu*8).astype(int); lu = uu*8 - col_
starts = np.array([0.72, 0.80, 0.66, 1.10, 0.76, 1.10, 0.84, 0.70])
st_ = starts[col_]
wmix = ss(st_, st_ + 0.22, vv)
fine = 0.88 + 0.12*np.sin(lu*2*math.pi*9 + 3*np.sin(vv*13 + col_))
blk, wht = 0.028, 0.86
lum_ = (blk*(1-wmix) + wht*wmix) * fine
teeth = 0.80 + 0.18*np.abs(np.sin(lu*math.pi*5 + col_))
alpha_ = (vv < teeth).astype(np.float32) * (np.abs(lu - 0.5) < 0.47)
hair_img = make_img('Hair_Jena', np.stack([lum_, lum_*0.99, lum_*1.03, alpha_], 2).astype(np.float32))
def build_cards(name, cards):
    verts, faces, uvs, vt, owner = [], [], [], [], []
    for ci, (pts, w, colk, kind) in enumerate(cards):
        n = len(pts); base = len(verts)
        tw = rng.uniform(-0.25, 0.25)
        for j, p in enumerate(pts):
            t = j/(n-1)
            tg = nrmz(np.array(pts[min(j+1,n-1)]) - np.array(pts[max(j-1,0)]))
            rad = nrmz(np.array(p) - Hc)
            sd = nrmz(np.cross(tg, rad)); nn = np.cross(sd, tg)
            sd = nrmz(sd*math.cos(tw*t) + nn*math.sin(tw*t))
            ww = w*max(0.08, 1.0 - t**1.6)
            for side_ in (-0.5, 0.0, 0.5):
                ridge = (0.5 - abs(side_))*2*ww*0.35
                verts.append(np.array(p) + sd*ww*side_ + rad*(0.0015*(1-t) + ridge)); uvs.append(((colk + 0.5 + side_*0.94)/8.0, t)); vt.append(t); owner.append(ci)
        for j in range(n-1):
            a = base + 3*j; faces.append((a, a+1, a+4, a+3)); faces.append((a+1, a+2, a+5, a+4))
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    uvl = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices: uvl.data[li].uv = uvs[me.loops[li].vertex_index]
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob, np.array(vt), np.array(owner)
for o_ in [hair]: bpy.data.objects.remove(o_)
hair, h_t, h_own = build_cards('Hair', CARDS)
bun, b_t, b_own = build_cards('Bun', BUNC)
for o_ in (hair, bun): o_.data.materials.append(make_mat('Hair_Jena', img=hair_img, alpha=True, rough=0.45))
hairback.data.materials.clear(); hairback.data.materials.append(make_mat('HairBack_Jena', (0.022,0.021,0.024,1), rough=0.6))
path_ = f'{OUT}/tex/Hair_Jena.png'; hair_img.filepath_raw = path_; hair_img.file_format = 'PNG'; hair_img.save()
note('hair verts', len(hair.data.vertices), 'bun verts', len(bun.data.vertices))
# --- spring chains: 12 sectors around the head + 2 bang chains; old VRoid hair bones removed ---
def sector(pts, kind):
    p0 = np.array(pts[0]) - Hc
    if kind == 'bang': return 12 + (0 if p0[0] > 0 else 1)
    a = math.atan2(p0[0], p0[1]); return int(((a + math.pi) / (2*math.pi)) * 12) % 12
csec = np.array([sector(c[0], c[3]) for c in CARDS])
CH = {}
for s_ in sorted(set(csec.tolist())):
    mem = [CARDS[i][0] for i in np.where(csec == s_)[0]]
    path = np.array([np.mean([np.array(m[min(len(m)-1, int(round(f*(len(m)-1))))]) for m in mem], 0) for f in (0.12, 0.40, 0.70, 1.0)])
    CH[s_] = path
bpy.context.view_layer.objects.active = arm
for ob_ in bpy.context.view_layer.objects: ob_.select_set(ob_ == arm)
bpy.ops.object.mode_set(mode='EDIT'); eb_ = arm.data.edit_bones
_ami = arm.matrix_world.inverted()
for e_ in [e for e in eb_ if e.name.startswith('J_Sec_Hair')]: eb_.remove(e_)
CHN = {}
for k_, (s_, path) in enumerate(sorted(CH.items())):
    ch = k_ + 1; par = eb_['J_Bip_C_Head']; names = []
    for j in range(3):
        e = eb_.new(f'J_Sec_Hair{j+1}_{ch:02d}'); e.head = _ami @ Vector(path[j]); e.tail = _ami @ Vector(path[j+1]); e.parent = par; e.use_connect = False
        par = e; names.append(e.name)
    tail_dir = Vector(path[3] - path[2]).normalized()*0.02
    e = eb_.new(f'J_Sec_Hair3_{ch:02d}_end'); e.head = _ami @ Vector(path[3]); e.tail = _ami @ (Vector(path[3]) + tail_dir); e.parent = par
    CHN[s_] = names
bpy.ops.object.mode_set(mode='OBJECT')
def weight_cards(ob, tvals, owners, secs):
    hg = ob.vertex_groups.new(name='J_Bip_C_Head'); groups = {}
    for i in range(len(tvals)):
        t = float(tvals[i]); s_ = secs[owners[i]]
        wh = 1.0 - float(ss(0.06, 0.30, t))
        hg.add([i], wh, 'REPLACE')
        if s_ is None or wh >= 0.999: continue
        j = min(2, int(t*3)); nm = CHN[s_][j]
        if nm not in groups: groups[nm] = ob.vertex_groups.new(name=nm)
        groups[nm].add([i], 1.0 - wh, 'REPLACE')
weight_cards(hair, h_t, h_own, list(csec))
HAIR_ZMAP = (-10.0, 1.0)
note('hair chains', len(CHN))
REP['hair'] = {'kind': 'procedural cards (no VRoid strands)', 'cards': len(CARDS), 'bun_loops': len(BUNC), 'chains': len(CHN)}
bpy.ops.mesh.primitive_torus_add(major_radius=0.020, minor_radius=0.005, major_segments=32, minor_segments=10, generate_uvs=True)
tie = bpy.context.active_object; tie.name = 'HairTie'
tie.rotation_euler = Vector((0,0,1)).rotation_difference(dirv).to_euler(); tie.location = bun_c - dirv*0.006
with ctx(tie): bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
tie.data.materials.append(make_mat('HairTie_Black', (0.03,0.03,0.035,1), rough=0.35))
