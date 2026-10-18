
# v3.7 ASSEMBLY, run 7 (RUN6B-FINDINGS fixes: shirt seam/shell weld + smoothed pushes + corrective body weights + posed clearance; front locks <=8 deg;
#   RUN 8c: culling+flush off; her weights harmonized per weld group + seam zone BEFORE the retarget; smoothed weld snaps; seam-zone displacement relax; weld snap in each posed-clearance iteration.
#   RUN 8b (Saidie 3:38-3:41 PM): head asset's OWN hair (no Blowout), shirt Tshirt-LewdFaceBlack.png, inner-shell flush + backface cull at the band/sleeve seam, seam close-ups.
#   RUN 8 (on 7b): band+sleeve-top seam weights spatially averaged; posed clearance adds arms-forward frames 166-172; front locks per bone vs body+bra+shirt, stick-out cap 2 cm; final lock gate; Tummy close-ups.
#   halter loop rides the Neck offset rigidly (no vertex pushes); Tummy hem clearance; variants A0 bang 1:1 / A1 bang curled <=15 deg). Based on run 6c (hair: NO chain lifts, rest pose 1:1, only a rigid whole-hair offset <=10 mm up/back + uniform scale <=3 % - root 17:27Z). Run 6b (fixes from run 6 QA: layer-coherent pushes on her double-shell shirt/bra, bra halter moved with the outfit Neck bone, hair chains CURLED with a stick-out penalty instead of a 45-deg swing, hair-through-body in the chain search). Run 6 (shirt: her own outfit weights, arm chain retargeted from the outfit's A-pose onto Panda's rest so sleeves sit ON the arms, then local clearance only; bra halter pushed off the neck; dense multi-camera eye/cheek check with per-chain pose search; measure system; Umeko dropped). Run 5: (hair: its own Head bone on her Head bone at the head's scale, bang chains posed off the eyes if needed; shirt: rigid re-seat + offset along BODY normals, no cover_fix). Run 4 notes: (head on Panda's Head bone at proportional scale, no hair push, shorts re-seated + hugged, bra hidden under the shirt). Saidie 10:11 AM Oct 18: "if the body face and the final render does not look 1 to 1 to the assets I fed you, then you have done it wrong"
# Attach + fit + rig ONLY. Her Panda body (authored material), her Female Head (face 1.png + ZinPia doe 5, no shape-key bakes, no reshape),
# her Blowout haircards (B&W.png) [alt: Umeko + her black->white jpg], Outfitriggedpanda shirt (Tshirt-BasicGrey.png) + bra (plain black, her 10:30 ask),
# Booty Shorts (Textures/Colors/Black.png). ONE armature (Panda's). Clothes weights = Data Transfer from the body. Zero Meshy.
import bpy, sys, os, math, json, traceback
from mathutils import Vector, Matrix
from mathutils.kdtree import KDTree
import numpy as np
argv=sys.argv[sys.argv.index('--')+1:]; IN,OUT=argv[0],argv[1]; os.makedirs(OUT+'/proof',exist_ok=True)
import time as _t; _T0=_t.time()
def log(*a): print('[v3]',f'{_t.time()-_T0:.0f}s',*a,flush=True)
VAR=os.environ.get('VARIANT','A0')
P=dict(HEAD_K=6.75, SHORTS_FIT='hug', HUG_OFF=0.0025, FIT_HAIR=False, FIT_SHIRT=0.006, SEAM_BLEND=False, BRA_UNDER_SHIRT='hide', CRAN_BELOW=0.02, SHORTS_TEX='Black.png', HAIR='blowout', SHIRT=True, HAIR_W_RATIO=1.55, HAIR_TOP_GAP=0.010, HAIR_DZ=0.010, HAIR_DY=0.006, HAIR_DEPTH_K=1.1,
       NECK_R_K=0.97, NECK_SINK=0.015, SEAM_BAND=0.035, BRA_COL=(0.012,0.012,0.013), BRA_ROUGH=0.7,
       ARM_DOWN=74, SHOULDER_DOWN=10, ELBOW_BEND=-12, WRIST_BEND=8, RELAX=True, SAMPLES=32, ASM_SAMPLES=16, CRANIUM=True, HEAD_TEX='1.png',
       SET='full', SHIRT_RETARGET=True, SHIRT_WEIGHTS='original', STRAP_PUSH=0.002, SHIRT_RESEAT=False, TT=False, TT_FRAMES=96, TT_SAMPLES=12, TT_W=720, TT_H=1280)
try:
    J=json.load(open(os.path.dirname(os.path.abspath(__file__))+'/assemble.json')); P.update(J.get('all',{})); P.update(J.get(VAR,{}))
except Exception as e: log('no assemble.json',e)
if os.environ.get('TT_SHARD') is not None: P['TT']=True
rep={'variant':VAR,'params':P}; log('variant',VAR,P)
LAYER_OBJS=set()
FILES={}
for r,ds,fs in os.walk(IN):
    if '/.cache' in r: continue
    for f in fs: FILES.setdefault(f.lower(),os.path.join(r,f))
bpy.ops.wm.read_factory_settings(use_empty=True); sc=bpy.context.scene
def tris(o): return sum(len(p.vertices)-2 for p in o.data.polygons) if o.type=='MESH' else 0
def wco(o): return np.array([tuple(o.matrix_world@v.co) for v in o.data.vertices])
def imp_fbx(path):
    before=set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=path); return [o for o in bpy.data.objects if o not in before]
def sel(objs,active=None):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active=active or objs[0]
def set_tex(mat,path,alpha=False):
    if not path or not os.path.exists(path): log('MISSING TEX',path); return False
    mat.use_nodes=True; nt=mat.node_tree; b=[n for n in nt.nodes if n.type=='BSDF_PRINCIPLED']
    if not b: b=[nt.nodes.new('ShaderNodeBsdfPrincipled')]; nt.links.new(b[0].outputs[0],[n for n in nt.nodes if n.type=='OUTPUT_MATERIAL'][0].inputs[0])
    b=b[0]
    for l in [l for l in nt.links if l.to_socket==b.inputs['Base Color'] or (alpha and l.to_socket==b.inputs['Alpha'])]: nt.links.remove(l)
    t=nt.nodes.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(path,check_existing=True); nt.links.new(t.outputs[0],b.inputs['Base Color'])
    if alpha: nt.links.new(t.outputs[1],b.inputs['Alpha'])
    return True
def fix_images():
    miss=[]
    for im in bpy.data.images:
        if im.source!='FILE': continue
        p=bpy.path.abspath(im.filepath)
        if im.packed_file or (p and os.path.exists(p) and im.size[0]>0): continue
        b=os.path.basename(p.replace('\\','/')).lower()
        if b in FILES: im.filepath=FILES[b]; im.reload()
        else: miss.append(im.name)
    return miss
def mats_report(o):
    out=[]
    for s in o.material_slots:
        m=s.material
        if not m: continue
        out.append((m.name,[n.image.name for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] if m.use_nodes else []))
    return out
def apply_tf(objs,M):
    """uniform scale + translation of an imported rig (armature + its meshes) and bake it in (no rotation, no shape change)"""
    roots=[o for o in objs if o.parent is None or o.parent not in objs]
    for o in roots:
        if o.parent is not None: mw=o.matrix_world.copy(); o.parent=None; o.matrix_world=mw
        o.matrix_world=M@o.matrix_world
    bpy.context.view_layer.update(); sel(objs,objs[0]); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
# ---------- 1. her Panda body, appended, authored material as-is
BF=IN+"/Panda's Fit Base (High - Flat Foot)/"
with bpy.data.libraries.load(BF+"Panda's Fit Base (High - Flat Foot).blend",link=False) as (df,dt): dt.objects=list(df.objects)
for o in dt.objects:
    if o is not None: sc.collection.objects.link(o)
for im_ in bpy.data.images:
    base=im_.name.split('.png')[0]+'.png'
    if os.path.exists(BF+base): im_.filepath=BF+base; im_.reload()
B=bpy.data.objects['Armature']; BODY=bpy.data.objects['Body']
rep['body_objects']=[(o.name,o.type) for o in dt.objects if o]; rep['body_materials']=mats_report(BODY); rep['body_bones0']=len(B.data.bones)
log('body',tris(BODY),rep['body_materials'],'bones',len(B.data.bones))
BX=[o for o in dt.objects if o and o.type=='MESH' and o is not BODY and o.visible_get()]
for o in BX: log('extra body-file mesh',o.name)
# ---------- 2. her Female Head, WITH its armature (bones merged into Panda's later); bunisu pigtails/bangs meshes dropped (she chose other hair)
HD=IN+'/1691108855vrmodels_store_female-head-by-bunisu/Female head/'; ZP=IN+'/ZinPia_Doe Eyes (Sunny Head)/'
new=imp_fbx(HD+'Female head + hair.fbx'); FH=[o for o in new if o.type=='MESH' and o.name=='Female Head'][0]; FA=[o for o in new if o.type=='ARMATURE'][0]
# run 8 (Saidie 3:38 PM: "since there's already hair on the head model, just don't use the blowout hair"): HAIR='head' keeps the head asset's OWN hair meshes
# (bunisu 'Hair - ...' meshes, their own weights to the head's Hair Root / Bangs / piggy / Back hair bones), 1:1, riding the head's single uniform transform.
HHM=[o for o in new if o.type=='MESH' and o is not FH and o.name.lower().startswith('hair')] if P.get('HAIR')=='head' else []
rep['head_fbx_meshes']=[(o.name,o.type,(len(o.data.vertices) if o.type=='MESH' else 0)) for o in new]; log('head fbx objects',rep['head_fbx_meshes'])
for o in new:
    if o.type=='MESH' and o is not FH and o not in HHM: bpy.data.objects.remove(o)
if P.get('HAIR')=='head' and not HHM: raise RuntimeError('HAIR=head but the head fbx has no hair mesh')
for o in HHM:
    for s_l in o.material_slots:
        m=s_l.material
        if not m: continue
        m.use_nodes=True; nt=m.node_tree; bb=[x for x in nt.nodes if x.type=='BSDF_PRINCIPLED']
        for l in [l for l in nt.links if bb and l.to_socket in (bb[0].inputs['Base Color'],bb[0].inputs['Alpha'])]: nt.links.remove(l)
        if bb: bb[0].inputs['Base Color'].default_value=(0.03,0.03,0.035,1); bb[0].inputs['Roughness'].default_value=0.45; bb[0].inputs['Alpha'].default_value=1.0
rep['head_hair_meshes']=[(o.name,len(o.data.vertices),tris(o),[s_l.material.name for s_l in o.material_slots if s_l.material]) for o in HHM]; log('head hair meshes',rep['head_hair_meshes'])
HAIR_RAW0=None
if HHM:
    _hv=np.vstack([wco(o) for o in HHM]); HAIR_RAW0=(_hv.max(0)-_hv.min(0)).tolist()
rep['head_fbx_bones']=[b.name for b in FA.data.bones]; log('head fbx bones',rep['head_fbx_bones'])
HT=P['HEAD_TEX']
if HT=='auto':
    def med(path,stride=37):
        im=bpy.data.images.load(path,check_existing=True); a=np.empty(im.size[0]*im.size[1]*4,dtype=np.float32); im.pixels.foreach_get(a); a=a.reshape(-1,4)[::stride]
        m=(a[:,3]>0.9)&(a[:,:3].mean(1)>0.35)&(a[:,:3].mean(1)<0.97); return np.median(a[m,:3],0) if m.sum()>100 else None
    bm0=med(BF+'BODY.png'); best=None
    for i in range(1,6):
        m_=med(HD+f'female head textures/{i}.png')
        if m_ is None or bm0 is None: continue
        d_=float(np.abs(m_-bm0).sum()); rep.setdefault('head_tex_dist',{})[f'{i}.png']=round(d_,4)
        if best is None or d_<best[0]: best=(d_,f'{i}.png')
    HT=best[1] if best else '1.png'
rep['head_tex']=HT; log('head texture',HT,rep.get('head_tex_dist'))
for s in FH.material_slots:
    m=s.material
    if not m: continue
    n=m.name.lower()
    if n.startswith('face'): set_tex(m,HD+'female head textures/'+HT,alpha=True); m.blend_method='HASHED'
    elif n.startswith('eyes'): set_tex(m,ZP+'doe 5.png')
    elif n.startswith('effects'):
        m.use_nodes=True; bb_=[x for x in m.node_tree.nodes if x.type=='BSDF_PRINCIPLED']
        if bb_: bb_[0].inputs['Alpha'].default_value=0.0
rep['head_missing_images']=fix_images(); rep['head_materials']=mats_report(FH)
# ---------- 3. attach (run 4). Her Female Head is a front shell (open at the back, no neck of its own; the Neck/Head bones it ships with
#            are where it expects the body's Neck/Head bones). So: her head's own Head bone goes onto Panda's Head bone (that is how the head was
#            authored to sit on a body), ONE uniform scale about that bone, no rotation, no reshape. Scale = proportion rule (Saidie 11:27 "shrunken head"):
#            crown-to-chin = total height / HEAD_K (anime 6.5-7). Panda's neck top then sits inside the jaw shell; its back is covered by the cranium below.
BV=wco(BODY); zt=float(BV[:,2].max()); fz=float(BV[:,2].min())
HV=wco(FH); h_before=float(HV[:,2].max()-HV[:,2].min()); top0=float(HV[:,2].max()); chin0=float(HV[:,2].min())
hb0=FA.matrix_world@FA.data.bones['Head'].head_local; nb0=FA.matrix_world@FA.data.bones['Neck'].head_local if 'Neck' in FA.data.bones else None
pbH=B.matrix_world@B.data.bones['Head'].head_local; pbN=B.matrix_world@B.data.bones['Neck'].head_local if 'Neck' in B.data.bones else None
h0=top0-chin0; a0=top0-hb0.z; K=P.get('HEAD_K',6.75)
s_=(pbH.z-fz)/(K*h0-a0) if K*h0>a0 else 1.4
if P.get('HEAD_SCALE'): s_=float(P['HEAD_SCALE'])
s_=min(max(s_,1.0),2.0)
M_=Matrix.Translation(pbH)@Matrix.Scale(s_,4)@Matrix.Translation(-hb0)
HEAD_RAW_DIMS=(wco(FH).max(0)-wco(FH).min(0)).tolist()
apply_tf([FA,FH]+HHM,M_)
ALIGN={'head_bone_vs_panda_head_mm':round(float(((FA.matrix_world@FA.data.bones['Head'].head_local)-pbH).length)*1000,2)}
HV=wco(FH); hmn=HV.min(0); hmx=HV.max(0)
def _dir(a,b):
    if a is None or b is None: return None
    d=(b-a).normalized(); return [round(x,4) for x in d]
rep['attach']={'mode':'her Head bone -> Panda Head bone, uniform scale, no rotation','head_scale_factor':s_,'HEAD_K':K,'head_bone_native':list(hb0),'panda_head_bone':list(pbH),
               'head_neck_to_head_dir':_dir(nb0,hb0),'panda_neck_to_head_dir':_dir(pbN,pbH),'rotation_applied_deg':0.0,
               'head_h_before':h_before,'head_h_after':float(hmx[2]-hmn[2]),'head_w_after':float(hmx[0]-hmn[0]),'chin_z':float(hmn[2]),'crown_z':float(hmx[2]),'body_neck_top_z':zt,
               'total_height':float(hmx[2]-fz),'height_over_head':float((hmx[2]-fz)/(hmx[2]-hmn[2]))}
# neck check: Panda's open neck ring vs her head shell (front of the ring must be above the jaw underside, back covered by the cranium)
from collections import Counter
def boundary(o):
    cnt=Counter(ek for p in o.data.polygons for ek in p.edge_keys)
    return set(v for ek,c in cnt.items() if c==1 for v in ek)
bnd_b=boundary(BODY); RING=np.array([BV[i] for i in bnd_b if BV[i,2]>zt-0.08 and abs(BV[i,0])<0.09]) if bnd_b else np.zeros((0,3))
rim_y=float(hmx[1])
rep['attach']['neck_ring']={'verts':len(RING),'z_min':float(RING[:,2].min()) if len(RING) else None,'z_max':float(RING[:,2].max()) if len(RING) else None,
                            'y_min':float(RING[:,1].min()) if len(RING) else None,'y_max':float(RING[:,1].max()) if len(RING) else None,'head_shell_back_y':rim_y}
log('ATTACH',rep['attach'])
# ---------- 4. her hair (as authored, its own texture; only uniformly scaled + placed onto the head), with its own bone chains
def hair_import():
    if P['HAIR']=='head':
        if len(HHM)>1: sel(HHM,HHM[0]); bpy.ops.object.join()
        HR=HHM[0]; HR.name='Hair'; return HR,None,[]
    if P['HAIR']=='umeko':
        new=imp_fbx(IN+'/assets/hair_umeko_gift.fbx'); tex=(IN+'/assets/hair_texture_black_to_white_1713.jpg',False)
    else:
        new=imp_fbx(IN+"/Blowout Nikkie's haircards.fbx"); tex=(IN+'/Textures/B&W.png',True)
    HM=[o for o in new if o.type=='MESH']; HA=[o for o in new if o.type=='ARMATURE']
    for o in HM:
        for s in o.material_slots:
            if s.material:
                set_tex(s.material,tex[0],alpha=tex[1])
                if tex[1]: s.material.blend_method='HASHED'
    HE=[o for o in new if o.type=='EMPTY']
    if len(HM)>1: sel(HM,HM[0]); bpy.ops.object.join()
    HR=HM[0]; HR.name='Hair'
    return HR,(HA[0] if HA else None),HE
HR,HA,HE=hair_import(); rep['hair_bones']=[b.name for b in HA.data.bones] if HA else []
log('hair',P['HAIR'],tris(HR),'bones',len(rep['hair_bones']),'groups',len(HR.vertex_groups))
if P['HAIR']=='head':
    s=s_; HAIR_RAW_DIMS=HAIR_RAW0; rep['hair_align']='head asset own hair: rides the head transform (her Head bone -> Panda Head bone, uniform %.4fx), no offsets'%s_
    rep['hair_offsets_m']={'none':True}; ALIGN['hair_head_bone_vs_head_bone_mm']=0.0; rep['hair_fit']={'hair':'head','scale':s}; log('hair fit (head own hair)',s)
else:
    UV_=wco(HR); umn=UV_.min(0); umx=UV_.max(0)
    s=(hmx[0]-hmn[0])*P['HAIR_W_RATIO']/(umx[0]-umn[0])
    kh_=s_/1.025   # run-3 offsets were in metres at head scale 1.025; keep them relative to her head at the new scale
    pivot=Vector(((umn[0]+umx[0])/2,(umn[1]+umx[1])/2,umx[2])); target=Vector(((hmn[0]+hmx[0])/2,hmn[1]+P['HAIR_DEPTH_K']*(hmx[0]-hmn[0])/2+P['HAIR_DY']*kh_,hmx[2]+(P['HAIR_TOP_GAP']+P['HAIR_DZ'])*kh_))
    rep['hair_offsets_m']={'DY':P['HAIR_DY']*kh_,'DZ_plus_gap':(P['HAIR_TOP_GAP']+P['HAIR_DZ'])*kh_,'W_RATIO':P['HAIR_W_RATIO']}
    Mh=Matrix.Translation(target)@Matrix.Scale(s,4)@Matrix.Translation(-pivot); how='bbox'
    # preferred: the hair's own Head bone onto her head's own Head bone (how the hair was authored to sit on a head), same uniform scale
    try:
        if P.get('HAIR_ALIGN','bone')=='bone' and HA and 'Head' in HA.data.bones and 'Head' in FA.data.bones:
            hb=HA.matrix_world@HA.data.bones['Head'].head_local; tb=FA.matrix_world@FA.data.bones['Head'].head_local
            Mb=Matrix.Translation(tb+Vector((0,P['HAIR_DY'],P['HAIR_DZ_BONE'] if 'HAIR_DZ_BONE' in P else 0.0)))@Matrix.Scale(s,4)@Matrix.Translation(-hb)
            topb=(Mb@Vector((0,0,umx[2]))).z; ctr_b=Mb@Vector(((umn[0]+umx[0])/2,(umn[1]+umx[1])/2,umx[2])); ctr_x=Mh@pivot
            rep['hair_align_compare']={'bone_top_minus_head_top':topb-float(hmx[2]),'bone_vs_bbox_offset':list(ctr_b-ctr_x),'hair_head_bone':list(hb),'head_head_bone':list(tb)}
            log('hair align compare',rep['hair_align_compare'])
            if -0.01 < topb-float(hmx[2]) < 0.05 and (ctr_b-ctr_x).length<0.05: Mh=Mb; how='bone'
    except Exception as e: traceback.print_exc(); log('HAIRALIGNERR',e)
    if P.get('HAIR_ALIGN')=='bone_strict':
        # run 5 (RUN4-FINDINGS): the hair's own Head bone onto her head's own Head bone, ONE uniform scale (= the head's, or HAIR_SCALE), no offsets, no push
        hb=HA.matrix_world@HA.data.bones['Head'].head_local; tb=FA.matrix_world@FA.data.bones['Head'].head_local
        s=float(P.get('HAIR_SCALE') or s_)
        Mh=Matrix.Translation(tb)@Matrix.Scale(s,4)@Matrix.Translation(-hb); how=f'bone_strict: hair Head bone -> her Head bone, uniform {s:.4f}x, no offsets'
        rep['hair_offsets_m']={'none':True}; rep['hair_bone_native']=list(hb); rep['head_bone_target']=list(tb)
    rep['hair_align']=how; log('hair align',how)
    HAIR_RAW_DIMS=(umx-umn).tolist()
    apply_tf([x for x in (HA,HR) if x],Mh)
    try: ALIGN['hair_head_bone_vs_head_bone_mm']=round(float(((HA.matrix_world@HA.data.bones['Head'].head_local)-(FA.matrix_world@FA.data.bones['Head'].head_local)).length)*1000,2)
    except Exception as e: ALIGN['hair_head_bone_vs_head_bone_mm']=str(e)
    for e_ in HE: bpy.data.objects.remove(e_)
    rep['hair_fit']={'hair':P['HAIR'],'scale':s}; log('hair fit',s)
CR=None
if P['CRANIUM']:
    import bmesh
    cx=(hmn[0]+hmx[0])/2; hw=(hmx[0]-hmn[0])/2; zc=hmn[2]+0.62*(hmx[2]-hmn[2]); cy=hmn[1]+1.05*hw
    bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=32,v_segments=16,radius=1.0)
    ru=(hmx[2]-zc)*0.97; rl=ru
    # run 4: reach down behind her head shell far enough to cover the back of Panda's open neck top (the 'stump' seen behind the jaw in run 3)
    back=RING[RING[:,1]>rim_y-0.004] if len(RING) else RING
    if len(back): rl=max(ru,zc-(float(back[:,2].min())-P.get('CRAN_BELOW',0.012)))
    rep['cranium']={'upper_r':ru,'lower_r':rl,'bottom_z':zc-rl,'ring_back_verts':int(len(back))}; log('cranium',rep['cranium'])
    for v in bm.verts: v.co=Vector((cx+v.co.x*hw*0.93, cy+v.co.y*hw*1.02, zc+v.co.z*(ru if v.co.z>0 else rl)))
    dv=[v for v in bm.verts if v.co.y < hmn[1]+0.55*hw]; bmesh.ops.delete(bm,geom=dv,context='VERTS')
    me=bpy.data.meshes.new('Cranium'); bm.to_mesh(me); bm.free(); CR=bpy.data.objects.new('Cranium',me); sc.collection.objects.link(CR)
    cm=bpy.data.materials.new('ScalpDark'); cm.use_nodes=True; cb=cm.node_tree.nodes['Principled BSDF']; cb.inputs['Base Color'].default_value=(0.012,0.012,0.014,1); cb.inputs['Roughness'].default_value=0.6; me.materials.append(cm)
# ---------- 5. her clothes (made for / sitting on Panda as shipped; no reshape)
new=imp_fbx(IN+'/Outfitriggedpanda.fbx'); BRA=[o for o in new if o.name=='Bra'][0]; SHIRT=[o for o in new if o.type=='MESH' and o.name!='Bra']
SHIRT=SHIRT[0] if SHIRT else None
OA=[o for o in new if o.type=='ARMATURE']; OA=OA[0] if OA else None
OHEAD={b.name:(OA.matrix_world@b.head_local).copy() for b in OA.data.bones} if OA else {}
rep['outfit_armature']={'name':OA.name if OA else None,'bones':len(OHEAD)}
SHIRT_GROUPS0=[g.name for g in SHIRT.vertex_groups] if SHIRT is not None else []
rep['shirt_original_groups']=SHIRT_GROUPS0; log('outfit armature',rep['outfit_armature'],'shirt groups',SHIRT_GROUPS0)
rep['shirt_material_before']=mats_report(SHIRT) if SHIRT is not None else None
LAYER_OBJS.update({'Bra'}|({'Shirt'} if SHIRT is not None else set()))
for o in new:
    if o is not BRA and o is not SHIRT: bpy.data.objects.remove(o)
if SHIRT is not None:
    for s_l in SHIRT.material_slots:
        if s_l.material:
            set_tex(s_l.material,IN+'/'+P.get('SHIRT_TEX','Tshirt-BasicGrey.png'))
            # run 8: backfaces of the shirt render transparent (as Unity/VRChat cull them), so the dark inner shell can never show through the outer one
            if P.get('SHIRT_BACKFACE_CULL',True):
                try:
                    m=s_l.material; m.use_backface_culling=True; nt=m.node_tree; out_=[n for n in nt.nodes if n.type=='OUTPUT_MATERIAL'][0]; lk=[l for l in nt.links if l.to_socket==out_.inputs['Surface']]
                    if lk:
                        src=lk[0].from_socket; nt.links.remove(lk[0]); g_=nt.nodes.new('ShaderNodeNewGeometry'); tr_=nt.nodes.new('ShaderNodeBsdfTransparent'); mx_=nt.nodes.new('ShaderNodeMixShader')
                        nt.links.new(g_.outputs['Backfacing'],mx_.inputs[0]); nt.links.new(src,mx_.inputs[1]); nt.links.new(tr_.outputs[0],mx_.inputs[2]); nt.links.new(mx_.outputs[0],out_.inputs['Surface'])
                except Exception as e: log('BACKFACEERR',e)
    rep['shirt_texture']=P.get('SHIRT_TEX','Tshirt-BasicGrey.png')
    SHIRT.name='Shirt'
bm_=bpy.data.materials.new('BraBlack'); bm_.use_nodes=True; bb2=bm_.node_tree.nodes['Principled BSDF']; bb2.inputs['Base Color'].default_value=(*P['BRA_COL'],1); bb2.inputs['Roughness'].default_value=P['BRA_ROUGH']
BRA.data.materials.clear(); BRA.data.materials.append(bm_)
new=imp_fbx(IN+'/Booty Shorts by Beanie.fbx'); SH=[o for o in new if o.type=='MESH'][0]; SH.name='Shorts'
for o in new:
    if o is not SH: bpy.data.objects.remove(o)
for s_l in SH.material_slots:
    if s_l.material: set_tex(s_l.material,IN+'/Textures/Colors/'+P['SHORTS_TEX'])
rep['cloth_missing_images']=fix_images()
CLOTH=[x for x in (SHIRT,BRA,SH) if x]
for o in CLOTH:
    o.parent=None if o.parent is None or o.parent.type!='ARMATURE' else o.parent
    mw=o.matrix_world.copy(); o.parent=None; o.matrix_world=mw
    for md in list(o.modifiers):
        if md.type=='ARMATURE': o.modifiers.remove(md)
    sel([o]); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
for o in list(bpy.data.objects):
    if o.type in ('ARMATURE','EMPTY') and o not in (B,FA,HA): bpy.data.objects.remove(o)
if not P['SHIRT'] and SHIRT is not None: bpy.data.objects.remove(SHIRT); SHIRT=None; CLOTH=[x for x in (BRA,SH)]

# ---------- run 7 (RUN6B-FINDINGS fix 1): record her shirt's/bra's coincident seam vertices and double-layer shell twins BEFORE any retarget or push,
#            so that afterwards each group is snapped back together (shared midpoint, same displacement for both shell layers). No reshaping: the
#            groups keep exactly the relative offsets they had in her original mesh.
WELD={}
def weld_record(o,r_co=0.0001,r_shell=0.0025):
    me=o.data; n=len(me.vertices); X=wco(o); NRM=np.array([tuple(o.matrix_world.to_3x3()@v.normal) for v in me.vertices])
    kd=KDTree(n)
    for i,p in enumerate(X): kd.insert(Vector(tuple(p)),i)
    kd.balance(); par=list(range(n))
    def f(a):
        while par[a]!=a: par[a]=par[par[a]]; a=par[a]
        return a
    def un(a,b):
        a,b=f(a),f(b)
        if a!=b: par[a]=b
    nco=0
    for i,p in enumerate(X):
        for _,j,_ in kd.find_range(Vector(tuple(p)),max(r_co,0.0006)):
            if j>i: un(i,j); nco+=1
    pick=-np.ones(n,dtype=np.int64)
    for i,p in enumerate(X):
        best=None
        for _,j,d in kd.find_n(Vector(tuple(p)),8):
            if j==i or d<0.0006 or d>r_shell: continue
            dv=(X[j]-X[i])/max(d,1e-9)
            if abs(float(dv@NRM[i]))>0.7 and abs(float(NRM[i]@NRM[j]))>0.5: best=j; break
        if best is not None: pick[i]=best
    nsh=0
    for i in range(n):
        j=pick[i]
        if j>=0 and pick[j]==i and j>i: un(i,j); nsh+=1
    G={}
    for i in range(n): G.setdefault(f(i),[]).append(i)
    groups=[np.array(g) for g in G.values() if len(g)>1]
    big=max((len(g) for g in groups),default=0)
    WELD[o.name]={'X0':X.copy(),'groups':groups}
    E=np.array([tuple(e.vertices) for e in me.edges],dtype=np.int64)
    WELD[o.name]['E']=E
    r={'verts':n,'coincident_pairs':nco,'shell_pairs':nsh,'groups':len(groups),'verts_in_groups':int(sum(len(g) for g in groups)),'largest_group':big}
    rep.setdefault('weld',{})[o.name]={'recorded':r}; log('WELD record',o.name,r); return r
def weld_gap(o):
    if o.name not in WELD: return None
    X=wco(o); g=WELD[o.name]['groups']; X0=WELD[o.name]['X0']; mx=0.0; bad=0
    for gg in g:
        rel=X[gg]-X0[gg]; s=float(np.linalg.norm(rel-rel.mean(0),axis=1).max())
        mx=max(mx,s); bad+=int(s>0.0005)
    return {'max_group_split_mm':round(mx*1000,2),'groups_split_gt_0p5mm':bad}
def set_world(o,Xn):
    """write new world positions; the same per-vertex delta goes onto every shape key (her keys keep their deltas)"""
    X=wco(o); Dl=(np.asarray(Xn)-X)@np.array(o.matrix_world.inverted().to_3x3()).T; n=len(X)
    if o.data.shape_keys:
        for kb in o.data.shape_keys.key_blocks:
            a=np.empty(n*3); kb.data.foreach_get('co',a); kb.data.foreach_set('co',(a.reshape(-1,3)+Dl).ravel())
    a=np.empty(n*3); o.data.vertices.foreach_get('co',a); o.data.vertices.foreach_set('co',(a.reshape(-1,3)+Dl).ravel())
    o.data.update(); bpy.context.view_layer.update()
def weld_snap(o,tag=''):
    if o.name not in WELD or not P.get('WELD',True): return None
    before=weld_gap(o); X=wco(o); X0=WELD[o.name]['X0']; Xn=X.copy()
    for gg in WELD[o.name]['groups']:
        d=(X[gg]-X0[gg]).mean(0); Xn[gg]=X0[gg]+d
    if P.get('WELD_SMOOTH',False):
        Dd=Xn-X; ing=np.zeros(len(X),bool)
        for gg in WELD[o.name]['groups']: ing[gg]=True
        E_=WELD[o.name]['E']; Ds=Dd.copy(); deg_=np.zeros(len(X)); np.add.at(deg_,E_[:,0],1); np.add.at(deg_,E_[:,1],1); deg_=np.maximum(deg_,1)
        for _ in range(int(P.get('WELD_SMOOTH_ITERS',12))):
            A_=np.zeros_like(Ds); np.add.at(A_,E_[:,0],Ds[E_[:,1]]); np.add.at(A_,E_[:,1],Ds[E_[:,0]]); A_/=deg_[:,None]
            Ds=np.where(ing[:,None],Dd,0.5*Ds+0.5*A_)
        Xn=X+Ds
    set_world(o,Xn); after=weld_gap(o)
    r={'before':before,'after':after,'max_vertex_move_mm':round(float(np.linalg.norm(Xn-X,axis=1).max())*1000,2)}
    rep['weld'][o.name]['snap'+tag]=r; log('WELD snap',o.name,tag,r); return r
def group_max(o,D):
    if o.name not in WELD: return D
    nrm=np.linalg.norm(D,axis=1); out=D.copy()
    for gg in WELD[o.name]['groups']:
        j=gg[int(np.argmax(nrm[gg]))]; out[gg]=D[j]
    return out
def smooth_field(o,D,iters=25,cap=None):
    """Laplacian falloff of a push field: every required push is kept (projection), its neighbours ease in, so no edge is torn by a step change"""
    E=WELD[o.name]['E'] if o.name in WELD else np.array([tuple(e.vertices) for e in o.data.edges],dtype=np.int64); n=len(D)
    deg=np.zeros(n); np.add.at(deg,E[:,0],1); np.add.at(deg,E[:,1],1); deg[deg==0]=1
    need=np.linalg.norm(D,axis=1)
    if cap is not None: need=np.minimum(need,cap)
    U=np.zeros_like(D); m=need>1e-7; U[m]=D[m]/np.linalg.norm(D[m],axis=1)[:,None]; D=U*need[:,None]
    for _ in range(iters):
        A=np.zeros_like(D); np.add.at(A,E[:,0],D[E[:,1]]); np.add.at(A,E[:,1],D[E[:,0]]); A/=deg[:,None]
        D=0.5*D+0.5*A
        pr=(D*U).sum(1); df=need-pr; k=m&(df>0); D[k]+=df[k][:,None]*U[k]
    return D
try:
    for o_ in (SHIRT,BRA):
        if o_ is not None: weld_record(o_)
except Exception as e: traceback.print_exc(); log('WELDRECERR',e)

# ---------- run 6 measure: SOLO snapshots (each asset as imported, with only the transform it was given) for the measure system
def tri_arr(o,evaluated=True):
    dg=bpy.context.evaluated_depsgraph_get(); e=o.evaluated_get(dg) if evaluated else o; me=e.to_mesh(); me.calc_loop_triangles(); mw=o.matrix_world
    V=np.array([tuple(mw@v.co) for v in me.vertices],dtype=np.float32); F=np.array([tuple(t.vertices) for t in me.loop_triangles],dtype=np.int32)
    MI=np.array([t.material_index for t in me.loop_triangles],dtype=np.int16); e.to_mesh_clear(); return V,F,MI
SOLO={}
try:
    for nm_,o_,sc_,rawd in (('body',BODY,1.0,None),('head',FH,s_,HEAD_RAW_DIMS),('hair',HR,float(rep['hair_fit']['scale']),HAIR_RAW_DIMS),('bra',BRA,1.0,None),('shorts',SH,1.0,None))+((('shirt',SHIRT,1.0,None),) if SHIRT is not None else ()):
        V_,F_,MI_=tri_arr(o_,evaluated=False); SOLO[nm_]={'V':V_,'F':F_,'MI':MI_,'scale':sc_,'raw_dims':rawd if rawd is not None else (V_.max(0)-V_.min(0)).tolist()}
except Exception as e: traceback.print_exc(); log('SOLOERR',e)

# ---------- run 6: her outfit (shirt + bra) on its OWN Panda weights. Measured offline on her FBXs: the outfit was authored in an A-pose (upper arm ~40 deg
#            down) while Panda's rest is a T-pose, so the sleeves hung below the arms and data-transfer weights gave sleeve verts chest weights (the flare
#            and streaks of runs 4-5). Fix: each arm-chain bone of the outfit armature (shoulder/arm/elbow/wrist, joint-to-joint direction) is mapped onto the
#            matching Panda rest bone (rotation + head translation); every vertex moves by the blend of those bone deltas with ITS OWN outfit weights
#            (= posing the outfit armature into Panda's rest and applying it). Torso bones stay put. Then her weights are kept (names mapped).
def nmap(n):
    n2=n.replace('_001','')
    for suf in ('_L','_R'):
        if n2.endswith(suf) and n2[:-2] in ('Ass_Wiggle','Twist_Butt','Wrist_Twist','Twist_Leg','Twist_Ankle'): n2=n2[:-2]+'.'+suf[1]
    return n2
RET={}
def outfit_deltas():
    PHd={b.name:(B.matrix_world@b.head_local) for b in B.data.bones}
    OH={nmap(k):v for k,v in OHEAD.items()}
    CH={}
    for sd,s1 in (('Left','L'),('Right','R')):
        CH[sd+' shoulder']=sd+' arm'; CH[sd+' arm']=sd+' elbow'; CH[sd+' elbow']=sd+' wrist'; CH[sd+' wrist']='MiddleFinger1_'+s1
    DEL={}; ang={}
    for b,c in CH.items():
        if not all(k in OH for k in (b,c)) or not all(k in PHd for k in (b,c)):
            if b.endswith('wrist') and b.replace('wrist','elbow') in DEL: DEL[b]=DEL[b.replace('wrist','elbow')]; ang[b]='= elbow'
            continue
        do=(OH[c]-OH[b]); dp=(PHd[c]-PHd[b])
        if do.length<1e-5 or dp.length<1e-5: continue
        q=do.normalized().rotation_difference(dp.normalized()); a=math.degrees(q.angle)
        DEL[b]=Matrix.Translation(PHd[b])@q.to_matrix().to_4x4()@Matrix.Translation(-OH[b]); ang[b]=round(a,1)
    for sd,s1 in (('Left','L'),('Right','R')):
        if sd+' elbow' in DEL: DEL['Wrist_Twist.'+s1]=DEL[sd+' elbow']
    return DEL,ang
def retarget_mesh(o,DEL):
    gi={g.index:nmap(g.name) for g in o.vertex_groups}; mw=o.matrix_world; mwi=mw.inverted(); moved=[]; n0=0
    Dn={k:np.array(v) for k,v in DEL.items()}; I4=np.eye(4)
    for v in o.data.vertices:
        ws=[(gi[ge.group],ge.weight) for ge in v.groups if ge.weight>0]; tot=sum(w for _,w in ws)
        if tot<=0: n0+=1; continue
        M=np.zeros((4,4))
        for nme,w in ws: M+=(w/tot)*Dn.get(nme,I4)
        p=mw@v.co; q=M@np.array([p.x,p.y,p.z,1.0]); nq=Vector(tuple(q[:3]))
        moved.append((nq-p).length); v.co=mwi@nq
    o.data.update(); mv=np.array(moved) if moved else np.zeros(1)
    return {'verts':len(o.data.vertices),'unweighted':n0,'moved_gt_1mm':int((mv>0.001).sum()),'max_move_mm':round(float(mv.max())*1000,1)}
def map_groups(o):
    bnames=set(b.name for b in B.data.bones); PHd={b.name:(B.matrix_world@b.head_local) for b in B.data.bones}; log_={}
    for g in list(o.vertex_groups):
        t=nmap(g.name)
        if t not in bnames:
            oh=OHEAD.get(g.name)
            t=min(bnames,key=lambda b:(PHd[b]-oh).length) if oh is not None else 'Hips'
        log_[g.name]=t
        if t==g.name: continue
        tg=o.vertex_groups.get(t)
        if tg is None: g.name=t; continue
        for v in o.data.vertices:
            for ge in v.groups:
                if ge.group==g.index and ge.weight>0: tg.add([v.index],ge.weight,'ADD')
        o.vertex_groups.remove(g)
    return log_
# ---------- run 8c: tears at the armholes start in the retarget: coincident seam verts / shell twins of her shirt carry DIFFERENT weights (322 groups tore by up
#            to 48 mm, then the weld snapped single verts back = folds). Before the retarget, her own weights are harmonized: every weld group shares one
#            (mean) weight set, and the band + sleeve-top seam zone (verts near shoulder/arm weights) gets one spatially averaged set (20 mm, Gaussian 8 mm).
def pre_harmonize(o):
    if o.name not in WELD: return
    gl=[g for g in o.vertex_groups]; names=[g.name for g in gl]; G=len(gl); n=len(o.data.vertices); Wm=np.zeros((n,G))
    for v in o.data.vertices:
        for ge in v.groups: Wm[v.index,ge.group]=ge.weight
    s=Wm.sum(1); s[s==0]=1; Wm/=s[:,None]; W0=Wm.copy()
    for gg in WELD[o.name]['groups']: Wm[gg]=Wm[gg].mean(0)
    armg=[k for k,nm_ in enumerate(names) if any(t in nmap(nm_).lower() for t in ('shoulder','arm','elbow'))]
    X=wco(o); kd=KDTree(n)
    for i,p in enumerate(X): kd.insert(Vector(tuple(p)),i)
    kd.balance(); R=float(P.get('SEAM_R',0.02)); sig=float(P.get('SEAM_SIG',0.008))
    core=np.where(Wm[:,armg].sum(1)>0.02)[0] if armg else np.zeros(0,dtype=np.int64); zone=np.zeros(n,bool)
    for i in core:
        if zone[i]: continue
        for _,j,_ in kd.find_range(Vector(tuple(X[i])),R): zone[j]=True
    zi=np.where(zone)[0]
    for it in range(2):
        Wn=Wm.copy()
        for i in zi:
            hits=kd.find_range(Vector(tuple(X[i])),R); j=np.array([h[1] for h in hits],dtype=np.int64); w=np.exp(-np.array([h[2] for h in hits])**2/(2*sig*sig))
            Wn[i]=(Wm[j]*w[:,None]).sum(0)/w.sum()
        Wm=Wn
        for gg in WELD[o.name]['groups']: Wm[gg]=Wm[gg].mean(0)
    allidx=list(range(n))
    for k,g in enumerate(gl):
        g.remove(allidx)
        col=Wm[:,k]; nz=np.where(col>0.0005)[0]
        for i in nz: g.add([int(i)],float(col[i]),'REPLACE')
    o.data.update()
    r={'groups':len(WELD[o.name]['groups']),'arm_groups':[names[k] for k in armg],'zone_verts':int(len(zi)),'max_L1_change':round(float(np.abs(Wm-W0).sum(1).max()),3),'verts_changed_gt_0p05':int((np.abs(Wm-W0).sum(1)>0.05).sum())}
    rep.setdefault('pre_harmonize',{})[o.name]=r; log('PRE harmonize',o.name,r)
ORIG_W=set()
NECKR=None
if P.get('SHIRT_RETARGET',True) and OHEAD:
    try:
        DEL,ang=outfit_deltas(); RET['bone_angles_deg']=ang; RET['bones']=sorted(DEL)
        okang=isinstance(ang.get('Left arm'),float) and 10<ang['Left arm']<75
        RET['sanity_left_arm_angle_ok']=okang
        if okang:
            # run 6b: her bra's halter ring is weighted to the outfit's Neck bone, which sits 3.6 cm lower and 3.9 cm further forward than Panda's.
            # Without moving it with that bone the ring lands INSIDE Panda's neck and the fit pushed it out the FRONT (a choker, not her loop).
            # So the bra also gets the Neck bone's head offset (translation only) - the same 'pose the outfit armature onto Panda' step.
            OHn={nmap(k):v for k,v in OHEAD.items()}; PHn=B.matrix_world@B.data.bones['Neck'].head_local if 'Neck' in B.data.bones else None
            DELB=dict(DEL)
            NECKR=None
            if 'Neck' in OHn and PHn is not None:
                RET['bra_neck_offset_m']=[round(x,4) for x in (PHn-OHn['Neck'])]
                if P.get('BRA_NECK')=='rigid' and BRA is not None:
                    # run 7 (fix 4): the whole halter loop rides the outfit Neck -> Panda Neck offset as ONE rigid translation (full above the cups,
                    # smooth 4 cm blend into the cups), instead of a partial per-weight move + vertex pushes (the run-6b zig-zag). Her loop keeps its shape/width.
                    Xb_=wco(BRA); zc_=max(float(np.percentile(Xb_[:,2],60)),float(OHn['Neck'].z)-0.10); t_=np.clip((Xb_[:,2]-zc_)/0.04,0,1)
                    NECKR={'off':np.array(tuple(PHn-OHn['Neck'])),'f':t_*t_*(3-2*t_),'zc':zc_,'X0':Xb_}
                else: DELB['Neck']=Matrix.Translation(PHn-OHn['Neck'])
            for o,DD in ((SHIRT,DEL),(BRA,DELB)):
                if o is None or not o.vertex_groups: continue
                if P.get('PRE_HARMONIZE',False) and o is SHIRT:
                    try: pre_harmonize(o)
                    except Exception as e: traceback.print_exc(); log('PREHARMERR',e); rep['pre_harmonize_error']=str(e)
                RET[o.name]=retarget_mesh(o,DD); RET[o.name+'_group_map']=map_groups(o); ORIG_W.add(o.name)
            if NECKR is not None:
                try:
                    f_=NECKR['f']; Xr_=wco(BRA); Xn_=Xr_*(1-f_)[:,None]+(NECKR['X0']+NECKR['off'])*f_[:,None]; set_world(BRA,Xn_)
                    RET['bra_neck_rigid']={'zc':round(NECKR['zc'],4),'verts_full_rigid':int((f_>0.999).sum()),'verts_blend':int(((f_>0.001)&(f_<=0.999)).sum()),'offset_m':[round(float(x),4) for x in NECKR['off']]}
                except Exception as e: traceback.print_exc(); log('NECKRIGIDERR',e); RET['bra_neck_rigid_error']=str(e)
        log('outfit retarget',RET)
    except Exception as e: traceback.print_exc(); log('RETARGETERR',e); RET['error']=str(e)
rep['outfit_retarget']=RET
try:
    for o_ in (SHIRT,BRA):
        if o_ is not None and o_.name in WELD: WELD[o_.name]['XR']=wco(o_)
except Exception as e: traceback.print_exc(); log('XRERR',e)
# clothes FIT (brief: "fit clothes"): where her Panda body pokes through a garment, that garment's vertices are pushed out to sit just over the skin
# (smoothed; nothing else moves; her UVs/textures/cut untouched). Layered: bra + shorts over the body, shirt over body + bra + shorts. Max push reported.
from mathutils.bvhtree import BVHTree
def world_bvh(objs):
    dg=bpy.context.evaluated_depsgraph_get(); V=[]; F=[]
    for t in objs:
        e=t.evaluated_get(dg); me=e.to_mesh(); off=len(V)
        V+=[tuple(t.matrix_world@v.co) for v in me.vertices]; F+=[tuple(off+i for i in p.vertices) for p in me.polygons]; e.to_mesh_clear()
    return BVHTree.FromPolygons(V,F)
def fit_out(o,targets,off,deep=0.05,iters=5,only=None,damp=None):
    T=world_bvh(targets); mw=o.matrix_world; n=len(o.data.vertices)
    dg=bpy.context.evaluated_depsgraph_get(); ev=o.evaluated_get(dg)
    X=np.array([tuple(mw@v.co) for v in ev.data.vertices]) if len(ev.data.vertices)==n else np.array([tuple(mw@v.co) for v in o.data.vertices])
    nb=[[] for _ in range(n)]
    for e in o.data.edges: a,b=e.vertices; nb[a].append(b); nb[b].append(a)
    def need(X):
        N=np.zeros_like(X)
        for i in range(n):
            loc,nr,idx,d=T.find_nearest(Vector(X[i]),deep)
            if loc is None: continue
            s=(Vector(X[i])-loc).dot(nr)
            if -deep<s<off: N[i]=np.array(nr)*(off-s)
        return N
    N=need(X)
    if only is not None: N[~only(X)]=0
    D=N.copy()
    for _ in range(iters):
        A=np.array([D[nb[i]].mean(0) if nb[i] else D[i] for i in range(n)]); D=0.5*D+0.5*A
        big=np.linalg.norm(N,axis=1)>np.linalg.norm(D,axis=1); D[big]=N[big]
    if damp is not None: D=D*damp[:,None]
    X2=X+D; N2=need(X2)
    if only is not None: N2[~only(X2)]=0
    if damp is not None: N2=N2*damp[:,None]
    X2+=N2
    tot=layer_coherent(o,X2-X); mm=np.linalg.norm(tot,axis=1)*1000
    mwi=mw.inverted()
    Dl=[tuple(mwi.to_3x3()@Vector(d)) for d in tot]
    if o.data.shape_keys:
        for kb in o.data.shape_keys.key_blocks:
            for i in range(n): kb.data[i].co+=Vector(Dl[i])
    for i in range(n): o.data.vertices[i].co+=Vector(Dl[i])
    o.data.update()
    r={'poking_verts':int((np.linalg.norm(N,axis=1)>1e-6).sum()),'moved_verts':int((mm>0.1).sum()),'max_push_mm':round(float(mm.max()),1),'mean_push_mm_moved':round(float(mm[mm>0.1].mean()) if (mm>0.1).any() else 0.0,1),'of_verts':n}
    rep.setdefault('cloth_fit',{})[o.name]=r; log('fit',o.name,r)
BK_={k.name:k.value for k in BODY.data.shape_keys.key_blocks} if BODY.data.shape_keys else {}
rep['body_active_keys']={k:round(v,3) for k,v in BK_.items() if v>0.001}; log('body active shape keys',rep['body_active_keys'],'of',len(BK_))
for o in CLOTH:
    ks=[k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else []
    matched={}
    for kb in (o.data.shape_keys.key_blocks if o.data.shape_keys else []):
        if kb.name in BK_ and BK_[kb.name]>0.001 and kb!=o.data.shape_keys.reference_key: kb.value=BK_[kb.name]; matched[kb.name]=kb.value
    rep.setdefault('cloth_keys',{})[o.name]={'keys':ks[:60],'matched_to_body':matched}; log('cloth keys',o.name,ks[:60],'matched',matched)
bpy.context.view_layer.update()
# ---- run 4 shorts (Saidie 11:27 "her shorts aren't correct size"). Measured offline on her FBXs: at their native transform the shorts float ~28 mm off
#      this Panda body (median) while the back waistband sits up to 30 mm inside it, i.e. they were seated for a differently tilted pelvis. So: a RIGID re-seat
#      (pitch + translation, no scale), her own shape keys (Thicc/Cheeks/Tummy), then a layer-preserving shrinkwrap to HUG_OFF over the skin.
from mathutils.kdtree import KDTree as _KD
def signed(o,T):
    dg=bpy.context.evaluated_depsgraph_get(); ev=o.evaluated_get(dg); mw=o.matrix_world
    X=np.array([tuple(mw@v.co) for v in ev.data.vertices]); S=np.ones(len(X)); N=np.zeros_like(X)
    for i,p in enumerate(X):
        loc,nr,idx,d=T.find_nearest(Vector(p),0.25)
        if loc is None: continue
        S[i]=(Vector(p)-loc).dot(nr); N[i]=tuple(nr)
    return X,S,N
def sstats(S): return {'poke_lt0':int((S<0).sum()),'poke_lt3mm':int((S<-0.003).sum()),'poke_lt10mm':int((S<-0.01).sum()),'min_mm':round(float(S.min())*1000,1),
                       'gap_p25_50_75_90_mm':[round(float(x)*1000,1) for x in np.percentile(S,[25,50,75,90])]}
_LKD={}
def layer_coherent(o,Dw,r=0.0006):
    if o.name not in LAYER_OBJS: return Dw
    if o.name not in _LKD:
        X=wco(o); kd=KDTree(len(X))
        for i,p in enumerate(X): kd.insert(Vector(tuple(p)),i)
        kd.balance(); _LKD[o.name]=[[j for _,j,_ in kd.find_range(Vector(tuple(p)),r)] for p in X]
    G=_LKD[o.name]; Dw=np.asarray(Dw,dtype=float); nrm=np.linalg.norm(Dw,axis=1); out=Dw.copy()
    for i,g in enumerate(G):
        if len(g)>1: j=g[int(np.argmax(nrm[g]))]; out[i]=Dw[j]
    return out
def add_disp(o,Dw):
    Dw=layer_coherent(o,Dw)
    mwi3=o.matrix_world.inverted().to_3x3(); n=len(o.data.vertices); Dl=[mwi3@Vector(tuple(d)) for d in Dw]
    if o.data.shape_keys:
        for kb in o.data.shape_keys.key_blocks:
            for i in range(n): kb.data[i].co+=Dl[i]
    for i in range(n): o.data.vertices[i].co+=Dl[i]
    o.data.update(); bpy.context.view_layer.update()
def hug(o,target,lo=-0.035,hi=0.045,r_layer=0.008,r_smooth=0.010):
    T=world_bvh([BODY]); X,S,N=signed(o,T); n=len(X)
    kd=_KD(n)
    for i,p in enumerate(X): kd.insert(Vector(p),i)
    kd.balance()
    m=np.array([min(S[j] for _,j,_ in kd.find_range(Vector(p),r_layer)) for p in X])   # innermost layer at this spot (keeps waistband/trim thickness)
    Z=(m>lo)&(m<hi); D=N*np.where(Z,target-m,0.0)[:,None]
    zi=np.where(Z)[0]
    if len(zi)==0: return {'zone_verts':0}
    kz=_KD(len(zi))
    for k,i in enumerate(zi): kz.insert(Vector(X[i]),k)
    kz.balance(); D2=np.zeros_like(D)
    for i,p in enumerate(X):
        js=[zi[k] for _,k,_ in kz.find_range(Vector(p),r_smooth)]
        if js: D2[i]=D[js].mean(0)
        else: _,k,_=kz.find(Vector(p)); D2[i]=D[zi[k]]
    add_disp(o,D2); mv=np.linalg.norm(D2,axis=1)*1000
    return {'zone_verts':int(Z.sum()),'move_mm_p50_90_99_max':[round(float(x),1) for x in np.percentile(mv,[50,90,99,100])]}
SF=P.get('SHORTS_FIT','hug'); rep['shorts_fit']={'mode':SF}
try:
    TB=world_bvh([BODY]); _,S0,_=signed(SH,TB); rep['shorts_fit']['native']=sstats(S0)
    kv=P.get('SHORTS_KEYS',{'Thicc':1.0,'Cheeks':1.0,'Tummy':0.0})
    if SH.data.shape_keys:
        for kb in SH.data.shape_keys.key_blocks:
            if kb.name in kv: kb.value=kv[kb.name]
    rep['shorts_fit']['keys']={kb.name:kb.value for kb in SH.data.shape_keys.key_blocks} if SH.data.shape_keys else {}
    bpy.context.view_layer.update(); _,S1,_=signed(SH,TB); rep['shorts_fit']['with_keys']=sstats(S1)
    dy,dz,pitch=P.get('SHORTS_RIGID',(0.0145,0.0133,-10.25))
    c=Vector(tuple(wco(SH).mean(0)))
    Mr=Matrix.Translation(c+Vector((0,dy,dz)))@Matrix.Rotation(math.radians(pitch),4,'X')@Matrix.Translation(-c)
    mw0=SH.matrix_world.copy(); SH.matrix_world=Mr@mw0; bpy.context.view_layer.update(); _,S2,_=signed(SH,TB)
    if float(np.median(np.abs(S2)))<float(np.median(np.abs(S1))):
        sel([SH]); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True); rep['shorts_fit']['rigid']={'dy_m':dy,'dz_m':dz,'pitch_deg':pitch,'scale':1.0,'after':sstats(S2)}
    else:
        SH.matrix_world=mw0; bpy.context.view_layer.update(); rep['shorts_fit']['rigid']={'skipped':'did not improve','would_be':sstats(S2)}
    if SF=='hug': rep['shorts_fit']['hug']=hug(SH,P.get('HUG_OFF',0.0025))
    _,S3,_=signed(SH,TB); rep['shorts_fit']['after_hug']=sstats(S3)
except Exception as e: traceback.print_exc(); log('SHORTSERR',e)
log('shorts fit',rep['shorts_fit'])
def cover_fix(o,unders,off,maxd=0.02,iters=2):
    """shirt faces that dip under a body/shorts vertex (the black patches in run 3): push those faces out over it"""
    out=[]
    nb=[[] for _ in range(len(o.data.vertices))]
    for e in o.data.edges: a_,b_=e.vertices; nb[a_].append(b_); nb[b_].append(a_)
    for it in range(iters):
        dg=bpy.context.evaluated_depsgraph_get(); mw=o.matrix_world; Xs=[tuple(mw@v.co) for v in o.data.vertices]
        Tsh=BVHTree.FromPolygons(Xs,[tuple(p.vertices) for p in o.data.polygons]); n=len(Xs); PU=np.zeros((n,3)); hits=0
        for u in unders:
            ev=u.evaluated_get(dg); me=ev.to_mesh(); mwu=u.matrix_world; r3=mwu.to_3x3()
            for v in me.vertices:
                co=mwu@v.co; nr=(r3@v.normal).normalized()
                loc,fn,fi,d=Tsh.ray_cast(co+nr*0.0002,-nr,maxd)
                if loc is None: continue
                hits+=1; vec=np.array(tuple(nr))*(d+off)
                for vi in o.data.polygons[fi].vertices:
                    if np.dot(vec,vec)>np.dot(PU[vi],PU[vi]): PU[vi]=vec
            ev.to_mesh_clear()
        D=PU.copy()
        for _ in range(3):
            A=np.array([D[nb[i]].mean(0) if nb[i] else D[i] for i in range(n)]); D=0.5*D+0.5*A
            big=np.linalg.norm(PU,axis=1)>np.linalg.norm(D,axis=1); D[big]=PU[big]
        add_disp(o,D); out.append({'under_verts_poking':hits,'shirt_verts_moved':int((np.linalg.norm(D,axis=1)>1e-4).sum()),'max_mm':round(float(np.linalg.norm(D,axis=1).max())*1000,1)})
    rep.setdefault('cloth_fit',{})['Shirt cover fix']=out; log('cover fix',out)

def _bvh_tris(o):
    """world-space BVH of an object's evaluated mesh (triangles) + per-tri face normal"""
    dg=bpy.context.evaluated_depsgraph_get(); e=o.evaluated_get(dg); me=e.to_mesh(); me.calc_loop_triangles(); mw=o.matrix_world
    V=[tuple(mw@v.co) for v in me.vertices]; F=[tuple(t.vertices) for t in me.loop_triangles]; e.to_mesh_clear()
    return BVHTree.FromPolygons(V,F),np.array(V)
def _far_hits(T,org,d,maxd):
    """distance to the FARTHEST surface of T along ray org+t*d, t in (0,maxd] (walks through every layer)"""
    far=None; o_=Vector(org); t0=0.0
    for _ in range(8):
        loc,nr,idx,dist=T.ray_cast(o_,d,maxd-t0)
        if loc is None: break
        t0+=dist; far=t0; o_=loc+d*0.0003; t0+=0.0003
        if t0>=maxd: break
    return far
def shirt_v5(o,unders,off):
    """run 5 shirt fit (Saidie: no black patches at the waist, no shorts/skin through the shirt):
       (a) rigid re-seat (pitch + translation, no scale) only if it reduces body penetration and does not make the shirt stand off;
       (b) every shirt vertex offset OUTWARD ALONG THE BODY NORMAL to clear skin AND the outermost layer of the shorts by `off`;
       (c) face-level check: any body/shorts vertex still outside the shirt (ray along -body normal hits the shirt) pushes that shirt face out along the body normal."""
    r={}; TB=world_bvh([BODY])
    def pen(X):
        S=np.ones(len(X)); N=np.zeros_like(X); L=np.zeros_like(X)
        for i,p in enumerate(X):
            loc,nr,idx,d=TB.find_nearest(Vector(p),0.15)
            if loc is None: continue
            S[i]=(Vector(p)-loc).dot(nr); N[i]=tuple(nr); L[i]=tuple(loc)
        return S,N,L
    X0=wco(o); S0,_,_=pen(X0)
    def score(S):
        m=S>-0.08; P_=np.clip(0.004-S[m],0,None); return float(P_.sum())
    def gap(S): m=(S>-0.08)&(S<0.10); return float(np.median(S[m]))
    r['native']={'pen_score':round(score(S0),3),'verts_under_skin':int(((S0<0)&(S0>-0.08)).sum()),'median_gap_mm':round(gap(S0)*1000,1),'min_mm':round(float(S0[S0>-0.08].min())*1000,1)}
    c=Vector(tuple(X0.mean(0)))
    def tf(dy,dz,pt): return Matrix.Translation(c+Vector((0,dy,dz)))@Matrix.Rotation(math.radians(pt),4,'X')@Matrix.Translation(-c)
    def ev(x):
        M=tf(*x); X=np.array([tuple(M@Vector(p)) for p in X0]); S,_,_=pen(X); return score(S),gap(S)
    if P.get('SHIRT_RESEAT',True):
        best=[0.0,0.0,0.0]; bs,bg=ev(best); g0=bg; steps=[0.008,0.008,3.0]; nev=1
        for rnd in range(4):
            for k in range(3):
                for sg in (1,-1):
                    x=list(best); x[k]+=sg*steps[k]
                    if abs(x[0])>0.03 or abs(x[1])>0.03 or abs(x[2])>12: continue
                    sc_,gp_=ev(x); nev+=1
                    if sc_<bs*0.97 and gp_<g0+0.004: best,bs,bg=x,sc_,gp_
            steps=[v/2 for v in steps]
        r['reseat_search']={'evals':nev,'best_dy_dz_pitch':[round(best[0],4),round(best[1],4),round(best[2],2)],'pen_score':round(bs,3),'median_gap_mm':round(bg*1000,1)}
        if bs<0.6*score(S0):
            o.matrix_world=tf(*best)@o.matrix_world; sel([o]); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True); bpy.context.view_layer.update(); r['reseat']='applied'
        else: r['reseat']='skipped (did not cut body penetration by 40%)'
    TU=[_bvh_tris(u)[0] for u in unders]
    nb=[[] for _ in range(len(o.data.vertices))]
    for e in o.data.edges: a_,b_=e.vertices; nb[a_].append(b_); nb[b_].append(a_)
    def smooth(PU,it=4):
        D=PU.copy()
        for _ in range(it):
            A_=np.array([D[nb[i]].mean(0) if nb[i] else D[i] for i in range(len(D))]); D=0.5*D+0.5*A_
            big=np.linalg.norm(PU,axis=1)>np.linalg.norm(D,axis=1); D[big]=PU[big]
        return D
    # (b) vertex offset along the body normal
    for it in range(2):
        X=wco(o); S,N,L=pen(X); PU=np.zeros_like(X); nsh=0
        for i in range(len(X)):
            if not (-0.08<S[i]<0.07): continue
            need=off
            n_=Vector(tuple(N[i]))
            for T in TU:
                h=_far_hits(T,Vector(tuple(L[i]))-n_*0.01,n_,0.08)
                if h is not None:
                    h-=0.01
                    if -0.01<h<0.03: need=max(need,h+off); nsh+=1
            if S[i]<need: PU[i]=N[i]*(need-S[i])
        D=smooth(PU); add_disp(o,D); mm=np.linalg.norm(D,axis=1)*1000
        r[f'normal_offset_pass{it+1}']={'verts_needing_push':int((np.linalg.norm(PU,axis=1)>1e-5).sum()),'over_shorts_checks':nsh,'max_mm':round(float(mm.max()),1),'mean_moved_mm':round(float(mm[mm>0.1].mean()) if (mm>0.1).any() else 0,1)}
    # (c) face-level: body + shorts vertices still OUTSIDE the shirt
    def outside_count(push=True):
        Xs=wco(o); Tsh=BVHTree.FromPolygons([tuple(p) for p in Xs],[tuple(p.vertices) for p in o.data.polygons]); PU=np.zeros_like(Xs); hits=0
        zlo=float(Xs[:,2].min())-0.005; zhi=float(Xs[:,2].max())
        for u in [BODY]+list(unders):
            Uw=wco(u)
            for p in Uw:
                if not (zlo<p[2]<zhi): continue
                loc,nr,idx,d=TB.find_nearest(Vector(p),0.15)
                if loc is None: continue
                n_=Vector(nr); hl,hn,hf,hd=Tsh.ray_cast(Vector(p)+n_*0.0002,-n_,0.025)
                if hl is None: continue
                hits+=1
                if push:
                    vec=np.array(tuple(n_))*(hd+off)
                    for vi in o.data.polygons[hf].vertices:
                        if np.dot(vec,vec)>np.dot(PU[vi],PU[vi]): PU[vi]=vec
        return hits,PU
    out=[]
    for it in range(3):
        h,PU=outside_count(True)
        if h==0: out.append({'outside_verts':0}); break
        D=smooth(PU,3); add_disp(o,D); out.append({'outside_verts':h,'shirt_verts_moved':int((np.linalg.norm(D,axis=1)>1e-4).sum()),'max_mm':round(float(np.linalg.norm(D,axis=1).max())*1000,1)})
    h,_=outside_count(False); out.append({'final_outside_verts':h})
    r['face_level']=out
    X=wco(o); S,_,_=pen(X); r['final']={'verts_under_skin':int(((S<0)&(S>-0.08)).sum()),'median_gap_mm':round(gap(S)*1000,1)}
    rep.setdefault('cloth_fit',{})['Shirt v5']=r; log('SHIRT v5',r)
def _eval_tris_w(o,mat_ok=None):
    dg=bpy.context.evaluated_depsgraph_get(); e=o.evaluated_get(dg); me=e.to_mesh(); me.calc_loop_triangles(); mw=o.matrix_world
    V=np.array([tuple(mw@v.co) for v in me.vertices]); keep=[t for t in me.loop_triangles if mat_ok is None or mat_ok(t.material_index)]
    F=[tuple(t.vertices) for t in keep]; e.to_mesh_clear()
    return BVHTree.FromPolygons([tuple(v) for v in V],F),V,F,None,None
FH_SOLID0={i for i,s_l in enumerate(FH.material_slots) if s_l.material and not s_l.material.name.lower().startswith('effects')}

# ---------- run 6: bra halter strap (Saidie 12:49 "the bra strap is not correctly put on"). Only the strap ring above the cups: every strap vertex AND every
#            strap face sample (centre + edge midpoints, so straight faces cannot dip under the curved neck between vertices) is moved out along the
#            visible neck surface normal (Panda body + her head shell) to >= STRAP_PUSH clearance. Nothing shortened or tightened; verts already clear do not move.
def strap_push(o,off):
    r={}
    try:
        nz=float((B.matrix_world@B.data.bones['Neck'].head_local).z); X=wco(o)
        cupz=float(np.percentile(X[:,2],60)); zcut=max(cupz,nz-0.10); selv=X[:,2]>zcut; r['zcut']=round(zcut,4); r['strap_verts']=int(selv.sum())
        TF_,VF_,FF_,_,_=_eval_tris_w(FH,lambda mi:mi in FH_SOLID0); TBd=world_bvh([BODY])
        faces=[tuple(p.vertices) for p in o.data.polygons if all(selv[i] for i in p.vertices)]
        def sdist(q):
            best=None
            for T in (TBd,TF_):
                loc,nr,idx,d=T.find_nearest(Vector(q),0.03)
                if loc is None: continue
                if best is None or d<best[0]: best=(d,loc,nr)
            if best is None: return None,None
            return (Vector(q)-best[1]).dot(best[2]),np.array(tuple(best[2]))
        hist=[]
        for it in range(3):
            X=wco(o); PU=np.zeros_like(X); bad=0; mins=[]
            for i in np.where(selv)[0]:
                s0,n0=sdist(X[i])
                if s0 is None: continue
                mins.append(s0)
                if s0<off:
                    v=n0*(off-s0)
                    if v@v>PU[i]@PU[i]: PU[i]=v
            for f in faces:
                Q=[X[list(f)].mean(0)]+[(X[f[k]]+X[f[(k+1)%len(f)]])/2 for k in range(len(f))]
                for q in Q:
                    s0,n0=sdist(q)
                    if s0 is None: continue
                    mins.append(s0)
                    if s0<off*0.75:
                        bad+=1; v=n0*(off*0.75-s0)
                        for vi in f:
                            if v@v>PU[vi]@PU[vi]: PU[vi]=v
            mm=np.linalg.norm(PU,axis=1)*1000
            hist.append({'iter':it,'min_clearance_mm':round(float(min(mins))*1000,2) if mins else None,'face_samples_under':bad,'verts_moved':int((mm>0.05).sum()),'max_move_mm':round(float(mm.max()),2)})
            if (mm>0.05).sum()==0: break
            add_disp(o,PU)
        r['passes']=hist
    except Exception as e: traceback.print_exc(); r['error']=str(e)
    rep['strap_push']=r; log('strap push',r)

def strap_rigid(o,off):
    """run 7: halter clearance by a RIGID move of the whole loop (same smooth mask as the neck offset): translation back/up <= 10/5 mm and a uniform
       scale <= 8 % about Panda's Neck bone. No per-vertex pushes, so the loop keeps her smooth shape and width. Picks the smallest move that clears."""
    r={}
    try:
        f_=NECKR['f']; X=wco(o); ring=np.where(f_>0.5)[0]; r['ring_verts']=int(len(ring))
        TF_,VF_,FF_,_,_=_eval_tris_w(FH,lambda mi:mi in FH_SOLID0); TBd=world_bvh([BODY])
        rs=set(ring.tolist()); faces=[tuple(p.vertices) for p in o.data.polygons if all(i in rs for i in p.vertices)]
        piv=np.array(tuple(B.matrix_world@B.data.bones['Neck'].head_local))
        def sd(q):
            best=None
            for T in (TBd,TF_):
                loc,nr,idx,d=T.find_nearest(Vector(tuple(q)),0.03)
                if loc is None: continue
                if best is None or d<best[0]: best=(d,(Vector(tuple(q))-loc).dot(nr))
            return None if best is None else best[1]
        def Xof(dy,dz,s):
            T=piv+(X-piv)*s+np.array((0,dy,dz)); return X+(T-X)*f_[:,None]
        def minclr(Xc):
            m=1.0
            for i in ring:
                v=sd(Xc[i]); m=min(m,v) if v is not None else m
            for fc in faces:
                q=Xc[list(fc)].mean(0); v=sd(q); m=min(m,v) if v is not None else m
            return m
        base=minclr(X); r['before_min_clearance_mm']=round(base*1000,2); cand=[]
        if base<off:
            for s in tuple(x for x in (1.0,1.02,1.04,1.06,1.08) if x<=float(P.get('STRAP_SCALE_MAX',1.04))+1e-9):
                for dy in (0.0,0.0025,0.005,0.0075,0.01):
                    for dz in (0.0,0.0025,0.005):
                        if s==1.0 and dy==0 and dz==0: continue
                        m=minclr(Xof(dy,dz,s)); cost=dy+dz+0.25*(s-1.0); cand.append((m>=off,-cost if m>=off else m,dy,dz,s,m))
            ok=[c for c in cand if c[0]]
            pick=max(ok,key=lambda c:c[1]) if ok else max(cand,key=lambda c:c[1])
            _,_,dy,dz,s,m=pick; set_world(o,Xof(dy,dz,s)); r.update({'move_back_mm':dy*1000,'move_up_mm':dz*1000,'uniform_scale':s,'after_min_clearance_mm':round(m*1000,2),'cleared':bool(ok),'evals':len(cand)})
        else: r['after_min_clearance_mm']=r['before_min_clearance_mm']; r['cleared']=True
        if not r.get('cleared') and P.get('STRAP_SMOOTH_PUSH',True):
            # run 7b: residual = ONE smooth bulge along the loop (group-coherent, Laplacian falloff over the strap), never per-vertex spikes
            hist=[]; ringm=f_>0.001
            for it in range(4):
                Xc=wco(o); PU=np.zeros_like(Xc); mn=1.0
                def nrm_at(q):
                    best=None
                    for T in (TBd,TF_):
                        loc,nr,idx,d=T.find_nearest(Vector(tuple(q)),0.03)
                        if loc is None: continue
                        if best is None or d<best[0]: best=(d,(Vector(tuple(q))-loc).dot(nr),np.array(tuple(nr)))
                    return best
                for i in np.where(ringm)[0]:
                    b_=nrm_at(Xc[i])
                    if b_ is None: continue
                    mn=min(mn,b_[1])
                    if b_[1]<off: v=b_[2]*(off-b_[1]); PU[i]=v if v@v>PU[i]@PU[i] else PU[i]
                for fc in faces:
                    q=Xc[list(fc)].mean(0); b_=nrm_at(q)
                    if b_ is None: continue
                    mn=min(mn,b_[1])
                    if b_[1]<off*0.75:
                        v=b_[2]*(off*0.75-b_[1])
                        for vi in fc:
                            if v@v>PU[vi]@PU[vi]: PU[vi]=v
                mm=np.linalg.norm(PU,axis=1)
                hist.append({'iter':it,'min_clearance_mm':round(mn*1000,2),'verts_needing':int((mm>1e-5).sum()),'max_need_mm':round(float(mm.max())*1000,2)})
                if (mm>1e-5).sum()==0: break
                PU=group_max(o,PU); PU=smooth_field(o,PU,iters=40); PU[~ringm]=0; set_world(o,Xc+PU)
            r['smooth_residual_push']=hist
        # shape check: pairwise distances inside the fully-rigid part change only by the uniform scale
        Xa=wco(o); rg=np.where(f_>0.999)[0]
        if len(rg)>3:
            idx=np.random.default_rng(7).choice(len(rg),min(400,len(rg)),replace=False); a=rg[idx]; b=np.roll(a,1)
            d0=np.linalg.norm(NECKR['X0'][a]-NECKR['X0'][b],axis=1); d1=np.linalg.norm(Xa[a]-Xa[b],axis=1)
            r['ring_shape_max_dev_mm_after_uniform_scale']=round(float(np.abs(d1-d0*r.get('uniform_scale',1.0)).max())*1000,3)
    except Exception as e: traceback.print_exc(); r['error']=str(e)
    rep['strap_rigid']=r; log('strap rigid',r)
BRA_HIDDEN=SHIRT is not None and P.get('BRA_UNDER_SHIRT','hide')=='hide'
if P.get('FIT',True):
    for o,tg,off in ((BRA,[BODY],P.get('FIT_BRA',0.002)),(SH,[BODY],P.get('FIT_SHORTS',0.0015 if SF=='hug' else 0.0025))):
        try: fit_out(o,tg,off,damp=(1.0-NECKR['f']) if (o is BRA and NECKR is not None and P.get('BRA_NECK')=='rigid') else None)
        except Exception as e: traceback.print_exc(); log('FITERR',o.name,e)
    if NECKR is not None and P.get('BRA_NECK')=='rigid': strap_rigid(BRA,P.get('STRAP_RIGID',0.0015))
    elif P.get('STRAP_PUSH'): strap_push(BRA,P['STRAP_PUSH'])
    if P.get('FIT_HAIR',False):   # run 4: OFF (it flattened her hair cards onto the face in runs 2-3)
        try: fit_out(HR,[FH],P.get('FIT_HAIR_OFF',0.0015),deep=0.03,only=lambda X:X[:,1]<float(hmn[1]+hmx[1])/2)
        except Exception as e: traceback.print_exc(); log('FITERR','Hair',e)
    if SHIRT is not None:
        try:
            if P.get('SHIRT_FIT','v5')=='v5': shirt_v5(SHIRT,[SH] if BRA_HIDDEN else [BRA,SH],P.get('FIT_SHIRT',0.006))
            else:
                for tg_ in ((BODY,SH) if BRA_HIDDEN else (BODY,BRA,SH)): fit_out(SHIRT,[tg_],P.get('FIT_SHIRT',0.006)); rep['cloth_fit']['Shirt over '+tg_.name]=rep['cloth_fit'].pop('Shirt')
        except Exception as e: traceback.print_exc(); log('FITERR','Shirt',e)

# ---------- run 7 shirt post-pass (RUN6B fixes 1 + 5): (a) Tummy key: with her shorts' Tummy=1 the hem is pushed out locally over the shorts' outer layer;
#            (b) the whole push field (retargeted -> fitted) is re-smoothed with a Laplacian falloff so no single step tears an edge (each step <= 25 mm);
#            (c) weld: every seam group / shell pair snapped back together (shared midpoint, same displacement on both layers);
#            (d) group-coherent clearance pass over the body (a whole group moves by its largest need), then a final weld check.
def shirt_need_body(o,off,T=None):
    T=T or world_bvh([BODY]); X=wco(o); N=np.zeros_like(X); S=np.ones(len(X))
    for i,p in enumerate(X):
        loc,nr,idx,d=T.find_nearest(Vector(tuple(p)),0.08)
        if loc is None: continue
        s=(Vector(tuple(p))-loc).dot(nr); S[i]=s
        if -0.08<s<off: N[i]=np.array(tuple(nr))*(off-s)
    return N,S
def tummy_clear(o,off=0.0015,cap=0.025):
    r={}
    kb=SH.data.shape_keys.key_blocks.get('Tummy') if SH.data.shape_keys else None
    if kb is None: rep['tummy_clear']={'skipped':'no Tummy key'}; return
    v0=kb.value; kb.value=1.0; bpy.context.view_layer.update()
    try:
        Tsh,VS=_bvh_tris(SH); TB=world_bvh([BODY]); X=wco(o); D=np.zeros_like(X)
        zlo,zhi=float(VS[:,2].min())-0.01,float(VS[:,2].max())+0.03; hit=0
        for i,p in enumerate(X):
            if not (zlo<p[2]<zhi): continue
            loc,nr,idx,d=TB.find_nearest(Vector(tuple(p)),0.10)
            if loc is None: continue
            far=_far_hits(Tsh,loc+nr*0.0003,nr,0.08)
            if far is None: continue
            s=(Vector(tuple(p))-loc).dot(nr); need=far+off-s
            if need>0: D[i]=np.array(tuple(nr))*min(need,cap); hit+=1
        D=group_max(o,D); D=smooth_field(o,D,iters=20,cap=cap); set_world(o,wco(o)+D)
        mm=np.linalg.norm(D,axis=1)*1000; r={'hem_verts_needing_push':hit,'moved_gt_0p1mm':int((mm>0.1).sum()),'max_mm':round(float(mm.max()),1)}
    except Exception as e: traceback.print_exc(); r['error']=str(e)
    kb.value=v0; bpy.context.view_layer.update(); rep['tummy_clear']=r; log('tummy clear',r)

# ---------- run 8c: the armholes / band-sleeve seam carried folded (inverted) faces from the arm retarget, seen as dark slits (7b) or holes (8 with culling).
#            Relax ONLY that seam zone: the shirt's total displacement from her original mesh is Laplacian-smoothed there (topology + coincident/shell groups
#            move as one), so the folds unfold while the rest of her shirt keeps its exact fit; the outward-only clearance below runs after it.
def shirt_seam_relax(o,iters=None):
    iters=int(iters or P.get('SEAM_RELAX_ITERS',30))
    X0=WELD[o.name]['X0']; E=WELD[o.name]['E']; G=WELD[o.name]['groups']; X=wco(o); D=X-X0; n=len(X)
    names={g.index:g.name.lower() for g in o.vertex_groups}
    a=np.zeros(n)
    for v in o.data.vertices:
        tot=sum(ge.weight for ge in v.groups) or 1.0
        a[v.index]=sum(ge.weight for ge in v.groups if any(s in names.get(ge.group,'') for s in ('arm','shoulder','elbow')))/tot
    z=np.clip(8*a*(1-a),0,1)
    for _ in range(int(P.get('SEAM_RELAX_DILATE',12))):
        S_=np.zeros(n); C_=np.zeros(n); np.add.at(S_,E[:,0],z[E[:,1]]); np.add.at(S_,E[:,1],z[E[:,0]]); np.add.at(C_,E[:,0],1); np.add.at(C_,E[:,1],1)
        z=np.maximum(z,0.85*S_/np.maximum(C_,1))
        for gg in G: z[gg]=z[gg].max()
    D0=D.copy()
    for _ in range(iters):
        S_=np.zeros_like(D); C_=np.zeros(n); np.add.at(S_,E[:,0],D[E[:,1]]); np.add.at(S_,E[:,1],D[E[:,0]]); np.add.at(C_,E[:,0],1); np.add.at(C_,E[:,1],1)
        M=S_/np.maximum(C_,1)[:,None]; D=D+(0.5*z)[:,None]*(M-D)
        for gg in G: D[gg]=D[gg].mean(0)
    set_world(o,X0+D); mv=np.linalg.norm(D-D0,axis=1)
    r={'zone_verts_gt0p5':int((z>0.5).sum()),'zone_verts_any':int((z>0.01).sum()),'iters':iters,'max_move_mm':round(float(mv.max())*1000,1),'p95_move_mm':round(float(np.percentile(mv[z>0.01],95))*1000,1) if (z>0.01).any() else 0}
    rep['shirt_seam_relax']=r; log('SEAM relax',r)
def shirt_post(o):
    r={}
    if o.name not in WELD: rep['shirt_post']={'skipped':'no weld record'}; return
    XR=WELD[o.name].get('XR',WELD[o.name]['X0'])
    if P.get('TUMMY_CLEAR',True): tummy_clear(o)
    X=wco(o); D=X-XR; nm=np.linalg.norm(D,axis=1)
    r['push_field_before']={'max_mm':round(float(nm.max())*1000,1),'verts_gt_25mm':int((nm>0.025).sum())}
    cap=float(P.get('PUSH_CAP',0.025))
    # steps of <= cap each; the projection keeps every required push, so a > cap need is reached in more than one smoothed step
    Ds=np.zeros_like(D); rem=D.copy(); steps=0
    while steps<4:
        steps+=1; st=rem.copy(); sn=np.linalg.norm(st,axis=1); k=sn>cap; st[k]*= (cap/sn[k])[:,None]
        st=smooth_field(o,st,iters=25); Ds+=st
        Un=np.zeros_like(D); mk=nm>1e-7; Un[mk]=D[mk]/nm[mk][:,None]; left=np.clip(nm-(Ds*Un).sum(1),0,None); rem=Un*left[:,None]
        if np.linalg.norm(rem,axis=1).max()<0.0005: break
    set_world(o,XR+Ds); r['smooth_steps']=steps
    nm2=np.linalg.norm(Ds,axis=1); r['push_field_after_smooth']={'max_mm':round(float(nm2.max())*1000,1),'mean_moved_mm':round(float(nm2[nm2>1e-4].mean())*1000,1) if (nm2>1e-4).any() else 0}
    r['weld1']=weld_snap(o,'1')
    if P.get('SEAM_RELAX',False):
        try: shirt_seam_relax(o)
        except Exception as e: traceback.print_exc(); log('SEAMRELAXERR',e); rep['shirt_seam_relax_error']=str(e)
    TB=world_bvh([BODY]); hist=[]
    for it in range(3):
        N,S=shirt_need_body(o,float(P.get('FIT_SHIRT',0.003)),TB); m=(S>-0.08)
        hist.append({'iter':it,'min_mm':round(float(S[m].min())*1000,2),'under_skin':int(((S<0)&m).sum()),'need_verts':int((np.linalg.norm(N,axis=1)>1e-6).sum())})
        if (np.linalg.norm(N,axis=1)>1e-6).sum()==0: break
        N=group_max(o,N); N=smooth_field(o,N,iters=15,cap=cap); set_world(o,wco(o)+N)
    N,S=shirt_need_body(o,0.0,TB); m=(S>-0.08); hist.append({'final_min_mm':round(float(S[m].min())*1000,2),'under_skin':int(((S<0)&m).sum())})
    r['clearance']=hist; r['weld2']=weld_snap(o,'2')
    rep['shirt_post']=r; log('SHIRT post',json.dumps(r,default=str)[:1500])
if SHIRT is not None and P.get('WELD',True):
    try: shirt_post(SHIRT)
    except Exception as e: traceback.print_exc(); log('SHIRTPOSTERR',e)
if BRA is not None and P.get('WELD',True):
    try: weld_snap(BRA,'bra')
    except Exception as e: traceback.print_exc(); log('BRAWELDERR',e)
# clothes weights: Data Transfer from the Panda body (Vertex Data > Vertex Groups, nearest face interpolated), applied, cleaned, normalized, max 4 influences
def transfer_weights(o):
    old=[g.name for g in o.vertex_groups]; o.vertex_groups.clear()
    sel([o]); md=o.modifiers.new('WT','DATA_TRANSFER'); md.object=BODY; md.use_vert_data=True; md.data_types_verts={'VGROUP_WEIGHTS'}; md.vert_mapping='POLYINTERP_NEAREST'
    md.layers_vgroup_select_src='ALL'; md.layers_vgroup_select_dst='NAME'
    bpy.ops.object.datalayout_transfer(modifier=md.name)
    while o.modifiers[0].name!=md.name: bpy.ops.object.modifier_move_up(modifier=md.name)
    try: bpy.ops.object.modifier_apply(modifier=md.name); how='Data Transfer modifier, applied'
    except Exception as e:
        log('modifier apply refused',o.name,e); o.modifiers.remove(o.modifiers[md.name])
        sel([o,BODY],BODY); bpy.ops.object.data_transfer(data_type='VGROUP_WEIGHTS',use_create=True,vert_mapping='POLYINTERP_NEAREST',layers_select_src='ALL',layers_select_dst='NAME')
        sel([o]); how='Data Transfer operator (same transfer; mesh has shape keys)'
    rep.setdefault('cloth_weight_method',{})[o.name]=how
    try:
        bpy.ops.object.vertex_group_clean(group_select_mode='ALL',limit=0.001)
        bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL',limit=4)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL',lock_active=False)
    except Exception as e: log('WTCLEAN',o.name,e)
    used=set(ge.group for v in o.data.vertices for ge in v.groups if ge.weight>0)
    drop=[g.name for g in o.vertex_groups if g.index not in used]
    for nm_ in drop: o.vertex_groups.remove(o.vertex_groups[nm_])
    mx=max((len(v.groups) for v in o.data.vertices),default=0); nz=sum(1 for v in o.data.vertices if not v.groups)
    rep.setdefault('cloth_weights',{})[o.name]={'old_groups':len(old),'new_groups':len(o.vertex_groups),'max_influences':mx,'unweighted_verts':nz,'groups':[g.name for g in o.vertex_groups]}
    log('weights',o.name,rep['cloth_weights'][o.name])
def clean_weights(o):
    sel([o])
    try:
        bpy.ops.object.vertex_group_clean(group_select_mode='ALL',limit=0.001)
        bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL',limit=4)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL',lock_active=False)
    except Exception as e: log('WTCLEAN',o.name,e)
    used=set(ge.group for v in o.data.vertices for ge in v.groups if ge.weight>0)
    for nm_ in [g.name for g in o.vertex_groups if g.index not in used]: o.vertex_groups.remove(o.vertex_groups[nm_])
    mx=max((len(v.groups) for v in o.data.vertices),default=0); nz=sum(1 for v in o.data.vertices if not v.groups)
    rep.setdefault('cloth_weight_method',{})[o.name]='her own outfit weights (Outfitriggedpanda.fbx), names mapped to Panda bones, cleaned, max 4, normalized'
    rep.setdefault('cloth_weights',{})[o.name]={'new_groups':len(o.vertex_groups),'max_influences':mx,'unweighted_verts':nz,'groups':[g.name for g in o.vertex_groups]}
    log('weights (own)',o.name,rep['cloth_weights'][o.name])
    if nz: raise RuntimeError(f'{nz} unweighted verts on {o.name}')
for o in CLOTH:
    if P.get('SHIRT_WEIGHTS','original')=='original' and o.name in ORIG_W:
        try: clean_weights(o); continue
        except Exception as e: traceback.print_exc(); log('OWNWEIGHTS failed -> transfer',o.name,e)
    try: transfer_weights(o)
    except Exception as e: traceback.print_exc(); log('WTERR',o.name,e)
# ---------- run 7 (RUN6B fix 2): the shirt sank up to 25.6 mm into the body in the posed idle/squat because her outfit weights (authored on a different
#            body) and Panda's body weights disagree near the armpits/sides/hips. Corrective weights: shirt verts close to the skin take the body's own
#            weights at the nearest skin point (barycentric), blended by distance (<= 10 mm: body, >= 30 mm: hers). Seam groups / shell twins share weights.
def _vw(o):
    gi={g.index:g.name for g in o.vertex_groups}; return [{gi[ge.group]:ge.weight for ge in v.groups if ge.weight>0} for v in o.data.vertices]
def _write_w(o,Wl):
    for nm_ in set(k for w in Wl for k in w):
        if o.vertex_groups.get(nm_) is None: o.vertex_groups.new(name=nm_)
    gidx={g.name:g for g in o.vertex_groups}; cur=_vw(o)
    for i,(w0,w1) in enumerate(zip(cur,Wl)):
        for k in w0:
            if k not in w1 or w1[k]<=0.0005: gidx[k].remove([i])
        for k,w in w1.items():
            if w>0.0005 and abs(w0.get(k,-1)-w)>1e-6: gidx[k].add([i],float(w),'REPLACE')
def _norm4(w):
    it=sorted(w.items(),key=lambda kv:-kv[1])[:4]; s=sum(x for _,x in it)
    return {k:x/s for k,x in it} if s>0 else w
def weights_equalize(o):
    if o.name not in WELD: return 0
    Wl=_vw(o); n=0
    for gg in WELD[o.name]['groups']:
        acc={}
        for i in gg:
            for k,w in Wl[i].items(): acc[k]=acc.get(k,0)+w/len(gg)
        acc=_norm4(acc)
        for i in gg:
            if Wl[i]!=acc: Wl[i]=dict(acc); n+=1
    _write_w(o,Wl); return n
def body_weight_blend(o,d_full=0.010,d_zero=0.030):
    dg=bpy.context.evaluated_depsgraph_get(); eb=BODY.evaluated_get(dg); me=eb.to_mesh(); me.calc_loop_triangles(); mw=BODY.matrix_world
    use_ev=len(me.vertices)==len(BODY.data.vertices)
    if use_ev: V=np.array([tuple(mw@v.co) for v in me.vertices]); F=np.array([tuple(t.vertices) for t in me.loop_triangles],dtype=np.int64)
    eb.to_mesh_clear()
    if not use_ev:
        me2=BODY.data; me2.calc_loop_triangles(); V=wco(BODY); F=np.array([tuple(t.vertices) for t in me2.loop_triangles],dtype=np.int64)
    T=BVHTree.FromPolygons(V.tolist(),F.tolist())
    bones=set(b.name for b in B.data.bones); WB=_vw(BODY); WB=[{k:w for k,w in d.items() if k in bones} for d in WB]
    X=wco(o); Wl=_vw(o); nb=0; full=0
    from mathutils.geometry import barycentric_transform as _bt
    for i,p in enumerate(X):
        loc,nr,fi,d=T.find_nearest(Vector(tuple(p)),d_zero)
        if loc is None: continue
        a=float(np.clip((d_zero-d)/(d_zero-d_full),0,1))
        if a<=0: continue
        tri=F[fi]; bc=_bt(loc,Vector(tuple(V[tri[0]])),Vector(tuple(V[tri[1]])),Vector(tuple(V[tri[2]])),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
        wb={}
        for k_,c_ in zip(tri,bc):
            for g,w in WB[k_].items(): wb[g]=wb.get(g,0)+max(c_,0)*w
        if not wb: continue
        s=sum(wb.values()); wb={k:w/s for k,w in wb.items()}
        new={}
        for k,w in Wl[i].items(): new[k]=new.get(k,0)+(1-a)*w
        for k,w in wb.items(): new[k]=new.get(k,0)+a*w
        Wl[i]=_norm4(new); nb+=1; full+=int(a>=0.999)
    _write_w(o,Wl)
    r={'verts_blended':nb,'verts_full_body_weights':full,'of':len(X),'d_full_mm':d_full*1000,'d_zero_mm':d_zero*1000,'body_eval_mesh':use_ev}
    rep['shirt_body_weights']=r; log('shirt body-weight blend',r)

# ---------- run 8 (RUN7 1b): the top of the right sleeve (where the off-shoulder band meets the sleeve) opened into a slit/notch once the arm is lowered,
#            plus a ~3 mm notch under the left arm, because the band and the sleeve-top carried different weights. Fix: ONE shared, spatially averaged
#            weight set over the band + sleeve-top seam zone (every shirt vert within SEAM_R of a vert that carries shoulder/arm weight), Gaussian over
#            3D rest-space neighbours ACROSS pieces/islands, so surfaces that touch in rest deform together. Mesh shape untouched (weights only).
def seam_weight_average(o,R=None,sig=None,iters=2):
    R=float(R or P.get('SEAM_R',0.02)); sig=float(sig or P.get('SEAM_SIG',0.008))
    names=[g.name for g in o.vertex_groups]; G=len(names); n=len(o.data.vertices)
    Wm=np.zeros((n,G))
    for v in o.data.vertices:
        for ge in v.groups: Wm[v.index,ge.group]=ge.weight
    s=Wm.sum(1); s[s==0]=1; Wm/=s[:,None]
    armg=[k for k,nm_ in enumerate(names) if ('shoulder' in nm_.lower() or nm_.lower().endswith(' arm') or 'upperarm' in nm_.lower() or nm_.lower().endswith(' elbow'))]
    X=wco(o); kd=KDTree(n)
    for i,p in enumerate(X): kd.insert(Vector(tuple(p)),i)
    kd.balance()
    core=np.where(Wm[:,armg].sum(1)>0.02)[0] if armg else np.zeros(0,dtype=np.int64)
    zone=np.zeros(n,bool)
    for i in core:
        if zone[i]: continue
        for _,j,_ in kd.find_range(Vector(tuple(X[i])),R): zone[j]=True
    zi=np.where(zone)[0]; NB={}
    for i in zi:
        hits=kd.find_range(Vector(tuple(X[i])),R); NB[i]=(np.array([h[1] for h in hits],dtype=np.int64),np.exp(-np.array([h[2] for h in hits])**2/(2*sig*sig)))
    W0=Wm.copy()
    for it in range(iters):
        Wn=Wm.copy()
        for i in zi:
            j,w=NB[i]; Wn[i]=(Wm[j]*w[:,None]).sum(0)/w.sum()
        Wm=Wn
    gi=names; Wl=_vw(o); ch=0; mxd=0.0
    for i in zi:
        d={gi[k]:float(Wm[i,k]) for k in range(G) if Wm[i,k]>0.002}
        d=_norm4(d); Wl[i]=d; ch+=1
    mxd=float(np.abs(Wm[zi]-W0[zi]).sum(1).max()) if len(zi) else 0.0
    _write_w(o,Wl)
    r={'arm_groups':[names[k] for k in armg],'core_verts':int(len(core)),'zone_verts':int(len(zi)),'radius_mm':R*1000,'sigma_mm':sig*1000,'iters':iters,'max_weight_change_L1':round(mxd,3)}
    rep['seam_weight_avg']=r; log('SEAM weight avg',r)
try:
    if SHIRT is not None and P.get('SHIRT_BODYW',True): body_weight_blend(SHIRT)
    if SHIRT is not None and P.get('SEAM_AVG',True):
        try: seam_weight_average(SHIRT)
        except Exception as e: traceback.print_exc(); log('SEAMAVGERR',e); rep['seam_weight_avg_error']=str(e)
    for o_ in (SHIRT,BRA):
        if o_ is not None and P.get('WELD',True):
            n_=weights_equalize(o_); rep.setdefault('weld',{}).setdefault(o_.name,{})['weights_equalized_verts']=n_; log('weights equalized',o_.name,n_)
    for o_ in (SHIRT,BRA):
        if o_ is not None: clean_weights(o_)
except Exception as e: traceback.print_exc(); log('WBLENDERR',e); rep['wblend_error']=str(e)
# ---------- 6. ONE armature: merge the head's and the hair's bones into Panda's (same-name bones -> Panda's; their extra bones parented under Panda Head)
bodyn=set(b_.name for b_ in B.data.bones); DUP={}
arms=[a for a in (FA,HA) if a]
for k,arm in enumerate(arms):
    for b_ in arm.data.bones:
        if b_.name in bodyn:
            o_=b_.name; b_.name=f'DUP{k}_'+o_; DUP[b_.name]=o_
log('dup bones',DUP)
roots=[b_.name for arm in arms for b_ in arm.data.bones if b_.parent is None and b_.name not in DUP]
sel([B]+arms,B); bpy.ops.object.join()
bpy.ops.object.mode_set(mode='EDIT'); eb=B.data.edit_bones
for d,t in DUP.items():
    if d in eb:
        for c in list(eb[d].children): c.parent=eb[t]
        eb.remove(eb[d])
for r_ in roots:
    if r_ in eb and eb[r_].parent is None: eb[r_].parent=eb['Head']; log('rooted under Head',r_)
def kill(name):
    if name in eb:
        for c in list(eb[name].children): kill(c.name)
        eb.remove(eb[name])
if P.get('HAIR')!='head': kill('Hair Root')   # bones of the bunisu pigtails/bangs meshes (kept when HAIR='head')
bpy.ops.object.mode_set(mode='OBJECT')
def merge_groups(o):
    for g in list(o.vertex_groups):
        if g.name in DUP:
            t=DUP[g.name]; tg=o.vertex_groups.get(t)
            if tg is None: g.name=t; continue
            for v in o.data.vertices:
                for ge in v.groups:
                    if ge.group==g.index: tg.add([v.index],ge.weight,'ADD')
            o.vertex_groups.remove(g)
for o in (FH,HR): merge_groups(o)
bn=set(b.name for b in B.data.bones)
# eyes -> LeftEye / RightEye (the head's weighted eye pair)
def gcount(o,n):
    g=o.vertex_groups.get(n)
    return 0 if g is None else sum(1 for v in o.data.vertices for ge in v.groups if ge.group==g.index and ge.weight>0)
pairs=[(l,r) for l,r in (('Eye_L','Eye_R'),('Eye_Left','Eye_Right'),('LeftEye','RightEye')) if l in bn and r in bn]
if pairs:
    best=max(pairs,key=lambda p:gcount(FH,p[0])+gcount(FH,p[1])); rep['eye_pairs']={f'{l}/{r}':gcount(FH,l)+gcount(FH,r) for l,r in pairs}
    for old,newn in ((best[0],'LeftEye'),(best[1],'RightEye')):
        if old==newn: continue
        if newn in B.data.bones: B.data.bones[newn].name=newn+'_unused'
        B.data.bones[old].name=newn
        g=FH.vertex_groups.get(old)
        if g is not None and FH.vertex_groups.get(newn) is None: g.name=newn
    log('eyes',rep['eye_pairs'],'->',best)
bn=set(b.name for b in B.data.bones)
# hair: every hair vertex weighted (unweighted cards ride Head); cranium rides Head
def ensure_head(o):
    hg=o.vertex_groups.get('Head') or o.vertex_groups.new(name='Head')
    nz=[v.index for v in o.data.vertices if not any(ge.weight>0 and o.vertex_groups[ge.group].name in bn for ge in v.groups)]
    if nz: hg.add(nz,1.0,'REPLACE')
    return len(nz)
rep['hair_unweighted_to_head']=ensure_head(HR)
if CR: ensure_head(CR)
# head neck seam: bottom band of her head takes the body's own neck weights (blended up to her head's weights) so the seam never opens when posed. Weights only, no geometry change.
try:
    if not P.get('SEAM_BLEND',False): raise StopIteration('seam weight blend off in run 4 (no ring seam: Panda neck tucks into her head shell)')
    bw={}; KD=KDTree(len(BODY.data.vertices)); gi={g.index:g.name for g in BODY.vertex_groups}; n_=0
    for v in BODY.data.vertices:
        co=BODY.matrix_world@v.co
        if co.z>zt-0.08: KD.insert(co,v.index); bw[v.index]={gi[ge.group]:ge.weight for ge in v.groups if gi[ge.group] in bn}; n_+=1
    KD.balance(); zbot=float(wco(FH)[:,2].min()); band=P['SEAM_BAND']; changed=0
    hgi={g.index:g.name for g in FH.vertex_groups}
    for v in FH.data.vertices:
        co=FH.matrix_world@v.co; t=(co.z-zbot)/band
        if t>=1.0: continue
        s2=max(0.0,t); s2=s2*s2*(3-2*s2)
        _,idx,_=KD.find(co); wb=bw.get(idx,{})
        wh={hgi[ge.group]:ge.weight for ge in v.groups}
        keys=set(wb)|set(k for k in wh if k in bn)
        mix={k:(1-s2)*wb.get(k,0.0)+s2*wh.get(k,0.0) for k in keys}; tot=sum(mix.values()) or 1.0
        for k,w in mix.items():
            g=FH.vertex_groups.get(k) or FH.vertex_groups.new(name=k); g.add([v.index],w/tot,'REPLACE')
        changed+=1
    rep['neck_seam_weight_blend']={'body_neck_verts':n_,'head_verts_blended':changed,'band_m':band}; log('seam weights',rep['neck_seam_weight_blend'])
except StopIteration as e: rep['neck_seam_weight_blend']=str(e)
except Exception as e: traceback.print_exc(); log('SEAMERR',e)
# every mesh: child of the ONE armature with an Armature modifier
MESHES=[x for x in (BODY,)+tuple(BX)+(FH,HR,CR)+tuple(CLOTH) if x]
for o in MESHES:
    mw=o.matrix_world.copy(); o.parent=B; o.parent_type='OBJECT'; o.matrix_world=mw
    am=[m for m in o.modifiers if m.type=='ARMATURE']
    for m in am[1:]: o.modifiers.remove(m)
    if not am: am=[o.modifiers.new('Armature','ARMATURE')]
    am[0].object=B
    while o.modifiers[0].type!='ARMATURE':
        sel([o]); bpy.ops.object.modifier_move_up(modifier=am[0].name)
for o in list(bpy.data.objects):
    if o.type=='ARMATURE' and o is not B: log('removing stray armature',o.name); bpy.data.objects.remove(o)
bpy.context.view_layer.update()
# bones dump
def bones_txt():
    L=[f'ARMATURE {B.name}: {len(B.data.bones)} bones (one armature in the file: {sum(1 for o in bpy.data.objects if o.type=="ARMATURE")})','']
    def walk(b,d):
        L.append('  '*d+b.name); [walk(c,d+1) for c in b.children]
    for b in B.data.bones:
        if b.parent is None: walk(b,0)
    L+=['','MESHES (parent, armature modifier, vertex groups, max influences, unweighted verts, tris):']
    for o in MESHES:
        am=[m.object.name for m in o.modifiers if m.type=='ARMATURE' and m.object]
        mx=max((len([g for g in v.groups if g.weight>0]) for v in o.data.vertices),default=0); nz=sum(1 for v in o.data.vertices if not any(g.weight>0 for g in v.groups))
        miss=[g.name for g in o.vertex_groups if g.name not in bn]
        L.append(f'  {o.name}: parent={o.parent.name if o.parent else None}, armature_mod={am}, groups={len(o.vertex_groups)}, max_infl={mx}, unweighted={nz}, groups_without_bone={miss[:12]}, tris={tris(o)}')
    return '\n'.join(L)
if BRA_HIDDEN:
    BRA.hide_render=True; BRA.hide_set(True); rep['bra']='hidden under the shirt (kept in the .blend; unhide it for the no-shirt look)'; log('bra hidden under shirt')
BT=bones_txt(); open(OUT+'/proof/v37-bones.txt','w').write(BT); log('BONES\n'+BT[:3000])

# ---------- run 6 RIG QA part 1: hierarchy audit (every mesh -> exactly one Armature modifier on the ONE Panda armature, parent = it, weights sane)
try:
    AUD={'armatures':[o.name for o in bpy.data.objects if o.type=='ARMATURE'],'empties':[o.name for o in bpy.data.objects if o.type=='EMPTY'],'meshes':{}}
    for o in MESHES:
        am=[m for m in o.modifiers if m.type=='ARMATURE']; gi={g.index:g.name for g in o.vertex_groups}
        sums=np.array([sum(ge.weight for ge in v.groups if ge.weight>0 and gi.get(ge.group) in bn) for v in o.data.vertices]) if len(o.data.vertices) else np.zeros(1)
        infl=max((len([g for g in v.groups if g.weight>0]) for v in o.data.vertices),default=0)
        AUD['meshes'][o.name]={'parent':o.parent.name if o.parent else None,'armature_modifiers':[m.object.name if m.object else None for m in am],'unweighted':int((sums<=0).sum()),
            'max_influences':infl,'weights_not_normalized_gt_1pct':int((np.abs(sums-1)>0.01).sum()),'groups_without_bone':[g.name for g in o.vertex_groups if g.name not in bn][:10]}
    AUD['eye_verts']={'LeftEye':gcount(FH,'LeftEye'),'RightEye':gcount(FH,'RightEye')}
    AUD['hair_chain_roots_under_Head']=sorted(b.name for b in B.data.bones if b.parent and b.parent.name=='Head' and b.name.startswith('Blw_'))
    AUD['toe_bones']=[b for b in ('Left toe','Right toe') if b in B.data.bones]; AUD['finger_bones']=len([b for b in B.data.bones if 'Finger' in b.name or 'Thumb' in b.name])
    AUD['gate']=bool(len(AUD['armatures'])==1 and all(m['parent']==B.name and m['armature_modifiers']==[B.name] and m['unweighted']==0 and m['max_influences']<=4 for k,m in AUD['meshes'].items() if k not in ('Body','Female Head','Hair','Cranium')) and all(m['parent']==B.name and m['armature_modifiers']==[B.name] and m['unweighted']==0 for m in AUD['meshes'].values()))
    json.dump(AUD,open(OUT+'/proof/rigqa-audit.json','w'),indent=1,default=str); rep['rig_audit']=AUD; log('RIG AUDIT',json.dumps(AUD)[:1500])
except Exception as e: traceback.print_exc(); log('AUDITERR',e)
meshes=MESHES
rep['tris']={o.name:tris(o) for o in meshes}; rep['tris_total']=sum(rep['tris'].values())
rep['shapekeys_head']=[k.name for k in FH.data.shape_keys.key_blocks] if FH.data.shape_keys else []
log('tris',rep['tris_total'],rep['tris'])
json.dump(rep,open(OUT+'/build-report.json','w'),indent=1,default=str)
SAVE_NAME={'A0':'jena-v37r8-final','A1':'jena-v37r8-A1','A2':'jena-v37r8-noshirt'}.get(VAR)
# ---------- studio: IDENTICAL to the solo asset renders (grey world 0.18, warm key / cool fill / rim suns, AgX Base Contrast, 85 mm, same framing rule)
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=P['ASM_SAMPLES']; sc.cycles.use_denoising=True
sc.render.film_transparent=False; sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGB'
sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Base Contrast'
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; bg=w.node_tree.nodes['Background']; bg.inputs[0].default_value=(0.18,0.18,0.18,1); bg.inputs[1].default_value=1.0
def sun(name,rot,e,col=(1,1,1)):
    L=bpy.data.lights.new(name,'SUN'); L.energy=e; L.color=col; L.angle=math.radians(8); o=bpy.data.objects.new(name,L); sc.collection.objects.link(o); o.rotation_euler=[math.radians(a) for a in rot]; return o
sun('key',(55,0,-35),3.2,(1,0.96,0.92)); sun('fill',(70,0,45),1.1,(0.92,0.95,1)); sun('rim',(60,0,165),2.4)
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam; cam.data.lens=85
DIRS={'front':Vector((0,-1,0)),'back':Vector((0,1,0)),'side':Vector((-1,0,0)),'q34':Vector((-0.72,-0.69,0)).normalized(),'q34L':Vector((0.72,-0.69,0)).normalized()}
def bbox(objs):
    dg=bpy.context.evaluated_depsgraph_get(); pts=[]
    for o in objs:
        e=o.evaluated_get(dg); vv=e.data.vertices; st=max(1,len(vv)//4000); pts+=[e.matrix_world@vv[i].co for i in range(0,len(vv),st)]
    mn=Vector([min(p[i] for p in pts) for i in range(3)]); mx=Vector([max(p[i] for p in pts) for i in range(3)]); return mn,mx
def place(objs,view,res,pad,zoff=0.0,box=None):
    mn,mx=box or bbox(objs); ce=(mn+mx)/2; ce.z+=zoff; sz=mx-mn; d_=DIRS[view]; asp=res[0]/res[1]
    wdt=abs(d_.y)*sz.x+abs(d_.x)*sz.y; need=max(sz.z,wdt/asp)*pad; dist=need/(24/85)+max(sz)/2
    sc.render.resolution_x,sc.render.resolution_y=res; cam.data.sensor_fit='VERTICAL'; cam.data.sensor_height=24
    cam.location=ce+d_*dist; cam.rotation_euler=(ce-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.clip_start=dist*0.01; cam.data.clip_end=dist*4
def shot(name,objs,view,res=(780,1040),pad=1.12,zoff=0.0,box=None):
    try:
        place(objs,view,res,pad,zoff,box); sc.render.filepath=OUT+'/proof/'+name+'.png'; bpy.ops.render.render(write_still=True); log('render',name)
    except Exception as e: traceback.print_exc(); log('RENDERERR',name,e)
def solo(objs):
    """hide everything except objs (for the untouched-asset check)"""
    keep=set(objs)
    st={o.name:o.hide_render for o in meshes}
    for o in meshes: o.hide_render=o not in keep
    return st
def unsolo(st):
    for o in meshes: o.hide_render=st[o.name]
HAIRNAME='umeko-hair' if P['HAIR']=='umeko' else ('female-head-hair' if P['HAIR']=='head' else 'blowout-haircards')
ASSETS={'panda-body':[BODY]+BX,'female-head':[FH],HAIRNAME:[HR],'booty-shorts':[SH],'outfit-bra':[BRA]}
if SHIRT is not None: ASSETS['outfit-shirt-grey']=[SHIRT]
SETS={'face':[],'full':['panda-body','female-head',HAIRNAME,'booty-shorts','outfit-shirt-grey','outfit-bra'],'umeko':[HAIRNAME],'noshirt':['outfit-bra','booty-shorts']}
SIDE_L=Vector((1,0,0))
def wrot(name,deg,axis):
    if not deg or name not in B.pose.bones: return
    pb=B.pose.bones[name]; h=pb.head.copy(); pb.matrix=Matrix.Translation(h)@Matrix.Rotation(math.radians(deg),4,axis)@Matrix.Translation(-h)@pb.matrix; bpy.context.view_layer.update()
def pose_relaxed(test=False):
    bpy.context.view_layer.objects.active=B; bpy.ops.object.mode_set(mode='POSE')
    for pb in B.pose.bones: pb.matrix_basis=BANG.get(pb.name,Matrix()).copy() if 'BANG' in globals() else Matrix()
    bpy.context.view_layer.update()
    SHD=P['SHOULDER_DOWN']
    for name,sgn,deg in (('Left shoulder',1,SHD),('Right shoulder',-1,SHD),('Left arm',1,P['ARM_DOWN']-SHD),('Right arm',-1,P['ARM_DOWN']-SHD)): wrot(name,sgn*deg,'Y')
    for sd,sgn in (('Left',1),('Right',-1)):
        wrot(sd+' elbow',P['ELBOW_BEND'],'X'); wrot(sd+' wrist',sgn*P['WRIST_BEND'],'Y')
        for f_ in ('IndexFinger','MiddleFinger','RingFinger','LittleFinger'):
            for j,a_ in ((1,18),(2,26),(3,18)): wrot(f'{f_}{j}_{sd[0]}',sgn*a_,'Y')
        for j in (1,2): wrot(f'Thumb{j}_{sd[0]}',sgn*14,'Y')
    if test:
        wrot('Head',30,'Z'); wrot('Right leg',-28,'X'); wrot('Right knee',55,'X')
    elif P['RELAX']:
        wrot('Right leg',-6,'X'); wrot('Right knee',14,'X')
        for nm_ in ('Right ankle','Right foot'):
            if nm_ in B.pose.bones: wrot(nm_,-6,'X'); break
    bpy.ops.object.mode_set(mode='OBJECT'); bpy.context.view_layer.update()

def pose_outfit_apose():
    """Panda's arm chain posed into the A-pose her outfit was authored in (same joint directions as the outfit armature), for the shirt 1:1 renders"""
    rest(); OH={nmap(k):v for k,v in OHEAD.items()}
    for sd,s1 in (('Left','L'),('Right','R')):
        for b,c in ((sd+' shoulder',sd+' arm'),(sd+' arm',sd+' elbow'),(sd+' elbow',sd+' wrist'),(sd+' wrist','MiddleFinger1_'+s1)):
            if b not in B.pose.bones or c not in B.pose.bones or b not in OH or c not in OH: continue
            bpy.context.view_layer.update(); mw=B.matrix_world
            cur=(mw@B.pose.bones[c].head)-(mw@B.pose.bones[b].head); tgt=OH[c]-OH[b]
            q=cur.normalized().rotation_difference(tgt.normalized()); axis_a=(mw.inverted().to_3x3()@q.axis).normalized()
            pb=B.pose.bones[b]; h=pb.head.copy(); pb.matrix=Matrix.Translation(h)@Matrix.Rotation(q.angle,4,axis_a)@Matrix.Translation(-h)@pb.matrix
    bpy.context.view_layer.update()
def rest():
    bpy.context.view_layer.objects.active=B; bpy.ops.object.mode_set(mode='POSE')
    for pb in B.pose.bones: pb.matrix_basis=BANG.get(pb.name,Matrix()).copy() if 'BANG' in globals() else Matrix()
    bpy.ops.object.mode_set(mode='OBJECT'); bpy.context.view_layer.update()

# ---------- run 5: EYE RULE. Both eyes must be fully visible (front + 3/4). Ray test from every visible eye point toward the camera through the
#            hair (alpha-aware: a ray through a transparent part of a card does not count). If bangs cover an eye, ONLY the implicated front bang
#            chain(s) are rotated up (pose on the chain's first bone, no mesh edit), smallest angle that clears both views. Cheek/face crossings reported.

# ---------- run 5: SKIN MATCH (Saidie 12:05 PM Oct 18: "I'd also try to make her face color matches her body skin tone"). Her explicit ask, so the
#            face texture gets ONE per-channel colour grade (linear gain; shape, UVs and every painted detail untouched). Calibrated in the SAME studio
#            light: clothes + hair hidden, front camera, mean colour of lower-cheek/jaw patches vs upper-chest/neck patches, 3 iterations.
#            Result baked to face_matched.png (used by the material and embedded in the .fbx); her 1.png stays in the .blend as an unlinked node.
from bpy_extras.object_utils import world_to_camera_view
def _s2l(c): c=np.clip(c,0,1); return np.where(c<=0.04045,c/12.92,((c+0.055)/1.055)**2.4)
def _l2s(c): c=np.clip(c,0,1); return np.where(c<=0.0031308,c*12.92,1.055*c**(1/2.4)-0.055)
def _lab(rgb):
    l=_s2l(np.array(rgb)); M=np.array([[0.4124,0.3576,0.1805],[0.2126,0.7152,0.0722],[0.0193,0.1192,0.9505]]); X=M@l/np.array([0.95047,1.0,1.08883])
    f=np.where(X>0.008856,np.cbrt(X),7.787*X+16/116); return np.array([116*f[1]-16,500*(f[0]-f[1]),200*(f[1]-f[2])])
def _dE(a,b): return float(np.linalg.norm(_lab(a)-_lab(b)))
FACE_MAT=[s_l.material for s_l in FH.material_slots if s_l.material and s_l.material.name.lower().startswith('face')]
def _face_node():
    for m in FACE_MAT:
        bsdf=[n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'][0]
        for l in m.node_tree.links:
            if l.to_socket==bsdf.inputs['Base Color'] and l.from_node.type=='TEX_IMAGE': return m,l.from_node
    return None,None
def _pts():
    fv=np.array([tuple(FH.matrix_world@FH.data.vertices[i].co) for p in FH.data.polygons if FH.material_slots[p.material_index].material in FACE_MAT for i in p.vertices])
    hw=(hmx[0]-hmn[0])/2; h=hmx[2]-hmn[2]; cz=hmn[2]
    F=[]
    for sg in (1,-1):
        m=(np.abs(fv[:,2]-(cz+0.20*h))<0.03*h)&(sg*fv[:,0]>0.22*hw)&(sg*fv[:,0]<0.42*hw)
        if m.any():
            q=fv[m]; F.append(q[np.argmin(q[:,1])])
    bv=wco(BODY); cx=0.0; Bp=[]
    for zoff,xo in ((-0.11,0.0),(-0.10,0.035),(-0.10,-0.035)):
        m=(np.abs(bv[:,2]-(hmn[2]+zoff))<0.006)&(np.abs(bv[:,0]-xo)<0.008)
        if m.any(): q=bv[m]; Bp.append(q[np.argmin(q[:,1])])
    return [Vector(tuple(p)) for p in F],[Vector(tuple(p)) for p in Bp]
def _cal(name):
    keep={BODY,FH}|set(BX)|({CR} if CR else set()); st={o.name:o.hide_render for o in bpy.data.objects if o.type=='MESH'}
    for o in bpy.data.objects:
        if o.type=='MESH': o.hide_render=o not in keep
    hm_,hx_=bbox([FH]); box=(Vector((hm_.x,hm_.y,hm_.z-0.16)),hx_)
    sc.render.resolution_percentage=100; place([FH],'front',(480,720),1.1,box=box); sc.cycles.samples=16
    sc.render.filepath=OUT+'/proof/'+name+'.png'; bpy.ops.render.render(write_still=True)
    for o in bpy.data.objects:
        if o.type=='MESH' and o.name in st: o.hide_render=st[o.name]
    im=bpy.data.images.load(OUT+'/proof/'+name+'.png'); W_,H_=im.size; a=np.empty(W_*H_*4,dtype=np.float32); im.pixels.foreach_get(a); a=a.reshape(H_,W_,4)[:,:,:3]; bpy.data.images.remove(im)
    def samp(P_):
        out=[]
        for p in P_:
            v=world_to_camera_view(sc,cam,p); x=int(v.x*W_); y=int(v.y*H_)
            if 4<=x<W_-4 and 4<=y<H_-4: out.append(a[y-3:y+4,x-3:x+4].reshape(-1,3).mean(0))
        return np.mean(out,0) if out else None
    return samp(FP),samp(BP)
SKIN={}
try:
    if P.get('SKIN_MATCH',True) and FACE_MAT:
        FP,BP=_pts(); SKIN['points']={'face':[list(map(lambda x:round(x,4),p)) for p in FP],'body':[list(map(lambda x:round(x,4),p)) for p in BP]}
        fm,node=_face_node(); im0=node.image; W0,H0=im0.size; px0=np.empty(W0*H0*4,dtype=np.float32); im0.pixels.foreach_get(px0); px0=px0.reshape(-1,4)
        lin0=_s2l(px0[:,:3])
        new=bpy.data.images.new('face_matched.png',W0,H0,alpha=True); new.filepath_raw=OUT+'/face_matched.png'; new.file_format='PNG'
        g=np.ones(3); hist=[]
        for it in range(4):
            if it==0: node.image=im0
            else:
                px=px0.copy(); px[:,:3]=_l2s(lin0*g); new.pixels.foreach_set(px.ravel()); new.update(); node.image=new
            f_,b_=_cal('skinmatch-cal-'+('before' if it==0 else f'it{it}'))
            if f_ is None or b_ is None: raise RuntimeError(f'calibration points off-frame face={f_} body={b_}')
            dE=_dE(f_,b_); hist.append({'iter':it,'gain':[round(x,4) for x in g],'face_rgb':[round(float(x)*255,1) for x in f_],'body_rgb':[round(float(x)*255,1) for x in b_],'dE76':round(dE,2)})
            log('SKIN',hist[-1])
            if it==3: break
            g=np.clip(g*(_s2l(b_)/np.maximum(_s2l(f_),1e-4))**0.9,0.5,1.8)
        best=min(hist,key=lambda h:h['dE76']); SKIN['iterations']=hist; SKIN['chosen']=best
        if best['iter']==0: node.image=im0; SKIN['note']='original was already the closest'
        else:
            g=np.array(best['gain']); px=px0.copy(); px[:,:3]=_l2s(lin0*g); new.pixels.foreach_set(px.ravel()); new.update(); new.save(); node.image=new
            keepn=fm.node_tree.nodes.new('ShaderNodeTexImage'); keepn.image=im0; keepn.label='ORIGINAL face 1.png (unlinked; face_matched.png = this x gain '+str(best['gain'])+')'; keepn.location=(node.location.x,node.location.y-320)
except Exception as e: traceback.print_exc(); log('SKINERR',e); SKIN['error']=str(e)
rep['skin_match']=SKIN
BANG={}
def _hair_alpha():
    try:
        im=None
        for s_l in HR.material_slots:
            m=s_l.material
            if m and m.use_nodes:
                for n in m.node_tree.nodes:
                    if n.type=='TEX_IMAGE' and n.image: im=n.image
        if im is None or P['HAIR'] in ('umeko','head'): return None
        w_,h_=im.size; a=np.empty(w_*h_*4,dtype=np.float32); im.pixels.foreach_get(a); return a.reshape(h_,w_,4)[:,:,3],w_,h_
    except Exception as e: log('ALPHAERR',e); return None
HALPHA=_hair_alpha()
def _eval_tris(o,mat_ok=None):
    dg=bpy.context.evaluated_depsgraph_get(); e=o.evaluated_get(dg); me=e.to_mesh(); me.calc_loop_triangles(); mw=o.matrix_world
    V=np.array([tuple(mw@v.co) for v in me.vertices]); keep=[t for t in me.loop_triangles if mat_ok is None or mat_ok(t.material_index)]
    F=[tuple(t.vertices) for t in keep]
    uvl=me.uv_layers.active; UV=[[tuple(uvl.data[l].uv) for l in t.loops] for t in keep] if uvl else None
    TV=[tuple(t.vertices) for t in keep]; e.to_mesh_clear()
    return BVHTree.FromPolygons([tuple(v) for v in V],F),V,F,UV,TV
FH_EYE_MATS={i for i,s_l in enumerate(FH.material_slots) if s_l.material and s_l.material.name.lower().startswith('eyes')}
FH_SOLID={i for i,s_l in enumerate(FH.material_slots) if s_l.material and not s_l.material.name.lower().startswith('effects')}
DIRS_EYE={'front':Vector((0,-1,0)),'q34':Vector((-0.72,-0.69,0)).normalized()}   # subject -> camera (same as DIRS)
def cover_pct(ec): return max(v['pct'] for vw in ec.values() for v in vw.values())
def chains_for(hit_tris,TVH):
    """first bone (child of the hair root/Head) of every chain whose bones carry the covering hair triangles"""
    gi={g.index:g.name for g in HR.vertex_groups}; cnt=Counter()
    for ti in hit_tris:
        for vi in TVH[ti]:
            gs=[(ge.weight,gi[ge.group]) for ge in HR.data.vertices[vi].groups if ge.weight>0]
            if gs: cnt[max(gs)[1]]+=1
    roots=Counter()
    for bn_,c_ in cnt.items():
        if bn_ not in B.data.bones: continue
        b=B.data.bones[bn_]
        while b.parent is not None and b.parent.name not in ('Head','Blowout_Root','Hair_root','Hair Root'): b=b.parent
        if b.name in ('Head','Blowout_Root','Hair_root','Neck','Chest','Spine','Hips'): continue
        roots[b.name]+=c_
    return dict(cnt),dict(roots)
def face_cross():
    """hair triangles crossing her face skin below the brow line (cheeks/nose/eyes), by bone"""
    TF,VF,FF,_,_=_eval_tris(FH,lambda mi:mi in FH_SOLID and mi not in FH_EYE_MATS)
    TH,VH,FHt,UVH,TVH=_eval_tris(HR)
    ez=EYE_TOP_Z; ov=TH.overlap(TF)
    bad=set(a for a,b in ov if all(VF[j][2]<ez for j in FF[b]) and VF[FF[b][0]][1]<HEADCY)
    gi={g.index:g.name for g in HR.vertex_groups}; byb=Counter()
    for ti in bad:
        vi=TVH[ti][0]; gs=[(ge.weight,gi[ge.group]) for ge in HR.data.vertices[vi].groups if ge.weight>0]
        if gs: byb[max(gs)[1]]+=1
    return {'hair_tris_crossing_face_below_brow':len(bad),'by_bone':dict(byb.most_common(8))}

# ---------- run 6 EYE + CHEEK RULE (dense). Points: ~1500 random samples per eye on the eye surfaces (fixed seed) and ~600 per cheek; rays go to the ACTUAL
#            camera position of each proof view (full-body front + 3/4, face close-up front + 3/4, blink close-up), alpha-aware (alpha > 0.15 counts:
#            even a thin wisp). Hits are attributed to hair chains; each implicated chain is posed (root bone only, no mesh edit) by the smallest
#            sweep (tip outward, toward the temple) + lift (tip forward/up, away from the face) that clears its own hits on both eyes and the cheeks while
#            keeping hair-through-face below the brow <= max(10, unposed level).
_RNG=np.random.default_rng(6)
def _samples(TV,n):
    A=np.array([np.linalg.norm(np.cross(t[1]-t[0],t[2]-t[0]))/2 for t in TV]); 
    if len(TV)==0 or A.sum()<=0: return []
    idx=_RNG.choice(len(TV),n,p=A/A.sum()); u=_RNG.random((n,2)); m=u.sum(1)>1; u[m]=1-u[m]
    T=np.array(TV)[idx]; Pp=T[:,0]+(T[:,1]-T[:,0])*u[:,0:1]+(T[:,2]-T[:,0])*u[:,1:2]; return [Vector(tuple(p)) for p in Pp]
def _face_tris_world(pred):
    dg=bpy.context.evaluated_depsgraph_get(); e=FH.evaluated_get(dg); me=e.to_mesh(); me.calc_loop_triangles(); mw=FH.matrix_world
    V=np.array([tuple(mw@v.co) for v in me.vertices]); out=[]
    for t in me.loop_triangles:
        if pred(t,V): out.append(V[list(t.vertices)])
    e.to_mesh_clear(); return out
def cam_positions():
    st=(sc.render.resolution_x,sc.render.resolution_y,cam.location.copy(),cam.rotation_euler.copy())
    hm_,hx_=bbox([FH]); C={}
    vis=[o for o in MESHES if not o.hide_render]
    for nm_,objs,vw,res,pad,zo in (('front_full',vis,'front',(768,1376),1.06,0),('q34_full',vis,'q34',(768,1376),1.06,0),('face',[FH],'front',(1024,1024),1.25,0),
                                   ('face34',[FH],'q34',(1024,1024),1.25,0),('blink',[FH],'front',(768,768),0.75,0.12*(hx_.z-hm_.z))):
        place(objs,vw,res,pad,zo); C[nm_]=cam.location.copy()
    sc.render.resolution_x,sc.render.resolution_y=st[0],st[1]; cam.location=st[2]; cam.rotation_euler=st[3]
    return C
EYEP={}; CHEEKP={}
def build_points():
    ev=_face_tris_world(lambda t,V:t.material_index in FH_EYE_MATS)
    L=[t for t in ev if t[:,0].mean()>0]; Rr=[t for t in ev if t[:,0].mean()<=0]
    EYEP['L']=_samples(L,1500); EYEP['R']=_samples(Rr,1500)
    ez=[p.z for p in EYEP['L']+EYEP['R']]; ebot=min(ez); chin=float(hmn[2]); hw=(hmx[0]-hmn[0])/2; cx=(hmn[0]+hmx[0])/2
    zlo=chin+0.40*(ebot-chin); zhi=ebot-0.004
    def ck(t,V,sg):
        c=t.mean(0)
        return zlo<c[2]<zhi and 0.28*hw<sg*(c[0]-cx)<0.75*hw
    fm={i for i,s_l in enumerate(FH.material_slots) if s_l.material and s_l.material.name.lower().startswith('face')}
    dg=bpy.context.evaluated_depsgraph_get(); e=FH.evaluated_get(dg); me=e.to_mesh(); me.calc_loop_triangles(); mw=FH.matrix_world
    V=np.array([tuple(mw@v.co) for v in me.vertices])
    for sg,sd in ((1,'L'),(-1,'R')):
        TV=[V[list(t.vertices)] for t in me.loop_triangles if t.material_index in fm and ck(V[list(t.vertices)],V,sg)]
        CHEEKP[sd]=_samples(TV,600)
    e.to_mesh_clear()
    rep['eye_points']={k:len(v) for k,v in EYEP.items()}; rep['cheek_points']={k:len(v) for k,v in CHEEKP.items()}; rep['cheek_band_z']=[zlo,zhi]
_TFC=[]
def hair_eval():
    if not _TFC: _TFC.append(_eval_tris(FH,lambda mi:mi in FH_SOLID)[0])
    TF=_TFC[0]; TH,VH,FHt,UVH,TVH=_eval_tris(HR); return TF,TH,VH,UVH,TVH
from mathutils.geometry import barycentric_transform
def _alpha_at(l2,i2,VH,UVH,TVH):
    if HALPHA is None or UVH is None: return 1.0
    A_,w_,h_=HALPHA; a0,b0,c0=[Vector(VH[j]) for j in TVH[i2]]
    uvw=barycentric_transform(l2,a0,b0,c0,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
    uv=sum((Vector(UVH[i2][j])*uvw[j] for j in range(3)),Vector((0,0)))
    return float(A_[int((uv.y%1.0)*(h_-1)),int((uv.x%1.0)*(w_-1))])
def cover(PTS,CAMS,views,ATH=0.15):
    TF,TH,VH,UVH,TVH=hair_eval(); out={}; hits=Counter()
    for vw in views:
        C=CAMS[vw]; out[vw]={}
        for sd,pts in PTS.items():
            vis=0; cov=0
            for p in pts:
                dv=(C-p); dist=dv.length; d=dv/dist; o_=p+d*0.0006
                l1,_,_,_=TF.ray_cast(o_,d,dist)
                if l1 is not None: continue
                vis+=1; oo=o_; rem=dist
                for _ in range(8):
                    l2,n2,i2,d2=TH.ray_cast(oo,d,rem)
                    if l2 is None: break
                    if _alpha_at(l2,i2,VH,UVH,TVH)>ATH: cov+=1; hits[i2]+=1; break
                    oo=l2+d*0.0003; rem-=d2+0.0003
                    if rem<=0: break
            out[vw][sd]={'covered':cov,'visible':vis,'pct':round(100.0*cov/max(vis,1),2)}
    return out,hits,TVH
def chain_of_tris(hits,TVH):
    gi={g.index:g.name for g in HR.vertex_groups}; roots=Counter()
    for ti,c_ in hits.items():
        vi=TVH[ti][0]; gs=[(ge.weight,gi[ge.group]) for ge in HR.data.vertices[vi].groups if ge.weight>0]
        if not gs: continue
        bn_=max(gs)[1]
        if bn_ not in B.data.bones: roots['(unweighted)']+=c_; continue
        b=B.data.bones[bn_]
        while b.parent is not None and b.parent.name not in ('Head','Blowout_Root','Hair_root','Hair Root'): b=b.parent
        roots[b.name if b.name not in ('Head','Neck','Chest','Spine','Hips') else '(Head-weighted cards)']+=c_
    return roots
EYE_VIEWS=('front_full','q34_full','face','face34','blink'); CHEEK_VIEWS=('front_full','face','face34')
_TBODY=[]
def _root_of_vertex(vi,gi):
    gs=[(ge.weight,gi[ge.group]) for ge in HR.data.vertices[vi].groups if ge.weight>0]
    if not gs: return '(unweighted)'
    bn_=max(gs)[1]
    if bn_ not in B.data.bones: return '(unweighted)'
    b=B.data.bones[bn_]
    while b.parent is not None and b.parent.name not in ('Head','Blowout_Root','Hair_root','Hair Root'): b=b.parent
    return b.name if b.name not in ('Head','Neck','Chest','Spine','Hips') else '(Head-weighted cards)'
def hair_body_pen():
    # run 6b: hair card verts more than 2 mm inside her body (the grey tips poking out at the collarbone in run 6), by chain
    if not _TBODY: _TBODY.append(world_bvh([BODY]))
    dg=bpy.context.evaluated_depsgraph_get(); e_=HR.evaluated_get(dg); me_=e_.to_mesh(); mw_=HR.matrix_world; gi={g.index:g.name for g in HR.vertex_groups}; cnt=Counter()
    zmax=float(hmn[2])+0.02
    for v in me_.vertices:
        p=mw_@v.co
        if p.z>zmax: continue
        loc,nr,idx,d=_TBODY[0].find_nearest(p,0.05)
        if loc is not None and (p-loc).dot(nr)<-0.002: cnt[_root_of_vertex(v.index,gi)]+=1
    e_.to_mesh_clear(); return cnt
def metrics():
    e,eh,TVH=cover(EYEP,CAMS,EYE_VIEWS); c,ch,_=cover(CHEEKP,CAMS,CHEEK_VIEWS)
    fc=face_cross(); bp=hair_body_pen()
    return {'eye':e,'cheek':c,'eye_max_pct':max(v['pct'] for vw in e.values() for v in vw.values()),'cheek_max_pct':max(v['pct'] for vw in c.values() for v in vw.values()),
            'cross':fc['hair_tris_crossing_face_below_brow'],'cross_by_bone':fc['by_bone'],'eye_chains':dict(chain_of_tris(eh,TVH)),'cheek_chains':dict(chain_of_tris(ch,TVH)),'body_pen_chains':dict(bp),'body_pen_total':int(sum(bp.values()))}
def _chain_tip(root):
    b=B.pose.bones[root]
    while b.children: b=max(b.children,key=lambda c:len(c.children_recursive))
    return B.matrix_world@b.tail
AXW=lambda v:(B.matrix_world.inverted().to_3x3()@Vector(v)).normalized()
def set_chain(root,sw,lf,sgn):
    pb=B.pose.bones[root]; pb.matrix_basis=Matrix(); bpy.context.view_layer.update()
    h=pb.head.copy(); R=Matrix.Rotation(math.radians(sgn[1]*lf),4,AXW((1,0,0)))@Matrix.Rotation(math.radians(sgn[0]*sw),4,AXW((0,1,0)))
    pb.matrix=Matrix.Translation(h)@R@Matrix.Translation(-h)@pb.matrix; bpy.context.view_layer.update()
def chain_signs(root,side_hint):
    set_chain(root,0,0,(1,1)); t0=_chain_tip(root)
    set_chain(root,8,0,(1,1)); t1=_chain_tip(root)
    out_sign=1 if t0.x>0.004 else (-1 if t0.x<-0.004 else (1 if side_hint=='L' else -1))
    s_sw=1 if (t1.x-t0.x)*out_sign>0 else -1
    set_chain(root,0,8,(1,1)); t2=_chain_tip(root)
    front_chain=t0.y<float(HEADCY)
    s_lf=(1 if t2.y<t0.y else -1) if front_chain else (1 if t2.y>t0.y else -1)   # front locks: tip toward -Y (away from face/chest); back locks: toward +Y (away from the back)
    set_chain(root,0,0,(1,1)); return (s_sw,s_lf)
try:
    _ev=[(FH.matrix_world@FH.data.vertices[i].co) for p in FH.data.polygons if p.material_index in FH_EYE_MATS for i in p.vertices]
    EYE_TOP_Z=max(v.z for v in _ev)+0.004 if _ev else float(hmx[2]); HEADCY=float((hmn[1]+hmx[1])/2)
    rest(); CAMS=cam_positions(); rep['eye_cameras']={k:[round(x,3) for x in v] for k,v in CAMS.items()}
    build_points()
    m0=metrics(); rep['eyes_before']=m0; log('EYES before',json.dumps(m0,default=str)[:1500])
    CROSS_MAX=max(10,m0['cross']); rep['cross_max']=CROSS_MAX
    # run 6c (root 17:27Z): NO chain lifts at all - her hair keeps its authored rest pose 1:1. The eyes are helped only by the hair's own
    # placement: one rigid offset of the whole hair (up/back, each <= 10 mm) and an optional uniform scale <= 3 % about its Head bone,
    # chosen on the dense eye/cheek/face-crossing/body metrics. Residual strands over the brow are reported, not hidden.
    hb_names=[n_ for n_ in rep.get('hair_bones',[]) if n_ in B.data.bones and n_ not in bodyn]
    piv=B.matrix_world@B.data.bones['Head'].head_local if 'Head' in B.data.bones else Vector(((hmn[0]+hmx[0])/2,(hmn[1]+hmx[1])/2,hmn[2]))   # 6c retry: FA (head's own armature) is already merged+removed here
    me_h=HR.data; n_h=len(me_h.vertices); CO0=np.empty(n_h*3); me_h.vertices.foreach_get('co',CO0); CO0=CO0.reshape(-1,3)
    mwh=np.array(HR.matrix_world); mwhi=np.linalg.inv(mwh)
    def Mof(dy,dz,sc_):
        return Matrix.Translation(piv+Vector((0,dy,dz)))@Matrix.Scale(sc_,4)@Matrix.Translation(-piv)
    def set_hair(M):
        Mm=mwhi@np.array(M)@mwh; X=CO0@Mm[:3,:3].T+Mm[:3,3]; me_h.vertices.foreach_set('co',X.ravel()); me_h.update(); bpy.context.view_layer.update()
    evals=0; grid_=[]; best=None
    _HH=P['HAIR']=='head'
    for sc_ in ((1.0,) if _HH else (1.0,1.015,1.03)):
        for dz in ((0.0,) if _HH else (0.0,0.0025,0.005,0.0075,0.01)):
            for dy in ((0.0,) if _HH else (0.0,0.0025,0.005,0.0075,0.01)):
                set_hair(Mof(dy,dz,sc_)); mm_=metrics(); evals+=1
                scr=mm_['eye_max_pct']+2*max(0,mm_['cross']-CROSS_MAX)+0.02*mm_['body_pen_total']+0.3*(dy+dz)*100+10*(sc_-1)
                grid_.append((round(dy*1000,1),round(dz*1000,1),sc_,mm_['eye_max_pct'],mm_['cheek_max_pct'],mm_['cross'],mm_['body_pen_total'],round(scr,2)))
                if best is None or scr<best[0]: best=(scr,dy,dz,sc_)
    set_hair(Matrix()); _,dy,dz,sc_=best; M=Mof(dy,dz,sc_)
    set_hair(M)
    try:
        if hb_names and (dy or dz or sc_!=1.0):
            Ma=B.matrix_world.inverted()@M@B.matrix_world
            bpy.context.view_layer.objects.active=B; bpy.ops.object.mode_set(mode='EDIT')
            for n_ in hb_names:
                eb_=B.data.edit_bones.get(n_)
                if eb_ is not None: eb_.head=Ma@eb_.head; eb_.tail=Ma@eb_.tail
            bpy.ops.object.mode_set(mode='OBJECT'); bpy.context.view_layer.update()
    except Exception as e: traceback.print_exc(); log('HAIRBONEMOVEERR',e)
    BANG.clear()
    tried={'mode':'rigid whole-hair placement only (no chain poses)','chosen_dy_back_mm':round(dy*1000,1),'chosen_dz_up_mm':round(dz*1000,1),'chosen_uniform_scale':sc_,
           'grid_dy_dz_scale_eye_cheek_cross_bodypen_score':sorted(grid_,key=lambda g:g[-1])[:12],'hair_bones_moved':len(hb_names)}
    log('hair placement',tried)
    rep['hair_placement_search']=tried; rep['eye_evals']=evals
    # ---------- run 7 (RUN6B fixes 3 + 7). Reference = the hair exactly as 6b placed it. Stick-out = how far a moved vertex ends up OUTSIDE every 6b surface
    #            (body, head, cranium, hair, clothes): a lock that only moves within/along the 6b silhouette scores ~0, a wing scores its distance.
    try:
        H7={}
        _ref_objs=[o_ for o_ in (BODY,FH,CR,HR,SHIRT,BRA,SH) if o_ is not None]
        T6b=world_bvh(_ref_objs); TBb=world_bvh([BODY])
        gi_h={g.index:g.name for g in HR.vertex_groups}
        def chain_bones(root):
            out=[root]; b=B.pose.bones[root]
            while b.children: b=max(b.children,key=lambda c:len(c.children_recursive)); out.append(b.name)
            return out
        def chain_verts(root):
            names=set(n_.name for n_ in [B.pose.bones[root]]+list(B.pose.bones[root].children_recursive))
            return np.array([v.index for v in HR.data.vertices if any(gi_h[ge.group] in names and ge.weight>0.05 for ge in v.groups)],dtype=np.int64)
        def hair_world_eval():
            dg=bpy.context.evaluated_depsgraph_get(); e_=HR.evaluated_get(dg); me_=e_.to_mesh(); mw_=HR.matrix_world
            Xe=np.array([tuple(mw_@v.co) for v in me_.vertices]); e_.to_mesh_clear(); return Xe
        def stick_out(idx,Xe):
            mx=0.0
            for i in idx:
                p=Vector(tuple(Xe[i]))
                lb,nb_,_,_=TBb.find_nearest(p,0.05)
                if lb is not None and (p-lb).dot(nb_)<0: continue
                loc,_,_,d=T6b.find_nearest(p,0.08)
                mx=max(mx,d if loc is not None else 0.08)
            return mx
        def curl(root,deg,axis_w):
            bn=chain_bones(root); k=len(bn)
            for n_ in bn: B.pose.bones[n_].matrix_basis=Matrix()
            bpy.context.view_layer.update()
            for n_ in bn:
                pb=B.pose.bones[n_]; h=pb.head.copy(); pb.matrix=Matrix.Translation(h)@Matrix.Rotation(math.radians(deg/k),4,AXW(axis_w))@Matrix.Translation(-h)@pb.matrix
                bpy.context.view_layer.update()
        def uncurl(root):
            for n_ in chain_bones(root): B.pose.bones[n_].matrix_basis=Matrix()
            bpy.context.view_layer.update()
        def pen_of(root):
            return int(hair_body_pen().get(root,0))
        def signs(root,side):
            s_sw,s_lf=chain_signs(root,side); return s_sw,s_lf
        DONE=[]
        # fix 3: the two long front locks only, forward (tip away from the chest), smallest angle <= 8 deg that gets each to <= 5 verts inside the body
        if P.get('FRONT_LOCKS',True):
            # run 7b: each bone of the lock, root -> tip, gets the smallest forward angle (<= LOCK_MAX_DEG per bone) that lifts ITS OWN segment off the
            # skin (<= 1 vert > 2 mm inside), so the lock follows her chest instead of swinging out stiffly; stick-out vs 6b <= 10 mm for the whole lock.
            # run 8: penetration counted against body + bra + shirt (white tips through the cups / collarbones), root -> tip, each bone curls OUTWARD
            # (forward, along her chest) by the smallest angle <= LOCK_MAX_DEG that clears its own segment; whole-lock stick-out cap LOCK_STICK (2 cm) so the
            # lock rests ON the shirt; a later bone may curl back in (<= what its parents added) only while its own segment stays clear, so the lock
            # hugs the shirt instead of floating. Gate (checked again after posed clearance): <= 10 lock tris inside body/bra/shirt.
            bmax=float(P.get('LOCK_MAX_DEG',15)); SCAP=float(P.get('LOCK_STICK',0.020))
            TBc=world_bvh([o_ for o_ in (BODY,BRA,SHIRT) if o_ is not None])
            gidx_h={g.name:g.index for g in HR.vertex_groups}
            def seg_verts(bname):
                gi_=gidx_h.get(bname)
                if gi_ is None: return np.zeros(0,dtype=np.int64)
                out=[]
                for v in HR.data.vertices:
                    ws=[(ge.weight,ge.group) for ge in v.groups if ge.weight>0]
                    if ws and max(ws)[1]==gi_: out.append(v.index)
                return np.array(out,dtype=np.int64)
            def sd_c(idx,Xe):
                S_=np.full(len(idx),0.06)
                for k_,i in enumerate(idx):
                    p=Vector(tuple(Xe[i])); lb,nb_,_,_=TBc.find_nearest(p,0.06)
                    if lb is not None: S_[k_]=(p-lb).dot(nb_)
                return S_
            def pen_idx(idx,Xe): return int((sd_c(idx,Xe)<-0.001).sum())
            def rot_bone(bn_,deg):
                pb=B.pose.bones[bn_]; h=pb.head.copy(); pb.matrix=Matrix.Translation(h)@Matrix.Rotation(math.radians(deg),4,AXW((1,0,0)))@Matrix.Translation(-h)@pb.matrix
                bpy.context.view_layer.update()
            for root,side in (('Blw_Front_L','L'),('Blw_Front_R','R')):
                if root not in B.pose.bones: H7[root]={'missing':True}; continue
                s_sw,s_lf=signs(root,side); idx=chain_verts(root); uncurl(root); Xe=hair_world_eval()
                rec={'pen_before_body':pen_of(root),'pen_before_body_bra_shirt':pen_idx(idx,Xe),'lift_sign':s_lf,'stick_cap_mm':SCAP*1000,'per_bone':[]}
                acc=0
                for bn_ in chain_bones(root):
                    sv=seg_verts(bn_); Xe=hair_world_eval(); pb0=pen_idx(sv,Xe); best=(0,pb0,0.0); mb0=B.pose.bones[bn_].matrix_basis.copy()
                    if pb0>1:
                        cand=None
                        for a in range(1,int(bmax)+1):
                            B.pose.bones[bn_].matrix_basis=mb0.copy(); bpy.context.view_layer.update(); rot_bone(bn_,s_lf*a)
                            Xe=hair_world_eval(); pa=pen_idx(sv,Xe); so=stick_out(idx,Xe)
                            if so>SCAP: break
                            if cand is None or pa<cand[1]: cand=(a,pa,so)
                            if pa<=1: break
                        if cand is not None and cand[1]<pb0: best=cand
                    elif acc>0 and len(sv):
                        # hug: curl back in toward the shirt while this segment stays clear (>= 1 mm outside) - never past what the parents added
                        for a in range(1,int(min(acc,bmax))+1):
                            B.pose.bones[bn_].matrix_basis=mb0.copy(); bpy.context.view_layer.update(); rot_bone(bn_,-s_lf*a)
                            Xe=hair_world_eval(); S_=sd_c(sv,Xe)
                            if (S_<0.001).sum()>1: break
                            best=(-a,int((S_<-0.001).sum()),stick_out(idx,Xe))
                    B.pose.bones[bn_].matrix_basis=mb0.copy(); bpy.context.view_layer.update()
                    if best[0]: rot_bone(bn_,s_lf*best[0])
                    acc+=best[0]
                    rec['per_bone'].append((bn_,int(len(sv)),pb0,best[0],best[1],round(best[2]*1000,1)))
                Xe=hair_world_eval()
                rec['pen_after_body']=pen_of(root); rec['pen_after_body_bra_shirt']=pen_idx(idx,Xe); rec['stick_out_mm']=round(stick_out(idx,Xe)*1000,1)
                rec['angle_deg']=max([abs(t[3]) for t in rec['per_bone']]+[0])
                if rec['angle_deg']>0: DONE.append(root)
                H7[root]=rec
        # fix 7 / variant A1: curl ONLY the chain that covers each eye (right: Blw_Bangs_R), smallest angle <= 15 deg (lift, sweep, or both) that gets
        # that eye under 15 % in every proof view, with the wing check (stick-out <= 10 mm vs 6b). A0 keeps the bang 1:1.
        if P.get('BANG_LIFT'):
            m_=metrics(); H7['eyes_before_lift']={'eye_max_pct':m_['eye_max_pct'],'eye_chains':m_['eye_chains']}
            ec,_,TVH_=cover(EYEP,CAMS,EYE_VIEWS)
            def eye_pct(e,sd): return max(e[vw][sd]['pct'] for vw in e)
            for sd in ('R','L'):
                e0,h0,TV0=cover({sd:EYEP[sd]},CAMS,EYE_VIEWS); p_=max(e0[vw][sd]['pct'] for vw in e0)
                rec={'eye':sd,'pct_before':p_}
                if p_<15: rec['note']='already under 15 %'; H7['bang_'+sd]=rec; continue
                ch=chain_of_tris(h0,TV0); cands=[c for c,_ in ch.most_common() if c in B.pose.bones and c not in DONE]
                if sd=='R' and 'Blw_Bangs_R' in cands: cands=['Blw_Bangs_R']
                if not cands: rec['note']='no posable chain'; H7['bang_'+sd]=rec; continue
                root=cands[0]; rec['chain']=root; idx=chain_verts(root); tried=[]; pick=None
                # run 7b: both signs, three world axes, whole-chain curl AND root-only swing, 3..15 deg
                def apply_b(mode,ax,sg,a):
                    uncurl(root)
                    if mode=='curl': curl(root,sg*a,ax)
                    else:
                        pb=B.pose.bones[root]; h=pb.head.copy(); pb.matrix=Matrix.Translation(h)@Matrix.Rotation(math.radians(sg*a),4,AXW(ax))@Matrix.Translation(-h)@pb.matrix; bpy.context.view_layer.update()
                for a in (3,6,9,12,15):
                    for mode in ('curl','swing'):
                        for ax in ((1,0,0),(0,1,0),(0,0,1)):
                            for sg in (1,-1):
                                apply_b(mode,ax,sg,a)
                                e1,_,_=cover({sd:EYEP[sd]},CAMS,EYE_VIEWS); p1=max(e1[vw][sd]['pct'] for vw in e1); so=stick_out(idx,hair_world_eval())
                                fc=face_cross()['hair_tris_crossing_face_below_brow']
                                tried.append((a,mode,'xyz'[ax.index(1)],sg,p1,round(so*1000,1),fc))
                    good=[t for t in tried if t[0]==a and t[4]<15 and t[5]<=10.0 and t[6]<=CROSS_MAX]
                    if good: pick=min(good,key=lambda t:(t[4],t[5])); break
                uncurl(root)
                ok=[t for t in tried if t[5]<=10.0 and t[6]<=CROSS_MAX]
                bestok=min(ok,key=lambda t:(t[4],t[0])) if ok else None
                rec['best_within_limits']=bestok
                if pick is None and bestok is not None and bestok[4]<=p_-5: pick=bestok; rec['note']='15 % not reachable within 15 deg + 10 mm stick-out; applied the best within limits'
                elif pick is None: rec['note']='15 % not reachable and nothing within limits helps by >= 5 points; bang left 1:1'
                if pick:
                    a,mode,axn,sg=pick[0],pick[1],pick[2],pick[3]; apply_b(mode,{'x':(1,0,0),'y':(0,1,0),'z':(0,0,1)}[axn],sg,a)
                    DONE.append(root); rec.update({'angle_deg':a,'mode':mode,'axis':axn,'sign':sg,'pct_after':pick[4],'stick_out_mm':pick[5],'face_cross':pick[6]})
                rec['tried']=tried; H7['bang_'+sd]=rec; log('A1 bang',sd,{k:v for k,v in rec.items() if k!='tried'})
        # bake the chosen chain poses into her rig's rest (pose applied to those hair bones + the hair mesh written in that pose) so the .blend/.fbx carry it
        if DONE:
            bake=[n_ for r_ in DONE for n_ in [r_]+[c.name for c in B.pose.bones[r_].children_recursive]]
            Xe=hair_world_eval(); mwi_=np.linalg.inv(np.array(HR.matrix_world)); XL=Xe@mwi_[:3,:3].T+mwi_[:3,3]
            n_h2=len(HR.data.vertices)
            if len(XL)==n_h2:
                bpy.context.view_layer.objects.active=B; bpy.ops.object.mode_set(mode='POSE')
                for pb in B.pose.bones: pb.bone.select=pb.name in bake
                bpy.ops.pose.armature_apply(selected=True)
                for pb in B.pose.bones: pb.bone.select=False
                bpy.ops.object.mode_set(mode='OBJECT')
                if HR.data.shape_keys:
                    a=np.empty(n_h2*3); HR.data.vertices.foreach_get('co',a); dl=XL-a.reshape(-1,3)
                    for kb in HR.data.shape_keys.key_blocks:
                        b_=np.empty(n_h2*3); kb.data.foreach_get('co',b_); kb.data.foreach_set('co',(b_.reshape(-1,3)+dl).ravel())
                HR.data.vertices.foreach_set('co',XL.ravel()); HR.data.update(); bpy.context.view_layer.update()
                for n_ in bake: B.pose.bones[n_].matrix_basis=Matrix()
                bpy.context.view_layer.update()
                drift=float(np.linalg.norm(hair_world_eval()-Xe,axis=1).max())
                H7['baked']={'bones':len(bake),'roots':DONE,'max_drift_mm_after_bake':round(drift*1000,3)}
            else: H7['baked']={'error':'evaluated vertex count differs; kept as pose','roots':DONE}
            for r_ in DONE: BANG.pop(r_,None)
        H7['body_pen_after']=dict(hair_body_pen())
        rep['hair_run7']=H7; log('HAIR run7',json.dumps(H7,default=str)[:2500])
    except Exception as e: traceback.print_exc(); log('HAIR7ERR',e); rep['hair_run7_error']=str(e)
    mf=metrics(); rep['eyes_after']=mf; log('EYES after',json.dumps(mf,default=str)[:1500],'BANG',list(BANG))
except Exception as e: traceback.print_exc(); log('EYECHECKERR',e); rep['eyecheck_error']=str(e)

# ---------- run 6 QA jobs (separate Actions shards; nothing here touches the saved files)
def _img_magenta(path):
    try:
        im=bpy.data.images.load(path); a=np.empty(im.size[0]*im.size[1]*4,dtype=np.float32); im.pixels.foreach_get(a); bpy.data.images.remove(im)
        a=a.reshape(-1,4); m=(a[:,0]>0.85)&(a[:,1]<0.15)&(a[:,2]>0.85); return round(float(m.mean())*100,4)
    except Exception as e: return str(e)
def _setcam(target,az,el,dist,lens=50):
    d=Vector((math.cos(math.radians(el))*math.sin(math.radians(az)),-math.cos(math.radians(el))*math.cos(math.radians(az)),math.sin(math.radians(el))))
    cam.location=target+d*dist; cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.lens=lens; cam.data.sensor_fit='VERTICAL'; cam.data.sensor_height=24
    cam.data.clip_start=0.01; cam.data.clip_end=dist*6
def _signed_to_q(T,V,maxd=0.1):
    S=[]
    for p in V:
        loc,nr,idx,d=T.find_nearest(Vector(tuple(p)),maxd)
        if loc is not None: S.append((Vector(tuple(p))-loc).dot(nr))
    return np.array(S) if S else np.zeros(1)
def qa_sweep():
    sh=int(os.environ.get('QA_SHARD','0')); n=int(os.environ.get('QA_SHARDS','1')); os.makedirs(OUT+'/sweep',exist_ok=True)
    pose_relaxed(); vis=[o for o in MESHES if not o.hide_render]; mn,mx=bbox(vis); cx,cy=(mn.x+mx.x)/2,(mn.y+mx.y)/2
    bz=lambda b:float((B.matrix_world@B.pose.bones[b].head).z) if b in B.pose.bones else None
    ez=float(EYE_TOP_Z)-0.01; kz=bz('Right knee') or (mn.z+0.37); hz=bz('Hips'); 
    RINGS=[('top-down',mx.z-0.03,72,0.95),('crown',mx.z-0.07,38,0.9),('face',ez,8,0.85),('neck',bz('Neck') or ez-0.12,8,0.85),('chest',(bz('Chest') or hz+0.17)+0.04,6,0.95),
           ('waist',bz('Spine') or hz+0.08,5,0.95),('hips',hz-0.03,4,0.95),('thighs',(hz+kz)/2,3,0.95),('knees',kz,3,0.9),('shins',kz*0.5+0.04,5,0.9),('feet',mn.z+0.06,14,0.85),('ground-up',mn.z+0.03,-22,0.9)]
    jobs=[(k,a) for k in range(len(RINGS)) for a in range(0,360,15)]; per=(len(jobs)+n-1)//n; mine=jobs[sh*per:(sh+1)*per]
    sc.render.resolution_x=sc.render.resolution_y=640; sc.render.resolution_percentage=100; sc.cycles.samples=int(P.get('SWEEP_SAMPLES',10)); sc.render.use_persistent_data=True
    sc.render.image_settings.file_format='JPEG'; sc.render.image_settings.quality=88
    out={'variant':VAR,'rings':[(r[0],round(r[1],3),r[2]) for r in RINGS],'stills':{}}
    for k,a in mine:
        nmr,z,el,dist=RINGS[k]; _setcam(Vector((cx,cy,z)),a,el,dist)
        pth=OUT+f'/sweep/ring_{k:02d}_angle_{a:03d}.jpg'; sc.render.filepath=pth
        try: bpy.ops.render.render(write_still=True); out['stills'][os.path.basename(pth)]={'magenta_pct':_img_magenta(pth)}
        except Exception as e: out['stills'][os.path.basename(pth)]={'error':str(e)}
        log('still',k,a)
    if sh==0:
        # geometric clipping per ring band, relaxed pose: clothing verts inside the body (body shows through) and hair inside the face
        TBq=world_bvh([BODY]); band={}
        for o in [x for x in (SHIRT,BRA,SH) if x is not None and not x.hide_render]:
            V_,F_,_=tri_arr(o)
            for k,(nmr,z,el,dist) in enumerate(RINGS):
                m=np.abs(V_[:,2]-z)<0.06
                if m.any():
                    Sm=_signed_to_q(TBq,V_[m],0.06)
                    band.setdefault(nmr,{})[o.name]={'verts':int(m.sum()),'inside_body_gt_1mm':int((Sm<-0.001).sum()),'min_mm':round(float(Sm.min())*1000,2)}
        out['clipping_by_ring_relaxed_pose']=band; out['hair_through_face_below_brow']=face_cross()
    json.dump(out,open(OUT+f'/sweep/sweep-{VAR}-shard{sh}.json','w'),indent=1,default=str)
QA_ANIM=[(0,36,'head turn L/R'),(36,60,'nod'),(60,90,'eyes L/R/up/down'),(90,120,'blink + visemes aa/oh/ee'),(120,150,'spine twist + bend'),(150,190,'arms raise/forward + elbow bend'),
         (190,225,'fingers curl + spread'),(225,265,'leg raise + knee bend + squat'),(265,280,'toes curl'),(280,300,'head shake + hair swing')]
def anim_pose(f):
    pose_relaxed(); KB=FH.data.shape_keys.key_blocks if FH.data.shape_keys else {}
    for k in ('vrc.blink_left','vrc.blink_right','vrc.v_aa','vrc.v_oh','vrc.v_e'):
        if k in KB: KB[k].value=0.0
    seg=[x for x in QA_ANIM if x[0]<=f<x[1]][0]; u=(f-seg[0])/(seg[1]-seg[0]); S=math.sin(2*math.pi*u); E=math.sin(math.pi*u)
    nm_=seg[2]
    if nm_=='head turn L/R': wrot('Head',40*S,'Z')
    elif nm_=='nod': wrot('Head',22*S,'X')
    elif nm_.startswith('eyes'):
        q=int(u*4)%4; a=math.sin(math.pi*((u*4)%1))
        for e_ in ('LeftEye','RightEye'):
            if q==0: wrot(e_,22*a,'Z')
            elif q==1: wrot(e_,-22*a,'Z')
            elif q==2: wrot(e_,-14*a,'X')
            else: wrot(e_,14*a,'X')
    elif nm_.startswith('blink'):
        q=int(u*4)%4; a=math.sin(math.pi*((u*4)%1)); key={0:('vrc.blink_left','vrc.blink_right'),1:('vrc.v_aa',),2:('vrc.v_oh',),3:('vrc.v_e',)}[q]
        for k in key:
            if k in KB: KB[k].value=a
    elif nm_.startswith('spine'):
        wrot('Spine',25*math.sin(2*math.pi*min(u*2,1)) if u<0.5 else 0,'Z'); 
        if u>=0.5: wrot('Chest',20*math.sin(2*math.pi*(u-0.5)),'X')
    elif nm_.startswith('arms'):
        q=int(u*3)%3; a=math.sin(math.pi*((u*3)%1))
        for sd,sg in (('Left',1),('Right',-1)):
            if q==0: wrot(sd+' arm',-sg*100*a,'Y')
            elif q==1: wrot(sd+' arm',-60*a,'X')
            else: wrot(sd+' elbow',-95*a,'X')
    elif nm_.startswith('fingers'):
        a=E
        for sd,sg in (('Left',1),('Right',-1)):
            for f_ in ('IndexFinger','MiddleFinger','RingFinger','LittleFinger'):
                for j in (1,2,3): wrot(f'{f_}{j}_{sd[0]}',sg*(60*a if u<0.6 else 0),'Y')
                if u>=0.6: wrot(f'{f_}1_{sd[0]}',{'IndexFinger':-1,'MiddleFinger':0,'RingFinger':1,'LittleFinger':2}[f_]*10*math.sin(math.pi*(u-0.6)/0.4),'Z')
            for j in (0,1,2): wrot(f'Thumb{j}_{sd[0]}',sg*35*a,'Y')
    elif nm_.startswith('leg'):
        q=int(u*3)%3; a=math.sin(math.pi*((u*3)%1))
        if q==0: wrot('Left leg',-55*a,'X')
        elif q==1: wrot('Right leg',-30*a,'X'); wrot('Right knee',85*a,'X')
        else:
            hp=B.pose.bones['Hips']; hp.matrix=Matrix.Translation(B.matrix_world.inverted().to_3x3()@Vector((0,0,-0.16*a)))@hp.matrix; bpy.context.view_layer.update()
            for sd in ('Left','Right'): wrot(sd+' leg',-65*a,'X'); wrot(sd+' knee',115*a,'X'); wrot(sd+' ankle',-45*a,'X')
    elif nm_.startswith('toes'):
        for sd in ('Left','Right'): wrot(sd+' toe',35*S,'X')
    else:
        wrot('Head',30*math.sin(4*math.pi*u),'Z')
        for r_ in [b.name for b in B.pose.bones if b.parent and ((b.name.startswith('Blw_') and b.parent.name=='Head') or b.parent.name=='Hair Root')]: wrot(r_,14*math.sin(4*math.pi*u+0.6),'Y')
    bpy.context.view_layer.update()
def qa_rig():
    sh=int(os.environ.get('QA_SHARD','0')); n=int(os.environ.get('QA_SHARDS','1')); os.makedirs(OUT+'/rigqa',exist_ok=True)
    pose_relaxed(); vis=[o for o in MESHES if not o.hide_render]; mn,mx=bbox(vis)
    H=mx.z-mn.z; ctr=Vector(((mn.x+mx.x)/2,(mn.y+mx.y)/2,mn.z+0.5*H))
    rest(); REST={}
    for o in vis:
        V_,F_,_=tri_arr(o); E_=np.array([tuple(e.vertices) for e in o.data.edges],dtype=np.int64); L0=np.linalg.norm(V_[E_[:,0]]-V_[E_[:,1]],axis=1) if len(E_) else np.zeros(0)
        gi={g.index:g.name for g in o.vertex_groups}; mb=[]
        for v in o.data.vertices:
            gs=[(ge.weight,gi[ge.group]) for ge in v.groups if ge.weight>0 and gi.get(ge.group) in B.pose.bones]; mb.append(max(gs)[1] if gs else None)
        REST[o.name]={'V':V_,'E':E_,'L0':L0,'mb':mb}
    RB={pb.name:(B.matrix_world@pb.matrix).copy() for pb in B.pose.bones}
    RBi={k:v.inverted() for k,v in RB.items()}; BODYPOLYS=[tuple(p.vertices) for p in BODY.data.polygons]
    eyesel={sd:[i for p in FH.data.polygons if p.material_index in FH_EYE_MATS for i in p.vertices if (FH.matrix_world@FH.data.vertices[i].co).x*(1 if sd=='L' else -1)>0] for sd in ('L','R')}
    eyerest={sd:REST[FH.name]['V'][sorted(set(ix))] for sd,ix in eyesel.items()}
    JOINTS=[(j,p) for j,p in (('Left wrist','Left elbow'),('Right wrist','Right elbow'),('Left elbow','Left arm'),('Right elbow','Right arm'),('Left knee','Left leg'),('Right knee','Right leg'),('Left arm','Left shoulder'),('Right arm','Right shoulder')) if j in B.pose.bones and p in B.pose.bones]
    def joint_rad(Vb,M):
        out={}
        for j,p in JOINTS:
            hj=(M[j]).translation; hp_=(M[p]).translation; ax=(hj-hp_).normalized()
            d=Vb-np.array(tuple(hj)); m=np.linalg.norm(d,axis=1)<0.045
            if m.sum()<10: continue
            proj=d[m]-np.outer(d[m]@np.array(tuple(ax)),np.array(tuple(ax))); out[j]=float(np.linalg.norm(proj,axis=1).mean())
        return out
    rad0=joint_rad(REST[BODY.name]['V'],RB)
    NF=300; per=(NF+n-1)//n; fr=range(sh*per,min(NF,(sh+1)*per))
    sc.render.resolution_x,sc.render.resolution_y=480,854; sc.cycles.samples=int(P.get('RIGQA_SAMPLES',6)); sc.render.image_settings.file_format='JPEG'; sc.render.image_settings.quality=86
    res={'frames':{},'segments':QA_ANIM,'toe_bones':[b for b in ('Left toe','Right toe') if b in B.data.bones],'jaw_bone':[b.name for b in B.data.bones if 'jaw' in b.name.lower()]}
    TBq=None
    for f in fr:
        anim_pose(f); rf={}
        PB={pb.name:(B.matrix_world@pb.matrix).copy() for pb in B.pose.bones}; DB={k:PB[k]@RBi[k] for k in PB}
        cur={o.name:tri_arr(o)[0] for o in vis}
        for o in vis:
            Rr=REST[o.name]; Vp=cur[o.name]
            if len(Rr['E']):
                L1=np.linalg.norm(Vp[Rr['E'][:,0]]-Vp[Rr['E'][:,1]],axis=1); r_=L1/np.maximum(Rr['L0'],1e-7); st=int(((r_>1.4)|(r_<0.6)).sum())
            else: st=0
            # vertices not following their main bone: posed vs rigid transform of that bone (beyond 6 cm)
            far=0
            for i in range(0,len(Vp),3):
                b=Rr['mb'][i]
                if b is None: continue
                q=DB[b]@Vector(tuple(Rr['V'][i]))
                if (Vector(tuple(Vp[i]))-q).length>0.06: far+=1
            rf[o.name]={'stretch_edges_gt40pct':st,'verts_off_bone_gt6cm_x3':far}
        if f%2==0:
            TBq=BVHTree.FromPolygons([tuple(p) for p in cur[BODY.name]],BODYPOLYS)
            for o in [x for x in (SHIRT,BRA,SH,HR) if x is not None and x in vis]:
                Vp=cur[o.name][::2]; c3=0; mn_=0.0
                for p in Vp:
                    loc,nr,idx,d=TBq.find_nearest(Vector(tuple(p)),0.03)
                    if loc is None: continue
                    sdd=(Vector(tuple(p))-loc).dot(nr)
                    if sdd<-0.003: c3+=1
                    mn_=min(mn_,sdd)
                rf[o.name]['inside_body_gt3mm_x2']=c3; rf[o.name]['min_signed_mm']=round(mn_*1000,1)
        rad=joint_rad(cur[BODY.name],PB); rf['joint_radius_ratio']={j:round(rad[j]/rad0[j],3) for j in rad if j in rad0}
        ey={}
        for sd,ix in eyesel.items():
            ix=sorted(set(ix)); cp=cur[FH.name][ix]; c0=eyerest[sd]; bn_='LeftEye' if sd=='L' else 'RightEye'
            if bn_ in PB:
                hb_=np.array(tuple(PB[bn_].translation)); hb0_=np.array(tuple(RB[bn_].translation))
                lc=PB[bn_].inverted()@Vector(tuple(cp.mean(0))); lc0=RB[bn_].inverted()@Vector(tuple(c0.mean(0)))
                ey[sd]={'centre_shift_in_eye_bone_space_mm':round(float((lc-lc0).length)*1000,2),'radius_change_mm':round(float(np.linalg.norm(cp-hb_,axis=1).max()-np.linalg.norm(c0-hb0_,axis=1).max())*1000,2)}
        rf['eyes']=ey
        res['frames'][f]=rf
        for vw,az in (('front',0),('q34',-45)):
            _setcam(ctr,az,4,H*1.25/(24/50)*1.0,50); sc.render.filepath=OUT+f'/rigqa/f{f:03d}_{vw}.jpg'
            try: bpy.ops.render.render(write_still=True)
            except Exception as e: log('RQERR',f,e)
        log('rigqa frame',f)
    json.dump(res,open(OUT+f'/rigqa/rigqa-shard{sh}.json','w'),indent=1,default=str)

# ---------- run 6 QA-run: EXHAUSTIVE bone + shape-key pass and Jena's body schema (Saidie 12:55). Separate Actions run; shards over bones / shape keys.
HUMANOID={'Hips':'Hips','Spine':'Spine','Chest':'Chest','Neck':'Neck','Head':'Head','LeftEye':'LeftEye','RightEye':'RightEye',
  'Left shoulder':'LeftShoulder','Left arm':'LeftUpperArm','Left elbow':'LeftLowerArm','Left wrist':'LeftHand','Right shoulder':'RightShoulder','Right arm':'RightUpperArm','Right elbow':'RightLowerArm','Right wrist':'RightHand',
  'Left leg':'LeftUpperLeg','Left knee':'LeftLowerLeg','Left ankle':'LeftFoot','Left toe':'LeftToes','Right leg':'RightUpperLeg','Right knee':'RightLowerLeg','Right ankle':'RightFoot','Right toe':'RightToes'}
for sd,S1 in (('L','Left'),('R','Right')):
    for f_,U in (('Thumb','Thumb'),('IndexFinger','Index'),('MiddleFinger','Middle'),('RingFinger','Ring'),('LittleFinger','Little')):
        js=(0,1,2) if f_=='Thumb' else (1,2,3)
        for j,nmj in zip(js,('Proximal','Intermediate','Distal')): HUMANOID[f'{f_}{j}_{sd}']=f'{S1}{U}{nmj}'
def region_of(n):
    l=n.lower()
    if n.startswith('Blw_') or n.startswith(('Bangs','piggy','Back hair','Hair Root')): return 'hair'
    if 'eye' in l: return 'eyes'
    if any(k in l for k in ('finger','thumb')): return 'hands/fingers'
    if 'toe' in l or 'ankle' in l: return 'feet'
    if any(k in l for k in ('wrist','elbow','arm','shoulder')): return 'arms'
    if any(k in l for k in ('leg','knee','butt','ass_')): return 'legs/hips'
    if any(k in l for k in ('boob','breast')): return 'chest'
    if any(k in l for k in ('head','neck','cheek','tongue','drool','earring')): return 'head/neck'
    return 'torso'
def limit_of(n):
    l=n.lower()
    if 'eye' in l: return 25
    if any(k in l for k in ('spine','chest','neck','hips')): return 25
    if 'toe' in l: return 30
    return 45
def _evalV(objs): return {o.name:tri_arr(o)[0] for o in objs}
def _desc(b):
    out={b.name}
    for c in b.children_recursive: out.add(c.name)
    return out
def _wmask(o,names,th=0.01):
    gi={g.index:g.name for g in o.vertex_groups}
    return np.array([any(ge.weight>th and gi.get(ge.group) in names for ge in v.groups) for v in o.data.vertices])
def qa_bones():
    sh=int(os.environ.get('QA_SHARD','0')); n=int(os.environ.get('QA_SHARDS','1')); os.makedirs(OUT+'/allbones',exist_ok=True); os.makedirs(OUT+'/training/motion',exist_ok=True)
    rest(); vis=[o for o in MESHES if not o.hide_render]; R0=_evalV(vis)
    EDG={o.name:np.array([tuple(e.vertices) for e in o.data.edges],dtype=np.int64) for o in vis}
    L0={k:np.linalg.norm(R0[k][E[:,0]]-R0[k][E[:,1]],axis=1) for k,E in EDG.items()}
    bones=[b.name for b in B.data.bones]; tests=[(b,ax,sg) for b in bones for ax in ('X','Y','Z') for sg in (1,-1)]
    per=(len(tests)+n-1)//n; mine=tests[sh*per:(sh+1)*per]
    sc.render.resolution_x=sc.render.resolution_y=360; sc.cycles.samples=int(P.get('EXH_SAMPLES',4)); sc.render.image_settings.file_format='JPEG'; sc.render.image_settings.quality=84
    res={}; prev=None
    for b,ax,sg in mine:
        if b!=prev:
            rest(); bd=B.data.bones[b]; D=_desc(bd); MSK={o.name:_wmask(o,D) for o in vis}; prev=b
        rest(); ang=sg*limit_of(b); wrot(b,ang,ax); Vp=_evalV(vis); out={'deg':ang,'axis':ax}
        mv_out=0; mv_in=0; st=0; mx=0.0
        for o in vis:
            d=np.linalg.norm(Vp[o.name]-R0[o.name],axis=1); mvd=d>0.001; m=MSK[o.name]
            mv_in+=int((mvd&m).sum()); oo=int((mvd&~m).sum()); mv_out+=oo
            if oo: out.setdefault('moved_outside_region',{})[o.name]=oo
            E=EDG[o.name]
            if len(E):
                r_=np.linalg.norm(Vp[o.name][E[:,0]]-Vp[o.name][E[:,1]],axis=1)/np.maximum(L0[o.name],1e-7); s_=int(((r_>1.4)|(r_<0.6)).sum()); st+=s_
                if s_: out.setdefault('stretch_by_mesh',{})[o.name]=s_
            mx=max(mx,float(d.max()))
        out.update({'verts_moved_in_region':mv_in,'verts_moved_outside_region':mv_out,'stretch_edges_gt40pct':st,'max_disp_mm':round(mx*1000,1)})
        if 'eye' in b.lower() and b in ('LeftEye','RightEye'):
            sd_=1 if b=='LeftEye' else -1; ix=[i for p in FH.data.polygons if p.material_index in FH_EYE_MATS for i in p.vertices if R0[FH.name][i][0]*sd_>0]; ix=sorted(set(ix))
            hb=np.array(tuple(B.matrix_world@B.pose.bones[b].head)); out['eye_radius_change_mm']=round(float(np.linalg.norm(Vp[FH.name][ix]-hb,axis=1).max()-np.linalg.norm(R0[FH.name][ix]-hb,axis=1).max())*1000,2)
        out['verdict']='PASS' if (mv_out==0 and st==0 and abs(out.get('eye_radius_change_mm',0))<0.5) else 'CHECK'
        key=f'{b}|{ax}{"+" if sg>0 else "-"}'; res[key]=out
        pb=B.pose.bones[b]; tgt=B.matrix_world@pb.head; ext=max(0.12,min(0.9,3.0*max((B.matrix_world@B.pose.bones[c].tail-tgt).length for c in D if c in B.pose.bones)))
        _setcam(tgt,-30,10,ext/(24/50)*1.1,50); fn=f"{b.replace(' ','_')}_{ax}{'p' if sg>0 else 'm'}"
        sc.render.filepath=OUT+f'/allbones/{fn}.jpg'
        try: bpy.ops.render.render(write_still=True)
        except Exception as e: log('EXHERR',e)
        lmk={pb2.name:[round(x,4) for x in (B.matrix_world@pb2.head)] for pb2 in B.pose.bones}
        json.dump({'test':key,'bone':b,'humanoid':HUMANOID.get(b),'rotation':{'axis_armature':ax,'deg':ang},'image':f'allbones/{fn}.jpg','bone_heads_world_m':lmk,'checks':out},open(OUT+f'/training/motion/{fn}.json','w'))
        log('bone',key,out['verdict'])
    json.dump(res,open(OUT+f'/allbones/bones-shard{sh}.json','w'),indent=1,default=str)
def qa_shapes():
    os.makedirs(OUT+'/allshapes',exist_ok=True); rest(); vis=[o for o in MESHES if not o.hide_render]; res={}
    sc.render.resolution_x=sc.render.resolution_y=420; sc.cycles.samples=int(P.get('EXH_SAMPLES',4)); sc.render.image_settings.file_format='JPEG'; sc.render.image_settings.quality=84
    for o in vis:
        if not o.data.shape_keys: continue
        KB=o.data.shape_keys.key_blocks; base=[k for k in KB if k.value>0]; keep={k.name:k.value for k in KB}
        for k in KB: k.value=0.0
        bpy.context.view_layer.update(); V0=tri_arr(o)[0]
        mn_,mx_=V0.min(0),V0.max(0); tgt=Vector(tuple((mn_+mx_)/2)); ext=float(max(mx_-mn_))
        if o is FH: tgt=Vector((float((mn_[0]+mx_[0])/2),float(mn_[1]),float(mn_[2]+0.62*(mx_[2]-mn_[2])))); ext=float(mx_[2]-mn_[2])*0.8
        _setcam(tgt,-20,5,ext/(24/50)*1.15,50); sc.render.filepath=OUT+f'/allshapes/{o.name.replace(" ","_")}__0.jpg'
        try: bpy.ops.render.render(write_still=True)
        except Exception as e: log('SHERR',e)
        for k in KB:
            if k==o.data.shape_keys.reference_key: continue
            k.value=1.0; bpy.context.view_layer.update(); V1=tri_arr(o)[0]; d=np.linalg.norm(V1-V0,axis=1); k.value=0.0
            mvd=d>0.0005; r_={'mesh':o.name,'moved_verts':int(mvd.sum()),'max_disp_mm':round(float(d.max())*1000,2)}
            if mvd.any():
                P_=V0[mvd]; r_['region_bbox_m']=[[round(x,4) for x in P_.min(0)],[round(x,4) for x in P_.max(0)]]
                p99=float(np.percentile(d[mvd],99)); r_['p99_mm']=round(p99*1000,2)
                spike=float(d.max())>0.02 and float(d.max())>5*max(p99,1e-6); r_['spike']=bool(spike)
            else: r_['spike']=False
            r_['verdict']='EMPTY (no effect)' if not mvd.any() else ('CHECK spike' if r_['spike'] else 'PASS')
            safe=''.join(ch if ch.isalnum() else '_' for ch in k.name)
            k.value=1.0; bpy.context.view_layer.update(); sc.render.filepath=OUT+f'/allshapes/{o.name.replace(" ","_")}__{safe}.jpg'
            try: bpy.ops.render.render(write_still=True)
            except Exception as e: log('SHERR',e)
            if 'tummy' in k.name.lower():
                # run 8: does the shirt hem hold over the shorts at Tummy=1? torso close-ups front / side / 3-4 at 0 and 1, plus the hem clearance number
                try:
                    tz=Vector((float((mn_[0]+mx_[0])/2),float((mn_[1]+mx_[1])/2),float(mx_[2])+0.03)); sc.render.resolution_x=sc.render.resolution_y=640
                    TBs=world_bvh([o]) ; tumr={}
                    for val in (0.0,1.0):
                        k.value=val; bpy.context.view_layer.update()
                        if SHIRT is not None:
                            Ts=world_bvh([o]); Vs=tri_arr(SHIRT)[0]; Ss=_signed_to_q(Ts,Vs,0.03); tumr[f'shirt_vs_shorts_min_mm_at_{val:g}']=round(float(Ss.min())*1000,2); tumr[f'shirt_verts_inside_shorts_gt1mm_at_{val:g}']=int((Ss<-0.001).sum())
                        for vn,az in (('front',0),('side',90),('q34',35)):
                            _setcam(tz,az,4,0.62/(24/50),50); sc.render.filepath=OUT+f'/allshapes/TUMMY_{vn}_{int(val)}.jpg'
                            try: bpy.ops.render.render(write_still=True)
                            except Exception as e: log('SHERR',e)
                    k.value=0.0; bpy.context.view_layer.update(); sc.render.resolution_x=sc.render.resolution_y=420; r_['tummy_hem']=tumr; log('TUMMY',tumr)
                except Exception as e: traceback.print_exc(); log('TUMMYERR',e); k.value=0.0
            k.value=0.0; r_['image']=f'allshapes/{o.name.replace(" ","_")}__{safe}.jpg'; res[f'{o.name}|{k.name}']=r_; log('shape',o.name,k.name,r_['verdict'])
        for k in KB: k.value=keep[k.name]
        bpy.context.view_layer.update()
    json.dump(res,open(OUT+'/allshapes/shapes.json','w'),indent=1,default=str)
def body_schema():
    bpy.context.view_layer.objects.active=B; bpy.ops.object.mode_set(mode='EDIT'); rolls={e.name:round(math.degrees(e.roll),2) for e in B.data.edit_bones}; bpy.ops.object.mode_set(mode='OBJECT')
    mw=B.matrix_world; out={'armature':B.name,'bone_count':len(B.data.bones),'units':'metres, Blender world (Z up, character faces -Y)','bones':[],'meshes':{}}
    for b in B.data.bones:
        out['bones'].append({'name':b.name,'parent':b.parent.name if b.parent else None,'children':[c.name for c in b.children],'head_rest_m':[round(x,4) for x in mw@b.head_local],
            'tail_rest_m':[round(x,4) for x in mw@b.tail_local],'length_m':round(b.length*mw.to_scale()[0],4),'roll_deg':rolls.get(b.name),'region':region_of(b.name),'humanoid':HUMANOID.get(b.name),
            'test_range_deg':limit_of(b.name)})
    for o in MESHES:
        gi=Counter(); [gi.update([o.vertex_groups[ge.group].name]) for v in o.data.vertices for ge in v.groups if ge.weight>0.3]
        out['meshes'][o.name]={'verts':len(o.data.vertices),'shape_keys':[k.name for k in o.data.shape_keys.key_blocks] if o.data.shape_keys else [],'main_bones':dict(gi.most_common(12))}
    json.dump(out,open(OUT+'/training/body-schema.json','w'),indent=1)
# ---------- run 7 (RUN6B fix 2, second half): clearance pass in the POSED idle (frame 0) and squat (frame 258) of the rig motion test. Shirt verts that sink
#            into the posed body are pushed out there; the push is carried back to the rest mesh through each vertex's own skinning matrix (inverse LBS),
#            group-coherent (seams/shells move together) and Laplacian-smoothed. Rest pose only gets pushed OUT, never in.
def _skin_mats(o):
    names=[g.name for g in o.vertex_groups]; mw=np.array(B.matrix_world); mwi=np.linalg.inv(mw); S=[]
    for nm_ in names:
        if nm_ in B.pose.bones:
            pb=B.pose.bones[nm_]; S.append(mw@np.array(pb.matrix)@np.linalg.inv(np.array(pb.bone.matrix_local))@mwi)
        else: S.append(np.eye(4))
    S=np.array(S); n=len(o.data.vertices); Wm=np.zeros((n,len(names)))
    for v in o.data.vertices:
        for ge in v.groups: Wm[v.index,ge.group]=ge.weight
    s=Wm.sum(1); s[s==0]=1; Wm/=s[:,None]
    return np.einsum('ng,gab->nab',Wm,S)
def _posed_signed(o):
    TB=world_bvh([BODY]); V,_,_=tri_arr(o); S=np.ones(len(V)); N=np.zeros_like(V)
    for i,p in enumerate(V):
        loc,nr,idx,d=TB.find_nearest(Vector(tuple(p)),0.06)
        if loc is None: continue
        S[i]=(Vector(tuple(p))-loc).dot(nr); N[i]=tuple(nr)
    return S,N
def posed_clear(o,frames=(0,258),off=0.002):
    r={'frames':list(frames),'passes':[]}
    for it in range(int(P.get('POSED_ITERS',3))):
        Drest=np.zeros((len(o.data.vertices),3)); st={}
        for f in frames:
            anim_pose(f); S,N=_posed_signed(o); m=(S>-0.06)&(S<off)
            st[f]={'lt_minus3mm':int((S<-0.003).sum()),'min_mm':round(float(S[S>-0.06].min())*1000,1)}
            if m.any():
                M=_skin_mats(o); dp=N*(off-S)[:,None]; dp[~m]=0
                R=np.linalg.inv(M[:,:3,:3]+np.eye(3)*1e-9); dr=np.einsum('nab,nb->na',R,dp)
                k=np.linalg.norm(dr,axis=1)>np.linalg.norm(Drest,axis=1); Drest[k]=dr[k]
        rest()
        r['passes'].append({'iter':it,'per_frame_before':st,'verts_pushed':int((np.linalg.norm(Drest,axis=1)>1e-5).sum()),'max_mm':round(float(np.linalg.norm(Drest,axis=1).max())*1000,1)})
        if (np.linalg.norm(Drest,axis=1)>1e-5).sum()==0: break
        Drest=group_max(o,Drest); Drest=smooth_field(o,Drest,iters=15,cap=float(P.get('PUSH_CAP',0.025))); set_world(o,wco(o)+Drest)
        if P.get('POSED_WELD_EACH',False): weld_snap(o,f'posed{it}')
    fin={}
    for f in frames:
        anim_pose(f); S,_=_posed_signed(o); fin[f]={'lt_minus3mm':int((S<-0.003).sum()),'min_mm':round(float(S[S>-0.06].min())*1000,1)}
    rest(); r['after']=fin; r['weld']=weld_snap(o,'posed')
    rep['posed_clear']=r; log('POSED clear',json.dumps(r,default=str)[:1500])
if SHIRT is not None and P.get('POSED_CLEAR',True):
    try: posed_clear(SHIRT,frames=tuple(int(x) for x in P.get('POSED_FRAMES',(0,258))))
    except Exception as e: traceback.print_exc(); log('POSEDCLEARERR',e); rep['posed_clear_error']=str(e); rest()

# ---------- run 8 (Saidie 3:38 PM screenshot, HARD gate): no dark slits/specks at the band/sleeve seam. After everything else, the shirt's INNER shell is
#            kept flush behind its OUTER shell in the proof (relaxed) pose and at rest: inner-layer verts at/outside the outer surface go 0.8 mm behind it,
#            carried back to the rest mesh through their own skinning (inverse LBS). Only the hidden inner layer moves; the visible outer layer is untouched.
def shirt_shell_flush(o,gap=0.0008):
    r={'passes':[]}
    me=o.data
    for pose_nm in ('relaxed','rest','relaxed'):
        if pose_nm=='rest': rest()
        else: pose_relaxed()
        V,F,_=tri_arr(o); V=V.astype(np.float64); F=F.astype(np.int64)
        TB=world_bvh([BODY])
        C_=V[F].mean(1); N_=np.cross(V[F[:,1]]-V[F[:,0]],V[F[:,2]]-V[F[:,0]]); nl=np.linalg.norm(N_,axis=1); ok=nl>1e-12; N_[ok]/=nl[ok][:,None]
        side=np.zeros(len(F))
        for k,c in enumerate(C_):
            loc,nr,_,d=TB.find_nearest(Vector(tuple(c)),0.10)
            if loc is None or not ok[k]: continue
            dv=c-np.array(loc); dn=np.linalg.norm(dv)
            side[k]=float(np.dot(N_[k],dv/dn)) if dn>1e-6 else float(np.dot(N_[k],np.array(nr)))
        outer=side>0.25; inner=side<-0.25
        if outer.sum()<10 or inner.sum()<10: r['passes'].append({'pose':pose_nm,'skipped':'no two-layer split','outer':int(outer.sum()),'inner':int(inner.sum())}); continue
        TO=BVHTree.FromPolygons(V.tolist(),F[outer].tolist())
        vin=np.zeros(len(V),bool); vout=np.zeros(len(V),bool); vin[F[inner].ravel()]=True; vout[F[outer].ravel()]=True; cand=np.where(vin&~vout)[0]
        dp=np.zeros_like(V); nfix=0
        for i in cand:
            loc,nr,_,d=TO.find_nearest(Vector(tuple(V[i])),0.006)
            if loc is None: continue
            s_=float(np.dot(V[i]-np.array(loc),np.array(nr)))
            if s_>-gap*0.75: dp[i]=np.array(loc)-np.array(nr)*gap-V[i]; nfix+=1
        if nfix:
            M=_skin_mats(o); R=np.linalg.inv(M[:,:3,:3]+np.eye(3)*1e-9); dr=np.einsum('nab,nb->na',R,dp)
            rest(); set_world(o,wco(o)+dr)
        r['passes'].append({'pose':pose_nm,'outer_faces':int(outer.sum()),'inner_faces':int(inner.sum()),'inner_only_verts':int(len(cand)),'flushed':nfix,'max_mm':round(float(np.linalg.norm(dp,axis=1).max())*1000,2)})
    rest(); rep['shirt_shell_flush']=r; log('SHELL flush',json.dumps(r,default=str)[:800])
if SHIRT is not None and P.get('SHELL_FLUSH',True):
    try: shirt_shell_flush(SHIRT)
    except Exception as e: traceback.print_exc(); log('SHELLERR',e); rep['shirt_shell_flush_error']=str(e); rest()
# ---------- run 8: hair gate on the FINAL meshes: hair tris with a vert > 1 mm inside body/bra/shirt, per chain root, at rest and in the proof pose
def hair_final_pen():
    out={}
    try:
        gi_h={g.index:g.name for g in HR.vertex_groups}
        def root_of(vi):
            ws=[(ge.weight,gi_h.get(ge.group,'')) for ge in HR.data.vertices[vi].groups if ge.weight>0]
            if not ws: return '(unweighted)'
            bn_=max(ws)[1]
            if bn_ not in B.data.bones: return bn_
            b=B.data.bones[bn_]
            while b.parent is not None and b.parent.name not in ('Head','Blowout_Root','Hair_root','Hair Root'): b=b.parent
            return b.name
        ROOT=[root_of(v.index) for v in HR.data.vertices]
        for pose_nm in ('rest','relaxed'):
            if pose_nm=='rest': rest()
            else: pose_relaxed()
            dg=bpy.context.evaluated_depsgraph_get(); per={}
            for tag,objs in (('body',[BODY]),('body_bra_shirt',[o_ for o_ in (BODY,BRA,SHIRT) if o_ is not None and not o_.hide_render])):
                V_=[];F_=[];off_=0
                for o_ in objs:
                    e_=o_.evaluated_get(dg); me_=e_.to_mesh(); me_.calc_loop_triangles(); mw_=o_.matrix_world
                    V_+=[tuple(mw_@v.co) for v in me_.vertices]; F_+=[tuple(off_+x for x in t.vertices) for t in me_.loop_triangles]; off_+=len(me_.vertices); e_.to_mesh_clear()
                T=BVHTree.FromPolygons(V_,F_)
                e_=HR.evaluated_get(dg); me_=e_.to_mesh(); mw_=HR.matrix_world; Xh=[mw_@v.co for v in me_.vertices]; polys=[tuple(p.vertices) for p in me_.polygons]; e_.to_mesh_clear()
                zmax=float(hmn[2])+0.02; bad=set()
                for i,p in enumerate(Xh):
                    if p.z>zmax: continue
                    loc,nr,_,_=T.find_nearest(p,0.05)
                    if loc is not None and (p-loc).dot(nr)<-0.001: bad.add(i)
                cnt={}
                for p in polys:
                    if any(x in bad for x in p):
                        k_=ROOT[p[0]]; cnt[k_]=cnt.get(k_,0)+len(p)-2
                per[tag]={'verts_inside_gt1mm':len(bad),'tris_inside':int(sum(cnt.values())),'tris_by_chain':cnt}
            out[pose_nm]=per
        rest()
    except Exception as e: traceback.print_exc(); out['error']=str(e); rest()
    rep['hair_final_pen']=out; log('HAIR final pen',json.dumps(out,default=str)[:900])
try: hair_final_pen()
except Exception as e: log('HFPERR',e)
QA=os.environ.get('QA')
if QA:
    try:
        if QA=='sweep': qa_sweep()
        elif QA=='rigqa': qa_rig()
        elif QA=='bones':
            if os.environ.get('QA_SHARD','0')=='0':
                os.makedirs(OUT+'/training',exist_ok=True)
                try: body_schema()
                except Exception as e: traceback.print_exc(); log('SCHEMAERR',e)
            qa_bones()
        elif QA=='shapes': qa_shapes()
        elif QA=='schema':
            os.makedirs(OUT+'/training',exist_ok=True); body_schema()
            json.dump({k:rep.get(k) for k in ('weld','seam_weight_avg','shirt_post','tummy_clear','shirt_body_weights','posed_clear','strap_rigid','hair_run7','hair_final_pen','shirt_shell_flush','shirt_seam_relax','head_hair_meshes','outfit_retarget','eyes_after')},open(OUT+'/training/run8-fit-report.json','w'),indent=1,default=str)
    except Exception as e: traceback.print_exc(); log('QAERR',e)
    log('QA DONE'); import sys as _s; _s.stdout.flush(); os._exit(0)
if not P['TT'] and not os.environ.get('QA'):

    # ---------- run 6 MEASURE SYSTEM (Saidie 12:46: sizes + alignment + clearance from every angle). Numbers to measure.json; geometry (solo vs assembled, rest pose)
    #            to measure-geom.npz so the multi-angle silhouette IoU sheet is drawn off-runner from exactly these vertices.
    def _hull_perim(P2):
        P2=sorted(set(map(tuple,np.round(P2,5))))
        if len(P2)<3: return 0.0
        def cr(o,a,b): return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
        lo=[];hi=[]
        for p in P2:
            while len(lo)>=2 and cr(lo[-2],lo[-1],p)<=0: lo.pop()
            lo.append(p)
        for p in reversed(P2):
            while len(hi)>=2 and cr(hi[-2],hi[-1],p)<=0: hi.pop()
            hi.append(p)
        H=np.array(lo[:-1]+hi[:-1]); return float(np.linalg.norm(np.roll(H,-1,0)-H,axis=1).sum())
    def _sym(V):
        if len(V)<10: return None
        idx=np.linspace(0,len(V)-1,min(3000,len(V))).astype(int); kd=KDTree(len(V))
        for i,p in enumerate(V): kd.insert(Vector(tuple(p)),i)
        kd.balance(); cx=float(BODYCX); d=[kd.find(Vector((2*cx-V[i,0],V[i,1],V[i,2])))[2] for i in idx]
        return round(float(np.mean(d))*1000,2)
    def _signed_to(T,V,maxd=0.1):
        S=[]
        for p in V:
            loc,nr,idx,d=T.find_nearest(Vector(tuple(p)),maxd)
            if loc is not None: S.append((Vector(tuple(p))-loc).dot(nr))
        return np.array(S) if S else np.zeros(1)
    MEAS={}
    try:
        rest(); ASM={}
        for nm_,o_ in (('body',BODY),('head',FH),('hair',HR),('bra',BRA),('shorts',SH))+((('shirt',SHIRT),) if SHIRT is not None else ()):
            V_,F_,MI_=tri_arr(o_); ASM[nm_]={'V':V_,'F':F_,'MI':MI_}
        BODYCX=float(np.median(ASM['body']['V'][:,0]))
        size={}
        for k in ASM:
            A_=ASM[k]['V']; S_=SOLO[k]['V'] if k in SOLO else None; da=(A_.max(0)-A_.min(0)); raw=np.array(SOLO[k]['raw_dims']) if k in SOLO else None
            e={'dims_m':[round(float(x),4) for x in da]}
            if raw is not None:
                ratio=da/np.maximum(raw,1e-9); expv=SOLO[k]['scale']; e['dims_over_raw']=[round(float(x),4) for x in ratio]; e['expected_scale']=round(expv,4)
                e['max_dev_pct']=round(float(np.max(np.abs(ratio/expv-1)))*100,2); e['gate_le_1pct']=bool(e['max_dev_pct']<=1.0)
            if S_ is not None and len(S_)==len(A_):
                dd=np.linalg.norm(A_-S_,axis=1); e['vertex_shift_vs_solo_mm']={'median':round(float(np.median(dd))*1000,2),'p95':round(float(np.percentile(dd,95))*1000,2),'max':round(float(dd.max())*1000,2)}
            size[k]=e
        HVa=ASM['head']['V']; BVa=ASM['body']['V']; HRa=ASM['hair']['V']
        tz=float(EYE_TOP_Z)-0.004; band=HVa[np.abs(HVa[:,2]-tz)<0.006]
        lm={'head_crown_chin_m':round(float(HVa[:,2].max()-HVa[:,2].min()),4),'head_width_temples_m':round(float(band[:,0].max()-band[:,0].min()),4) if len(band) else None,
            'total_height_m':round(float(max(HVa[:,2].max(),HRa[:,2].max())-BVa[:,2].min()),4)}
        lm['height_over_head']=round(lm['total_height_m']/lm['head_crown_chin_m'],3); lm['hair_width_over_head_width']=round(float(HRa[:,0].max()-HRa[:,0].min())/float(HVa[:,0].max()-HVa[:,0].min()),3)
        bz={b:float((B.matrix_world@B.data.bones[b].head_local).z) for b in ('Hips','Spine','Chest','Neck','Left arm') if b in B.data.bones}
        zs=bz.get('Left arm'); 
        if zs:
            bb_=BVa[np.abs(BVa[:,2]-zs)<0.006]; lm['shoulder_level_width_body_m']=round(float(bb_[:,0].max()-bb_[:,0].min()),4)
            if SHIRT is not None:
                sb_=ASM['shirt']['V'][np.abs(ASM['shirt']['V'][:,2]-zs)<0.006]; lm['shoulder_level_width_shirt_m']=round(float(sb_[:,0].max()-sb_[:,0].min()),4) if len(sb_) else None
        gir={}
        for lbl,z in (('hip_low',bz['Hips']-0.05),('hips',bz['Hips']),('waist',bz['Spine']),('underbust',bz['Chest']),('bust',bz['Chest']+0.06)):
            row={}
            for k in ('body','shorts','shirt','bra'):
                if k not in ASM: continue
                Vv=ASM[k]['V']; m=(np.abs(Vv[:,2]-z)<0.004)&(np.abs(Vv[:,0]-BODYCX)<0.19)
                if m.sum()>8: row[k]=round(_hull_perim(Vv[m][:,:2]),4)
            if 'body' in row:
                for k in list(row):
                    if k!='body': row[k+'_over_body']=round(row[k]/row['body'],3)
            gir[lbl]=dict(z=round(z,4),**row)
        lm['girth_hull_perimeter_m']=gir
        al=dict(ALIGN)
        try:
            fb=boundary(FH); FHV=wco(FH); low=np.array([FHV[i] for i in fb]); low=low[low[:,2]<np.percentile(low[:,2],15)] if len(low) else low
            if len(RING) and len(low): al['head_lowest_rim_vs_body_neck_ring_xy_mm']=round(float(np.linalg.norm(low[:,:2].mean(0)-RING[:,:2].mean(0)))*1000,1); al['note_neck']='her head is an open front shell that sits OVER Panda neck (by design), so this is informative, not a gate'
        except Exception as e: al['neck_ring_err']=str(e)
        for k in ASM: al[f'{k}_centroid_x_vs_body_midplane_mm']=round(float(ASM[k]['V'][:,0].mean()-BODYCX)*1000,2)
        sym={k:_sym(ASM[k]['V']) for k in ASM}; symsolo={k:_sym(SOLO[k]['V']) for k in SOLO}
        al['symmetry_mirror_nn_mean_mm']=sym; al['symmetry_mirror_nn_mean_mm_SOLO']=symsolo
        al['gate_bone_offsets_le_2mm']=bool(all(isinstance(al.get(k),float) and al[k]<=2.0 for k in ('head_bone_vs_panda_head_mm','hair_head_bone_vs_head_bone_mm')))
        TBm=world_bvh([BODY]); cl={}
        for k in ('shirt','bra','shorts'):
            if k not in ASM: continue
            Sx=_signed_to(TBm,ASM[k]['V'],0.08); cl[k+'_vs_body_mm']={'min':round(float(Sx.min())*1000,2),'p5':round(float(np.percentile(Sx,5))*1000,2),'median':round(float(np.median(Sx))*1000,2),'n_lt_-1mm':int((Sx<-0.001).sum()),'n':int(len(Sx))}
        fcx=face_cross(); cl['hair_through_face_below_brow_tris']=fcx['hair_tris_crossing_face_below_brow']
        cl['gate_clothes_no_pen_gt_1mm']=bool(all(v['n_lt_-1mm']==0 for k,v in cl.items() if isinstance(v,dict)))
        MEAS={'size':size,'landmarks':lm,'alignment':al,'clearance':cl,'strap':rep.get('strap_push'),'eyes_after':{k:rep.get('eyes_after',{}).get(k) for k in ('eye_max_pct','cheek_max_pct','cross')}}
        np.savez_compressed(OUT+'/measure-geom.npz',**{f'{w}_{k}_{a}':d[a] for w,D_ in (('solo',SOLO),('asm',ASM)) for k,d in D_.items() for a in ('V','F')})
    except Exception as e: traceback.print_exc(); log('MEASUREERR',e); MEAS['error']=str(e)
    json.dump(MEAS,open(OUT+'/proof/measure.json','w'),indent=1,default=str); log('MEASURE',json.dumps(MEAS,default=str)[:3000])
    # texture audit: every material slot on every mesh, its image textures (missing = magenta in renders)
    try:
        TEXA={}
        for o in MESHES:
            for s_l in o.material_slots:
                m=s_l.material
                if not m: TEXA[f'{o.name}/(empty slot)']='EMPTY'; continue
                ims=[(n.image.name,n.image.colorspace_settings.name,n.image.size[0]>0) for n in (m.node_tree.nodes if m.use_nodes else []) if n.type=='TEX_IMAGE' and n.image]
                linked=[n.image.name for n in (m.node_tree.nodes if m.use_nodes else []) if n.type=='TEX_IMAGE' and n.image and n.outputs[0].is_linked]
                TEXA[f'{o.name}/{m.name}']={'images':ims,'linked':linked,'plain_by_design':m.name in ('BraBlack','ScalpDark') or m.name.lower().startswith('effects')}
        uvs={}
        if SHIRT is not None: uvs={'shirt_uv_layers':[u.name for u in SHIRT.data.uv_layers],'active':SHIRT.data.uv_layers.active.name if SHIRT.data.uv_layers.active else None,'active_render':[u.name for u in SHIRT.data.uv_layers if u.active_render]}
        rep['texture_audit']=TEXA; rep['shirt_uv']=uvs; json.dump({'materials':TEXA,'shirt_uv':uvs},open(OUT+'/proof/texture-audit.json','w'),indent=1,default=str)
    except Exception as e: traceback.print_exc(); log('TEXAERR',e)

json.dump(rep,open(OUT+'/build-report.json','w'),indent=1,default=str)
if SAVE_NAME and not P['TT']:
    try:
        rest()
        try: bpy.ops.file.pack_all()
        except Exception as e: log('PACKERR',e)
        bpy.ops.wm.save_as_mainfile(filepath=OUT+'/'+SAVE_NAME+'.blend',compress=True); log('blend saved')
    except Exception as e: log('BLENDERR',e)
if not P['TT']:
    SET=SETS[P['SET']]
    # A) 1:1 proofs in REST pose (as the solo renders), camera framed on that asset exactly as its solo render was:
    #    asm-<asset>-<view> = the asset ON the assembled avatar ; iso-<asset>-front = the same asset in the assembled file with everything else hidden (untouched check)
    for nm in SET:
        if nm not in ASSETS: continue
        if nm=='outfit-shirt-grey' and OHEAD:
            try: pose_outfit_apose()
            except Exception as e: traceback.print_exc(); log('APOSEERR',e)   # run 6: her shirt was authored in an A-pose -> compare it in that pose
        for v in ('front','q34','back'): shot(f'asm-{nm}-{v}',ASSETS[nm],v)
        st=solo(ASSETS[nm]); shot(f'iso-{nm}-front',ASSETS[nm],'front'); unsolo(st)
        rest()
    sc.cycles.samples=P['SAMPLES']
    pose_relaxed()
    ALL=[o for o in meshes if o.visible_get()]
    hm,hx=bbox([FH])
    if P['SET']=='full':
        for v in ('front','side','back','q34'): shot('pose-'+v,ALL,v,res=(768,1376),pad=1.06)
        shot('face',[FH],'front',res=(1024,1024),pad=1.25); shot('face34',[FH],'q34',res=(1024,1024),pad=1.25)
        if SHIRT is not None: shot('shirt-over-bra-q34',[SHIRT],'q34',res=(1024,1024),pad=1.15)
        shot('skinmatch-face34',[FH],'q34',res=(1024,1024),pad=1.6,zoff=-0.25*(hx.z-hm.z)); shot('skinmatch-neck',[FH],'front',res=(1024,1024),pad=1.5,zoff=-0.55*(hx.z-hm.z))
        shot('neckside',[FH],'side',res=(1024,1024),pad=1.9,zoff=-0.35*(hx.z-hm.z))

        try:
            # run 6 close-ups: sleeves (front/side/back), halter strap (front/side/back), shirt fabric texture
            if SHIRT is not None:
                smn,smx=bbox([SHIRT]); hgt=smx.z-smn.z
                sbox=(Vector((smn.x,smn.y,smx.z-0.55*hgt)),smx)
                for v in ('front','side','back'): shot('sleeves-closeup-'+v,ALL,v,res=(1024,1024),pad=1.05,box=sbox)
                cbox=(Vector((-0.06,smn.y,smx.z-0.42*hgt)),Vector((0.06,smx.y,smx.z-0.26*hgt)))
                shot('shirt-texture-closeup',[SHIRT],'front',res=(1024,1024),pad=1.0,box=cbox)
                # run 8: Saidie's crop (front 3/4 of the shoulder where the off-shoulder band meets the sleeve), each side, ~2x the sleeves close-up
                for sd_,vw_ in (('R','q34'),('L','q34L')):
                    try:
                        bn_={'R':'Right arm','L':'Left arm'}[sd_]; c_=B.matrix_world@B.pose.bones[bn_].head; h_=float(P.get('SEAM_BOX',0.075))
                        shot('seam-closeup-'+sd_,ALL,vw_,res=(1024,1024),pad=1.0,box=(c_-Vector((h_,h_,h_)),c_+Vector((h_,h_,h_))))
                    except Exception as e: log('SEAMSHOTERR',e)
                pbox=(Vector((-0.19,smn.y,smx.z-0.70*hgt)),Vector((0.19,smx.y,smx.z-0.10*hgt)))
                shot('shirt-print-front',ALL,'front',res=(1024,1024),pad=1.0,box=pbox); shot('shirt-print-back',ALL,'back',res=(1024,1024),pad=1.0,box=pbox)
            bmn,bmx=bbox([BRA]); nz_=float((B.matrix_world@B.data.bones['Neck'].head_local).z)
            stb=(Vector((bmn.x,bmn.y,nz_-0.13)),Vector((bmx.x,bmx.y,nz_+0.05)))
            for v in ('front','side','back','q34'): shot('strap-'+v,ALL,v,res=(1024,1024),pad=1.08,box=stb)
            HR.hide_render=True; shot('strap-back-nohair',ALL,'back',res=(1024,1024),pad=1.08,box=stb); shot('strap-side-nohair',ALL,'side',res=(1024,1024),pad=1.08,box=stb); HR.hide_render=False
        except Exception as e: traceback.print_exc(); log('CLOSEERR',e)
        KB=FH.data.shape_keys.key_blocks if FH.data.shape_keys else {}
        bk=[k for k in ('vrc.blink_left','vrc.blink_right') if k in KB] or [k for k in KB.keys() if 'blink' in k.lower()][:1]; rep['blink_keys']=bk
        for val in (0.0,0.5,1.0):
            for k in bk: KB[k].value=val
            bpy.context.view_layer.update(); shot(f'blink-{int(val*100)}',[FH],'front',res=(768,768),pad=0.75,zoff=0.12*(hx.z-hm.z))
        for k in bk: KB[k].value=0.0
        for vk in ('vrc.v_aa','vrc.v_oh'):
            if vk in KB: KB[vk].value=1.0; bpy.context.view_layer.update(); shot('viseme-'+vk.split('_')[-1],[FH],'front',res=(768,768),pad=0.75,zoff=-0.1*(hx.z-hm.z)); KB[vk].value=0.0
    elif P['SET']=='face':
        shot('face',[FH],'front',res=(1024,1024),pad=1.25); shot('face34',[FH],'q34',res=(1024,1024),pad=1.25); shot('neckside',[FH],'side',res=(1024,1024),pad=1.9,zoff=-0.35*(hx.z-hm.z))
    elif P['SET']=='umeko':
        shot('pose-front',ALL,'front',res=(768,1376),pad=1.06); shot('face34',[FH,HR],'q34',res=(1024,1024),pad=1.15); shot('pose-back',ALL,'back',res=(768,1376),pad=1.06)
    else:
        shot('pose-front',ALL,'front',res=(768,1376),pad=1.06); shot('pose-back',ALL,'back',res=(768,1376),pad=1.06)

        try:
            # run 6 close-ups: sleeves (front/side/back), halter strap (front/side/back), shirt fabric texture
            if SHIRT is not None:
                smn,smx=bbox([SHIRT]); hgt=smx.z-smn.z
                sbox=(Vector((smn.x,smn.y,smx.z-0.55*hgt)),smx)
                for v in ('front','side','back'): shot('sleeves-closeup-'+v,ALL,v,res=(1024,1024),pad=1.05,box=sbox)
                cbox=(Vector((-0.06,smn.y,smx.z-0.42*hgt)),Vector((0.06,smx.y,smx.z-0.26*hgt)))
                shot('shirt-texture-closeup',[SHIRT],'front',res=(1024,1024),pad=1.0,box=cbox)
                # run 8: Saidie's crop (front 3/4 of the shoulder where the off-shoulder band meets the sleeve), each side, ~2x the sleeves close-up
                for sd_,vw_ in (('R','q34'),('L','q34L')):
                    try:
                        bn_={'R':'Right arm','L':'Left arm'}[sd_]; c_=B.matrix_world@B.pose.bones[bn_].head; h_=float(P.get('SEAM_BOX',0.075))
                        shot('seam-closeup-'+sd_,ALL,vw_,res=(1024,1024),pad=1.0,box=(c_-Vector((h_,h_,h_)),c_+Vector((h_,h_,h_))))
                    except Exception as e: log('SEAMSHOTERR',e)
                pbox=(Vector((-0.19,smn.y,smx.z-0.70*hgt)),Vector((0.19,smx.y,smx.z-0.10*hgt)))
                shot('shirt-print-front',ALL,'front',res=(1024,1024),pad=1.0,box=pbox); shot('shirt-print-back',ALL,'back',res=(1024,1024),pad=1.0,box=pbox)
            bmn,bmx=bbox([BRA]); nz_=float((B.matrix_world@B.data.bones['Neck'].head_local).z)
            stb=(Vector((bmn.x,bmn.y,nz_-0.13)),Vector((bmx.x,bmx.y,nz_+0.05)))
            for v in ('front','side','back','q34'): shot('strap-'+v,ALL,v,res=(1024,1024),pad=1.08,box=stb)
            HR.hide_render=True; shot('strap-back-nohair',ALL,'back',res=(1024,1024),pad=1.08,box=stb); shot('strap-side-nohair',ALL,'side',res=(1024,1024),pad=1.08,box=stb); HR.hide_render=False
        except Exception as e: traceback.print_exc(); log('CLOSEERR',e)

    # B) rig test (steer 10:31): arms down, head turned 30 deg, right knee bent; everything must follow
    if P['SET'] in ('full','noshirt'):
        pose_relaxed(test=True); ALL=[o for o in meshes if o.visible_get()]
        shot('posetest-front',ALL,'front',res=(768,1376),pad=1.06); shot('posetest-side',ALL,'side',res=(768,1376),pad=1.06)
        if P['SET']=='full':
            hm,hx=bbox([FH]); shot('posetest-neck',[FH],'q34',res=(1024,1024),pad=1.9,zoff=-0.35*(hx.z-hm.z))
    rest()
    if SAVE_NAME:
        try:
            sel([B]+[m for m in meshes if m.visible_get()],B)
            bpy.ops.export_scene.fbx(filepath=OUT+'/'+SAVE_NAME+'.fbx',use_selection=True,add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',armature_nodetype='NULL',apply_scale_options='FBX_SCALE_ALL',path_mode='COPY',embed_textures=True)
            log('fbx',os.path.getsize(OUT+'/'+SAVE_NAME+'.fbx'))
        except Exception as e: log('FBXERR',e)
else:
    # turntable frames: relaxed pose, same studio; subject turns on the spot
    sc.cycles.samples=P['TT_SAMPLES']; pose_relaxed()
    sh_i=int(os.environ['TT_SHARD']); sh_n=int(os.environ.get('TT_SHARDS','4')); NF=P['TT_FRAMES']
    mn,mx=bbox(meshes); R=0.5*max(mx.x-mn.x,mx.y-mn.y)
    cx_,cy_=(mn.x+mx.x)/2,(mn.y+mx.y)/2; box=(Vector((cx_-R,cy_-R,mn.z)),Vector((cx_+R,cy_+R,mx.z)))
    place(meshes,'front',(P['TT_W'],P['TT_H']),1.04,box=box)
    os.makedirs(OUT+'/frames',exist_ok=True); per=(NF+sh_n-1)//sh_n; M0=B.matrix_world.copy(); cc_=Vector(((mn.x+mx.x)/2,(mn.y+mx.y)/2,0))
    for f in range(sh_i*per,min(NF,(sh_i+1)*per)):
        B.matrix_world=Matrix.Translation(cc_)@Matrix.Rotation(2*math.pi*f/NF,4,'Z')@Matrix.Translation(-cc_)@M0; bpy.context.view_layer.update()
        sc.render.filepath=OUT+f'/frames/f{f:03d}.png'; bpy.ops.render.render(write_still=True); log('frame',f)
json.dump(rep,open(OUT+'/build-report.json','w'),indent=1,default=str)
log('DONE'); import sys as _s; _s.stdout.flush(); os._exit(0)
