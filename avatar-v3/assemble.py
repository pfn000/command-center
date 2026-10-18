
# v3.7 ASSEMBLY, run 5 (hair: its own Head bone on her Head bone at the head's scale, bang chains posed off the eyes if needed; shirt: rigid re-seat + offset along BODY normals, no cover_fix). Run 4 notes: (head on Panda's Head bone at proportional scale, no hair push, shorts re-seated + hugged, bra hidden under the shirt). Saidie 10:11 AM Oct 18: "if the body face and the final render does not look 1 to 1 to the assets I fed you, then you have done it wrong"
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
       SET='full', TT=False, TT_FRAMES=96, TT_SAMPLES=12, TT_W=720, TT_H=1280)
try:
    J=json.load(open(os.path.dirname(os.path.abspath(__file__))+'/assemble.json')); P.update(J.get('all',{})); P.update(J.get(VAR,{}))
except Exception as e: log('no assemble.json',e)
if os.environ.get('TT_SHARD') is not None: P['TT']=True
rep={'variant':VAR,'params':P}; log('variant',VAR,P)
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
for o in new:
    if o.type=='MESH' and o is not FH: bpy.data.objects.remove(o)
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
apply_tf([FA,FH],M_)
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
apply_tf([x for x in (HA,HR) if x],Mh)
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
for o in new:
    if o is not BRA and o is not SHIRT: bpy.data.objects.remove(o)
if SHIRT is not None:
    for s_l in SHIRT.material_slots:
        if s_l.material: set_tex(s_l.material,IN+'/Tshirt-BasicGrey.png')
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
# clothes FIT (brief: "fit clothes"): where her Panda body pokes through a garment, that garment's vertices are pushed out to sit just over the skin
# (smoothed; nothing else moves; her UVs/textures/cut untouched). Layered: bra + shorts over the body, shirt over body + bra + shorts. Max push reported.
from mathutils.bvhtree import BVHTree
def world_bvh(objs):
    dg=bpy.context.evaluated_depsgraph_get(); V=[]; F=[]
    for t in objs:
        e=t.evaluated_get(dg); me=e.to_mesh(); off=len(V)
        V+=[tuple(t.matrix_world@v.co) for v in me.vertices]; F+=[tuple(off+i for i in p.vertices) for p in me.polygons]; e.to_mesh_clear()
    return BVHTree.FromPolygons(V,F)
def fit_out(o,targets,off,deep=0.05,iters=5,only=None):
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
    X2=X+D; N2=need(X2)
    if only is not None: N2[~only(X2)]=0
    X2+=N2
    tot=X2-X; mm=np.linalg.norm(tot,axis=1)*1000
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
def add_disp(o,Dw):
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
BRA_HIDDEN=SHIRT is not None and P.get('BRA_UNDER_SHIRT','hide')=='hide'
if P.get('FIT',True):
    for o,tg,off in ((BRA,[BODY],P.get('FIT_BRA',0.002)),(SH,[BODY],P.get('FIT_SHORTS',0.0015 if SF=='hug' else 0.0025))):
        try: fit_out(o,tg,off)
        except Exception as e: traceback.print_exc(); log('FITERR',o.name,e)
    if P.get('FIT_HAIR',False):   # run 4: OFF (it flattened her hair cards onto the face in runs 2-3)
        try: fit_out(HR,[FH],P.get('FIT_HAIR_OFF',0.0015),deep=0.03,only=lambda X:X[:,1]<float(hmn[1]+hmx[1])/2)
        except Exception as e: traceback.print_exc(); log('FITERR','Hair',e)
    if SHIRT is not None:
        try:
            if P.get('SHIRT_FIT','v5')=='v5': shirt_v5(SHIRT,[SH] if BRA_HIDDEN else [BRA,SH],P.get('FIT_SHIRT',0.006))
            else:
                for tg_ in ((BODY,SH) if BRA_HIDDEN else (BODY,BRA,SH)): fit_out(SHIRT,[tg_],P.get('FIT_SHIRT',0.006)); rep['cloth_fit']['Shirt over '+tg_.name]=rep['cloth_fit'].pop('Shirt')
        except Exception as e: traceback.print_exc(); log('FITERR','Shirt',e)
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
for o in CLOTH:
    try: transfer_weights(o)
    except Exception as e: traceback.print_exc(); log('WTERR',o.name,e)
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
kill('Hair Root')   # bones of the bunisu pigtails/bangs meshes she did not choose
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
meshes=MESHES
rep['tris']={o.name:tris(o) for o in meshes}; rep['tris_total']=sum(rep['tris'].values())
rep['shapekeys_head']=[k.name for k in FH.data.shape_keys.key_blocks] if FH.data.shape_keys else []
log('tris',rep['tris_total'],rep['tris'])
json.dump(rep,open(OUT+'/build-report.json','w'),indent=1,default=str)
SAVE_NAME={'A0':'jena-v37r5','A1':'jena-v37r5-umeko','A2':'jena-v37r5-noshirt'}.get(VAR)
# ---------- studio: IDENTICAL to the solo asset renders (grey world 0.18, warm key / cool fill / rim suns, AgX Base Contrast, 85 mm, same framing rule)
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=P['ASM_SAMPLES']; sc.cycles.use_denoising=True
sc.render.film_transparent=False; sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGB'
sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Base Contrast'
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; bg=w.node_tree.nodes['Background']; bg.inputs[0].default_value=(0.18,0.18,0.18,1); bg.inputs[1].default_value=1.0
def sun(name,rot,e,col=(1,1,1)):
    L=bpy.data.lights.new(name,'SUN'); L.energy=e; L.color=col; L.angle=math.radians(8); o=bpy.data.objects.new(name,L); sc.collection.objects.link(o); o.rotation_euler=[math.radians(a) for a in rot]; return o
sun('key',(55,0,-35),3.2,(1,0.96,0.92)); sun('fill',(70,0,45),1.1,(0.92,0.95,1)); sun('rim',(60,0,165),2.4)
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam; cam.data.lens=85
DIRS={'front':Vector((0,-1,0)),'back':Vector((0,1,0)),'side':Vector((-1,0,0)),'q34':Vector((-0.72,-0.69,0)).normalized()}
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
HAIRNAME='umeko-hair' if P['HAIR']=='umeko' else 'blowout-haircards'
ASSETS={'panda-body':[BODY]+BX,'female-head':[FH],HAIRNAME:[HR],'booty-shorts':[SH],'outfit-bra':[BRA]}
if SHIRT is not None: ASSETS['outfit-shirt-grey']=[SHIRT]
SETS={'face':[],'full':['panda-body','female-head',HAIRNAME,'booty-shorts','outfit-shirt-grey','outfit-bra'],'umeko':[HAIRNAME],'noshirt':['outfit-bra','booty-shorts']}
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
        if im is None or P['HAIR']=='umeko': return None
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
def eye_cover(views=('front','q34')):
    TF,VF,FF,_,_=_eval_tris(FH,lambda mi:mi in FH_SOLID)
    TH,VH,FHt,UVH,TVH=_eval_tris(HR)
    pts=[]
    dg=bpy.context.evaluated_depsgraph_get(); e=FH.evaluated_get(dg); me=e.to_mesh(); me.calc_loop_triangles(); mw=FH.matrix_world
    for t in me.loop_triangles:
        if t.material_index in FH_EYE_MATS:
            P3=[mw@me.vertices[v].co for v in t.vertices]; pts.append((P3[0]+P3[1]+P3[2])/3); pts+=P3
    e.to_mesh_clear()
    out={}; hit_tris=set()
    for vw in views:
        d=DIRS_EYE[vw]
        res={'L':[0,0],'R':[0,0]}
        for p in pts:
            sd='L' if p.x>0 else 'R'
            o_=p+d*0.0006
            l1,_,_,_=TF.ray_cast(o_,d,0.4)
            if l1 is not None: continue   # eyelid/face in front: not a visible eye point
            res[sd][1]+=1; oo=o_; covered=False
            for _ in range(6):
                l2,n2,i2,d2=TH.ray_cast(oo,d,0.6)
                if l2 is None: break
                a_=1.0
                if HALPHA is not None and UVH is not None:
                    A_,w_,h_=HALPHA; a0,b0,c0=[Vector(VH[j]) for j in TVH[i2]]
                    from mathutils.geometry import barycentric_transform
                    uvw=barycentric_transform(l2,a0,b0,c0,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
                    uv=sum((Vector(UVH[i2][j])*uvw[j] for j in range(3)),Vector((0,0)))
                    a_=float(A_[int((uv.y%1.0)*(h_-1)),int((uv.x%1.0)*(w_-1))])
                if a_>0.35: covered=True; hit_tris.add(i2); break
                oo=l2+d*0.0003
            if covered: res[sd][0]+=1
        out[vw]={sd:{'covered':c_,'visible_pts':n_,'pct':round(100.0*c_/max(n_,1),1)} for sd,(c_,n_) in res.items()}
    return out,hit_tris,TVH
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
try:
    _eyez=[FH.matrix_world@v.co for v in FH.data.vertices]
    _ev=[ (FH.matrix_world@FH.data.vertices[i].co) for p in FH.data.polygons if p.material_index in FH_EYE_MATS for i in p.vertices]
    EYE_TOP_Z=max(v.z for v in _ev)+0.004 if _ev else float(hmx[2]); HEADCY=float((hmn[1]+hmx[1])/2)
    bpy.context.view_layer.objects.active=B; bpy.ops.object.mode_set(mode='POSE'); bpy.ops.object.mode_set(mode='OBJECT'); bpy.context.view_layer.update()
    ec,ht,TVH_=eye_cover(); rep['eyes_before']=ec; rep['face_cross_before']=face_cross(); log('EYES before',ec,'cross',rep['face_cross_before'])
    if cover_pct(ec)>P.get('EYE_TOL_PCT',1.0):
        cnt,roots=chains_for(ht,TVH_); rep['eye_cover_bones']=cnt; rep['eye_cover_chains']=roots; log('cover chains',roots,'bones',cnt)
        front=[r_ for r_ in roots if P['HAIR']=='umeko' or 'Bang' in r_] or [r_ for r_ in roots if any(k in r_ for k in ('Front','Flyaway'))]
        rep['bang_chains_rotated']=front; tried=[]
        if front:
            base={r_:B.pose.bones[r_].matrix_basis.copy() for r_ in front}
            ok=None
            # sign: the one that RAISES the chain tips (checked on the bones, not assumed)
            def tipz():
                bpy.context.view_layer.update(); return sum((B.matrix_world@B.pose.bones[r_].tail).z for r_ in front)
            z0=tipz(); [wrot(r_,-10,'X') for r_ in front]; zm=tipz()
            for r_ in front: B.pose.bones[r_].matrix_basis=base[r_].copy()
            bpy.context.view_layer.update(); SGN=-1 if zm>=z0 else 1; rep['bang_sign']=SGN
            for ang in range(5,65,5):
                for r_ in front: B.pose.bones[r_].matrix_basis=base[r_].copy()
                bpy.context.view_layer.update()
                for r_ in front: wrot(r_,SGN*ang,'X')   # tip swings UP (away from the eyes); pose only
                ec2,ht2,_=eye_cover(); pc=cover_pct(ec2); tried.append((ang,pc)); log('bang up',ang,'deg -> cover %',pc)
                if pc<=P.get('EYE_TOL_PCT',1.0): ok=ang; break
            rep['bang_tries']=tried; rep['bang_angle_deg']=ok
            if ok is None:
                best=min(tried,key=lambda t:(t[1],t[0]))[0]
                for r_ in front: B.pose.bones[r_].matrix_basis=base[r_].copy()
                bpy.context.view_layer.update()
                for r_ in front: wrot(r_,SGN*best,'X')
                rep['bang_angle_deg']=best; rep['bang_note']='no angle up to 60 deg fully cleared both eyes; kept the best'
            for r_ in front: BANG[r_]=B.pose.bones[r_].matrix_basis.copy()
        ec3,_,_=eye_cover(); rep['eyes_after']=ec3; rep['face_cross_after']=face_cross(); log('EYES after',ec3,'cross',rep['face_cross_after'],'BANG',list(BANG))
    else: rep['eyes_after']=ec; rep['bang_chains_rotated']=[]
except Exception as e: traceback.print_exc(); log('EYECHECKERR',e); rep['eyecheck_error']=str(e)
json.dump(rep,open(OUT+'/build-report.json','w'),indent=1,default=str)
if SAVE_NAME and not P['TT']:
    try: rest(); bpy.ops.wm.save_as_mainfile(filepath=OUT+'/'+SAVE_NAME+'.blend',compress=True); log('blend saved')
    except Exception as e: log('BLENDERR',e)
if not P['TT']:
    SET=SETS[P['SET']]
    # A) 1:1 proofs in REST pose (as the solo renders), camera framed on that asset exactly as its solo render was:
    #    asm-<asset>-<view> = the asset ON the assembled avatar ; iso-<asset>-front = the same asset in the assembled file with everything else hidden (untouched check)
    for nm in SET:
        if nm not in ASSETS: continue
        for v in ('front','q34','back'): shot(f'asm-{nm}-{v}',ASSETS[nm],v)
        st=solo(ASSETS[nm]); shot(f'iso-{nm}-front',ASSETS[nm],'front'); unsolo(st)
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
