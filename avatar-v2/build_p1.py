
# Jena avatar v2 build - Blender 4.2 headless on a GitHub runner. Part 1: setup, body, clothes.
import bpy, bmesh, sys, os, math, json, random, shutil
import numpy as np
from mathutils import Vector, Matrix, kdtree
from mathutils.bvhtree import BVHTree
A = sys.argv[sys.argv.index('--')+1:]
VRM, LOGO, OUT = A[0], A[1], A[2]
os.makedirs(OUT+'/tex', exist_ok=True)
REP = {'notes': [], 'stubbed': []}
def note(*a):
    s=' '.join(str(x) for x in a); print('[build]', s, flush=True); REP['notes'].append(s)
random.seed(7); np.random.seed(7)
bpy.ops.wm.read_factory_settings(use_empty=True)
shutil.copy(VRM, OUT+'/_base.glb'); bpy.ops.import_scene.gltf(filepath=OUT+'/_base.glb'); os.remove(OUT+'/_base.glb')
arm = [o for o in bpy.data.objects if o.type=='ARMATURE'][0]; arm.name='Armature'
MESH = {o.name:o for o in bpy.data.objects if o.type=='MESH'}
note('objects', list(MESH), 'bones', len(arm.data.bones))
body, face, hair = MESH['Body'], MESH['Face'], MESH['Hair']
def bpos(n, tail=False):
    b = arm.data.bones[n]; return arm.matrix_world @ (b.tail_local if tail else b.head_local)
def _landmarks():
    return {k: bpos(v) for k,v in dict(hips='J_Bip_C_Hips', spine='J_Bip_C_Spine', chest='J_Bip_C_Chest', uchest='J_Bip_C_UpperChest',
     neck='J_Bip_C_Neck', head='J_Bip_C_Head', sh='J_Bip_L_UpperArm', el='J_Bip_L_LowerArm', wr='J_Bip_L_Hand',
     leg='J_Bip_L_UpperLeg', knee='J_Bip_L_LowerLeg', ankle='J_Bip_L_Foot', toe='J_Bip_L_ToeBase', bust='J_Sec_L_Bust1', eye='J_Adj_L_FaceEye').items()}
L = _landmarks()
note('landmarks', {k:[round(c,3) for c in v] for k,v in L.items()})
assert L['sh'].x > 0, 'expected character left at +X'
FWD = -1.0  # character faces -Y in Blender
def matname(o, i):
    m = o.data.materials[i] if i < len(o.data.materials) else None
    return m.name if m else ''
def clean_slots(obj):
    """drop unused material slots. (Blender's materials.pop already remaps polygon indices; the old manual
    decrement double-shifted them and put the face skin on FaceMouth.) Rebuild by name instead."""
    me = obj.data
    if not len(me.materials): return
    mats = list(me.materials); idx = np.zeros(len(me.polygons), np.int32); me.polygons.foreach_get('material_index', idx)
    used = sorted(set(idx.tolist())); keep = [mats[i] for i in used if i < len(mats)]
    remap = {u: k for k, u in enumerate(used)}
    me.materials.clear()
    for m in keep: me.materials.append(m)
    me.polygons.foreach_set('material_index', np.array([remap[i] for i in idx], np.int32))
def split_faces(o, pred, newname):
    """move faces where pred(obj, face) into a new object (shape keys, weights, modifiers kept)"""
    n = o.copy(); n.data = o.data.copy(); n.name = newname; n.data.name = newname
    for c in o.users_collection: c.objects.link(n)
    for obj, keep in ((n, True), (o, False)):
        bm = bmesh.new(); bm.from_mesh(obj.data); bm.faces.ensure_lookup_table()
        dele = [f for f in bm.faces if bool(pred(obj, f, bm)) != keep]
        bmesh.ops.delete(bm, geom=dele, context='FACES'); bm.to_mesh(obj.data); bm.free(); clean_slots(obj)
    return n
def coords(o):
    a = np.zeros(len(o.data.vertices)*3, np.float32); o.data.vertices.foreach_get('co', a); return a.reshape(-1,3)
def set_coords(o, c):
    o.data.vertices.foreach_set('co', c.astype(np.float32).ravel()); o.data.update()
    sk = o.data.shape_keys
    if sk: sk.key_blocks[0].data.foreach_set('co', c.astype(np.float32).ravel())
def weights(o, names):
    idx = {o.vertex_groups[n].index for n in names if n in o.vertex_groups}
    w = np.zeros(len(o.data.vertices), np.float32)
    for v in o.data.vertices:
        for g in v.groups:
            if g.group in idx: w[v.index] += g.weight
    return w
def ss(e0, e1, x):
    t = np.clip((np.asarray(x, np.float64)-e0)/(e1-e0), 0, 1); return t*t*(3-2*t)
def make_img(name, arr):
    arr = np.asarray(arr, np.float32); h, w = arr.shape[:2]
    if arr.shape[2] == 3: arr = np.concatenate([arr, np.ones((h,w,1),np.float32)], 2)
    img = bpy.data.images.new(name, w, h, alpha=True); img.pixels.foreach_set(np.flipud(arr).ravel())
    path = f'{OUT}/tex/{name}.png'; img.filepath_raw = path; img.file_format = 'PNG'; img.save()
    bpy.data.images.remove(img); return bpy.data.images.load(path)
def make_mat(name, color=(1,1,1,1), img=None, alpha=False, rough=0.8, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; bsdf = nt.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = color; bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if img is not None:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img
        nt.links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
        if alpha: nt.links.new(t.outputs['Alpha'], bsdf.inputs['Alpha'])
    m.use_backface_culling = False
    return m
def ctx(o, sel=None):
    sel = sel or [o]
    return bpy.context.temp_override(object=o, active_object=o, selected_objects=sel, selected_editable_objects=sel)
def apply_mod(o, md):
    with ctx(o): bpy.ops.object.modifier_apply(modifier=md.name)
def join(target, others):
    with ctx(target, [target]+others): bpy.ops.object.join()
    return target
def copy_weights_nearest(dst, src):
    sc = coords(src); kd = kdtree.KDTree(len(sc))
    for i,c in enumerate(sc): kd.insert(c, i)
    kd.balance()
    sw = {v.index: [(src.vertex_groups[g.group].name, g.weight) for g in v.groups] for v in src.data.vertices}
    for g in src.vertex_groups:
        if g.name not in dst.vertex_groups: dst.vertex_groups.new(name=g.name)
    for v in dst.data.vertices:
        _, j, _ = kd.find(v.co)
        for n, wt in sw[j]: dst.vertex_groups[n].add([v.index], wt, 'REPLACE')
def add_armature(o):
    if not any(m.type=='ARMATURE' for m in o.modifiers):
        md = o.modifiers.new('Armature','ARMATURE'); md.object = arm
    o.parent = arm

# ---------- 0. whole-figure reshape to Jena (19, adult, her refs): head x0.86, legs x1.08, smaller less-anime eyes ----------
for _o in [o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('Icosphere')]: bpy.data.objects.remove(_o)
HS, LS = 0.86, 1.08
_piv = np.array([0.0, L['neck'].y, L['neck'].z]); _lz = float(L['leg'].z)
_eyec = {}
_fv = coords(face); _fmat = [''] * len(face.data.vertices)
for _p in face.data.polygons:
    for _v in _p.vertices: _fmat[_v] = matname(face, _p.material_index)
note('face materials at import', sorted(set(_fmat)))
_ir = np.array(['EyeIris' in m for m in _fmat])
for _s in (1,-1):
    _sel = _ir & (_fv[:,0]*_s > 0)
    if _sel.any(): _eyec[_s] = _fv[_sel].mean(0)
note('eye centres', {k:[round(float(x),3) for x in v] for k,v in _eyec.items()})
def _reshape(P, eyes=False):
    P = np.array(P, np.float64)
    if eyes:
        for _s, c in _eyec.items():
            d = np.hypot((P[:,0]-c[0])/1.0, (P[:,2]-c[2])/1.15)
            w = ss(0.034, 0.016, d) * (P[:,1] < c[1] + 0.03) * (P[:,0]*_s > -0.002)
            P[:,0] = c[0] + (P[:,0]-c[0])*(1-0.15*w); P[:,2] = c[2] + (P[:,2]-c[2])*(1-0.15*w)
    w = ss(L['neck'].z - 0.01, L['neck'].z + 0.04, P[:,2])[:,None]
    P = P + ((_piv + (P - _piv)*HS) - P) * w
    b = P[:,2] < _lz
    P[b,2] = P[b,2]*LS; P[~b,2] = P[~b,2] + (LS-1)*_lz
    return P
for _o in [o for o in bpy.data.objects if o.type=='MESH']:
    _mw = np.array(_o.matrix_world); _mi = np.linalg.inv(_mw); _eyes = (_o == face)
    def _xf(Pl):
        Pw = Pl @ _mw[:3,:3].T + _mw[:3,3]; Pw = _reshape(Pw, _eyes); return (Pw - _mw[:3,3]) @ _mi[:3,:3].T
    _n = len(_o.data.vertices)
    if _o.data.shape_keys:
        for _kb in _o.data.shape_keys.key_blocks:
            a = np.zeros(_n*3, np.float32); _kb.data.foreach_get('co', a); _kb.data.foreach_set('co', _xf(a.reshape(-1,3)).astype(np.float32).ravel())
    a = np.zeros(_n*3, np.float32); _o.data.vertices.foreach_get('co', a); _o.data.vertices.foreach_set('co', _xf(a.reshape(-1,3)).astype(np.float32).ravel()); _o.data.update()
bpy.context.view_layer.objects.active = arm
for _ob in bpy.context.view_layer.objects: _ob.select_set(_ob == arm)
bpy.ops.object.mode_set(mode='EDIT')
_amw = arm.matrix_world; _ami = _amw.inverted()
for _e in arm.data.edit_bones:
    hw = _amw @ _e.head; tw = _amw @ _e.tail; nh, nt = _reshape(np.array([hw[:], tw[:]]))
    _e.head = _ami @ Vector(nh); _e.tail = _ami @ Vector(nt)
bpy.ops.object.mode_set(mode='OBJECT')
L = _landmarks()
note('reshaped: head x%.2f legs x%.2f eyes pinched 15%%; new landmarks' % (HS, LS), {k:[round(c,3) for c in v] for k,v in L.items()})
REP['reshape'] = {'head_scale': HS, 'leg_scale': LS, 'eye_pinch': 0.15}
# ---------- 1. base Body -> skin only; HairBack (scalp) goes to hair; sample clothes/shoes dropped ----------
hairback = split_faces(body, lambda o,f,bm: 'HAIR' in matname(o, f.material_index), 'HairBack')
# VRoid culls the skin hidden under clothes: the sample has NO chest skin (z 1.1-1.25 empty).
# Fill it from the sample's Tops shell (torso band only), pulled 4 mm inward, re-materialed as skin.
_skin_i = [i for i,m in enumerate(body.data.materials) if m and 'SKIN' in m.name][0]
bm = bmesh.new(); bm.from_mesh(body.data); bm.faces.ensure_lookup_table(); bm.normal_update()
_fill = [f for f in bm.faces if 'Tops' in matname(body, f.material_index) and L['spine'].z + 0.06 < f.calc_center_median().z < L['sh'].z + 0.03 and abs(f.calc_center_median().x) < L['sh'].x + 0.01]
_fv = {v for f in _fill for v in f.verts}
for v in _fv: v.co -= v.normal * 0.004
for f in _fill: f.material_index = _skin_i
bm.to_mesh(body.data); bm.free(); note('chest fill from Tops faces', len(_fill), 'verts', len(_fv))
bm = bmesh.new(); bm.from_mesh(body.data); bm.faces.ensure_lookup_table()
bmesh.ops.delete(bm, geom=[f for f in bm.faces if 'SKIN' not in matname(body, f.material_index)], context='FACES'); bm.to_mesh(body.data); bm.free(); clean_slots(body)
note('body skin verts', len(body.data.vertices))
_sd = body.modifiers.new('Dense', 'SUBSURF'); _sd.subdivision_type = 'SIMPLE'; _sd.levels = 1; _sd.render_levels = 1
body.modifiers.move(len(body.modifiers)-1, 0); apply_mod(body, _sd)
note('body subdivided (simple) for smooth curves, verts', len(body.data.vertices))
def bust_w(Cc, s):
    """geometric bust weight (VRoid sample's bust bones weight only ~49 culled-area verts)"""
    c0 = np.array([L['bust'].x*s, L['bust'].y + FWD*0.035, L['bust'].z - 0.01])
    d = np.linalg.norm((Cc - c0) / np.array([1.0, 1.25, 1.1]), axis=1)
    return ss(0.085, 0.035, d) * ((Cc[:,1] - L['bust'].y)*FWD > -0.01) * (np.abs(Cc[:,0]) < L['sh'].x - 0.01)
# ---------- 2. Jena proportions (refs: fuller bust, wide hips, thick thighs) ----------
C = coords(body)
for names, s in ((['J_Sec_L_Bust1','J_Sec_L_Bust2'], 1), (['J_Sec_R_Bust1','J_Sec_R_Bust2'], -1)):
    wb = np.clip(np.maximum(weights(body, names), bust_w(C, s)), 0, 1)[:,None]
    c0 = np.array([L['bust'].x*s, L['bust'].y, L['bust'].z])
    C += (C - c0) * wb * np.array([0.48, 0.70, 0.42]) + wb*np.array([0, FWD*0.006, -0.004])
legz, kneez = L['leg'].z, L['knee'].z
arms = (np.abs(C[:,0]) > L['sh'].x - 0.02) & (C[:,2] > L['uchest'].z - 0.02)
f_ = np.exp(-((C[:,2] - (legz - 0.04))/0.13)**2) * (C[:,2] > kneez) * (~arms)
C[:,0] *= 1 + 0.18*f_
back = np.clip((C[:,1] - L['hips'].y)/0.08, 0, 1)
C[:,1] += 0.028*np.exp(-((C[:,2] - (legz - 0.02))/0.09)**2) * back * (~arms)
for s in (1,-1):
    sel = (C[:,0]*s > 0.015) & (C[:,2] < legz) & (C[:,2] > kneez) & (~arms)
    ax0, ay0 = L['leg'].x*s, L['leg'].y
    g = 1 + 0.15*ss(kneez, legz-0.05, C[:,2])
    C[sel,0] = ax0 + (C[sel,0]-ax0)*g[sel]; C[sel,1] = ay0 + (C[sel,1]-ay0)*g[sel]
C[:,0] *= 1 - 0.08*np.exp(-((C[:,2] - (L['spine'].z+0.06))/0.06)**2) * (~arms)
set_coords(body, C); BODY_C = C.copy()
REP['proportions'] = 'bust +48-70%, hips +18% width, seat +2.8cm, thighs +15%, waist -8%, head x0.86, legs x1.08'
# ---------- 3. clothes, each its own mesh, built from the body surface ----------
SH, WR = L['sh'], L['wr']
def is_arm(c): return abs(c[0]) > SH.x - 0.015 and c[2] > L['uchest'].z - 0.04
def from_body(name, face_pred, offset_fn, solid=0.0):
    o = body.copy(); o.data = body.data.copy(); o.name = name; o.data.name = name
    for c in body.users_collection: c.objects.link(o)
    bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if not face_pred(f.calc_center_median(), f)], context='FACES'); bm.to_mesh(o.data); bm.free()
    me = o.data; me.update()
    c = coords(o); n = np.zeros(len(me.vertices)*3, np.float32); me.vertices.foreach_get('normal', n); n = n.reshape(-1,3)
    off = np.array([offset_fn(v) for v in c], np.float32)[:,None]
    set_coords(o, c + n*off)
    if solid:
        md = o.modifiers.new('Solid','SOLIDIFY'); md.thickness = solid; md.offset = 1.0; md.use_rim = True
        o.modifiers.move(len(o.modifiers)-1, 0); apply_mod(o, md)
    me.materials.clear(); return o
neck_line = SH.z - 0.045; tee_hem = legz + 0.035
def tee_pred(c, f):
    if abs(c[0]) > WR.x + 0.035: return False
    if is_arm(c): return abs(c[0]) > SH.x + 0.045 or c[2] < SH.z - 0.032
    return tee_hem < c[2] < neck_line
tee = from_body('Tee', tee_pred, lambda v: 0.010 + 0.030*float(ss(tee_hem+0.12, tee_hem, v[2])), solid=0.002)
sh_hem = legz - 0.055
def hem_at(c):
    out = max(0.0, (abs(c[0]) - abs(L['leg'].x))/0.07) if c[2] < legz + 0.02 else 0.0
    return sh_hem + 0.045*min(out, 1.0)
shorts = from_body('Shorts', lambda c,f: (not is_arm(c)) and hem_at(c) < c[2] < legz + 0.135, lambda v: 0.0055, solid=0.0018)
th_top = legz - 0.42*(legz-kneez)
thigh = from_body('ThighHighs', lambda c,f: c[2] < th_top and abs(c[0]) > 0.004, lambda v: 0.0024)
wbs = np.maximum(bust_w(BODY_C, 1), bust_w(BODY_C, -1))
note('bust verts', int((wbs>0.3).sum()))
bz = BODY_C[wbs>0.3][:,2]; under = float(bz.min()) - 0.008; cup_top = float(bz.max()) + 0.004
def bra_pred(c, f):
    if is_arm(c): return False
    if under - 0.03 < c[2] < under + 0.004: return True
    w = float(np.mean([wbs[v.index] for v in f.verts]))
    return w > 0.12 and c[2] < cup_top and c[1]*FWD > 0
bra = from_body('Bra', bra_pred, lambda v: 0.0042, solid=0.0015)
note('clothes verts', {o.name: len(o.data.vertices) for o in (tee, shorts, thigh, bra)})
dg = bpy.context.evaluated_depsgraph_get(); BV = BVHTree.FromObject(body, dg)
def onbody(p, off):
    loc, nrm, i, d = BV.find_nearest(Vector(p)); return loc + nrm*off
def tube(name, pts, r, closed=False):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 2
    sp = cu.splines.new('POLY'); sp.points.add(len(pts)-1)
    for i,p in enumerate(pts): sp.points[i].co = (p[0],p[1],p[2],1)
    sp.use_cyclic_u = closed
    ob = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(ob)
    with ctx(ob): bpy.ops.object.convert(target='MESH')
    return bpy.data.objects[name]
straps = []
for s in (1,-1):
    a = np.array([s*(L['bust'].x+0.006), L['bust'].y - 0.02, cup_top - 0.004])
    top = np.array([s*0.075, L['neck'].y + 0.005, SH.z + 0.035]); b = np.array([s*0.075, L['uchest'].y + 0.12, under - 0.012])
    pts = [onbody((1-t)**2*a + 2*(1-t)*t*(top+np.array([0,-0.01,0.03])) + t*t*top, 0.0048) for t in np.linspace(0,1,14)]
    pts += [onbody((1-t)*top + t*b, 0.0048) for t in np.linspace(0,1,14)[1:]]
    straps.append(tube(f'Strap{s}', pts, 0.0038))
pend = onbody((0.0, L['uchest'].y - 0.12, SH.z - 0.025), 0.006)
chain = []
for k in range(40):
    th = 2*math.pi*k/40; front = max(0.0, -math.cos(th))**3
    p = Vector((0.058*math.sin(th)*(1-0.55*front), L['neck'].y - 0.050*math.cos(th), L['neck'].z - 0.012)).lerp(pend, front*0.92)
    chain.append(onbody(p, 0.0035) if front < 0.95 else p)
neck = tube('Necklace', chain, 0.0011, closed=True)
crs = []
for sc_, lo in (((0.0045,0.0028,0.026),(0,0,0)), ((0.0165,0.0028,0.0045),(0,0,0.0045))):
    bpy.ops.mesh.primitive_cube_add(size=1); cb = bpy.context.active_object; cb.scale = sc_
    cb.location = pend + Vector(lo) + Vector((0, FWD*0.002, -0.016)); crs.append(cb)
for o in [neck]+crs:
    with ctx(o): bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
join(neck, crs); neck.name = 'Necklace'
neck.data.materials.clear(); neck.data.materials.append(make_mat('Necklace_Silver', (0.82,0.83,0.86,1), rough=0.25, metal=1.0))
copy_weights_nearest(neck, body); add_armature(neck)
for st in straps: st.data.materials.clear(); copy_weights_nearest(st, body)
H = 512; n1 = np.random.rand(H,H).astype(np.float32)
knit = 0.62 + 0.05*(n1-0.5) + 0.03*np.sin(np.arange(H)[None,:]*math.pi/2.0)
tee.data.materials.append(make_mat('Tee_Knit', img=make_img('Tee_Heather', np.stack([knit*0.98, knit*0.98, knit*1.01], 2)), rough=0.9))
shorts.data.materials.append(make_mat('Shorts_Black', (0.02,0.02,0.022,1), rough=0.6))
shorts.data.materials.append(make_mat('Shorts_Trim_White', (0.92,0.92,0.92,1), rough=0.6))
sc = coords(shorts)
for p in shorts.data.polygons:
    vv = sc[list(p.vertices)]
    if all(v_[2] < hem_at(v_) + 0.010 for v_ in vv) and abs(vv[:,0]).min() > 0.02: p.material_index = 1
bra.data.materials.append(make_mat('Bra_Black', (0.015,0.015,0.017,1), rough=0.5))
for st in straps: st.data.materials.append(bra.data.materials[0])
join(bra, straps); bra.name = 'Bra'
