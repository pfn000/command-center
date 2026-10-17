
# ---------- 5. face: ARKit 52 + Oculus visemes + blink_Eye_L/R, iris colour, then Eye_L/Eye_R/Teeth/Tongue meshes ----------
fm = face.data; kb = fm.shape_keys.key_blocks
for k_ in kb:
    if '.' in k_.name: k_.name = k_.name.split('.',1)[1]
NV = len(fm.vertices)
B0 = np.zeros(NV*3, np.float32); kb[0].data.foreach_get('co', B0); B0 = B0.reshape(-1,3)
def D(n):
    a = np.zeros(NV*3, np.float32); kb[n].data.foreach_get('co', a); return a.reshape(-1,3) - B0
vmat = [''] * NV
for p in fm.polygons:
    for v in p.vertices: vmat[v] = matname(face, p.material_index)
def vm(s): return np.array([s in x for x in vmat])
skin_m, iris_m, hl_m = vm('Face_00'), vm('EyeIris'), vm('EyeHighlight')
X = B0[:,0]; mL = ss(-0.004, 0.004, X); mR = 1 - mL
cl = np.abs(D('Fcl_EYE_Close_L')).sum(1); left_is_L = (cl*(X>0)).sum() > (cl*(X<0)).sum()
CL_L, CL_R = ('Fcl_EYE_Close_L','Fcl_EYE_Close_R') if left_is_L else ('Fcl_EYE_Close_R','Fcl_EYE_Close_L')
REP['vroid_Close_L_is_character_left'] = bool(left_is_L)
dA = D('Fcl_MTH_A'); mag = np.linalg.norm(dA, axis=1)
mouth_w = np.clip(mag/(mag.max()+1e-9)*2.2, 0, 1)
mc = B0[mag > 0.5*mag.max()].mean(0)
upper = ss(mc[2]-0.002, mc[2]+0.004, B0[:,2]); lower = 1 - upper
cheek_w = np.exp(-(((np.abs(X)-0.038)/0.014)**2 + ((B0[:,2]-(mc[2]+0.012))/0.016)**2)) * skin_m
nose_w = np.exp(-(((np.abs(X)-0.008)/0.008)**2 + ((B0[:,2]-(mc[2]+0.028))/0.010)**2)) * skin_m
jaw_w = ss(mc[2]+0.004, mc[2]-0.03, B0[:,2]) * ss(0.075, 0.04, np.abs(X)) * (~iris_m)
irisL = (iris_m | hl_m) & (X>0); irisR = (iris_m | hl_m) & (X<0)
ONE = np.ones(NV, bool)
def T(m, v):
    out = np.zeros_like(B0); out[m] = v; return out
def W(vec, w): return np.asarray(vec, np.float32)[None,:]*np.asarray(w, np.float32)[:,None]
SK = {}; SRC = {}
def add(name, delta, how):
    SK[name] = np.asarray(delta, np.float32); SRC[name] = how
for side, m, ir, clk in (('Left', mL, irisL, CL_L), ('Right', mR, irisR, CL_R)):
    sg = 1 if side=='Left' else -1; mm = m[:,None]
    add('eyeBlink'+side, D(clk), 'VRoid '+clk)
    add('eyeLookUp'+side, T(ir, [0,0,0.0045]), 'procedural iris move')
    add('eyeLookDown'+side, T(ir, [0,0,-0.0045]) + 0.18*D(clk), 'procedural iris move + lid')
    add('eyeLookIn'+side, T(ir, [-sg*0.0055,0,0]), 'procedural iris move')
    add('eyeLookOut'+side, T(ir, [sg*0.0055,0,0]), 'procedural iris move')
    add('eyeSquint'+side, 0.45*D('Fcl_EYE_Joy')*mm, 'VRoid EYE_Joy x0.45, side-masked')
    add('eyeWide'+side, D('Fcl_EYE_Surprised')*mm, 'VRoid EYE_Surprised, side-masked')
    add('mouthSmile'+side, D('Fcl_MTH_Fun')*mm, 'VRoid MTH_Fun, side-masked')
    add('mouthFrown'+side, D('Fcl_MTH_Sorrow')*mm, 'VRoid MTH_Sorrow, side-masked')
    add('mouthDimple'+side, 0.4*D('Fcl_MTH_Fun')*mm, 'VRoid MTH_Fun x0.4, side-masked')
    add('mouthStretch'+side, 0.6*D('Fcl_MTH_I')*mm, 'VRoid MTH_I x0.6, side-masked')
    add('mouthPress'+side, 0.5*D('Fcl_MTH_Close')*mm, 'VRoid MTH_Close x0.5, side-masked')
    add('mouthLowerDown'+side, W([0,0,-0.0035], mouth_w*lower*m), 'procedural lip move')
    add('mouthUpperUp'+side, W([0,0,0.003], mouth_w*upper*m), 'procedural lip move')
    add('browDown'+side, D('Fcl_BRW_Angry')*mm, 'VRoid BRW_Angry, side-masked')
    add('browOuterUp'+side, D('Fcl_BRW_Surprised')*mm*ss(0.01,0.035,np.abs(X))[:,None], 'VRoid BRW_Surprised outer half')
    add('cheekSquint'+side, 0.3*D('Fcl_EYE_Joy')*mm + W([0,0,0.002], cheek_w*m), 'VRoid EYE_Joy + cheek lift')
    add('noseSneer'+side, W([0,0,0.0022], nose_w*m) + 0.25*D('Fcl_BRW_Angry')*mm, 'procedural nose lift + brow')
add('jawOpen', dA, 'VRoid MTH_A')
add('jawForward', 0.15*dA + W([0,FWD*0.004,0], jaw_w), 'procedural lower-face move')
add('jawLeft', 0.1*dA + W([0.006,0,0], jaw_w), 'procedural lower-face move')
add('jawRight', 0.1*dA + W([-0.006,0,0], jaw_w), 'procedural lower-face move')
add('mouthClose', D('Fcl_MTH_Close'), 'VRoid MTH_Close')
add('mouthFunnel', D('Fcl_MTH_O'), 'VRoid MTH_O'); add('mouthPucker', D('Fcl_MTH_U'), 'VRoid MTH_U')
add('mouthLeft', W([0.006,0,0], mouth_w), 'procedural'); add('mouthRight', W([-0.006,0,0], mouth_w), 'procedural')
add('mouthRollLower', W([0,-FWD*0.0025,0.0015], mouth_w*lower), 'procedural'); add('mouthRollUpper', W([0,-FWD*0.0025,-0.0012], mouth_w*upper), 'procedural')
add('mouthShrugLower', W([0,0,0.0028], mouth_w*lower), 'procedural'); add('mouthShrugUpper', W([0,0,0.0018], mouth_w*upper), 'procedural')
add('browInnerUp', D('Fcl_BRW_Sorrow'), 'VRoid BRW_Sorrow')
add('cheekPuff', np.c_[np.sign(X)*0.0045, np.full(NV, FWD*0.002), np.zeros(NV)]*cheek_w[:,None], 'procedural cheek push')
# mouth interior: classify FaceMouth islands by texture colour (teeth white, tongue pink/red, cavity dark)
mi = [i for i in range(len(fm.materials)) if 'FaceMouth' in matname(face,i)][0]
mimg = [n.image for n in fm.materials[mi].node_tree.nodes if n.type=='TEX_IMAGE' and n.image][0]
mw_, mh_ = mimg.size; mpx = np.array(mimg.pixels[:], np.float32).reshape(mh_, mw_, 4)
def kind_rgb(c_):
    lum_ = float(c_.mean())
    if lum_ > 0.62 and abs(c_[0]-c_[2]) < 0.15: return 'teeth'
    if c_[0] > c_[1] + 0.10 and lum_ > 0.18: return 'tongue'
    return 'cavity'
def mouth_islands(obj, bm):
    uv_ = bm.loops.layers.uv.active; isl_ = {}; kk_ = 0
    mf = [f for f in bm.faces if 'FaceMouth' in matname(obj, f.material_index)]
    for f in mf:
        if f.index in isl_: continue
        stack = [f]; isl_[f.index] = kk_
        while stack:
            x = stack.pop()
            for e in x.edges:
                for g in e.link_faces:
                    if g.index not in isl_ and 'FaceMouth' in matname(obj, g.material_index): isl_[g.index] = kk_; stack.append(g)
        kk_ += 1
    cols = {}
    for f in mf:
        u_, v_ = np.mean([l[uv_].uv[:] for l in f.loops], 0)
        cols.setdefault(isl_[f.index], []).append(mpx[int(np.clip(v_ % 1,0,.999)*mh_), int(np.clip(u_ % 1,0,.999)*mw_), :3])
    kinds = {i: kind_rgb(np.mean(c, 0)) for i, c in cols.items()}
    return isl_, kinds, {i: [round(float(x),2) for x in np.mean(c,0)] for i,c in cols.items()}
bm = bmesh.new(); bm.from_mesh(fm); bm.faces.ensure_lookup_table()
isl_, kinds, rgbs = mouth_islands(face, bm)
REP['mouth_islands'] = [{'island': i, 'kind': kinds[i], 'rgb': rgbs[i]} for i in kinds]
tongue_v = {v.index for f in bm.faces if f.index in isl_ and kinds[isl_[f.index]]=='tongue' for v in f.verts}
bm.free()
tm = np.zeros(NV, bool); tm[list(tongue_v)] = True
add('tongueOut', 0.45*dA + T(tm, [0, FWD*0.016, -0.004]), 'VRoid MTH_A x0.45 + tongue forward')
if not tongue_v: REP['stubbed'].append('tongue island not found by colour; tongueOut opens the jaw only')
REP['arkit_52'] = {k: SRC[k] for k in sorted(SK)}; note('ARKit shapes', len(SK))
VIS = {'viseme_sil': np.zeros_like(B0), 'viseme_PP': 0.8*D('Fcl_MTH_Close'), 'viseme_FF': 0.4*D('Fcl_MTH_I') + 0.6*SK['mouthRollLower'],
       'viseme_TH': 0.25*dA + T(tm,[0,FWD*0.006,0]), 'viseme_DD': 0.35*dA + 0.2*D('Fcl_MTH_I'), 'viseme_kk': 0.4*dA + 0.2*D('Fcl_MTH_E'),
       'viseme_CH': 0.5*D('Fcl_MTH_I') + 0.3*D('Fcl_MTH_U'), 'viseme_SS': 0.6*D('Fcl_MTH_I'), 'viseme_nn': 0.2*dA + 0.2*D('Fcl_MTH_E'),
       'viseme_RR': 0.5*D('Fcl_MTH_U') + 0.2*D('Fcl_MTH_O'), 'viseme_aa': dA, 'viseme_E': D('Fcl_MTH_E'), 'viseme_I': D('Fcl_MTH_I'),
       'viseme_O': D('Fcl_MTH_O'), 'viseme_U': D('Fcl_MTH_U')}
ALL = dict(SK); ALL.update(VIS); ALL['blink_Eye_L'] = SK['eyeBlinkLeft']; ALL['blink_Eye_R'] = SK['eyeBlinkRight']
for n, dlt in ALL.items():
    kk = face.shape_key_add(name=n, from_mix=False); kk.data.foreach_set('co', (B0 + dlt).astype(np.float32).ravel())
note('face shape keys total', len(fm.shape_keys.key_blocks))
# iris -> Jena blue-grey (from her character sheet), VRoid iris detail kept
for i in range(len(fm.materials)):
    if 'EyeIris' in matname(face, i):
        for n in fm.materials[i].node_tree.nodes:
            if n.type=='TEX_IMAGE' and n.image:
                im = n.image; w_, h_ = im.size; px = np.array(im.pixels[:], np.float32).reshape(-1,4)
                l_ = px[:,:3].mean(1, keepdims=True); px[:,:3] = np.clip(l_*np.array([0.42,0.52,0.66])*1.6, 0, 1)
                ni = bpy.data.images.new('EyeIris_Jena', w_, h_, alpha=True); ni.pixels.foreach_set(px.ravel())
                pth = f'{OUT}/tex/EyeIris_Jena.png'; ni.filepath_raw = pth; ni.file_format='PNG'; ni.save(); n.image = bpy.data.images.load(pth)
EYE = ('EyeIris','EyeHighlight','EyeWhite')
eye_l = split_faces(face, lambda o,f,bm: any(s in matname(o,f.material_index) for s in EYE) and f.calc_center_median().x > 0, 'Eye_L')
eye_r = split_faces(face, lambda o,f,bm: any(s in matname(o,f.material_index) for s in EYE), 'Eye_R')
def kind_pred(kind):
    cache = {}
    def pr(o, f, bm):
        key = (o.name, id(bm))
        if key not in cache: cache.clear(); cache[key] = mouth_islands(o, bm)
        il, kd, _ = cache[key]
        return f.index in il and kd[il[f.index]] == kind
    return pr
teeth = split_faces(face, kind_pred('teeth'), 'Teeth')
tongue = split_faces(face, kind_pred('tongue'), 'Tongue')
for o in (eye_l, eye_r, teeth, tongue):
    note(o.name, 'verts', len(o.data.vertices))
    if len(o.data.vertices) == 0: REP['stubbed'].append(o.name+' mesh came out empty')
