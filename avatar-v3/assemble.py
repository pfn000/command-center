
# v3.7 ASSEMBLY. Saidie 10:11 AM Oct 18: "if the body face and the final render does not look 1 to 1 to the assets I fed you, then you have done it wrong"
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
P=dict(SHORTS_TEX='Black.png', HAIR='blowout', SHIRT=True, HAIR_W_RATIO=1.40, HAIR_TOP_GAP=0.010, HAIR_DZ=0.006, HAIR_DY=0.0, HAIR_DEPTH_K=1.1,
       NECK_R_K=0.97, NECK_SINK=0.015, SEAM_BAND=0.035, BRA_COL=(0.012,0.012,0.013), BRA_ROUGH=0.55,
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
for s in FH.material_slots:
    m=s.material
    if not m: continue
    n=m.name.lower()
    if n.startswith('face'): set_tex(m,HD+'female head textures/'+P['HEAD_TEX'],alpha=True); m.blend_method='HASHED'
    elif n.startswith('eyes'): set_tex(m,ZP+'doe 5.png')
    elif n.startswith('effects'):
        m.use_nodes=True; bb_=[x for x in m.node_tree.nodes if x.type=='BSDF_PRINCIPLED']
        if bb_: bb_[0].inputs['Alpha'].default_value=0.0
rep['head_missing_images']=fix_images(); rep['head_materials']=mats_report(FH)
# ---------- 3. attach: head neck ring -> body neck ring. ONE uniform scale from the two ring radii (reported), sink 1.5 cm into the body's neck
BV=wco(BODY); zt=float(BV[:,2].max()); top=BV[BV[:,2]>zt-0.008]; bc=top[:,:2].mean(0); br=float(np.median(np.hypot(top[:,0]-bc[0],top[:,1]-bc[1])))
HV=wco(FH); h_before=float(HV[:,2].max()-HV[:,2].min()); zb=float(HV[:,2].min()); bot=HV[HV[:,2]<zb+0.006]; hc=bot[:,:2].mean(0); hr=float(np.median(np.hypot(bot[:,0]-hc[0],bot[:,1]-hc[1])))
s_=br/hr*P['NECK_R_K']
M=Matrix.Translation(Vector((bc[0],bc[1],zt-P['NECK_SINK'])))@Matrix.Scale(s_,4)@Matrix.Translation(Vector((-hc[0],-hc[1],-zb)))
apply_tf([FA,FH],M)
HV=wco(FH); hmn=HV.min(0); hmx=HV.max(0)
fz=float(BV[:,2].min())
rep['attach']={'body_neck_top_z':zt,'body_neck_ring_r':br,'head_neck_ring_r':hr,'head_scale_factor':s_,'head_h_before':h_before,'head_h_after':float(hmx[2]-hmn[2]),
               'head_w_after':float(hmx[0]-hmn[0]),'total_height':float(hmx[2]-fz),'head_to_height':float((hmx[2]-hmn[2])/(hmx[2]-fz))}
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
pivot=Vector(((umn[0]+umx[0])/2,(umn[1]+umx[1])/2,umx[2])); target=Vector(((hmn[0]+hmx[0])/2,hmn[1]+P['HAIR_DEPTH_K']*(hmx[0]-hmn[0])/2+P['HAIR_DY'],hmx[2]+P['HAIR_TOP_GAP']+P['HAIR_DZ']))
Mh=Matrix.Translation(target)@Matrix.Scale(s,4)@Matrix.Translation(-pivot)
apply_tf([x for x in (HA,HR) if x],Mh)
for e_ in HE: bpy.data.objects.remove(e_)
rep['hair_fit']={'hair':P['HAIR'],'scale':s}; log('hair fit',s)
CR=None
if P['CRANIUM']:
    import bmesh
    cx=(hmn[0]+hmx[0])/2; hw=(hmx[0]-hmn[0])/2; zc=hmn[2]+0.62*(hmx[2]-hmn[2]); cy=hmn[1]+1.05*hw
    bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=32,v_segments=16,radius=1.0)
    for v in bm.verts: v.co=Vector((cx+v.co.x*hw*0.93, cy+v.co.y*hw*1.02, zc+v.co.z*(hmx[2]-zc)*0.97))
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
# clothes weights: Data Transfer from the Panda body (Vertex Data > Vertex Groups, nearest face interpolated), applied, cleaned, normalized, max 4 influences
def transfer_weights(o):
    old=[g.name for g in o.vertex_groups]; o.vertex_groups.clear()
    sel([o]); md=o.modifiers.new('WT','DATA_TRANSFER'); md.object=BODY; md.use_vert_data=True; md.data_types_verts={'VGROUP_WEIGHTS'}; md.vert_mapping='POLYINTERP_NEAREST'
    md.layers_vgroup_select_src='ALL'; md.layers_vgroup_select_dst='NAME'
    bpy.ops.object.datalayout_transfer(modifier=md.name)
    while o.modifiers[0].name!=md.name: bpy.ops.object.modifier_move_up(modifier=md.name)
    bpy.ops.object.modifier_apply(modifier=md.name)
    try:
        bpy.ops.object.vertex_group_clean(group_select_mode='ALL',limit=0.001)
        bpy.ops.object.vertex_group_limit_total(group_select_mode='ALL',limit=4)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode='ALL',lock_active=False)
    except Exception as e: log('WTCLEAN',o.name,e)
    used=set(ge.group for v in o.data.vertices for ge in v.groups)
    for g in list(o.vertex_groups):
        if g.index not in used: o.vertex_groups.remove(g)
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
BT=bones_txt(); open(OUT+'/proof/v37-bones.txt','w').write(BT); log('BONES\n'+BT[:3000])
meshes=MESHES
rep['tris']={o.name:tris(o) for o in meshes}; rep['tris_total']=sum(rep['tris'].values())
rep['shapekeys_head']=[k.name for k in FH.data.shape_keys.key_blocks] if FH.data.shape_keys else []
log('tris',rep['tris_total'],rep['tris'])
json.dump(rep,open(OUT+'/build-report.json','w'),indent=1,default=str)
if VAR=='A0' and not P['TT']:
    try: bpy.ops.wm.save_as_mainfile(filepath=OUT+'/jena-v37.blend',compress=True); log('blend saved')
    except Exception as e: log('BLENDERR',e)
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
SETS={'full':['panda-body','female-head',HAIRNAME,'booty-shorts','outfit-shirt-grey'],'umeko':[HAIRNAME],'noshirt':['outfit-bra','booty-shorts']}
def wrot(name,deg,axis):
    if not deg or name not in B.pose.bones: return
    pb=B.pose.bones[name]; h=pb.head.copy(); pb.matrix=Matrix.Translation(h)@Matrix.Rotation(math.radians(deg),4,axis)@Matrix.Translation(-h)@pb.matrix; bpy.context.view_layer.update()
def pose_relaxed(test=False):
    bpy.context.view_layer.objects.active=B; bpy.ops.object.mode_set(mode='POSE')
    for pb in B.pose.bones: pb.matrix_basis=Matrix()
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
    for pb in B.pose.bones: pb.matrix_basis=Matrix()
    bpy.ops.object.mode_set(mode='OBJECT'); bpy.context.view_layer.update()
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
        shot('neckside',[FH],'side',res=(1024,1024),pad=1.9,zoff=-0.35*(hx.z-hm.z))
        KB=FH.data.shape_keys.key_blocks if FH.data.shape_keys else {}
        bk=[k for k in ('vrc.blink_left','vrc.blink_right') if k in KB] or [k for k in KB.keys() if 'blink' in k.lower()][:1]; rep['blink_keys']=bk
        for val in (0.0,0.5,1.0):
            for k in bk: KB[k].value=val
            bpy.context.view_layer.update(); shot(f'blink-{int(val*100)}',[FH],'front',res=(768,768),pad=0.75,zoff=0.12*(hx.z-hm.z))
        for k in bk: KB[k].value=0.0
        for vk in ('vrc.v_aa','vrc.v_oh'):
            if vk in KB: KB[vk].value=1.0; bpy.context.view_layer.update(); shot('viseme-'+vk.split('_')[-1],[FH],'front',res=(768,768),pad=0.75,zoff=-0.1*(hx.z-hm.z)); KB[vk].value=0.0
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
    if VAR=='A0':
        try:
            sel([B]+meshes,B)
            bpy.ops.export_scene.fbx(filepath=OUT+'/jena-v37.fbx',use_selection=True,add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',armature_nodetype='NULL',apply_scale_options='FBX_SCALE_ALL',path_mode='COPY',embed_textures=True)
            log('fbx',os.path.getsize(OUT+'/jena-v37.fbx'))
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
