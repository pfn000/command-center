
import bpy, sys, os, math, json, mathutils, bmesh
from mathutils import Vector, Matrix
argv=sys.argv[sys.argv.index('--')+1:]; IN,OUT=argv[0],argv[1]; A=IN+'/assets'; os.makedirs(OUT+'/proof',exist_ok=True)
def log(*a): print('[v3]',*a,flush=True)
P=dict(HAIR_W_RATIO=1.45, HAIR_TOP_GAP=0.010, HAIR_DY=0.012, HAIR_DZ=0.0, ARM_DOWN=68, SAMPLES=48, RENDER=True, EXPORT=True,
       BODY_DEC=0.55, HAIR_DEC=0.55, BRA_DEC=0.5, SHORTS_DEC=0.45)
try: P.update(json.load(open(os.path.dirname(os.path.abspath(__file__))+'/params.json')))
except Exception as e: log('no params',e)
log('params',P)
rep={'params':P}
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
def tris(o): return sum(len(p.vertices)-2 for p in o.data.polygons) if o.type=='MESH' else 0
def wbb(objs):
    pts=[o.matrix_world@Vector(c) for o in objs for c in o.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]),Vector([max(p[i] for p in pts) for i in range(3)])
def sel(objs,active=None):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active=active or objs[0]
def imp_fbx(f):
    before=set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=A+'/'+f)
    return [o for o in bpy.data.objects if o not in before]
# ---------- body (APPEND from .blend, not FBX)
with bpy.data.libraries.load(A+'/body_PandaFitBase_HighFlatFoot.blend',link=False) as (df,dt): dt.objects=list(df.objects)
for o in dt.objects: sc.collection.objects.link(o)
B=bpy.data.objects['Armature']; BODY=bpy.data.objects['Body']; B.name='Armature'
log('body bones',len(B.data.bones),'tris',tris(BODY))
# ---------- head (Female head + hair FBX; only the head mesh, its hair is pigtails)
new=imp_fbx('hair_female_head_hair.fbx')
FA=[o for o in new if o.type=='ARMATURE'][0]; FH=bpy.data.objects['Female Head']
for o in new:
    if o.type=='MESH' and o is not FH: bpy.data.objects.remove(o)
# ---------- hair (Umeko, shaggy shoulder-length = closest to her sheet)
new=imp_fbx('hair_umeko_gift.fbx')
UA=[o for o in new if o.type=='ARMATURE'][0]; UM=[o for o in new if o.type=='MESH'][0]; UM.name='Hair'
hmn,hmx=wbb([FH]); umn,umx=wbb([UM])
head_w=hmx.x-hmn.x; s=head_w*P['HAIR_W_RATIO']/(umx.x-umn.x)
yc=(hmn.y+hmx.y)/2
# scale about hair bbox top-center, then move top to head top
pivot=Vector(((umn.x+umx.x)/2,(umn.y+umx.y)/2,umx.z))
target=Vector(((hmn.x+hmx.x)/2, yc+P['HAIR_DY'], hmx.z+P['HAIR_TOP_GAP']+P['HAIR_DZ']))
M=Matrix.Translation(target)@Matrix.Scale(s,4)@Matrix.Translation(-pivot)
UA.matrix_world=M@UA.matrix_world
bpy.context.view_layer.update()
sel([UA,UM],UA); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
umn2,umx2=wbb([UM]); log('hair fit scale',round(s,3),'hair bb',[round(v,3) for v in umn2],[round(v,3) for v in umx2],'head bb',[round(v,3) for v in hmn],[round(v,3) for v in hmx])
rep['hair_fit']={'scale':s,'hair_bb':[list(umn2),list(umx2)],'head_bb':[list(hmn),list(hmx)]}
# ---------- clothes
new=imp_fbx('top_Outfitriggedpanda.fbx'); BRA=bpy.data.objects['Bra']
for o in new:
    if o is not BRA: bpy.data.objects.remove(o)
new=imp_fbx('shorts_BootyShorts_Beanie.fbx'); SH=bpy.data.objects['Booty Shorts']; SH.name='Shorts'
for o in new:
    if o is not SH: bpy.data.objects.remove(o)
# ---------- merge armatures into the body armature
for arm,ren in ((FA,{'Neck':'DUP_Neck','Head':'DUP_Head'}),(UA,{'Head':'DUP_Head2'})):
    for b in arm.data.bones:
        if b.name in ren: b.name=ren[b.name]
# FH/UM vertex groups named Head/Neck now point to the body's Head/Neck (same names)
sel([B,FA,UA],B); bpy.ops.object.join()
bpy.ops.object.mode_set(mode='EDIT'); eb=B.data.edit_bones
mapto={'DUP_Neck':'Neck','DUP_Head':'Head','DUP_Head2':'Head'}
for d,t in mapto.items():
    if d in eb:
        for c in list(eb[d].children): c.parent=eb[t]
        eb.remove(eb[d])
# drop the pigtail/bang bones of the deleted Female hair
def kill(name):
    if name in eb:
        for c in list(eb[name].children): kill(c.name)
        eb.remove(eb[name])
kill('Hair Root')
bpy.ops.object.mode_set(mode='OBJECT')
log('merged bones',len(B.data.bones))
REN={'Belly':'Spine','AssRoot':'Hips','Pussy_Root':'Hips','Pussy.R':'Hips','Pussy.L':'Hips','Pussy.R.001':'Hips','Pussy.L.001':'Hips',
     'Left thigh':'Left leg','Right thigh':'Right leg','Root_Butt':'Hips'}
bn=set(b.name for b in B.data.bones)
def fixname(n):
    if n in bn: return n
    if n in REN: return REN[n]
    for a,b2 in (('.1_L','.L'),('.1_R','.R'),('_L','.L'),('_R','.R')):
        if n.endswith(a) and n[:-len(a)]+b2 in bn: return n[:-len(a)]+b2
    m=n.replace('_001','').replace('_L','.L').replace('_R','.R')
    if m in bn: return m
    return None
def remap(o):
    gi={g.index:g for g in o.vertex_groups}; plan={}
    for g in list(o.vertex_groups):
        t=fixname(g.name)
        if t!=g.name: plan[g.name]=t
    for v in o.data.vertices:
        for ge in v.groups:
            g=gi[ge.group]
            if g.name in plan and plan[g.name]:
                tg=o.vertex_groups.get(plan[g.name]) or o.vertex_groups.new(name=plan[g.name])
                tg.add([v.index],ge.weight,'ADD')
    for n,t in plan.items(): o.vertex_groups.remove(o.vertex_groups[n])
    log('remap',o.name,plan)
for o in (BRA,SH,FH,UM): remap(o)
for o in (BODY,FH,UM,BRA,SH):
    mw=o.matrix_world.copy(); o.parent=B; o.matrix_world=mw
    am=[m for m in o.modifiers if m.type=='ARMATURE']
    if not am: am=[o.modifiers.new('Armature','ARMATURE')]
    am[0].object=B
for o in list(bpy.data.objects):
    if o.type=='ARMATURE' and o is not B: bpy.data.objects.remove(o)
# ---------- face/eye geometry facts
me=FH.data; mi={i:s.material.name if s.material else '' for i,s in enumerate(FH.material_slots)}
eyeL=[];eyeR=[]
uvl=me.uv_layers.active.data
eyeuv=[];euvL=[];euvR=[]
for p in me.polygons:
    if 'eye' in mi[p.material_index].lower():
        c=FH.matrix_world@p.center; (eyeL if c.x>0 else eyeR).append(c)
        for li in p.loop_indices: eyeuv.append(tuple(uvl[li].uv)); (euvL if c.x>0 else euvR).append(tuple(uvl[li].uv))
def uvbb(L): return [min(u[0] for u in L),min(u[1] for u in L),max(u[0] for u in L),max(u[1] for u in L)] if L else [0,0,1,1]
rep['eye_uv_L']=uvbb(euvL); rep['eye_uv_R']=uvbb(euvR); log('eye uv L',rep['eye_uv_L'],'R',rep['eye_uv_R'])
def ctr(ps): 
    if not ps: return None
    mn=Vector([min(p[i] for p in ps) for i in range(3)]); mx=Vector([max(p[i] for p in ps) for i in range(3)]); return (mn+mx)/2,(mx-mn)
eL,eR=ctr(eyeL),ctr(eyeR); log('eyeL',eL,'eyeR',eR)
if eyeuv: rep['eye_uv_bb']=[min(u[0] for u in eyeuv),min(u[1] for u in eyeuv),max(u[0] for u in eyeuv),max(u[1] for u in eyeuv)]
log('eye uv bb',rep.get('eye_uv_bb'))
rep['eyes']={'L':[list(eL[0]),list(eL[1])] if eL else None,'R':[list(eR[0]),list(eR[1])] if eR else None}

# ---------- her Meshy eyeball -> iris texture (the .glb is a 368k-tri disc: too heavy for VRChat, so it is rendered once and mapped onto the head's eye UVs)
EYE_TEX=None
try:
    before=set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=IN+'/refs/Meshy_Jena_Eyeball.glb')
    eo=[o for o in bpy.data.objects if o not in before]
    off=Vector((100,0,0))
    for o in eo:
        if o.parent is None: o.location+=off
    em=[o for o in eo if o.type=='MESH']
    sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=32; sc.cycles.use_denoising=True
    sc.render.film_transparent=False; sc.render.resolution_x=sc.render.resolution_y=1024; sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGB'
    sc.view_settings.view_transform='Standard'
    w0=bpy.data.worlds.new('weye'); sc.world=w0; w0.use_nodes=True; w0.node_tree.nodes['Background'].inputs[0].default_value=(1,1,1,1); w0.node_tree.nodes['Background'].inputs[1].default_value=0.9
    ec=bpy.data.objects.new('ecam',bpy.data.cameras.new('ecam')); sc.collection.objects.link(ec); sc.camera=ec; ec.data.type='ORTHO'; ec.data.ortho_scale=1.92
    ec.location=off+Vector((0,-5,0)); ec.rotation_euler=(math.radians(90),0,0); ec.data.clip_start=3; ec.data.clip_end=7
    sc.render.filepath=OUT+'/eye_iris.png'; bpy.ops.render.render(write_still=True)
    for o in eo: bpy.data.objects.remove(o)
    bpy.data.objects.remove(ec)
    sc.view_settings.view_transform='AgX'
    EYE_TEX=bpy.data.images.load(OUT+'/eye_iris.png'); EYE_TEX.pack(); log('meshy iris rendered')
except Exception as e: log('MESHYERR',e)
# ---------- materials
def img(name):
    p=A+'/'+name; return bpy.data.images.load(p,check_existing=True)
def newmat(name):
    m=bpy.data.materials.new(name); m.use_nodes=True; nt=m.node_tree; return m,nt,nt.nodes['Principled BSDF']
# body skin: her albedo 5867 (she re-sent it 5:07 PM as THE skin) (pale pink skin, nipples/navel)
mb,nt,bs=newmat('Skin'); t=nt.nodes.new('ShaderNodeTexImage'); t.image=img('5867c342-78a0-443f-aecc-a24f5d7dc6d3.jpg'); nt.links.new(t.outputs[0],bs.inputs['Base Color'])
bs.inputs['Roughness'].default_value=0.42; bs.inputs['Subsurface Weight'].default_value=0.08; bs.inputs['Subsurface Radius'].default_value=(1.0,0.35,0.25)
try: bs.inputs['Coat Weight'].default_value=0.12
except: pass
BODY.data.materials.clear(); BODY.data.materials.append(mb)
# skin tone for the head from the body texture's median skin pixel
import numpy as np
im=t.image; px=np.array(im.pixels[:]).reshape(-1,4)[::97,:3]; lum=px.mean(1); sk=px[(lum>0.35)&(lum<0.95)]
skin=tuple(np.median(sk,0)) if len(sk) else (0.85,0.68,0.66); log('skin rgb (linear-ish)',skin); rep['skin']=list(map(float,skin))
for i,s in enumerate(FH.material_slots):
    n=s.material.name.lower() if s.material else ''
    if n.startswith('face'):
        m,nt,b=newmat('Face'); b.inputs['Base Color'].default_value=(*skin,1); b.inputs['Roughness'].default_value=0.45
        if os.path.exists(A+'/face_skin_2_from_saidie_1708.jpg'):
            ft=nt.nodes.new('ShaderNodeTexImage'); ft.image=img('face_skin_2_from_saidie_1708.jpg'); nt.links.new(ft.outputs[0],b.inputs['Base Color']); log('face texture: her 2.png (5:08 PM)'); b.inputs['Subsurface Weight'].default_value=0.08; b.inputs['Subsurface Radius'].default_value=(1.0,0.35,0.25)
        s.material=m
    elif n.startswith('effects'):
        m,nt,b=newmat('Effects'); b.inputs['Alpha'].default_value=0.0; m.blend_method='HASHED' if hasattr(m,'blend_method') else None; s.material=m
    elif n.startswith('metal'):
        m,nt,b=newmat('Metal'); b.inputs['Base Color'].default_value=(0.8,0.8,0.82,1); b.inputs['Metallic'].default_value=1; b.inputs['Roughness'].default_value=0.25; s.material=m
    elif n.startswith('eyes'):
        # procedural blue-grey iris on the head's eye UVs until the Meshy iris is mapped
        m,nt,b=newmat('Eyes'); uv=nt.nodes.new('ShaderNodeTexCoord'); 
        L_=rep['eye_uv_L']; R_=rep['eye_uv_R']
        cL=((L_[0]+L_[2])/2,(L_[1]+L_[3])/2,0); cR=((R_[0]+R_[2])/2,(R_[1]+R_[3])/2,0)
        u0,v0,u1,v1=L_
        sp=nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(uv.outputs['Object'],sp.inputs[0])
        lt=nt.nodes.new('ShaderNodeMath'); lt.operation='LESS_THAN'; lt.inputs[1].default_value=0.0; nt.links.new(sp.outputs['X'],lt.inputs[0])
        mxv=nt.nodes.new('ShaderNodeMix'); mxv.data_type='VECTOR'; nt.links.new(lt.outputs[0],mxv.inputs['Factor']); mxv.inputs[4].default_value=cL; mxv.inputs[5].default_value=cR
        sub=nt.nodes.new('ShaderNodeVectorMath'); sub.operation='SUBTRACT'; nt.links.new(uv.outputs['UV'],sub.inputs[0]); nt.links.new(mxv.outputs[1],sub.inputs[1])
        mp=sub
        ln=nt.nodes.new('ShaderNodeVectorMath'); ln.operation='LENGTH'; nt.links.new(mp.outputs[0],ln.inputs[0])
        dv=nt.nodes.new('ShaderNodeMath'); dv.operation='DIVIDE'; dv.inputs[1].default_value=max(u1-u0,v1-v0)/2; nt.links.new(ln.outputs['Value'],dv.inputs[0])
        cr=nt.nodes.new('ShaderNodeValToRGB'); e=cr.color_ramp.elements
        e[0].position=0.0; e[0].color=(0.01,0.01,0.012,1); e[1].position=1.0; e[1].color=(0.9,0.9,0.92,1)
        for pos,col in ((0.16,(0.01,0.01,0.012,1)),(0.2,(0.20,0.27,0.36,1)),(0.42,(0.36,0.45,0.55,1)),(0.5,(0.10,0.13,0.17,1)),(0.54,(0.85,0.85,0.88,1))):
            x=e.new(pos); x.color=col
        nt.links.new(dv.outputs[0],cr.inputs[0]); nt.links.new(cr.outputs[0],b.inputs['Base Color']); b.inputs['Roughness'].default_value=0.08
        if EYE_TEX is not None:
            # Meshy eyeball image: island half-size -> IRIS_ZOOM of the disc radius
            hs=max(u1-u0,v1-v0)/2
            sc1=nt.nodes.new('ShaderNodeVectorMath'); sc1.operation='SCALE'; sc1.inputs['Scale'].default_value=0.5*P.get('IRIS_ZOOM',0.8)/hs; nt.links.new(sub.outputs[0],sc1.inputs[0])
            ad=nt.nodes.new('ShaderNodeVectorMath'); ad.operation='ADD'; ad.inputs[1].default_value=(0.5,0.5,0); nt.links.new(sc1.outputs[0],ad.inputs[0])
            ti=nt.nodes.new('ShaderNodeTexImage'); ti.image=EYE_TEX; ti.extension='EXTEND'; nt.links.new(ad.outputs[0],ti.inputs[0])
            nt.links.new(ti.outputs[0],b.inputs['Base Color'])
        s.material=m
# hair: black roots -> grey -> white tips (generated Z of the hair mesh)
def hairmat():
    m,nt,b=newmat('HairGradient'); tc=nt.nodes.new('ShaderNodeTexCoord'); sp=nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'],sp.inputs[0])
    nz=nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value=60; nt.links.new(tc.outputs['Object'],nz.inputs['Vector'])
    ad=nt.nodes.new('ShaderNodeMath'); ad.operation='MULTIPLY_ADD'; nt.links.new(nz.outputs['Fac'],ad.inputs[0]); ad.inputs[1].default_value=0.12; nt.links.new(sp.outputs['Z'],ad.inputs[2])
    cr=nt.nodes.new('ShaderNodeValToRGB'); e=cr.color_ramp.elements
    e[0].position=0.10; e[0].color=(0.82,0.82,0.82,1); e[1].position=0.62; e[1].color=(0.010,0.010,0.012,1)
    for pos,col in ((0.27,(0.45,0.45,0.46,1)),(0.45,(0.07,0.07,0.075,1))): x=e.new(pos); x.color=col
    nt.links.new(ad.outputs[0],cr.inputs[0]); nt.links.new(cr.outputs[0],b.inputs['Base Color'])
    b.inputs['Roughness'].default_value=0.38; b.inputs['Specular IOR Level'].default_value=0.6
    try: b.inputs['Sheen Weight'].default_value=0.3
    except: pass
    return m
HM=hairmat()
# her black->white strip atlas (5:13 PM): use it only if the Umeko UVs land on strands, not on the white background
HA=None
if os.path.exists(A+'/hair_texture_black_to_white_1713.jpg'):
    ai=img('hair_texture_black_to_white_1713.jpg'); W_,H_=ai.size; apx=np.array(ai.pixels[:]).reshape(H_,W_,4)
    uvd=UM.data.uv_layers.active.data; n=len(uvd); idx=range(0,n,max(1,n//4000)); white=0
    for i in idx:
        u,v=uvd[i].uv; x=min(W_-1,max(0,int((u%1)*W_))); y=min(H_-1,max(0,int((v%1)*H_)))
        if apx[y,x,:3].mean()>0.85: white+=1
    wf=white/len(idx); rep['hair_atlas_white_fraction']=wf; log('hair atlas: fraction of Umeko UVs on white background',round(wf,3))
    if wf<P.get('ATLAS_MAX_WHITE',0.3):
        HA,nt,b=newmat('HairAtlas'); ta=nt.nodes.new('ShaderNodeTexImage'); ta.image=ai; nt.links.new(ta.outputs[0],b.inputs['Base Color']); b.inputs['Roughness'].default_value=0.38
        HM=HA; log('hair: using her atlas')
    else: log('hair: atlas does not fit Umeko UVs -> gradient by height')
UM.data.materials.clear(); UM.data.materials.append(HM)
def solidmat(name,col,rough=0.4,metal=0.0):
    m,nt,b=newmat(name); b.inputs['Base Color'].default_value=(*col,1); b.inputs['Roughness'].default_value=rough; b.inputs['Metallic'].default_value=metal; return m,nt,b
# bra: grey ribbed knit
m,nt,b=solidmat('BraKnit',(0.30,0.29,0.30),0.7)
wv=nt.nodes.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value=180; wv.wave_type='BANDS'; wv.bands_direction='X'
bp=nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value=0.25; nt.links.new(wv.outputs['Fac'],bp.inputs['Height']); nt.links.new(bp.outputs[0],b.inputs['Normal'])
BRA.data.materials.clear(); BRA.data.materials.append(m)
# shorts: her black base color (52f8), AO (41d6), roughness (f14f)
m,nt,b=newmat('ShortsBlack')
tb=nt.nodes.new('ShaderNodeTexImage'); tb.image=img('52f8d9c0-f8e3-439b-88d0-8ac7c27be214.jpg')
ta=nt.nodes.new('ShaderNodeTexImage'); ta.image=img('41d6d1bf-d8bb-4dba-b796-1b80ac9f38a9.jpg'); ta.image.colorspace_settings.name='Non-Color'
tr=nt.nodes.new('ShaderNodeTexImage'); tr.image=img('f14f4077-56a8-49b7-b71b-577eb6d05c04.jpg'); tr.image.colorspace_settings.name='Non-Color'
mx=nt.nodes.new('ShaderNodeMix'); mx.data_type='RGBA'; mx.blend_type='MULTIPLY'; mx.inputs['Factor'].default_value=0.6
nt.links.new(tb.outputs[0],mx.inputs['A']); nt.links.new(ta.outputs[0],mx.inputs['B']); nt.links.new(mx.outputs['Result'],b.inputs['Base Color']); nt.links.new(tr.outputs[0],b.inputs['Roughness'])
SH.data.materials.clear(); SH.data.materials.append(m)
# ---------- decimate to the VRChat budget (<70k tris)
def dec(o,r):
    if r>=0.999: return
    if o.data.shape_keys:
        o.shape_key_clear()
    md=o.modifiers.new('Dec','DECIMATE'); md.ratio=r; md.use_collapse_triangulate=False
    sel([o]); bpy.ops.object.modifier_move_to_index(modifier='Dec',index=0); bpy.ops.object.modifier_apply(modifier='Dec')
dec(BODY,P['BODY_DEC']); dec(UM,P['HAIR_DEC']); dec(BRA,P['BRA_DEC']); dec(SH,P['SHORTS_DEC'])
# ---------- curvier (her sheet: wide hips, thick thighs, full bust, small waist) — pose-scale perpendicular to the bones, bake into the meshes, keep the rig
CUR=P.get('CURVY',{'Hips':(1.10,1.0,1.06),'Left leg':(1.14,1.0,1.12),'Right leg':(1.14,1.0,1.12),'Twist_Leg.L':(1.10,1.0,1.08),'Twist_Leg.R':(1.10,1.0,1.08),
     'Twist_Butt.L':(1.12,1.0,1.12),'Twist_Butt.R':(1.12,1.0,1.12),'Ass_Wiggle.L':(1.12,1.12,1.12),'Ass_Wiggle.R':(1.12,1.12,1.12),
     'BreastUpper2_L':(1.14,1.14,1.14),'BreastUpper2_R':(1.14,1.14,1.14),'Spine':(0.94,1.0,0.96)})
if CUR:
    saved={}
    for bn_,sc_ in CUR.items():
        if bn_ not in B.data.bones: log('curvy: no bone',bn_); continue
        for c in list(B.data.bones[bn_].children)+[B.data.bones[bn_]]:
            if c.name not in saved: saved[c.name]=c.inherit_scale; c.inherit_scale='NONE'
        B.pose.bones[bn_].scale=sc_
    bpy.context.view_layer.update()
    for o in (BODY,BRA,SH):
        sel([o]); am=[m for m in o.modifiers if m.type=='ARMATURE'][0]; bpy.ops.object.modifier_apply(modifier=am.name)
    sel([B]); bpy.ops.object.mode_set(mode='POSE'); bpy.ops.pose.armature_apply(selected=False); bpy.ops.object.mode_set(mode='OBJECT')
    for n_,v_ in saved.items(): B.data.bones[n_].inherit_scale=v_
    for o in (BODY,BRA,SH):
        md=o.modifiers.new('Armature','ARMATURE'); md.object=B
    log('curvy applied',list(CUR))
# ---------- bun + black claw clip + cross necklace (rigid to Head / Chest)
def add_mesh(name,bm,mat,group):
    me=bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); o=bpy.data.objects.new(name,me); sc.collection.objects.link(o)
    me.materials.append(mat); vg=o.vertex_groups.new(name=group); vg.add(list(range(len(me.vertices))),1.0,'REPLACE')
    o.parent=B; md=o.modifiers.new('Armature','ARMATURE'); md.object=B
    for p in me.polygons: p.use_smooth=True
    return o
hmn,hmx=wbb([FH]); umn,umx=wbb([UM])
hr=(hmx.x-hmn.x)/2
bunc=Vector((0, (hmn.y+hmx.y)/2+0.045, umx.z-0.012))
bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=16,v_segments=10,radius=hr*0.42)
for v in bm.verts:
    v.co.z*=0.8; v.co+=bunc
    v.co.x+=0.004*math.sin(v.co.z*900); v.co.y+=0.004*math.cos(v.co.x*800)
r2=bmesh.ops.create_uvsphere(bm,u_segments=12,v_segments=8,radius=hr*0.3)
for v in r2['verts']: v.co.z*=0.9; v.co+=bunc+Vector((0.012,0.01,0.012))
uvl=bm.loops.layers.uv.new('UVMap')
BUN=add_mesh('Bun',bm,bpy.data.materials['HairGradient'],'Head')
clip=bpy.data.materials.new('ClawClipBlack'); clip.use_nodes=True; cb=clip.node_tree.nodes['Principled BSDF']; cb.inputs['Base Color'].default_value=(0.008,0.008,0.009,1); cb.inputs['Roughness'].default_value=0.18
bm=bmesh.new()
cc=bunc+Vector((0,0.0,-hr*0.25))
for k in range(5):  # claw teeth arcs on each side
    for side in (-1,1):
        r=bmesh.ops.create_cube(bm,size=1.0)
        vs=r['verts']; x=(k-2)*0.0085
        for v in vs:
            v.co=Vector((v.co.x*0.004, v.co.y*0.006, v.co.z*0.03))
            a=side*0.55; v.co=Matrix.Rotation(a,3,'X')@v.co
            v.co+=cc+Vector((x, side*0.016, 0.0))
r=bmesh.ops.create_cube(bm,size=1.0)
for v in r['verts']: v.co=Vector((v.co.x*0.05,v.co.y*0.012,v.co.z*0.012))+cc+Vector((0,0,0.017))
uvl=bm.loops.layers.uv.new('UVMap')
CLIP=add_mesh('ClawClip',bm,clip,'Head')
# cross necklace: chain ring around the neck base + small cross on the sternum
silver=bpy.data.materials.new('Silver'); silver.use_nodes=True; sb=silver.node_tree.nodes['Principled BSDF']; sb.inputs['Base Color'].default_value=(0.85,0.85,0.88,1); sb.inputs['Metallic'].default_value=1; sb.inputs['Roughness'].default_value=0.2
neck=B.data.bones['Neck']; nh=B.matrix_world@neck.head_local
# find body cross-section at neck base to size the chain
nz=nh.z+P.get('NECK_DZ',0.0)
rx=P.get('NECK_RX',0.05); ry0=nh.y-P.get('NECK_RY',0.047); ry1=nh.y+P.get('NECK_RY',0.047); ring=[]
log('neck ring',len(ring),rx,ry0,ry1)
bm=bmesh.new(); prev=None; pts=[]
N=40
from mathutils.bvhtree import BVHTree
dg0=bpy.context.evaluated_depsgraph_get(); bvh=BVHTree.FromObject(BODY,dg0)
for i in range(N):
    a=2*math.pi*i/N
    x=(rx+0.006)*math.sin(a); y=((ry0+ry1)/2)+((ry1-ry0)/2+0.006)*(-math.cos(a)); z=nz-P.get('NECK_DROP',0.07)*max(0,math.cos(a))**2
    p=Vector((x,y,z)); hit=bvh.find_nearest(p)
    if hit and hit[0] is not None: p=hit[0]+hit[1].normalized()*0.0028
    pts.append(p)
log('necklace front point',pts[0])
for i in range(N):
    p0,p1=pts[i],pts[(i+1)%N]
    r=bmesh.ops.create_cube(bm,size=1.0); d=p1-p0; L=d.length
    rot=d.to_track_quat('X','Z').to_matrix()
    for v in r['verts']: v.co=rot@Vector((v.co.x*L,v.co.y*0.0012,v.co.z*0.0012))+(p0+p1)/2
low=pts[0]
cx=low+Vector((0,-0.002,-0.013))
for dims,off in (((0.0025,0.0016,0.018),(0,0,0)),((0.011,0.0016,0.0025),(0,0,0.003))):
    r=bmesh.ops.create_cube(bm,size=1.0)
    for v in r['verts']: v.co=Vector((v.co.x*dims[0],v.co.y*dims[1],v.co.z*dims[2]))+cx+Vector(off)
uvl=bm.loops.layers.uv.new('UVMap')
NECK=add_mesh('CrossNecklace',bm,silver,'Chest')
meshes=[o for o in bpy.data.objects if o.type=='MESH']
tri={o.name:tris(o) for o in meshes}; rep['tris']=tri; rep['tris_total']=sum(tri.values()); rep['bones']=len(B.data.bones)
rep['materials']=sorted(set(s.material.name for o in meshes for s in o.material_slots if s.material))
rep['shapekeys_head']=[k.name for k in FH.data.shape_keys.key_blocks][:20] if FH.data.shape_keys else []
log('TRIS',rep['tris_total'],tri); log('materials',rep['materials'])
# no piercings by default
if FH.data.shape_keys and 'No peircings ' in FH.data.shape_keys.key_blocks: FH.data.shape_keys.key_blocks['No peircings '].value=1.0
# ---------- export (rest pose) for Unity/VRChat
if P['EXPORT']:
    bpy.ops.wm.save_as_mainfile(filepath=OUT+'/jena-v3.blend',compress=True)
    sel([B]+meshes,B)
    try:
        bpy.ops.export_scene.fbx(filepath=OUT+'/jena-v3.fbx',use_selection=True,add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',armature_nodetype='NULL',apply_scale_options='FBX_SCALE_ALL',path_mode='COPY',embed_textures=True)
        log('fbx ok',os.path.getsize(OUT+'/jena-v3.fbx'))
    except Exception as e: log('FBXERR',e)
json.dump(rep,open(OUT+'/build-report.json','w'),indent=1,default=str)
# ---------- proof renders (posed: arms down, like her sheet)
bpy.context.view_layer.objects.active=B; bpy.ops.object.mode_set(mode='POSE')
for name,sgn in (('Left arm',1),('Right arm',-1)):
    pb=B.pose.bones[name]; h=pb.head.copy()
    R=Matrix.Translation(h)@Matrix.Rotation(math.radians(sgn*P['ARM_DOWN']),4,'Y')@Matrix.Translation(-h)
    pb.matrix=R@pb.matrix; bpy.context.view_layer.update()
bpy.ops.object.mode_set(mode='OBJECT')
if P['RENDER']:
    sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=P['SAMPLES']; sc.cycles.use_denoising=True
    sc.render.film_transparent=True; sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGBA'
    sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Medium High Contrast'; sc.view_settings.exposure=P.get('EXPOSURE',-0.45)
    w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; bg=w.node_tree.nodes['Background']; bg.inputs[0].default_value=(0.06,0.06,0.065,1); bg.inputs[1].default_value=1.0
    def area(name,loc,energy,size,col=(1,1,1)):
        L=bpy.data.lights.new(name,'AREA'); L.energy=energy; L.size=size; L.color=col; o=bpy.data.objects.new(name,L); sc.collection.objects.link(o); o.location=loc
        o.rotation_euler=(Vector((0,0,0.75))-Vector(loc)).to_track_quat('-Z','Y').to_euler(); return o
    area('key',(-1.6,-2.2,2.0),260,1.6,(1,0.97,0.94)); area('fill',(1.8,-1.8,1.2),110,2.0,(0.92,0.95,1)); area('rim',(0.4,2.4,2.0),220,1.4); area('rim2',(-1.2,2.0,1.4),120,1.2)
    cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam
    mn,mx=wbb([o for o in meshes if o.visible_get()])
    # deformed bounds: use evaluated mesh extents
    dg=bpy.context.evaluated_depsgraph_get(); pts=[]
    for o in meshes:
        e=o.evaluated_get(dg); vv=e.data.vertices; pts+= [e.matrix_world@vv[i].co for i in range(0,len(vv),7)]
    mn=Vector([min(p[i] for p in pts) for i in range(3)]); mx=Vector([max(p[i] for p in pts) for i in range(3)]); ce=(mn+mx)/2; H=mx.z-mn.z
    rep['posed_bb']=[list(mn),list(mx)]
    cam.data.type='PERSP'; cam.data.lens=85; dist=H*1.06/(36/85)*1.0
    def shot(name,view,rx,ry,lens=85,target=None,h=None):
        sc.render.resolution_x,sc.render.resolution_y=rx,ry; cam.data.lens=lens; cam.data.sensor_fit='VERTICAL'; cam.data.sensor_height=24
        tgt=target or ce; hh=h or H*1.06
        d=hh/(24/lens)
        dirs={'front':Vector((0,-1,0)),'back':Vector((0,1,0)),'side':Vector((-1,0,0)),'q34':Vector((-0.72,-0.69,0)).normalized()}
        cam.location=tgt+dirs[view]*d; cam.rotation_euler=(tgt-cam.location).to_track_quat('-Z','Y').to_euler(); cam.data.clip_end=d*3
        sc.render.filepath=OUT+'/proof/'+name+'.png'; bpy.ops.render.render(write_still=True); log('render',name)
    shot('front','front',768,1376); shot('side','side',768,1376); shot('back','back',864,1536)
    hmn,hmx=wbb([FH]); fc=(hmn+hmx)/2; fc.z+=0.01
    fc=Vector((0,(hmn.y+hmx.y)/2,hmx.z-0.055))
    shot('face','front',1024,1024,lens=100,target=fc,h=0.30)
    shot('face34','q34',1024,1024,lens=100,target=fc,h=0.30)
json.dump(rep,open(OUT+'/build-report.json','w'),indent=1,default=str)
log('DONE')
