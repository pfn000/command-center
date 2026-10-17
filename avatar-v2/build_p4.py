
# ---------- 6. rig per Saidie's RIG-SCHEMA (her names; Unity-Humanoid 'Hips' root; (G) jiggle bones get _END tips) ----------
meshes = [o for o in bpy.data.objects if o.type=='MESH']
for o in (bun, tie): add_armature(o)
for o in meshes + [bun, tie]: add_armature(o)
used = set()
for o in [o for o in bpy.data.objects if o.type=='MESH']:
    cnt = {}
    for v in o.data.vertices:
        for g in v.groups:
            if g.weight > 1e-4: cnt[g.group] = 1
    used |= {o.vertex_groups[i].name for i in cnt}
REN = {'J_Bip_C_Hips':'Hips','J_Bip_C_Spine':'Spine_04','J_Bip_C_Chest':'Spine_03','J_Bip_C_UpperChest':'Spine_02',
       'J_Bip_C_Neck':'Neck_01','J_Bip_C_Head':'Head','J_Bip_C_Head_end':'Head_END','J_Adj_L_FaceEye':'Eye_L_Bone','J_Adj_R_FaceEye':'Eye_R_Bone',
       'J_Sec_L_Bust1':'Boob_L','J_Sec_L_Bust2':'Boob_L_END','J_Sec_R_Bust1':'Boob_R','J_Sec_R_Bust2':'Boob_R_END'}
for s in 'LR':
    REN.update({f'J_Bip_{s}_Shoulder':f'Shoulder_{s}', f'J_Bip_{s}_UpperArm':f'UpperArm_{s}', f'J_Bip_{s}_LowerArm':f'LowerArm_{s}',
                f'J_Bip_{s}_Hand':f'Hand_{s}', f'J_Bip_{s}_UpperLeg':f'UperLeg_{s}', f'J_Bip_{s}_LowerLeg':f'LowerLeg_{s}',
                f'J_Bip_{s}_Foot':f'Ankle_{s}', f'J_Bip_{s}_ToeBase':f'Foot_{s}', f'J_Bip_{s}_ToeBase_end':f'Foot_{s}_END',
                f'J_Roll_{s}_UpperArm':f'UpperArm_Twist_{s}', f'J_Aim_{s}_Shoulder':f'Shoulder_Aim_{s}', f'J_Roll_{s}_Elbow':f'Elbow_Roll_{s}',
                f'J_Roll_{s}_LowerArm':f'LowerArm_Twist_{s}', f'J_Roll_{s}_Hand':f'Hand_Roll_{s}', f'J_Aim_{s}_UpperLeg':f'UperLeg_Aim_{s}',
                f'J_Roll_{s}_UpperLeg':f'UperLeg_Twist_{s}'})
    for fg in ('Thumb','Index','Middle','Ring','Little'):
        for j in (1,2,3): REN[f'J_Bip_{s}_{fg}{j}'] = f'{fg}_{j:02d}_{s}'
        REN[f'J_Bip_{s}_{fg}3_end'] = f'{fg}_{s}_END'
import re
hair_chains = {}
for b in arm.data.bones:
    m_ = re.match(r'J_Sec_Hair(\d+)_(\d+)(_end)?$', b.name)
    if m_: hair_chains.setdefault(int(m_.group(2)), []).append(b.name)
bpy.context.view_layer.objects.active = arm
for ob in bpy.context.view_layer.objects: ob.select_set(ob == arm)
bpy.ops.object.mode_set(mode='EDIT'); eb = arm.data.edit_bones
removed = []
kept_chains = 0
for ch, names in sorted(hair_chains.items()):
    if not any(n in used for n in names if not n.endswith('_end')):
        for n in names: eb.remove(eb[n]); removed.append(n)
        continue
    kept_chains += 1
    for n in names:
        e = eb[n]
        for attr in ('head','tail'):
            v = getattr(e, attr)
            if v.z < HAIR_ZMAP[0]: setattr(e, attr, Vector((v.x, v.y, HAIR_ZMAP[0] - (HAIR_ZMAP[0]-v.z)*HAIR_ZMAP[1])))
        m_ = re.match(r'J_Sec_Hair(\d+)_(\d+)(_end)?$', n)
        REN[n] = f'Hair_{ch:02d}_END' if m_.group(3) else f'Hair_{ch:02d}_{int(m_.group(1)):02d}'
for e in list(eb):
    if 'Tops' in e.name and e.name not in used and not any(c.name in used for c in e.children_recursive):
        removed.append(e.name); eb.remove(e)
REP['bones_removed'] = removed; REP['hair_chains_kept'] = kept_chains
def nb(name, parent, head, tail, deform):
    e = eb.new(name); e.head = Vector(head); e.tail = Vector(tail); e.parent = eb[parent]; e.use_deform = deform; return e
ADDED = []
for s, sg in (('L',1), ('R',-1)):
    leg = Vector((L['leg'].x*sg, L['leg'].y, L['leg'].z)); knee = Vector((L['knee'].x*sg, L['knee'].y, L['knee'].z))
    ank = Vector((L['ankle'].x*sg, L['ankle'].y, L['ankle'].z)); toe = Vector((L['toe'].x*sg, L['toe'].y, L['toe'].z))
    sh_ = knee.lerp(ank, 0.5); nb(f'Shin_{s}', f'J_Bip_{s}_LowerLeg', sh_, sh_ + (ank-knee)*0.25, False)
    for t, dx in enumerate((-0.022, -0.009, 0.002, 0.012, 0.021), 1):
        h = toe + Vector((dx*sg*-1 if False else -dx*sg*-1, FWD*0.012, -0.012))
        h = toe + Vector((sg*dx, FWD*0.012, -0.012))
        nb(f'Toes_{t:02d}_{s}', f'J_Bip_{s}_ToeBase', h, h + Vector((0, FWD*0.028 if t==1 else FWD*0.022, 0)), False)
    bh = Vector((leg.x*0.95, L['hips'].y + 0.075, leg.z - 0.02)); nb(f'Butt_{s}', f'J_Bip_{s}_UpperLeg', bh, bh + Vector((0, 0.05, 0)), True)
    nb(f'Butt_{s}_END', f'Butt_{s}', bh + Vector((0,0.05,0)), bh + Vector((0,0.07,0)), False)
    th = Vector((leg.x - sg*0.035, leg.y, (leg.z+knee.z)/2 + 0.05)); nb(f'ThighJiggle_{s}', f'J_Bip_{s}_UpperLeg', th, th + Vector((-sg*0.045,0,0)), True)
    nb(f'ThighJiggle_{s}_END', f'ThighJiggle_{s}', th + Vector((-sg*0.045,0,0)), th + Vector((-sg*0.06,0,0)), False)
    ADDED += [f'Shin_{s}', f'Butt_{s}', f'Butt_{s}_END', f'ThighJiggle_{s}', f'ThighJiggle_{s}_END'] + [f'Toes_{t:02d}_{s}' for t in range(1,6)]
nb('Floor_Anchor', 'J_Bip_C_Hips', (0,0,0), (0, FWD*0.15, 0), False)
nb('Jaw', 'J_Bip_C_Head', (0, L['head'].y - 0.005, mc[2] + 0.025), (0, L['head'].y - 0.065, mc[2] - 0.01), False)
nb('Hair_Bun_01', 'J_Bip_C_Head', bun_c - dirv*0.02, bun_c + dirv*0.01, True)
nb('Hair_Bun_END', 'Hair_Bun_01', bun_c + dirv*0.01, bun_c + dirv*0.03, False)
ADDED += ['Floor_Anchor', 'Jaw', 'Hair_Bun_01', 'Hair_Bun_END']
for n in ('J_Sec_L_Bust2','J_Sec_R_Bust2'):
    e = eb[n]; d_ = (e.tail - e.head); e.tail = e.head + d_.normalized()*max(d_.length, 0.02)
bpy.ops.object.mode_set(mode='OBJECT')
REP['bones_added'] = ADDED
# jiggle weights: carve a share of the existing weights into the new deform bones (normalized)
def carve(o, bone, center, sigma, share, mask_fn):
    c = coords(o); g = np.exp(-np.sum((c - np.array(center))**2, 1)/(2*sigma*sigma)) * share
    g *= np.array([mask_fn(x) for x in c], np.float32)
    if bone not in o.vertex_groups: o.vertex_groups.new(name=bone)
    vg = o.vertex_groups[bone]
    for v in o.data.vertices:
        w = float(g[v.index])
        if w < 0.01: continue
        for gg in v.groups:
            if gg.group != vg.index: gg.weight *= (1 - w)
        vg.add([v.index], w, 'REPLACE')
for s, sg in (('L',1), ('R',-1)):
    bc = (L['leg'].x*sg, L['hips'].y + 0.085, legz - 0.035); tcn = (L['leg'].x*sg - sg*0.04, L['leg'].y, (legz+kneez)/2 + 0.04)
    for o in (body, shorts):
        carve(o, f'Butt_{s}', bc, 0.05, 0.65, lambda x, sg=sg: float(x[1] > L['hips'].y and x[0]*sg > 0))
    for o in (body, thigh, shorts):
        carve(o, f'ThighJiggle_{s}', tcn, 0.045, 0.45, lambda x, sg=sg: float(x[0]*sg < L['leg'].x and x[0]*sg > 0))
bun.vertex_groups.new(name='Hair_Bun_01').add(list(range(len(bun.data.vertices))), 1.0, 'REPLACE')
tie.vertex_groups.new(name='J_Bip_C_Head').add(list(range(len(tie.data.vertices))), 1.0, 'REPLACE')
join(hair, [hairback, bun]); hair.name = 'Hair'
for old, new in REN.items():
    if old in arm.data.bones: arm.data.bones[old].name = new
for o in [o for o in bpy.data.objects if o.type=='MESH']:
    for old, new in REN.items():
        if old in o.vertex_groups and new not in o.vertex_groups: o.vertex_groups[old].name = new
REP['rename_map'] = REN
REP['meshes'] = {o.name: {'verts': len(o.data.vertices), 'materials': [m.name for m in o.data.materials],
                          'shape_keys': len(o.data.shape_keys.key_blocks)-1 if o.data.shape_keys else 0}
                 for o in bpy.data.objects if o.type=='MESH'}
REP['bones'] = sorted(b.name for b in arm.data.bones)
REP['landmarks_blender'] = {k: [round(c,4) for c in v] for k,v in L.items()}
REP['extra_points'] = {'bun_c': [round(x,4) for x in bun_c], 'mouth_c': [round(float(x),4) for x in mc], 'pend': [round(x,4) for x in pend],
                      'band_mid_z': round(mid,4), 'band_lo': round(band_lo,4), 'th_top': round(th_top,4), 'under': round(under,4)}
note('final meshes', REP['meshes'])
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/jena-v2.blend', compress=True)
bpy.ops.export_scene.gltf(filepath=OUT+'/jena-v2.glb', export_format='GLB', use_selection=False, export_skins=True, export_morph=True,
                          export_morph_normal=False, export_animations=False, export_apply=False, export_yup=True, export_def_bones=False)
json.dump(REP, open(OUT+'/build-report.json','w'), indent=1, default=str)
note('DONE')
