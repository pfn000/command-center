
import bpy, sys, os, math, json, mathutils, bmesh
from mathutils import Vector, Matrix
argv=sys.argv[sys.argv.index('--')+1:]; IN,OUT=argv[0],argv[1]; A=IN+'/assets'; os.makedirs(OUT+'/proof',exist_ok=True)
def log(*a): print('[v3]',*a,flush=True)
P=dict(HAIR_W_RATIO=1.40, HAIR_TOP_GAP=0.010, HAIR_DY=0.030, HAIR_DZ=0.006, HEAD_SCALE=1.14, SHORTS_DROP=0.035, SKIN_COAT=0.5, SKIN_ROUGH=0.3, BODY_MAT='5867', BRA_OFF=0.005, ARM_DOWN=68, SAMPLES=48, RENDER=True, EXPORT=True,
       BODY_DEC=0.55, HAIR_DEC=0.55, BRA_DEC=0.5, SHORTS_DEC=0.45)
try: P.update(json.load(open(os.path.dirname(os.path.abspath(__file__))+'/params.json')))
except Exception as e: log('no params',e)
TT=os.environ.get('TT_SHARD')
if TT is not None: P['EXPORT']=False; P['RENDER']=False; P['TT']=True
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
BF=IN+"/Panda's Fit Base (High - Flat Foot)/"
with bpy.data.libraries.load(BF+"Panda's Fit Base (High - Flat Foot).blend",link=False) as (df,dt): dt.objects=list(df.objects)
for o in dt.objects: sc.collection.objects.link(o)
B=bpy.data.objects['Armature']; BODY=bpy.data.objects['Body']; B.name='Armature'
log('body bones',len(B.data.bones),'tris',tris(BODY))
for im_ in bpy.data.images:
    base=im_.name.split('.png')[0]+'.png'
    if os.path.exists(BF+base): im_.filepath=BF+base; im_.reload(); log('relinked',im_.name,'->',base,list(im_.size))
# ---------- head (Female head + hair FBX; only the head mesh, its hair is pigtails)
new=imp_fbx('hair_female_head_hair.fbx')
FA=[o for o in new if o.type=='ARMATURE'][0]; FH=bpy.data.objects['Female Head']
for o in new:
    if o.type=='MESH' and o is not FH: bpy.data.objects.remove(o)
# ---------- hair (Umeko, shaggy shoulder-length = closest to her sheet)
HAIR=P.get('HAIR','blowout_cards')
hf={'blowout':IN+'/Blowout Solid textures.fbx','blowout_cards':IN+"/Blowout Nikkie's haircards.fbx",'umeko':A+'/hair_umeko_gift.fbx'}[HAIR]
before=set(bpy.data.objects); bpy.ops.import_scene.fbx(filepath=hf); new=[o for o in bpy.data.objects if o not in before]
UA=[o for o in new if o.type=='ARMATURE'][0]; hm=[o for o in new if o.type=='MESH']
for o in new: log('hair import',HAIR,o.name,o.type,tris(o),[s.material.name for s in o.material_slots if s.material] if o.type=='MESH' else len(o.data.bones))
for o in hm:
    for s in o.material_slots:
        if s.material and s.material.use_nodes:
            log('hair mat',s.material.name,[(n.image.name,n.image.filepath) for n in s.material.node_tree.nodes if n.type=='TEX_IMAGE' and n.image])
if len(hm)>1: sel(hm,hm[0]); bpy.ops.object.join()
UM=hm[0]; UM.name='Hair'
if UM.parent is not UA: mw=UM.matrix_world.copy(); UM.parent=UA; UM.matrix_world=mw
log('hair bones',[b_.name for b_ in UA.data.bones][:60])
if P.get('HEAD_SCALE',1.0)!=1.0:
    hmn,hmx=wbb([FH]); piv=Vector((0,(hmn.y+hmx.y)/2,hmn.z))
    S_=Matrix.Translation(piv)@Matrix.Scale(P['HEAD_SCALE'],4)@Matrix.Translation(-piv)
    FA.matrix_world=S_@FA.matrix_world; bpy.context.view_layer.update()
    sel([FA,FH],FA); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True); log('head scaled',P['HEAD_SCALE'])
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
bodyn=set(b_.name for b_ in B.data.bones); DUP={}
for k,arm in enumerate((FA,UA)):
    for b_ in arm.data.bones:
        if b_.name in bodyn:
            o_=b_.name; b_.name=f'DUP{k}_'+o_; DUP[b_.name]=o_
log('dup bones',DUP)
roots=[b_.name for arm in (FA,UA) for b_ in arm.data.bones if b_.parent is None and b_.name not in DUP]
# FH/UM vertex groups named Head/Neck now point to the body's Head/Neck (same names)
sel([B,FA,UA],B); bpy.ops.object.join()
bpy.ops.object.mode_set(mode='EDIT'); eb=B.data.edit_bones
for d,t in DUP.items():
    if d in eb:
        for c in list(eb[d].children): c.parent=eb[t]
        eb.remove(eb[d])
for r_ in roots:
    if r_ in eb and eb[r_].parent is None: eb[r_].parent=eb['Head']; log('rooted under Head',r_)
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
    if n in DUP: return DUP[n]
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
    if not P.get('USE_MESHY',False): raise RuntimeError('meshy off: using her ZinPia eye texture')
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
bs.inputs['Roughness'].default_value=P.get('SKIN_ROUGH',0.3); bs.inputs['Subsurface Weight'].default_value=0.1; bs.inputs['Subsurface Radius'].default_value=(1.0,0.35,0.25); bs.inputs['Subsurface Scale'].default_value=0.01
bs.inputs['Coat Weight'].default_value=P.get('SKIN_COAT',0.5); bs.inputs['Coat Roughness'].default_value=0.12
if P.get('BODY_MAT','original')=='original' and all(im_.size[0]>0 for im_ in bpy.data.images if im_.name.startswith(('BODY','Skin 1'))):
    log('body: her authored material (BODY.png + Skin 1.png)')
    for s_ in BODY.material_slots:
        for n_ in s_.material.node_tree.nodes:
            if n_.type=='BSDF_PRINCIPLED':
                n_.inputs['Roughness'].default_value=P.get('SKIN_ROUGH',0.36); n_.inputs['Coat Weight'].default_value=P.get('SKIN_COAT',0.18); n_.inputs['Coat Roughness'].default_value=0.25
                n_.inputs['Subsurface Weight'].default_value=0.12; n_.inputs['Subsurface Radius'].default_value=(1.0,0.35,0.25); n_.inputs['Subsurface Scale'].default_value=0.01
else: BODY.data.materials.clear(); BODY.data.materials.append(mb); log('body: fallback 5867')
# skin tone for the head from the body texture's median skin pixel
import numpy as np
im=t.image; px=np.array(im.pixels[:]).reshape(-1,4)[::97,:3]; lum=px.mean(1); sk=px[(lum>0.35)&(lum<0.95)]
skin=tuple(np.median(sk,0)) if len(sk) else (0.85,0.68,0.66); log('skin rgb (linear-ish)',skin); rep['skin']=list(map(float,skin))
for i,s in enumerate(FH.material_slots):
    n=s.material.name.lower() if s.material else ''
    if n.startswith('face'):
        m,nt,b=newmat('Face'); b.inputs['Base Color'].default_value=(*skin,1); b.inputs['Roughness'].default_value=P.get('SKIN_ROUGH',0.3)+0.05; b.inputs['Coat Weight'].default_value=P.get('SKIN_COAT',0.5)*0.7; b.inputs['Coat Roughness'].default_value=0.15
        HT=IN+'/1691108855vrmodels_store_female-head-by-bunisu/Female head/female head textures/'+P.get('FACE_TEX','1.png')
        if os.path.exists(HT):
            ft=nt.nodes.new('ShaderNodeTexImage'); ft.image=bpy.data.images.load(HT); nt.links.new(ft.outputs[0],b.inputs['Base Color']); nt.links.new(ft.outputs[1],b.inputs['Alpha']); log('face texture: her head pack',HT.split('/')[-1])
        elif os.path.exists(A+'/face_skin_2_from_saidie_1708.jpg'):
            ft=nt.nodes.new('ShaderNodeTexImage'); ft.image=img('face_skin_2_from_saidie_1708.jpg'); nt.links.new(ft.outputs[0],b.inputs['Base Color']); log('face texture: jpg she sent 5:08 PM'); b.inputs['Subsurface Weight'].default_value=0.08; b.inputs['Subsurface Radius'].default_value=(1.0,0.35,0.25)
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
        ET=IN+'/ZinPia_Doe Eyes (Sunny Head)/'+P.get('EYE_TEX','doe 5.png')
        if os.path.exists(ET):
            ti=nt.nodes.new('ShaderNodeTexImage'); ti.image=bpy.data.images.load(ET); nt.links.new(ti.outputs[0],b.inputs['Base Color']); nt.links.new(ti.outputs[1],b.inputs['Alpha'])
            ez=P.get('EYE_ZOOM',1.0); eo_=P.get('EYE_OFF',(0.0,0.0))
            if ez!=1.0 or eo_!=(0.0,0.0):
                mp2=nt.nodes.new('ShaderNodeMapping'); mp2.vector_type='POINT'; mp2.inputs['Scale'].default_value=(ez,ez,1); mp2.inputs['Location'].default_value=(0.5-0.5*ez+eo_[0],0.5-0.5*ez+eo_[1],0)
                nt.links.new(uv.outputs['UV'],mp2.inputs['Vector']); nt.links.new(mp2.outputs[0],ti.inputs[0]); ti.extension='EXTEND'
            b.inputs['Emission Strength'].default_value=0.15; nt.links.new(ti.outputs[0],b.inputs['Emission Color']); log('eyes: her ZinPia',ET.split('/')[-1])
        elif EYE_TEX is not None:
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
HCT=IN+'/Textures/'+P.get('HAIR_TEX','B&W.png')
if HAIR=='blowout_cards' and os.path.exists(HCT):
    HM,nt,b=newmat('HairCards'); tt=nt.nodes.new('ShaderNodeTexImage'); tt.image=bpy.data.images.load(HCT)
    gm=nt.nodes.new('ShaderNodeGamma'); gm.inputs['Gamma'].default_value=P.get('HAIR_GAMMA',1.9); nt.links.new(tt.outputs[0],gm.inputs['Color'])
    nt.links.new(gm.outputs[0],b.inputs['Base Color']); nt.links.new(tt.outputs[1],b.inputs['Alpha']); b.inputs['Roughness'].default_value=0.4
    b.inputs['Anisotropic'].default_value=0.6; b.inputs['Sheen Weight'].default_value=0.35; b.inputs['Sheen Roughness'].default_value=0.4; b.inputs['Specular IOR Level'].default_value=0.65; b.inputs['Roughness'].default_value=0.36
    try: HM.blend_method='HASHED'
    except: pass
    log('hair: Blowout haircards with her',HCT.split('/')[-1])
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
def ld(p,alt):
    q=IN+'/Textures/'+p
    return bpy.data.images.load(q) if os.path.exists(q) else img(alt)
tb=nt.nodes.new('ShaderNodeTexImage'); tb.image=ld(P.get('SHORTS_TEX','Colors/Black.png'),'52f8d9c0-f8e3-439b-88d0-8ac7c27be214.jpg')
ta=nt.nodes.new('ShaderNodeTexImage'); ta.image=ld('Main/Material.001_Mixed_AO.png','41d6d1bf-d8bb-4dba-b796-1b80ac9f38a9.jpg'); ta.image.colorspace_settings.name='Non-Color'
tr=nt.nodes.new('ShaderNodeTexImage'); tr.image=ld('Main/Material.001_Roughness.png','f14f4077-56a8-49b7-b71b-577eb6d05c04.jpg'); tr.image.colorspace_settings.name='Non-Color'
log('shorts textures',tb.image.filepath.split('/')[-1],ta.image.filepath.split('/')[-1])
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
dec(BODY,P['BODY_DEC']); dec(UM,P['HAIR_DEC'] if tris(UM)>9000 else 1.0); dec(BRA,P['BRA_DEC']); dec(SH,P['SHORTS_DEC'])
# ---------- curvier (her sheet: wide hips, thick thighs, full bust, small waist) — pose-scale perpendicular to the bones, bake into the meshes, keep the rig
CUR=P.get('CURVY',{'Hips':(1.10,1.0,1.06),'Left leg':(1.14,1.0,1.12),'Right leg':(1.14,1.0,1.12),'Twist_Leg.L':(1.10,1.0,1.08),'Twist_Leg.R':(1.10,1.0,1.08),
     'Twist_Butt.L':(1.12,1.0,1.12),'Twist_Butt.R':(1.12,1.0,1.12),'Ass_Wiggle.L':(1.12,1.12,1.12),'Ass_Wiggle.R':(1.12,1.12,1.12),
     'BreastUpper2_L':(1.14,1.14,1.14),'BreastUpper2_R':(1.14,1.14,1.14),'Spine':(0.88,1.0,0.93)})
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
bunm=bpy.data.materials.new('BunDark'); bunm.use_nodes=True; q=bunm.node_tree.nodes['Principled BSDF']; q.inputs['Base Color'].default_value=(0.02,0.02,0.022,1); q.inputs['Roughness'].default_value=0.42
BUN=add_mesh('Bun',bm,bunm,'Head')
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
    for v in r['verts']: v.co=rot@Vector((v.co.x*L,v.co.y*0.0019,v.co.z*0.0019))+(p0+p1)/2
low=pts[0]
cx=low+Vector((0,-0.0035,-0.021))
for dims,off in (((0.0045,0.0026,0.036),(0,0,0)),((0.021,0.0026,0.0045),(0,0,0.007))):
    r=bmesh.ops.create_cube(bm,size=1.0)
    for v in r['verts']: v.co=Vector((v.co.x*dims[0],v.co.y*dims[1],v.co.z*dims[2]))+cx+Vector(off)
uvl=bm.loops.layers.uv.new('UVMap')
NECK=add_mesh('CrossNecklace',bm,silver,'Chest')
# ---------- bra straps (thin black, over the shoulders) + small center bow, as on her sheet
blk=bpy.data.materials.new('StrapBlack'); blk.use_nodes=True; kb=blk.node_tree.nodes['Principled BSDF']; kb.inputs['Base Color'].default_value=(0.012,0.012,0.013,1); kb.inputs['Roughness'].default_value=0.5
dg0=bpy.context.evaluated_depsgraph_get(); bvh=BVHTree.FromObject(BODY,dg0)
bmn,bmx=wbb([BRA])
def snap(p,off):
    h=bvh.find_nearest(p)
    return h[0]+h[1].normalized()*off if h and h[0] is not None else p
def ribbon(bm,pts,w,t):
    for i in range(len(pts)-1):
        p0,p1=pts[i],pts[i+1]; d=p1-p0; L=d.length
        if L<1e-6: continue
        r=bmesh.ops.create_cube(bm,size=1.0); rot=d.to_track_quat('X','Z').to_matrix()
        for v in r['verts']: v.co=rot@Vector((v.co.x*L*1.08,v.co.y*w,v.co.z*t))+(p0+p1)/2
bm=bmesh.new()
sh_l=B.data.bones['Left shoulder']; shz=(B.matrix_world@sh_l.tail_local).z
for sgn in (1,-1):
    x=sgn*P.get('STRAP_X',0.055); pts=[]
    zt=bmx.z-0.004; zs=shz+0.03
    for k in range(25):
        t=k/24.0; a=math.pi*t
        y=-0.10*math.cos(a)+0.03; z=zt+(zs-zt)*math.sin(a)
        pts.append(snap(Vector((x+sgn*0.012*math.sin(a),y,z)),0.0022))
    ribbon(bm,pts,0.0035,0.0016)
# bow at the center gore
gv=[BRA.matrix_world@v.co for v in BRA.data.vertices if abs((BRA.matrix_world@v.co).x)<0.01]
if gv:
    g=min(gv,key=lambda p:p.y); gc=Vector((0,g.y-0.004,(max(p.z for p in gv)+min(p.z for p in gv))/2+0.01))
    for sx in (-1,1):
        r=bmesh.ops.create_uvsphere(bm,u_segments=8,v_segments=6,radius=1.0)
        for v in r['verts']: v.co=Vector((v.co.x*0.0055,v.co.y*0.0016,v.co.z*0.0034))+gc+Vector((sx*0.0055,0,0))
    r=bmesh.ops.create_uvsphere(bm,u_segments=8,v_segments=6,radius=0.0022)
    for v in r['verts']: v.co+=gc+Vector((0,-0.001,0))
uvl=bm.loops.layers.uv.new('UVMap')
STR=add_mesh('BraStraps',bm,blk,'Chest')
# bra back band (grey knit) + black clasp, closing the bra around the back
bm=bmesh.new(); zb=bmn.z+P.get('BAND_DZ',0.022); pts=[]
for k in range(41):
    a=math.pi*(k/40.0)   # from left side (x+) around the back to right side (x-)
    x=0.16*math.cos(a); y=0.12*math.sin(a)+0.0
    pts.append(snap(Vector((x,y,zb)),0.0022))
pts=[p for p in pts if p.y>bmx.y-0.03]
ribbon(bm,pts,P.get('BAND_W',0.016),0.0022)
cl=snap(Vector((0,0.2,zb)),0.0035)
r=bmesh.ops.create_cube(bm,size=1.0)
for v in r['verts']: v.co=Vector((v.co.x*0.014,v.co.y*0.003,v.co.z*0.012))+cl
uvl=bm.loops.layers.uv.new('UVMap')
BAND=add_mesh('BraBand',bm,bpy.data.materials['BraKnit'],'Chest'); log('bra band pts',len(pts))
# ---------- shorts: lower the waistband onto the hips (compress the top band down, keep it on the skin)
if P.get('SHORTS_DROP',0.035)>0:
    smn,smx=wbb([SH]); top=smx.z; z0=top-P.get('SHORTS_BAND',0.11); f=1-P['SHORTS_DROP']/(top-z0); moved=0
    mw=SH.matrix_world; mwi=mw.inverted()
    for v in SH.data.vertices:
        p=mw@v.co
        if p.z>z0:
            p.z=z0+(p.z-z0)*f; h=bvh.find_nearest(p)
            if h and h[0] is not None:
                n_=h[1].normalized()
                if (p-h[0]).dot(n_)<0.0015: p=h[0]+n_*0.0015
            v.co=mwi@p; moved+=1
    SH.data.update(); log('shorts waistband lowered',P['SHORTS_DROP'],'verts',moved)
# ---------- keep clothes outside the (curvier) skin
for o,off in ((SH,0.0016),(BRA,P.get('BRA_OFF',0.0035))):
    mw=o.matrix_world; mwi=mw.inverted(); pushed=0
    for v in o.data.vertices:
        p=mw@v.co; h=bvh.find_nearest(p)
        if h and h[0] is not None:
            n_=h[1].normalized()
            if (p-h[0]).dot(n_)<off: v.co=mwi@(h[0]+n_*off); pushed+=1
    o.data.update(); log('pushed outside skin',o.name,pushed)
# ---------- scalp cap: the Female head is a face shell; close the back of the head under the hair
if P.get('SCALP',True):
    hmn,hmx=wbb([FH]); hw=(hmx.x-hmn.x)/2
    sc_c=Vector((0,hmx.y+P.get('SCALP_DY',0.012),hmx.z-0.054))
    bm=bmesh.new(); r=bmesh.ops.create_uvsphere(bm,u_segments=20,v_segments=14,radius=1.0)
    for v in r['verts']: v.co=Vector((v.co.x*hw*0.84,v.co.y*P.get('SCALP_RY',0.05),v.co.z*0.056))+sc_c
    uvl=bm.loops.layers.uv.new('UVMap')
    scm=bpy.data.materials.new('ScalpBlack'); scm.use_nodes=True; q=scm.node_tree.nodes['Principled BSDF']; q.inputs['Base Color'].default_value=(0.015,0.015,0.016,1); q.inputs['Roughness'].default_value=0.4
    snt=scm.node_tree; wv=snt.nodes.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value=90; wv.bands_direction='X'; wv.inputs['Distortion'].default_value=4
    bp=snt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value=0.35; snt.links.new(wv.outputs['Fac'],bp.inputs['Height']); snt.links.new(bp.outputs[0],q.inputs['Normal'])
    SCALP=add_mesh('Scalp',bm,scm,'Head'); log('scalp cap',sc_c,hw)
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

if P.get('TT'):
    sh_i=int(os.environ['TT_SHARD']); sh_n=int(os.environ.get('TT_SHARDS','4')); NF=P.get('TT_FRAMES',96)
    sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=P.get('TT_SAMPLES',10); sc.cycles.use_denoising=True
    sc.render.film_transparent=False; sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGB'
    sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Medium High Contrast'; sc.view_settings.exposure=P.get('EXPOSURE',-0.45)
    w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; bg=w.node_tree.nodes['Background']; bg.inputs[0].default_value=(0.05,0.05,0.052,1); bg.inputs[1].default_value=1.0
    dg=bpy.context.evaluated_depsgraph_get(); pts=[]
    for o in meshes:
        e=o.evaluated_get(dg); vv=e.data.vertices; pts+=[e.matrix_world@vv[i].co for i in range(0,len(vv),7)]
    mn=Vector([min(p[i] for p in pts) for i in range(3)]); mx=Vector([max(p[i] for p in pts) for i in range(3)]); ce=(mn+mx)/2; Hh=(mx.z-mn.z)*1.08
    rig=bpy.data.objects.new('ttrig',None); sc.collection.objects.link(rig); rig.location=(ce.x,ce.y,0)
    def area(name,loc,energy,size,col=(1,1,1)):
        L=bpy.data.lights.new(name,'AREA'); L.energy=energy; L.size=size; L.color=col; o=bpy.data.objects.new(name,L); sc.collection.objects.link(o); o.location=loc
        o.rotation_euler=(Vector((0,0,0.75))-Vector(loc)).to_track_quat('-Z','Y').to_euler(); o.parent=rig; return o
    area('key',(-1.6,-2.2,2.0),260,1.6,(1,0.97,0.94)); area('fill',(1.8,-1.8,1.2),110,2.0,(0.92,0.95,1)); area('rim',(0.4,2.4,2.0),220,1.4); area('rim2',(-1.2,2.0,1.4),120,1.2)
    cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera=cam
    cam.data.lens=85; cam.data.sensor_fit='VERTICAL'; cam.data.sensor_height=24; d=Hh/(24/85)
    cam.location=Vector((0,-d,ce.z)); cam.rotation_euler=(Vector((0,0,ce.z))-cam.location).to_track_quat('-Z','Y').to_euler(); cam.parent=rig; cam.data.clip_end=d*3
    sc.render.resolution_x,sc.render.resolution_y=P.get('TT_W',1080),P.get('TT_H',1920)
    per=(NF+sh_n-1)//sh_n; os.makedirs(OUT+'/frames',exist_ok=True)
    for f in range(sh_i*per,min(NF,(sh_i+1)*per)):
        rig.rotation_euler=(0,0,2*math.pi*f/NF); bpy.context.view_layer.update()
        sc.render.filepath=OUT+f'/frames/f{f:03d}.png'; bpy.ops.render.render(write_still=True); log('frame',f)
json.dump(rep,open(OUT+'/build-report.json','w'),indent=1,default=str)
log('DONE')
