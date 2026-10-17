
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

# ---------- v3.1 FACE RESHAPE (semi-realistic): smaller almond eyes, nose bridge, applied to basis + every shape key
def _shift_all_keys(o,delta_world):
    mwi3=o.matrix_world.inverted().to_3x3(); n=len(o.data.vertices)
    dl=[mwi3@d for d in delta_world]
    if o.data.shape_keys:
        for kb in o.data.shape_keys.key_blocks:
            for i in range(n):
                if dl[i].length_squared>0: kb.data[i].co+=dl[i]
    for i in range(n):
        if dl[i].length_squared>0: o.data.vertices[i].co+=dl[i]
    o.data.update()
FR={}
if P.get('FACE_RESHAPE',True) and eL and eR:
    mw=FH.matrix_world; V=[mw@v.co for v in FH.data.vertices]; N=len(V)
    cL,sL=eL; cR,sR=eR; ipd=abs(cL.x-cR.x); ez=(sL.z+sR.z)/2; ex=(sL.x+sR.x)/2
    hmn,hmx=wbb([FH]); ycen=(hmn.y+hmx.y)/2
    D=[Vector((0,0,0)) for _ in range(N)]
    # 1) eyes: shrink toward each eye centre (x by EYE_SX, z by EYE_SZ) with a smooth falloff onto the skin
    rc=0.55*max(ex,ez)*P.get('EYE_RC',1.15); ro=rc*P.get('EYE_RO',1.9)
    sx_,sz_=P.get('EYE_SX',0.80),P.get('EYE_SZ',0.72)
    for i,p in enumerate(V):
        if p.y>ycen: continue
        for c in (cL,cR):
            dx=p.x-c.x; dz=p.z-c.z; d=math.hypot(dx,dz*ex/max(ez,1e-6)*0.8)
            if d<ro:
                t_=0.0 if d<=rc else (d-rc)/(ro-rc); w=1-t_*t_*(3-2*t_)
                D[i]+=Vector((dx*(sx_-1)*w,0,dz*(sz_-1)*w))
    # 2) nose: find the tip (most forward point on the centre line below the eyes), push the bridge + tip forward
    ez0=(cL.z+cR.z)/2
    cand=[(p.y,i) for i,p in enumerate(V) if abs(p.x)<0.10*ipd and ez0-0.95*ipd<p.z<ez0-0.15*ipd and p.y<ycen]
    if cand:
        tip=V[min(cand)[1]]; FR['nose_tip']=list(tip)
        amt=P.get('NOSE_PUSH',0.07)*ipd; sg=P.get('NOSE_SIG',0.11)*ipd
        for i,p in enumerate(V):
            if p.y>ycen: continue
            if tip.z-0.12*ipd<p.z<ez0+0.05*ipd:
                prof=min(1.0,max(0.0,(ez0+0.05*ipd-p.z)/(ez0+0.05*ipd-tip.z)))**0.7
                low=1.0 if p.z>=tip.z else max(0,1-(tip.z-p.z)/(0.12*ipd))
                wx=math.exp(-(p.x/sg)**2)
                D[i]+=Vector((0,-amt*prof*low*wx,0))
    # 3) longer lower face: stretch below the eyes down a little, fading out before the jaw/neck seam
    lf=P.get('LOWER_FACE',1.05)
    if lf!=1.0:
        zt=ez0-0.25*ipd; zb=ez0-1.55*ipd
        for i,p in enumerate(V):
            if p.y>ycen+0.2*ipd: continue
            if zb<p.z<zt:
                t=(zt-p.z)/(zt-zb); w=math.sin(math.pi*t)  # 0 at both ends -> no seam
                D[i]+=Vector((0,0,-(lf-1)*(zt-zb)*0.5*w))
    _shift_all_keys(FH,D); FR.update(ipd=ipd,eye_size=[ex,ez],rc=rc,ro=ro,moved=sum(1 for d in D if d.length>1e-5))
    log('face reshape',FR)
rep['face_reshape']=FR
# ---------- v3.1 BANGS: lift/part the fringe so both eyes + brows show (compress hair in front of the face upward above the brow line)
if P.get('BANGS_LIFT',True) and eL and eR:
    cL,sL=eL; cR,sR=eR; ipd=abs(cL.x-cR.x); ez0=(cL.z+cR.z)/2
    browz=ez0+P.get('BROW_UP',0.62)*ipd*0.5+max(sL.z,sR.z)*0.5
    hmn,hmx=wbb([FH]); yfront=hmn.y; mw=UM.matrix_world; mwi=mw.inverted(); n_=0
    kz=P.get('BANG_K',0.22)
    for v in UM.data.vertices:
        p=mw@v.co
        if p.y<yfront+0.55*ipd and abs(p.x)<P.get('BANG_W',1.05)*ipd and p.z<browz+0.02*ipd:
            t=max(0.0,min(1.0,(p.y-yfront)/(0.55*ipd)))   # fade at the sides/back
            nz=browz+(p.z-browz)*kz
            nz=p.z+(nz-p.z)*(1-t*t)
            # sweep to her right side like the sheet
            p.x+= -P.get('BANG_SWEEP',0.10)*ipd*(1-t)*max(0,(browz-p.z))/(ipd)
            p.z=nz; v.co=mwi@p; n_+=1
    UM.data.update(); log('bangs lifted above brow z',round(browz,4),'verts',n_); rep['bangs']={'browz':browz,'verts':n_}

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
            ti=nt.nodes.new('ShaderNodeTexImage'); ti.image=bpy.data.images.load(ET)
            if P.get('SCLERA',True):
                mxs=nt.nodes.new('ShaderNodeMix'); mxs.data_type='RGBA'; mxs.inputs['A'].default_value=(*P.get('SCLERA_COL',(0.80,0.78,0.77)),1)
                nt.links.new(ti.outputs[1],mxs.inputs['Factor']); nt.links.new(ti.outputs[0],mxs.inputs['B']); nt.links.new(mxs.outputs['Result'],b.inputs['Base Color'])
            else:
                nt.links.new(ti.outputs[0],b.inputs['Base Color']); nt.links.new(ti.outputs[1],b.inputs['Alpha'])
            ez=P.get('EYE_ZOOM',1.0); eo_=P.get('EYE_OFF',(0.0,0.0))
            if ez!=1.0 or eo_!=(0.0,0.0):
                mp2=nt.nodes.new('ShaderNodeMapping'); mp2.vector_type='POINT'; mp2.inputs['Scale'].default_value=(ez,ez,1); mp2.inputs['Location'].default_value=(0.5-0.5*ez+eo_[0],0.5-0.5*ez+eo_[1],0)
                nt.links.new(uv.outputs['UV'],mp2.inputs['Vector']); nt.links.new(mp2.outputs[0],ti.inputs[0]); ti.extension='EXTEND'
            b.inputs['Emission Strength'].default_value=P.get('EYE_EMIT',0.04); nt.links.new(ti.outputs[0],b.inputs['Emission Color']); b.inputs['Coat Weight'].default_value=1.0; b.inputs['Coat Roughness'].default_value=0.03; log('eyes: her ZinPia',ET.split('/')[-1])
        elif EYE_TEX is not None:
            # Meshy eyeball image: island half-size -> IRIS_ZOOM of the disc radius
            hs=max(u1-u0,v1-v0)/2
            sc1=nt.nodes.new('ShaderNodeVectorMath'); sc1.operation='SCALE'; sc1.inputs['Scale'].default_value=0.5*P.get('IRIS_ZOOM',0.8)/hs; nt.links.new(sub.outputs[0],sc1.inputs[0])
            ad=nt.nodes.new('ShaderNodeVectorMath'); ad.operation='ADD'; ad.inputs[1].default_value=(0.5,0.5,0); nt.links.new(sc1.outputs[0],ad.inputs[0])
            ti=nt.nodes.new('ShaderNodeTexImage'); ti.image=EYE_TEX; ti.extension='EXTEND'; nt.links.new(ad.outputs[0],ti.inputs[0])
            nt.links.new(ti.outputs[0],b.inputs['Base Color'])
        s.material=m

# ---------- v3.1 SKIN: pale PINK (tint + warm subsurface) + glossy wet-look, and makeup-style paint (blush, lid crease, nose, lips, knees/elbows/knuckles)
def pinkify(mat,tint,sat):
    nt=mat.node_tree; b=[n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'][0]
    lk=[l for l in nt.links if l.to_socket==b.inputs['Base Color']]
    if not lk: b.inputs['Base Color'].default_value=(b.inputs['Base Color'].default_value[0]*tint[0],b.inputs['Base Color'].default_value[1]*tint[1],b.inputs['Base Color'].default_value[2]*tint[2],1); src=None
    else: src=lk[0].from_socket; nt.links.remove(lk[0])
    if src is not None:
        hs=nt.nodes.new('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value=sat; nt.links.new(src,hs.inputs['Color'])
        mx=nt.nodes.new('ShaderNodeMix'); mx.data_type='RGBA'; mx.blend_type='MULTIPLY'; mx.inputs['Factor'].default_value=1.0; mx.inputs['B'].default_value=(*tint,1)
        nt.links.new(hs.outputs['Color'],mx.inputs['A']); nt.links.new(mx.outputs['Result'],b.inputs['Base Color'])
    b.inputs['Subsurface Weight'].default_value=P.get('SSS_W',0.22); b.inputs['Subsurface Radius'].default_value=(1.0,0.32,0.22); b.inputs['Subsurface Scale'].default_value=P.get('SSS_SCALE',0.02)
    b.inputs['Roughness'].default_value=P.get('SKIN_ROUGH2',0.32); b.inputs['Specular IOR Level'].default_value=0.6
    b.inputs['Coat Weight'].default_value=P.get('SKIN_COAT2',0.55); b.inputs['Coat Roughness'].default_value=0.08
    log('pinkify',mat.name,tint,sat)
def uv_lookup(o,matnames=None):
    me=o.data; uv=me.uv_layers.active.data; mw=o.matrix_world; d={}
    for p in me.polygons:
        if matnames is not None:
            mn_=o.material_slots[p.material_index].material.name if o.material_slots[p.material_index].material else ''
            if mn_ not in matnames: continue
        for li in p.loop_indices:
            vi=me.loops[li].vertex_index
            if vi not in d: d[vi]=tuple(uv[li].uv)
    from mathutils.kdtree import KDTree as _KD
    kd=_KD(len(d)); idx=list(d)
    for k,vi in enumerate(idx): kd.insert(mw@me.vertices[vi].co,k)
    kd.balance(); return kd,idx,d
def paint(o,image,ops,matnames=None,tag=''):
    if image is None or image.size[0]==0: log('paint: no image',tag); return
    import numpy as np
    W_,H_=image.size; px=np.empty(W_*H_*4,dtype=np.float32); image.pixels.foreach_get(px); px=px.reshape(H_,W_,4)
    kd,idx,d=uv_lookup(o,matnames)
    # UV units per metre near each point: from the 8 nearest verts
    def uvat(p):
        res=kd.find_n(p,8)
        if not res: return None,None
        (co0,k0,dist0)=res[0]; u0=Vector(d[idx[k0]])
        ratios=[]
        for co,k,dist in res[1:]:
            du=(Vector(d[idx[k]])-u0).length; dm=(co-co0).length
            if dm>1e-6 and du<0.2: ratios.append(du/dm)
        return u0,(sorted(ratios)[len(ratios)//2] if ratios else None)
    done=0
    for (p3,rad,col,stg) in ops:
        u,k=uvat(p3)
        if u is None or not k: continue
        cx,cy=u.x*W_,u.y*H_; r=max(1.5,rad*k*W_); R=int(r*2.6)+1
        x0,x1=int(max(0,cx-R)),int(min(W_,cx+R)); y0,y1=int(max(0,cy-R)),int(min(H_,cy+R))
        if x1<=x0 or y1<=y0: continue
        yy,xx=np.mgrid[y0:y1,x0:x1]; g=np.exp(-((xx-cx)**2+(yy-cy)**2)/(2*r*r))*stg
        reg=px[y0:y1,x0:x1,:3]; c=np.array(col,dtype=np.float32)
        px[y0:y1,x0:x1,:3]=reg*(1-g[...,None]*(1-c))
        done+=1
    image.pixels.foreach_set(px.ravel()); image.update()
    try:
        os.makedirs(OUT+'/tex',exist_ok=True); image.filepath_raw=OUT+'/tex/'+tag+'_painted.png'; image.file_format='PNG'; image.save()
    except Exception as e: log('tex save err',e)
    try: image.pack()
    except Exception as e: log('pack err',e)
    log('painted',tag,done,'of',len(ops))
FACE_M=next((s_.material for s_ in FH.material_slots if s_.material and s_.material.name.lower().startswith('face')),None); SKIN_M=BODY.material_slots[0].material if BODY.material_slots else None
PINK=tuple(P.get('PINK',(1.0,0.86,0.86))); SAT=P.get('SKIN_SAT',1.25)
for m_ in set([FACE_M]+[s_.material for s_ in BODY.material_slots if s_.material]):
    if m_: pinkify(m_,PINK,SAT)
if P.get('FACE_PAINT',True) and FACE_M and eL and eR:
    ft=[n for n in FACE_M.node_tree.nodes if n.type=='TEX_IMAGE']
    fimg=ft[0].image if ft else None
    if fimg is not None:
        fimg=fimg.copy(); fimg.name='face_painted'; ft[0].image=fimg
    cL=eL[0]; cR=eR[0]; ipd=abs(cL.x-cR.x); ez0=(cL.z+cR.z)/2
    exs=eL[1].x*P.get('EYE_SX',0.80); ezs=eL[1].z*P.get('EYE_SZ',0.72)
    fy=wbb([FH])[0].y
    def surf(x,z):  # nearest face surface point in front at (x,z)
        best=None
        for v in FH.data.vertices:
            q=FH.matrix_world@v.co
            if abs(q.x-x)<0.06*ipd and abs(q.z-z)<0.06*ipd and (best is None or q.y<best.y): best=q
        return best
    BL=(1.0,0.66,0.68); SH_=(0.78,0.62,0.62); LIP=(0.86,0.52,0.56); ops=[]
    for c,sg in ((cL,1),(cR,-1)):
        q=surf(c.x+sg*0.18*ipd,c.z-0.42*ipd)
        if q: ops.append((q,0.20*ipd,BL,P.get('BLUSH',0.45)))
        for k in range(9):  # lid crease arc
            t=(k-4)/4.0; q=surf(c.x+t*exs*0.62,c.z+ezs*0.5*(1.0-0.35*t*t)+P.get('CREASE_UP',0.055)*ipd)
            if q: ops.append((q,0.028*ipd,SH_,P.get('CREASE',0.5)))
        for k in range(5):  # soft under-eye/socket shading at the inner corner + upper lid
            t=(k-2)/2.0; q=surf(c.x-sg*0.42*exs,c.z+t*0.2*ezs)
            if q: ops.append((q,0.05*ipd,SH_,0.22))
    tip=FR.get('nose_tip')
    if tip:
        tip=Vector(tip)
        ops.append((surf(0,tip.z+0.02*ipd) or tip,0.09*ipd,BL,0.35))
        for k in range(6):  # bridge side shadows
            z=ez0-0.05*ipd-(ez0-tip.z)*k/6.0
            for sg in (1,-1):
                q=surf(sg*0.11*ipd,z)
                if q: ops.append((q,0.05*ipd,SH_,0.28))
        for sg in (1,-1):
            q=surf(sg*0.10*ipd,tip.z-0.02*ipd)
            if q: ops.append((q,0.035*ipd,SH_,0.35))
        mz=tip.z-P.get('MOUTH_DZ',0.36)*ipd   # lips (deepen whatever lip colour the pack has)
        for k in range(7):
            t=(k-3)/3.0; q=surf(t*0.22*ipd,mz+0.02*ipd*(1-t*t))
            if q: ops.append((q,0.05*ipd,LIP,P.get('LIPS',0.35)))
    paint(FH,fimg,ops,matnames={FACE_M.name},tag='face')
    rep['face_paint_ops']=len(ops)
if P.get('BODY_PAINT',True) and SKIN_M:
    bt=[n for n in SKIN_M.node_tree.nodes if n.type=='TEX_IMAGE']
    bimg=bt[0].image.copy() if bt and bt[0].image else None
    if bimg: bimg.name='body_painted'; bt[0].image=bimg
    bn_=B.data.bones; ops=[]; BLK=(1.0,0.70,0.72)
    def bhead(n): return B.matrix_world@bn_[n].head_local if n in bn_ else None
    log('bones sample',[b_.name for b_ in bn_][:90])
    for nm in P.get('PINK_JOINTS',['Left knee','Right knee','Left elbow','Right elbow','Left wrist','Right wrist']):
        h=bhead(nm)
        if h is None: continue
        fwd=Vector((0,-0.05,0)) if 'knee' in nm else Vector((0,0.04,0)) if 'elbow' in nm else Vector((0,0,0))
        ops.append((h+fwd,0.035 if 'knee' in nm else 0.025,BLK,0.4))
    for b_ in bn_:
        if any(k in b_.name.lower() for k in ('index','middle','ring','little','pinky')) and b_.name[-1:].isdigit()==False:
            ops.append((B.matrix_world@b_.head_local,0.008,BLK,0.3))
    ch=bhead('Chest') or bhead('Upper Chest')
    if ch: ops.append((ch+Vector((0,-0.12,0.06)),0.06,BLK,0.22))
    paint(BODY,bimg,ops,tag='body')
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
    # v3.1: black-dominant (roots + top half), grey -> white only at the ends; matte, low sheen
    bw=nt.nodes.new('ShaderNodeRGBToBW'); nt.links.new(tt.outputs[0],bw.inputs[0])
    cr=nt.nodes.new('ShaderNodeValToRGB'); e=cr.color_ramp.elements
    HR=P.get('HAIR_RAMP',[(0.0,0.006),(0.58,0.010),(0.74,0.06),(0.86,0.30),(1.0,0.72)])
    e[0].position=HR[0][0]; e[0].color=(HR[0][1],)*3+(1,); e[1].position=HR[-1][0]; e[1].color=(HR[-1][1],)*3+(1,)
    for pos,val in HR[1:-1]: x=e.new(pos); x.color=(val,val,val*1.03,1)
    nt.links.new(bw.outputs[0],cr.inputs[0]); nt.links.new(cr.outputs[0],b.inputs['Base Color']); nt.links.new(tt.outputs[1],b.inputs['Alpha'])
    b.inputs['Roughness'].default_value=P.get('HAIR_ROUGH',0.55); b.inputs['Anisotropic'].default_value=0.35; b.inputs['Sheen Weight'].default_value=P.get('HAIR_SHEEN',0.08)
    b.inputs['Sheen Roughness'].default_value=0.5; b.inputs['Specular IOR Level'].default_value=P.get('HAIR_SPEC',0.35); b.inputs['Coat Weight'].default_value=0.0
    try: HM.blend_method='HASHED'
    except: pass
    log('hair: Blowout haircards with her',HCT.split('/')[-1])
UM.data.materials.clear(); UM.data.materials.append(HM)

# v3.1: second, slightly smaller + rotated hair layer -> more, layered strands; breaks the flat-ribbon / helmet read
if P.get('HAIR_LAYER2',True) and HAIR=='blowout_cards':
    hmn_,hmx_=wbb([UM]); piv=Vector(((hmn_.x+hmx_.x)/2,(hmn_.y+hmx_.y)/2,hmx_.z))
    U2=UM.copy(); U2.data=UM.data.copy(); U2.name='Hair2'; sc.collection.objects.link(U2)
    M2=Matrix.Translation(piv)@Matrix.Rotation(math.radians(P.get('L2_ROT',7)),4,'Z')@Matrix.Scale(P.get('L2_SCALE',0.955),4)@Matrix.Translation(-piv)
    U2.matrix_world=M2@U2.matrix_world; bpy.context.view_layer.update(); sel([U2]); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    # keep the lifted fringe clear of the eyes in layer 2 too: drop its front-face verts below the brow
    sel([UM,U2],UM); bpy.ops.object.join(); log('hair layer 2 joined, tris',tris(UM))
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
bunc=Vector((0, (hmn.y+hmx.y)/2+P.get('BUN_DY',0.045), umx.z-P.get('BUN_DZ',0.012)))
bm=bmesh.new(); bmesh.ops.create_uvsphere(bm,u_segments=16,v_segments=10,radius=hr*0.42)
for v in bm.verts:
    v.co.z*=0.8; v.co+=bunc
    v.co.x+=0.004*math.sin(v.co.z*900); v.co.y+=0.004*math.cos(v.co.x*800)
r2=bmesh.ops.create_uvsphere(bm,u_segments=12,v_segments=8,radius=hr*0.3)
for v in r2['verts']: v.co.z*=0.9; v.co+=bunc+Vector((0.012,0.01,0.012))
uvl=bm.loops.layers.uv.new('UVMap')
bunm=bpy.data.materials.new('BunDark'); bunm.use_nodes=True; q=bunm.node_tree.nodes['Principled BSDF']; q.inputs['Base Color'].default_value=(0.02,0.02,0.022,1); q.inputs['Roughness'].default_value=0.42
BUN=add_mesh('Bun',bm,bunm,'Head')
clip=bpy.data.materials.new('ClawClipBlack'); clip.use_nodes=True; cb=clip.node_tree.nodes['Principled BSDF']; cb.inputs['Base Color'].default_value=(0.012,0.012,0.014,1); cb.inputs['Roughness'].default_value=0.12; cb.inputs['Coat Weight'].default_value=1.0; cb.inputs['Coat Roughness'].default_value=0.05
# v3.1: a real claw clip clamped on the BACK of the bun: horizontal spine + teeth arcing over the top and under the bun (visible from back, side, 3/4)
bm=bmesh.new(); rb=hr*0.42*P.get('CLIP_R',1.08); ccen=bunc+Vector((0,P.get('CLIP_DY',0.004),0))
def seg(bm,p0,p1,w,t):
    d=p1-p0; L=d.length
    if L<1e-7: return
    r=bmesh.ops.create_cube(bm,size=1.0); rot=d.to_track_quat('X','Z').to_matrix()
    for v in r['verts']: v.co=rot@Vector((v.co.x*L*1.15,v.co.y*w,v.co.z*t))+(p0+p1)/2
spine_y=ccen.y+rb*0.95; L_=P.get('CLIP_L',0.062)
for k in range(12): seg(bm,Vector((-L_/2+L_*k/12,spine_y,ccen.z)),Vector((-L_/2+L_*(k+1)/12,spine_y,ccen.z)),0.010,0.010)
NT=P.get('CLIP_TEETH',6)
for k in range(NT):
    x=-L_/2+L_*(k+0.5)/NT
    for a0,a1 in ((0,105),(0,-80)):
        pts=[]
        for j in range(9):
            a=math.radians(a0+(a1-a0)*j/8); rr=rb*0.95+0.002
            pts.append(Vector((x*(1-0.15*j/8),ccen.y+rr*math.cos(a),ccen.z+rr*math.sin(a))))
        for j in range(8): seg(bm,pts[j],pts[j+1],0.0045,0.0032)
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
# v3.1 bra: ONE continuous garment — a conforming knit underband all the way round (overlapping the cup bottoms), side wings up to the cups, back clasp
def strip(bm,ring,lo,hi,off):
    # ring: list of (x,y) directions at angle; build quads between z=lo(a) and z=hi(a), each vertex snapped to skin + off
    rows=[]
    for (px_,py_,zl,zh) in ring:
        col=[]
        for j in range(5):
            z=zl+(zh-zl)*j/4; dr=Vector((px_,py_,0)).normalized(); o_=Vector((tcx,tcy,z))+dr*0.45
            h=bvh.ray_cast(o_,-dr,0.6)
            q=(h[0]+h[1].normalized()*off) if h and h[0] is not None else snap(Vector((tcx+px_*0.5,tcy+py_*0.5,z)),off)
            col.append(bm.verts.new(q))
        rows.append(col)
    for i in range(len(rows)):
        a=rows[i]; b2=rows[(i+1)%len(rows)]
        for j in range(4): bm.faces.new((a[j],b2[j],b2[j+1],a[j+1]))
bm=bmesh.new(); zb=bmn.z+P.get('BAND_DZ2',0.004); NR=72; ring=[]
_ch=B.matrix_world@B.data.bones['Chest'].head_local if 'Chest' in B.data.bones else Vector((0,0,zb)); tcx,tcy=0.0,_ch.y
bh=P.get('BAND_H',0.020); wing=P.get('BAND_WING',0.035)
for k in range(NR):
    a=2*math.pi*k/NR; x=0.25*math.sin(a); y=-0.25*math.cos(a)   # a=0 front, pi/2 left side, pi back
    side=math.sin(a)**2
    front=max(0.0,math.cos(a))
    zl=zb-0.006; zh=zb+bh+wing*side**3-0.006*front
    ring.append((x,y,zl,zh))
strip(bm,ring,None,None,P.get('BAND_OFF',0.0030))
_h=bvh.ray_cast(Vector((0,tcy+0.45,zb+bh*0.5)),Vector((0,-1,0)),0.6); cl=(_h[0]+Vector((0,0.0042,0))) if _h[0] is not None else snap(Vector((0,0.3,zb+bh*0.5)),0.0042)
r=bmesh.ops.create_cube(bm,size=1.0)
for v in r['verts']: v.co=Vector((v.co.x*0.016,v.co.y*0.003,v.co.z*bh*0.9))+cl
pts=[0]
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

# ---------- v3.1 bottoms: cut her black shorts down to the sheet's high-cut THONG (front panel tapering to the crotch, thin back, thin side strings) + silver side rings
if P.get('BOTTOM','thong')=='thong':
    mw=SH.matrix_world; smn,smx=wbb([SH]); hx=(smx.x-smn.x)/2; top=max((mw@v.co).z for v in SH.data.vertices)
    cy=(B.matrix_world@B.data.bones['Hips'].head_local).y if 'Hips' in B.data.bones else (smn.y+smx.y)/2
    cen=[mw@v.co for v in SH.data.vertices if abs((mw@v.co).x)<0.012]
    crz=min(p.z for p in cen) if cen else smn.z
    bt=P.get('STRING_H',0.010); zt=top-bt
    FW=P.get('THONG_FRONT',(0.42,0.10)); BW=P.get('THONG_BACK',(0.20,0.05))
    bmT=bmesh.new(); bmT.from_mesh(SH.data); kill_=[]
    for f in bmT.faces:
        c=mw@f.calc_center_median()
        if c.z>zt: continue
        t=max(0.0,min(1.0,(zt-c.z)/max(1e-4,zt-crz)))
        a,b_=FW if c.y<cy else BW
        hw_=hx*(a+(b_-a)*t**0.8)
        if c.z<crz-0.012 or abs(c.x)>hw_: kill_.append(f)
    bmesh.ops.delete(bmT,geom=kill_,context='FACES'); bmT.to_mesh(SH.data); bmT.free(); SH.data.update()
    log('thong cut: removed faces',len(kill_),'top',round(top,4),'crotch z',round(crz,4),'hip half-width',round(hx,4))
    rep['thong']={'removed':len(kill_),'top':top,'crz':crz,'hx':hx}
    bmR=bmesh.new()
    for sg in (1,-1):
        x=sg*hx*FW[0]; z=top-bt*0.5
        h=bvh.ray_cast(Vector((x,cy-0.45,z)),Vector((0,1,0)),0.6)
        if h[0] is None: continue
        c=h[0]+h[1].normalized()*0.004; nrm=h[1].normalized()
        # small ring in the plane of the skin
        tng=nrm.cross(Vector((0,0,1))).normalized(); up=tng.cross(nrm).normalized(); RR=P.get('RING_R',0.0075); prev=None
        pts_=[c+(tng*math.cos(2*math.pi*j/16)+up*math.sin(2*math.pi*j/16))*RR for j in range(17)]
        for j in range(16):
            d=pts_[j+1]-pts_[j]; L=d.length; r=bmesh.ops.create_cube(bmR,size=1.0); rot=d.to_track_quat('X','Z').to_matrix()
            for v in r['verts']: v.co=rot@Vector((v.co.x*L*1.2,v.co.y*0.0022,v.co.z*0.0022))+(pts_[j]+pts_[j+1])/2
    bmR.loops.layers.uv.new('UVMap')
    RINGS=add_mesh('ThongRings',bmR,bpy.data.materials['Silver'] if 'Silver' in bpy.data.materials else bpy.data.materials.new('Silver2'),'Hips')
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
    area('key',(-1.6,-2.2,2.0),P.get('KEY_E',190),1.6,(1,0.93,0.90)); area('fill',(1.8,-1.8,1.2),P.get('FILL_E',70),2.0,(0.95,0.93,1)); area('rim',(0.4,2.4,2.0),220,1.4); area('rim2',(-1.2,2.0,1.4),120,1.2); area('spec',(2.2,-1.0,1.6),P.get('SPEC_E',90),0.5,(1,0.96,0.95))
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
    area('key',(-1.6,-2.2,2.0),P.get('KEY_E',190),1.6,(1,0.93,0.90)); area('fill',(1.8,-1.8,1.2),P.get('FILL_E',70),2.0,(0.95,0.93,1)); area('rim',(0.4,2.4,2.0),220,1.4); area('rim2',(-1.2,2.0,1.4),120,1.2); area('spec',(2.2,-1.0,1.6),P.get('SPEC_E',90),0.5,(1,0.96,0.95))
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
