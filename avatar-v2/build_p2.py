
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
alpha = 0.55 + 0.25*ss(0.86, 0.98, d_)
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
# ---------- 4. hair: drop long back strands (the bun replaces them), shorten locks to a bob, black -> white ends ----------
hc = coords(hair)
bm = bmesh.new(); bm.from_mesh(hair.data); bm.verts.ensure_lookup_table()
isl = np.full(len(bm.verts), -1); NI = 0
for v in bm.verts:
    if isl[v.index] >= 0: continue
    stack = [v]; isl[v.index] = NI
    while stack:
        x = stack.pop()
        for e in x.link_edges:
            o_ = e.other_vert(x)
            if isl[o_.index] < 0: isl[o_.index] = NI; stack.append(o_)
    NI += 1
bm.free()
neckz, eyez, headz = L['neck'].z, L['eye'].z, L['head'].z
chin = headz + 0.005
drop, comp = set(), set()
for i in range(NI):
    sel = hc[isl==i]
    if sel[:,2].min() < neckz - 0.02 and sel[:,1].mean() > L['head'].y + 0.015: drop.add(i)
    elif sel[:,2].min() < chin: comp.add(i)
note('hair islands', NI, 'dropped(back long)', len(drop), 'shortened', len(comp))
REP['hair'] = {'islands': NI, 'dropped_back': len(drop), 'shortened': len(comp)}
def zmap(zv): return np.where(zv < chin, chin - (chin - zv)*0.30, zv)
cm = np.isin(isl, list(comp)); hc[cm,2] = zmap(hc[cm,2]); set_coords(hair, hc)
dv = np.isin(isl, list(drop))
bm = bmesh.new(); bm.from_mesh(hair.data); bm.verts.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[bm.verts[i] for i in np.where(dv)[0]], context='VERTS'); bm.to_mesh(hair.data); bm.free()
HAIR_ZMAP = (chin, 0.30)
hc2 = coords(hair); isl2 = isl[~dv]
streak = [i for i in range(NI) if random.random() < 0.18]
wf = ss(eyez - 0.005, eyez - 0.075, hc2[:,2])
stm = np.isin(isl2, streak); wf[stm] = ss(eyez + 0.03, eyez - 0.03, hc2[stm,2])
def bake_recolor(o, wfac, matname_out):
    me = o.data
    ca = me.color_attributes.new('jena_w', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', np.repeat(np.asarray(wfac, np.float32)[:,None], 4, 1).ravel())
    srcimg = None
    for n in me.materials[0].node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image: srcimg = n.image; break
    W_, H_ = srcimg.size
    tgt = bpy.data.images.new(o.name+'_jena', W_, H_, alpha=True)
    m = bpy.data.materials.new(o.name+'_bake'); m.use_nodes = True; nt = m.node_tree
    for n in list(nt.nodes): nt.nodes.remove(n)
    outn = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission')
    tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = srcimg
    va = nt.nodes.new('ShaderNodeVertexColor'); va.layer_name = 'jena_w'
    bw = nt.nodes.new('ShaderNodeRGBToBW')
    pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.6
    dk = nt.nodes.new('ShaderNodeMath'); dk.operation = 'MULTIPLY'; dk.inputs[1].default_value = 0.16
    lt = nt.nodes.new('ShaderNodeMath'); lt.operation = 'MULTIPLY_ADD'; lt.inputs[1].default_value = 0.35; lt.inputs[2].default_value = 0.62
    sep = nt.nodes.new('ShaderNodeSeparateColor'); mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'ADD'
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'FLOAT'
    nt.links.new(tx.outputs['Color'], bw.inputs['Color']); nt.links.new(bw.outputs[0], pw.inputs[0])
    nt.links.new(pw.outputs[0], dk.inputs[0]); nt.links.new(pw.outputs[0], lt.inputs[0])
    nt.links.new(va.outputs['Color'], sep.inputs['Color'])
    nt.links.new(sep.outputs[0], mix.inputs['Factor']); nt.links.new(dk.outputs[0], mix.inputs['A']); nt.links.new(lt.outputs[0], mix.inputs['B'])
    comb = nt.nodes.new('ShaderNodeCombineColor')
    for ch in ('Red','Green','Blue'): nt.links.new(mix.outputs['Result'], comb.inputs[ch])
    nt.links.new(comb.outputs[0], em.inputs['Color']); nt.links.new(em.outputs[0], outn.inputs[0])
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = tgt; nt.nodes.active = tn
    me.materials.clear(); me.materials.append(m)
    sc_ = bpy.context.scene; sc_.render.engine = 'CYCLES'; sc_.cycles.device = 'CPU'; sc_.cycles.samples = 1
    for ob in bpy.context.view_layer.objects: ob.select_set(False)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.bake(type='EMIT', margin=6, use_clear=True)
    px = np.array(tgt.pixels[:], np.float32).reshape(-1,4)
    sp = np.array(srcimg.pixels[:], np.float32).reshape(-1,4)
    if len(sp) == len(px): px[:,3] = sp[:,3]
    tgt.pixels.foreach_set(px.ravel())
    path = f'{OUT}/tex/{o.name}_Jena.png'; tgt.filepath_raw = path; tgt.file_format = 'PNG'; tgt.save()
    me.materials.clear(); me.materials.append(make_mat(matname_out, img=bpy.data.images.load(path), alpha=True, rough=0.5))
    me.color_attributes.remove(me.color_attributes['jena_w'])
try:
    bake_recolor(hair, wf, 'Hair_Jena')
    bake_recolor(hairback, np.zeros(len(hairback.data.vertices)), 'HairBack_Jena')
    note('hair baked: black roots -> white ends')
except Exception as e:
    import traceback; traceback.print_exc()
    note('HAIR BAKE FAILED', repr(e)); REP['stubbed'].append('hair recolor bake failed: '+repr(e))
hb = coords(hairback); hz = coords(hair)
top_z = float(max(hb[:,2].max(), hz[:,2].max()))
ring = hb[(hb[:,2] > top_z - 0.10) & (hb[:,2] < top_z - 0.06)]
back_y = float(ring[:,1].max()) if len(ring) else L['head'].y + 0.09
bun_c = Vector((0.0, back_y - 0.005, top_z - 0.065)); head_c = Vector((0.0, L['head'].y + 0.01, eyez + 0.02))
dirv = (bun_c - head_c).normalized(); REP['bun_center'] = [round(x,3) for x in bun_c]
parts = []
for k_ in range(7):
    bpy.ops.mesh.primitive_torus_add(major_radius=0.026 + 0.008*random.random(), minor_radius=0.014 + 0.005*random.random(),
                                     major_segments=28, minor_segments=10, generate_uvs=True)
    t = bpy.context.active_object
    t.rotation_euler = (random.uniform(0, math.pi), random.uniform(0, math.pi), random.uniform(0, math.pi))
    t.location = bun_c + dirv*0.012 + Vector((random.uniform(-.012,.012), random.uniform(-.008,.008), random.uniform(-.01,.01)))
    parts.append(t)
for t in parts:
    with ctx(t): bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bun = join(parts[0], parts[1:]); bun.name = 'Bun'
S2 = 512; uq = np.linspace(0,1,S2)[None,:]; vq = np.linspace(0,1,S2)[:,None]
strand = 0.5 + 0.5*np.sin((vq*90 + 3*np.sin(uq*20))*math.pi)
wst = (np.sin(vq*7*math.pi + 1.3) > 0.82).astype(np.float32)
col = (0.05 + 0.06*strand)*(1-wst) + (0.62+0.3*strand)*wst
bun.data.materials.append(make_mat('Hair_Bun', img=make_img('Hair_Bun', np.stack([col,col,col*1.02], 2)), rough=0.5))
bpy.ops.mesh.primitive_torus_add(major_radius=0.024, minor_radius=0.0055, major_segments=32, minor_segments=10, generate_uvs=True)
tie = bpy.context.active_object; tie.name = 'HairTie'
tie.rotation_euler = Vector((0,0,1)).rotation_difference(dirv).to_euler(); tie.location = bun_c - dirv*0.012
with ctx(tie): bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
tie.data.materials.append(make_mat('HairTie_Black', (0.03,0.03,0.035,1), rough=0.35))
