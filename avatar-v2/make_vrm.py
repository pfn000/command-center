
# make_vrm.py: GLB (from Blender) -> VRM 1.0 with humanoid (her bone names), expressions (VRM presets + ARKit 52 + visemes + blink_Eye_L/R),
# spring bones (hair strands, bun, boobs, butt, thigh jiggle) with capsule/sphere colliders, node constraints (twist bones), MToon.
import json, struct, sys, numpy as np
src, dst_vrm, dst_glb, base_vrm = sys.argv[1:5]
def readglb(p):
    b = open(p,'rb').read(); l = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20+l])
    o = 20+l; bl = struct.unpack('<I', b[o:o+4])[0]; return j, b[o+8:o+8+bl]
def writeglb(p, j, bin_):
    js = json.dumps(j, separators=(',',':')).encode(); js += b' '*((4-len(js)%4)%4); bin_ += b'\0'*((4-len(bin_)%4)%4)
    out = b'glTF' + struct.pack('<II', 2, 12+8+len(js)+8+len(bin_)) + struct.pack('<I', len(js)) + b'JSON' + js + struct.pack('<I', len(bin_)) + b'BIN\0' + bin_
    open(p,'wb').write(out)
J, BIN = readglb(src); BJ, _ = readglb(base_vrm)
N = J['nodes']; idx = {n.get('name'): i for i, n in enumerate(N)}
par = {c: i for i, n in enumerate(N) for c in n.get('children', [])}
def local(n):
    t = np.array(n.get('translation',[0,0,0])); r = n.get('rotation',[0,0,0,1]); s = np.array(n.get('scale',[1,1,1]))
    x,y,z,w = r; R = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],[2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],[2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    M = np.eye(4); M[:3,:3] = R*s; M[:3,3] = t; return M
WM = {}
def world(i):
    if i in WM: return WM[i]
    M = local(N[i]); WM[i] = (world(par[i]) @ M) if i in par else M; return WM[i]
def P(name): return world(idx[name])[:3,3]
def to_local(name, p): return (np.linalg.inv(world(idx[name])) @ np.r_[p, 1])[:3].tolist()
rep = {}
# ---- humanoid
H = {'hips':'Hips','spine':'Spine_04','chest':'Spine_03','upperChest':'Spine_02','neck':'Neck_01','head':'Head','leftEye':'Eye_L_Bone','rightEye':'Eye_R_Bone'}
for s, S in (('L','left'), ('R','right')):
    H.update({S+'Shoulder':f'Shoulder_{s}', S+'UpperArm':f'UpperArm_{s}', S+'LowerArm':f'LowerArm_{s}', S+'Hand':f'Hand_{s}',
              S+'UpperLeg':f'UperLeg_{s}', S+'LowerLeg':f'LowerLeg_{s}', S+'Foot':f'Ankle_{s}', S+'Toes':f'Foot_{s}',
              S+'ThumbMetacarpal':f'Thumb_01_{s}', S+'ThumbProximal':f'Thumb_02_{s}', S+'ThumbDistal':f'Thumb_03_{s}'})
    for fg in ('Index','Middle','Ring','Little'):
        for k, nm in ((1,'Proximal'),(2,'Intermediate'),(3,'Distal')): H[f'{S}{fg}{nm}'] = f'{fg}_{k:02d}_{s}'
hb = {k: {'node': idx[v]} for k, v in H.items() if v in idx}
rep['humanoid_missing'] = [k for k, v in H.items() if v not in idx]
# ---- expressions
mesh_nodes = [(i, n) for i, n in enumerate(N) if 'mesh' in n]
tnames = {i: J['meshes'][n['mesh']].get('extras', {}).get('targetNames', []) for i, n in mesh_nodes}
def binds(names):
    out = []
    for i, tn in tnames.items():
        for nm, w in names:
            if nm in tn: out.append({'node': i, 'index': tn.index(nm), 'weight': w})
    return out
def ex(names, binary=False, **kw):
    d = {'isBinary': binary, 'morphTargetBinds': binds(names), 'overrideBlink': 'none', 'overrideLookAt': 'none', 'overrideMouth': 'none'}; d.update(kw); return d
preset = {'happy': ex([('Fcl_ALL_Joy',1)], overrideBlink='block'), 'angry': ex([('Fcl_ALL_Angry',1)], overrideBlink='block'), 'sad': ex([('Fcl_ALL_Sorrow',1)]),
          'relaxed': ex([('Fcl_ALL_Fun',1)]), 'surprised': ex([('Fcl_ALL_Surprised',1)]), 'neutral': ex([('Fcl_ALL_Neutral',1)]),
          'aa': ex([('viseme_aa',1)]), 'ih': ex([('viseme_I',1)]), 'ou': ex([('viseme_U',1)]), 'ee': ex([('viseme_E',1)]), 'oh': ex([('viseme_O',1)]),
          'blink': ex([('eyeBlinkLeft',1),('eyeBlinkRight',1)]), 'blinkLeft': ex([('blink_Eye_L',1)]), 'blinkRight': ex([('blink_Eye_R',1)]),
          'lookUp': ex([]), 'lookDown': ex([]), 'lookLeft': ex([]), 'lookRight': ex([])}
allt = set(sum(tnames.values(), []))
ARK = ['eyeBlinkLeft','eyeLookDownLeft','eyeLookInLeft','eyeLookOutLeft','eyeLookUpLeft','eyeSquintLeft','eyeWideLeft','eyeBlinkRight','eyeLookDownRight','eyeLookInRight','eyeLookOutRight','eyeLookUpRight','eyeSquintRight','eyeWideRight','jawForward','jawLeft','jawRight','jawOpen','mouthClose','mouthFunnel','mouthPucker','mouthLeft','mouthRight','mouthSmileLeft','mouthSmileRight','mouthFrownLeft','mouthFrownRight','mouthDimpleLeft','mouthDimpleRight','mouthStretchLeft','mouthStretchRight','mouthRollLower','mouthRollUpper','mouthShrugLower','mouthShrugUpper','mouthPressLeft','mouthPressRight','mouthLowerDownLeft','mouthLowerDownRight','mouthUpperUpLeft','mouthUpperUpRight','browDownLeft','browDownRight','browInnerUp','browOuterUpLeft','browOuterUpRight','cheekPuff','cheekSquintLeft','cheekSquintRight','noseSneerLeft','noseSneerRight','tongueOut']
custom = {n: ex([(n,1)]) for n in ARK + [t for t in sorted(allt) if t.startswith('viseme_')] + ['blink_Eye_L','blink_Eye_R'] if n in allt}
rep['arkit_present'] = sum(n in allt for n in ARK); rep['arkit_missing'] = [n for n in ARK if n not in allt]
rep['custom_expressions'] = len(custom); rep['meshes_with_targets'] = {N[i]['name']: len(t) for i, t in tnames.items() if t}
# ---- spring bones
colliders, cgroups = [], {}
def col(group, node, shape):
    colliders.append({'node': idx[node], 'shape': shape}); cgroups.setdefault(group, []).append(len(colliders)-1)
head_c = P('Head') + np.array([0, 0.085, 0.005])
col('head', 'Head', {'sphere': {'offset': to_local('Head', head_c), 'radius': 0.085}})
col('body', 'Neck_01', {'capsule': {'offset': to_local('Neck_01', P('Neck_01')), 'radius': 0.042, 'tail': to_local('Neck_01', P('Head'))}})
for nm, r, w in (('Spine_02', 0.07, 0.075), ('Spine_03', 0.085, 0.05), ('Spine_04', 0.085, 0.04), ('Hips', 0.10, 0.06)):
    c = P(nm) + np.array([0, 0.03, 0])
    col('body', nm, {'capsule': {'offset': to_local(nm, c - [w,0,0]), 'radius': r, 'tail': to_local(nm, c + [w,0,0])}})
for s in 'LR':
    for a, b, r, g in ((f'Shoulder_{s}', f'UpperArm_{s}', 0.045, 'arms'), (f'UpperArm_{s}', f'LowerArm_{s}', 0.040, 'arms'), (f'LowerArm_{s}', f'Hand_{s}', 0.033, 'arms'),
                       (f'UperLeg_{s}', f'LowerLeg_{s}', 0.075, 'legs'), (f'LowerLeg_{s}', f'Ankle_{s}', 0.05, 'legs')):
        col(g, a, {'capsule': {'offset': [0,0,0], 'radius': r, 'tail': to_local(a, P(b))}})
    if f'Boob_{s}_END' in idx:
        col('bust', f'Boob_{s}', {'sphere': {'offset': to_local(f'Boob_{s}', (P(f'Boob_{s}') + P(f'Boob_{s}_END'))/2), 'radius': 0.05}})
gnames = list(cgroups); groups = [{'name': g, 'colliders': cgroups[g]} for g in gnames]
G = {g: i for i, g in enumerate(gnames)}
springs = []
def chain(name, nodes, stiff, grav, drag, hit, grp, center=None):
    js = [{'node': idx[n], 'hitRadius': hit, 'stiffness': stiff, 'gravityPower': grav, 'gravityDir': [0,-1,0], 'dragForce': drag} for n in nodes if n in idx]
    if len(js) >= 2:
        sp = {'name': name, 'joints': js, 'colliderGroups': [G[g] for g in grp if g in G]}
        if center: sp['center'] = idx[center]
        springs.append(sp)
import re
hairs = {}
for n in idx:
    m = re.match(r'Hair_(\d+)_(\d+|END)$', n)
    if m: hairs.setdefault(m.group(1), []).append(n)
for ch, ns in sorted(hairs.items()):
    ns = sorted([x for x in ns if not x.endswith('END')]) + [x for x in ns if x.endswith('END')]
    chain('Hair_'+ch, ns, 0.9, 0.12, 0.45, 0.015, ['head','body','arms','bust'])
chain('Hair_Bun', ['Hair_Bun_01','Hair_Bun_END'], 1.6, 0.05, 0.6, 0.02, ['head'])
for s in 'LR':
    chain(f'Boob_{s}', [f'Boob_{s}', f'Boob_{s}_END'], 1.2, 0.05, 0.25, 0.02, ['arms'], 'Hips')
    chain(f'Butt_{s}', [f'Butt_{s}', f'Butt_{s}_END'], 1.6, 0.03, 0.35, 0.02, [], 'Hips')
    chain(f'ThighJiggle_{s}', [f'ThighJiggle_{s}', f'ThighJiggle_{s}_END'], 1.9, 0.02, 0.4, 0.015, [], 'Hips')
rep['springs'] = len(springs); rep['colliders'] = len(colliders); rep['collider_shapes'] = sorted({list(c['shape'])[0] for c in colliders})
# ---- node constraints (twist helpers), carried over from the base sample with her names
REN = json.load(open(sys.argv[5]))['rename_map'] if len(sys.argv) > 5 else {}
bn = {i: n.get('name') for i, n in enumerate(BJ['nodes'])}; nc = 0
for n in BJ['nodes']:
    c = (n.get('extensions') or {}).get('VRMC_node_constraint')
    if not c: continue
    me = REN.get(n['name'], n['name'])
    if me not in idx: continue
    c = json.loads(json.dumps(c)); cons = c['constraint']
    ok = True
    for k, v in cons.items():
        sname = REN.get(bn[v['source']], bn[v['source']])
        if sname not in idx: ok = False; break
        v['source'] = idx[sname]
    if ok: N[idx[me]].setdefault('extensions', {})['VRMC_node_constraint'] = c; nc += 1
rep['node_constraints'] = nc
# ---- materials: alpha modes + MToon
for m in J['materials']:
    nm = m['name']; m['doubleSided'] = True
    if 'Sheer' in nm: m['alphaMode'] = 'BLEND'
    elif any(s in nm for s in ('Hair_Jena','HairBack_Jena','FaceEyeline','FaceBrow','EyeHighlight','EyeIris','EyeWhite','FaceMouth','Face_00')):
        bm_ = [x for x in BJ['materials'] if x['name'] == nm]
        m['alphaMode'] = bm_[0].get('alphaMode', 'MASK') if bm_ else 'MASK'
        if m['alphaMode'] == 'MASK': m['alphaCutoff'] = bm_[0].get('alphaCutoff', 0.5) if bm_ else 0.5
    else: m['alphaMode'] = 'OPAQUE'
Jg = json.loads(json.dumps(J))
for n in Jg['nodes']:
    if 'extensions' in n: n['extensions'].pop('VRMC_node_constraint', None)
    if 'extensions' in n and not n['extensions']: n.pop('extensions')
writeglb(dst_glb, Jg, BIN)    # clean .glb (alpha modes fixed), no VRM extensions
J['extensionsUsed'] = sorted(set(J.get('extensionsUsed', [])) | {'VRMC_vrm','VRMC_springBone','VRMC_node_constraint'})
pbr = lambda m: m.get('pbrMetallicRoughness', {})
for m in J['materials']:
    bc = pbr(m).get('baseColorFactor', [1,1,1,1])
    mt = {'specVersion': '1.0', 'transparentWithZWrite': False, 'renderQueueOffsetNumber': 0,
          'shadeColorFactor': [bc[0]*0.72, bc[1]*0.70, bc[2]*0.74], 'shadingShiftFactor': -0.05, 'shadingToonyFactor': 0.92,
          'giEqualizationFactor': 0.9, 'matcapFactor': [0,0,0], 'parametricRimColorFactor': [0.25,0.25,0.28], 'parametricRimFresnelPowerFactor': 4.0,
          'parametricRimLiftFactor': 0.0, 'rimLightingMixFactor': 1.0, 'outlineWidthMode': 'none', 'outlineWidthFactor': 0.0,
          'outlineColorFactor': [0,0,0], 'outlineLightingMixFactor': 1.0, 'uvAnimationScrollXSpeedFactor': 0, 'uvAnimationScrollYSpeedFactor': 0, 'uvAnimationRotationSpeedFactor': 0}
    if 'baseColorTexture' in pbr(m): mt['shadeMultiplyTexture'] = {'index': pbr(m)['baseColorTexture']['index']}
    m.setdefault('extensions', {})['VRMC_materials_mtoon'] = mt
J['extensionsUsed'] = sorted(set(J['extensionsUsed']) | {'VRMC_materials_mtoon'})
J.setdefault('extensions', {})['VRMC_vrm'] = {
    'specVersion': '1.0',
    'meta': {'name': 'Jena v2', 'version': '2.0.0-proof', 'authors': ['Saidie Quinn Newara (NCOM)'],
             'copyrightInformation': 'Jena (c) Saidie Quinn Newara / NCOM. Base mesh: pixiv VRM1_Constraint_Twist_Sample (VRM Public License 1.0, modification + redistribution allowed).',
             'licenseUrl': 'https://vrm.dev/licenses/1.0/', 'avatarPermission': 'onlyAuthor', 'allowExcessivelyViolentUsage': False,
             'allowExcessivelySexualUsage': False, 'commercialUsage': 'personalProfit', 'allowPoliticalOrReligiousUsage': False,
             'allowAntisocialOrHateUsage': False, 'creditNotation': 'required', 'allowRedistribution': False, 'modification': 'prohibited'},
    'humanoid': {'humanBones': hb},
    'firstPerson': {'meshAnnotations': [{'node': i, 'type': 'auto'} for i, n in mesh_nodes]},
    'lookAt': {'type': 'bone', 'offsetFromHeadBone': [0, 0.06, 0.02],
               'rangeMapHorizontalInner': {'inputMaxValue': 90, 'outputScale': 10}, 'rangeMapHorizontalOuter': {'inputMaxValue': 90, 'outputScale': 10},
               'rangeMapVerticalDown': {'inputMaxValue': 90, 'outputScale': 10}, 'rangeMapVerticalUp': {'inputMaxValue': 90, 'outputScale': 10}},
    'expressions': {'preset': preset, 'custom': custom}}
J['extensions']['VRMC_springBone'] = {'specVersion': '1.0', 'colliders': colliders, 'colliderGroups': groups, 'springs': springs}
writeglb(dst_vrm, J, BIN)
json.dump(rep, open(dst_vrm + '.report.json', 'w'), indent=1); print(json.dumps(rep)[:3000])
