
import bpy, sys, os, math, json, mathutils, bmesh
from mathutils import Vector, Matrix
argv=sys.argv[sys.argv.index('--')+1:]; IN,OUT=argv[0],argv[1]; A=IN+'/assets'; os.makedirs(OUT+'/proof',exist_ok=True)
import time as _t; _T0=_t.time()
def log(*a): print('[v3]',f'{_t.time()-_T0:.0f}s',*a,flush=True)
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
# ---------- v3.2 HEAD FIT: neck lift + head sized to her sheet's ratio + seated on the neck (Saidie 8:13 PM Oct 17: "the head is off and is not sized correctly")
import numpy as np
VARIANT=os.environ.get('VARIANT',P.get('VARIANT','A')); rep['variant']=VARIANT; log('VARIANT',VARIANT)
def wco(o):
    n=len(o.data.vertices); a=np.empty(n*3); o.data.vertices.foreach_get('co',a); a=a.reshape(-1,3)
    M=np.array(o.matrix_world); return a@M[:3,:3].T+M[:3,3]
def wdelta(o,D):
    # add world-space deltas D (Nx3) to basis + every shape key
    M=np.array(o.matrix_world.inverted())[:3,:3]; dl=D@M.T; n=len(o.data.vertices)
    a=np.empty(n*3); o.data.vertices.foreach_get('co',a); o.data.vertices.foreach_set('co',(a.reshape(-1,3)+dl).ravel())
    if o.data.shape_keys:
        for kb in o.data.shape_keys.key_blocks:
            b_=np.empty(n*3); kb.data.foreach_get('co',b_); kb.data.foreach_set('co',(b_.reshape(-1,3)+dl).ravel())
    o.data.update()
def sstep(t): t=np.clip(t,0,1); return t*t*(3-2*t)
def bonew(n): return B.matrix_world@B.data.bones[n].head_local if n in B.data.bones else None
BV=wco(BODY); ztop=float(BV[:,2].max())
def neck_at(V,z,h=0.006,c=None,r=None):
    s=V[(V[:,2]>z-h)&(V[:,2]<z+h)]
    if c is not None: s=s[np.hypot(s[:,0]-c[0],s[:,1]-c[1])<r]
    if len(s)==0: return None
    return dict(cx=float((s[:,0].min()+s[:,0].max())/2),cy=float((s[:,1].min()+s[:,1].max())/2),rx=float((s[:,0].max()-s[:,0].min())/2),ry=float((s[:,1].max()-s[:,1].min())/2),front=float(s[:,1].min()),n=len(s))
nt0=neck_at(BV,ztop-0.025,0.012); NC=(nt0['cx'],nt0['cy']); NR=max(nt0['rx'],nt0['ry'])
zb=bonew('Neck').z; zhb=bonew('Head').z
LIFT=P.get('NECK_LIFT',0.035)
HF={'body_top':ztop,'neck_top_slice':nt0,'neck_bone_z':zb,'head_bone_z0':zhb,'lift':LIFT}
if LIFT:
    r_=np.hypot(BV[:,0]-NC[0],BV[:,1]-NC[1]); w_=sstep((BV[:,2]-zb)/P.get('NECK_BLEND',0.06))*(r_<NR*1.45)*(BV[:,2]>zb)
    D_=np.zeros_like(BV); D_[:,2]=LIFT*w_; wdelta(BODY,D_); HF['lift_verts']=int((w_>0).sum())
    sel([B]); bpy.ops.object.mode_set(mode='EDIT'); eb_=B.data.edit_bones
    def sub(b_):
        yield b_
        for c_ in b_.children: yield from sub(c_)
    hd=eb_['Head']; nk=eb_['Neck']; conn=(nk.tail-hd.head).length<1e-4
    plan_=[(b_,b_.head.copy()+Vector((0,0,LIFT)),b_.tail.copy()+Vector((0,0,LIFT))) for b_ in list(sub(hd))]
    nkt=nk.tail.copy()+Vector((0,0,LIFT))
    if conn: nk.tail=nkt
    for b_,h_,t_ in plan_: b_.head=h_; b_.tail=t_
    bpy.ops.object.mode_set(mode='OBJECT'); BV=wco(BODY)
HF['head_bone_z']=bonew('Head').z
# her head (face shell): chin, eyes, nose, forehead, measured on the mesh
FV=wco(FH); fmn=FV.min(0); fmx=FV.max(0); hw=(fmx[0]-fmn[0])/2; ymid=(fmn[1]+fmx[1])/2
em=[i for i,s in enumerate(FH.material_slots) if s.material and 'eye' in s.material.name.lower()]
eidx=sorted(set(v for p in FH.data.polygons if p.material_index in em for v in p.vertices))
eye_z=float(FV[eidx,2].mean()) if eidx else float(fmn[2]+0.42*(fmx[2]-fmn[2]))
cen=FV[(np.abs(FV[:,0]-(fmn[0]+fmx[0])/2)<0.22*hw)&(FV[:,1]<ymid)]
chin0=float(cen[:,2].min()); top0=float(fmx[2]); h0=top0-chin0
nb=cen[(cen[:,2]>chin0+0.15*(eye_z-chin0))&(cen[:,2]<eye_z)]; nose_y=float(nb[:,1].min()) if len(nb) else float(cen[:,1].min())
chf=float(cen[cen[:,2]<chin0+0.012][:,1].min()); fh_=cen[(cen[:,2]>eye_z+0.18*h0)&(cen[:,2]<eye_z+0.30*h0)]; fhy=float(fh_[:,1].min()) if len(fh_) else chf
pitch=math.degrees(math.atan2(fhy-chf,(eye_z+0.24*h0)-chin0))  # >0: forehead behind chin (face tilted up), <0: forehead ahead (pitched down)
HF.update(chin0=chin0,top0=top0,h0=h0,eye_z=eye_z,nose_y=nose_y,chin_front_y=chf,forehead_y=fhy,face_pitch_deg=pitch,face_hw=float(hw),fh_bb=[fmn.tolist(),fmx.tolist()])
# target from her sheet (front-full-1546.jpg: hair top y~30, chin y~232, soles y~1348 -> head = 0.150-0.156 of height); P['HEAD_RATIO']
r_t=P.get('HEAD_RATIO',0.150); g_=P['HAIR_TOP_GAP']+P['HAIR_DZ']
zc=chin0+LIFT+P.get('CHIN_DZ',0.0)
Ht=r_t*zc/(1-r_t); s_=max(0.5,(Ht-g_)/h0)*P.get('HEAD_SCALE',1.0)
sock_y=nose_y+P.get('SOCKET_K',1.66)*(eye_z-chin0)
nz_=neck_at(BV,zc+0.012,0.008,NC,NR*1.5) or nt0
ty=nz_['cy']+P.get('SOCKET_DY',0.0)
piv=Vector(((fmn[0]+fmx[0])/2,sock_y,chin0)); tgt=Vector((nz_['cx'],ty,zc))
Rp=Matrix.Rotation(math.radians(P.get('HEAD_PITCH',0.0)),4,'X')
S_=Matrix.Translation(tgt)@Rp@Matrix.Scale(s_,4)@Matrix.Translation(-piv)
FA.matrix_world=S_@FA.matrix_world; bpy.context.view_layer.update()
sel([FA,FH],FA); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
FV=wco(FH); HF.update(scale=s_,target_chin=zc,target_head_total=Ht,socket_y0=sock_y,neck_at_chin=nz_,head_bb_after=[FV.min(0).tolist(),FV.max(0).tolist()],
   neck_top_inside_head=bool(ztop+LIFT<FV[:,2].max() and ztop+LIFT>zc))
log('HEADFIT',{k:(round(v,4) if isinstance(v,float) else v) for k,v in HF.items()}); rep['head_fit']=HF
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
# ---------- v3.1 SEMI-REAL FACE from her head's own authored shape keys (Eyes -, Sharp, highlight -, forehead -, Lips +, ...): baked into the basis, every other key shifted the same, so visemes/blinks still work
BK=P.get('BAKE_KEYS',{})
if BK and FH.data.shape_keys:
    kbs=FH.data.shape_keys.key_blocks; basis=kbs[0]; n=len(FH.data.vertices); mw3=FH.matrix_world.to_3x3()
    D_=[Vector((0,0,0)) for _ in range(n)]; used={}
    for k_,v_ in BK.items():
        if k_ not in kbs: log('bake: no key',k_); continue
        kb=kbs[k_]; used[k_]=v_
        for i in range(n):
            d=kb.data[i].co-basis.data[i].co
            if d.length_squared>1e-14: D_[i]+=d*v_
    Dw=[mw3@d for d in D_]
    _shift_all_keys(FH,Dw)
    for k_ in used: kbs[k_].value=0.0
    log('baked face keys',used); rep['baked_face_keys']=used
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
# ---------- v3.1 hair length to the shoulders (her sheet): stretch the hair below eye level downward
if P.get('HAIR_LEN',1.0)!=1.0 and eL:
    zr=eL[0].z; mw=UM.matrix_world; mwi=mw.inverted(); n_=0
    for v in UM.data.vertices:
        p=mw@v.co
        if p.z<zr: p.z=zr-(zr-p.z)*P['HAIR_LEN']; v.co=mwi@p; n_+=1
    UM.data.update(); log('hair lengthened',P['HAIR_LEN'],n_)
# ---------- v3.2 FRINGE: wispy, uneven ends instead of the blunt cut (per-strand cut height + tapered tips); also run on hair layer 2 (stray strands over the cheek)
FRINGE={}
def fringe(O,tag):
    if not (eL and eR): return
    cL,sL=eL; cR,sR=eR; ipd=abs(cL.x-cR.x); ez0=(cL.z+cR.z)/2
    browz=ez0+max(sL.z,sR.z)*P.get('EYE_SZ',0.72)*0.5+P.get('BROW_GAP',0.30)*ipd
    from mathutils.bvhtree import BVHTree as _BVH
    dgh=bpy.context.evaluated_depsgraph_get(); hb=_BVH.FromObject(FH,dgh)
    mw=O.matrix_world; mwi=mw.inverted(); bmH=bmesh.new(); bmH.from_mesh(O.data); bmH.faces.ensure_lookup_table()
    isl={}; k=0
    for f in bmH.faces:
        if f.index in isl: continue
        st=[f]; isl[f.index]=k
        while st:
            g=st.pop()
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in isl: isl[h.index]=k; st.append(h)
        k+=1
    kill=[]; tv={}; side=0
    fw=P.get('BANG_W',1.6)*ipd
    for f in bmH.faces:
        c=mw@f.calc_center_median()
        if c.z>browz+0.03: continue
        h=hb.ray_cast(c,Vector((0,1,0)),P.get('BANG_DEPTH',0.05))
        if h[0] is None: continue
        i=isl[f.index]; u=((i*2654435761)%997)/997.0
        if abs(c.x)<=fw: zi=browz-u*P.get('FRINGE_VAR',0.22)*ipd
        else: zi=ez0-0.35*ipd  # side strands may frame the face but never cross the cheek
        if c.z<zi:
            kill.append(f); tv.setdefault(i,set()).update(v for v in f.verts)
            if abs(c.x)>fw: side+=1
    # remember each touched strand's surviving verts before deleting
    surv={}
    for f in bmH.faces:
        i=isl[f.index]
        if i in tv and f not in kill: surv.setdefault(i,set()).update(f.verts)
    ks=set(kill); bmesh.ops.delete(bmH,geom=list(ks),context='FACES')
    tap=0; band=P.get('TIP_BAND',0.35)*ipd
    for i,vs in surv.items():
        vs=[v for v in vs if v.is_valid]
        if len(vs)<3: continue
        W=[mw@v.co for v in vs]; zmin=min(p.z for p in W); cx=sum(p.x for p in W)/len(W); cy=sum(p.y for p in W)/len(W)
        for v,p in zip(vs,W):
            t=1-(p.z-zmin)/band
            if t>0:
                t=t*t*P.get('TIP_PINCH',0.7); p2=Vector((p.x+(cx-p.x)*t,p.y+(cy-p.y)*t*0.5,p.z)); v.co=mwi@p2; tap+=1
    bmH.to_mesh(O.data); bmH.free(); O.data.update()
    FRINGE[tag]={'browz':browz,'removed':len(ks),'side_removed':side,'strands_cut':len(tv),'tip_verts':tap}
    log('fringe',tag,FRINGE[tag])
if P.get('BANGS_LIFT',True): fringe(UM,'layer1')
rep['bangs']=FRINGE

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
    isface=mat.name.lower().startswith('face')
    b.inputs['Roughness'].default_value=P.get('FACE_ROUGH',0.42) if isface else P.get('SKIN_ROUGH2',0.32); b.inputs['Specular IOR Level'].default_value=0.5 if isface else 0.6
    b.inputs['Coat Weight'].default_value=P.get('FACE_COAT',0.18) if isface else P.get('SKIN_COAT2',0.45); b.inputs['Coat Roughness'].default_value=0.2 if isface else 0.08
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
        if isinstance(p3,tuple) and p3 and p3[0]=='UV': u,k=p3[1],p3[2]
        else: u,k=uvat(p3)
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
    from mathutils.bvhtree import BVHTree as _BVH
    from mathutils.interpolate import poly_3d_calc as _p3c
    _bvF=_BVH.FromObject(FH,bpy.context.evaluated_depsgraph_get()); _mwi=FH.matrix_world.inverted(); _mwi3=_mwi.to_3x3(); _me=FH.data; _uvd=_me.uv_layers.active.data
    _fmi=[i for i,s_ in enumerate(FH.material_slots) if s_.material is FACE_M]
    def surf(x,z):  # exact face-surface UV at (x,z) seen from the front (barycentric, no vertex snapping)
        h=_bvF.ray_cast(_mwi@Vector((x,fy-0.08,z)),_mwi3@Vector((0,1,0)),0.3)
        if h[0] is None: return None
        poly=_me.polygons[h[2]]
        if poly.material_index not in _fmi: return None
        li=list(poly.loop_indices); vco=[_me.vertices[_me.loops[l].vertex_index].co for l in li]; uvs=[Vector(_uvd[l].uv) for l in li]
        w=_p3c(vco,h[0]); uv=Vector((0,0))
        for wi,u in zip(w,uvs): uv+=u*wi
        lw=sum((vco[i]-vco[i-1]).length for i in range(len(vco))); lu=sum((uvs[i]-uvs[i-1]).length for i in range(len(uvs)))
        k=lu/lw/FH.matrix_world.to_scale()[0] if lw>1e-9 else None
        return ('UV',uv,k)
    BL=(1.0,0.66,0.68); SH_=tuple(P.get('SHADE_COL',(0.88,0.68,0.66))); LIP=(0.86,0.52,0.56); ops=[]
    for c,sg in ((cL,1),(cR,-1)):
        q=surf(c.x+sg*0.18*ipd,c.z-0.42*ipd)
        if q: ops.append((q,0.20*ipd,BL,P.get('BLUSH',0.45)))
        for k in range(9):  # lid crease arc
            t=(k-4)/4.0; q=surf(c.x+t*exs*0.62,c.z+ezs*0.5*(1.0-0.35*t*t)+P.get('CREASE_UP',0.055)*ipd)
            if q: ops.append((q,P.get('CREASE_R',0.045)*ipd,SH_,P.get('CREASE',0.6)))
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
                if q: ops.append((q,0.05*ipd,SH_,P.get('BRIDGE',0.14)))
        for sg in (1,-1):
            q=surf(sg*0.10*ipd,tip.z-0.02*ipd)
            if q: ops.append((q,0.035*ipd,SH_,0.35))
        mz=tip.z-P.get('MOUTH_DZ',0.64)*ipd   # lips (deepen whatever lip colour the pack has)
        for k in range(7):
            t=(k-3)/3.0; q=surf(t*0.22*ipd,mz+0.02*ipd*(1-t*t))
            if q: ops.append((q,0.05*ipd,LIP,P.get('LIPS',0.2)))
    BROW=tuple(P.get('BROW_COL',(0.22,0.19,0.19)))
    for c,sg in ((cL,1),(cR,-1)):
        for k in range(13):   # inner (thicker) -> outer tail, gentle arch
            t=k/12.0; x=c.x+sg*(-0.55*exs+1.25*exs*t); z=c.z+ezs*0.5+P.get('BROW_UP2',0.16)*ipd+0.05*ipd*math.sin(math.pi*min(1,t*1.3))-0.02*ipd*t
            q=surf(x,z)
            if q: ops.append((q,(0.030-0.014*t)*ipd,BROW,P.get('BROW_S',0.75)*(1-0.35*t)))
    paint(FH,fimg,ops,matnames={FACE_M.name},tag='face')
    rep['face_paint_ops']=len(ops)
if P.get('BODY_PAINT',True) and SKIN_M:
    bt=[n for n in SKIN_M.node_tree.nodes if n.type=='TEX_IMAGE']
    bimg=bt[0].image.copy() if bt and bt[0].image else None
    if bimg: bimg.name='body_painted'; bt[0].image=bimg
    bn_=B.data.bones; ops=[]; BLK=(1.0,0.70,0.72)
    def bhead(n): return B.matrix_world@bn_[n].head_local if n in bn_ else None
    log('bones sample',[b_.name for b_ in bn_][:90])
    from mathutils.bvhtree import BVHTree as _BVH
    _bb=_BVH.FromObject(BODY,bpy.context.evaluated_depsgraph_get())
    for nm in ('Left knee','Right knee'):
        h=bhead(nm)
        if h is None: continue
        hh=_bb.ray_cast(Vector((h.x,h.y-0.5,h.z)),Vector((0,1,0)),0.7)
        if hh[0] is not None: ops.append((hh[0],P.get('KNEE_R',0.028),BLK,P.get('KNEE_S',0.22)))
    ch=bhead('Chest') or bhead('Upper Chest')
    if ch: ops.append((ch+Vector((0,-0.12,0.06)),0.06,BLK,P.get('CHEST_S',0.12)))
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
    # keep the lifted fringe clear of the eyes in layer 2 too (v3.2: actually do it -> no stray strand across the cheek)
    fringe(U2,'layer2')
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
        if o.data.shape_keys: o.shape_key_clear()
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
    for a0,a1 in ((0,P.get('CLIP_UP',55)),(0,-P.get('CLIP_DN',55))):
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
    vs_=[]
    for j,p_ in enumerate(pts):
        tg=(pts[min(j+1,len(pts)-1)]-pts[max(j-1,0)]).normalized(); h_=bvh.find_nearest(p_); n_=h_[1].normalized() if h_[0] is not None else Vector((0,-1,0))
        sd=tg.cross(n_).normalized()*P.get('STRAP_W',0.0045)/2; vs_.append((bm.verts.new(p_-sd),bm.verts.new(p_+sd)))
    for a_,b_ in zip(vs_,vs_[1:]): bm.faces.new((a_[0],b_[0],b_[1],a_[1]))
# bow at the center gore
gv=[BRA.matrix_world@v.co for v in BRA.data.vertices if abs((BRA.matrix_world@v.co).x)<0.01]
if gv and P.get('BOW',True):
    g=min(gv,key=lambda p:p.y); gc=Vector((0,g.y-0.004,(max(p.z for p in gv)+min(p.z for p in gv))/2+0.01))
    for sx in (-1,1):
        r=bmesh.ops.create_uvsphere(bm,u_segments=8,v_segments=6,radius=1.0)
        for v in r['verts']: v.co=Vector((v.co.x*0.0038,v.co.y*0.0014,v.co.z*0.0024))+gc+Vector((sx*0.0038,0,0))
    r=bmesh.ops.create_uvsphere(bm,u_segments=8,v_segments=6,radius=0.0016)
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

# ---------- v3.1 bottoms: a high-cut black THONG generated ON her body (conforming panel front->crotch->back, thin hip strings, silver rings), in her shorts' black fabric; weights transferred from the body
def weights_from_body(o):
    dt=o.modifiers.new('DT','DATA_TRANSFER'); dt.object=BODY; dt.use_vert_data=True; dt.data_types_verts={'VGROUP_WEIGHTS'}; dt.vert_mapping='POLYINTERP_NEAREST'
    dt.layers_vgroup_select_src='ALL'; dt.layers_vgroup_select_dst='NAME'
    sel([o]); bpy.ops.object.datalayout_transfer(modifier='DT'); bpy.ops.object.modifier_move_to_index(modifier='DT',index=0); bpy.ops.object.modifier_apply(modifier='DT')
if P.get('BOTTOM','thong')=='thong':
    smn,smx=wbb([SH]); hx=(smx.x-smn.x)/2
    cy=(B.matrix_world@B.data.bones['Hips'].head_local).y if 'Hips' in B.data.bones else (smn.y+smx.y)/2
    hc=bvh.ray_cast(Vector((0,cy,smn.z-0.5)),Vector((0,0,1)),1.0); crz=hc[0].z if hc[0] is not None else smn.z+0.05
    zO=crz+0.11; zpt=crz+P.get('PANEL_H',0.085); zbt=zpt+P.get('BACK_UP',0.045)
    FW0,FW1,BW0,BW1=[hx*v for v in P.get('THONG_W',(0.40,0.09,0.07,0.11))]
    off=0.0022; rows=[]
    def cast(x,th):
        d=Vector((0,-math.cos(th),-math.sin(th))); o_=Vector((x,cy,zO))+d*0.5; h=bvh.ray_cast(o_,-d,0.7)
        return (h[0]+h[1].normalized()*off) if h[0] is not None else None
    NTH=90
    for k in range(NTH+1):
        th=math.radians(-10+200*k/NTH); c=cast(0,th)
        if c is None: continue
        front=th<math.radians(90)
        if front and c.z>zpt: continue
        if (not front) and c.z>zbt: continue
        if front: t=max(0,min(1,(zpt-c.z)/max(1e-4,zpt-crz))); hw=FW0+(FW1-FW0)*t**0.75
        else: t=max(0,min(1,(c.z-crz)/max(1e-4,zbt-crz))); hw=BW0+(BW1-BW0)*t
        row=[cast(hw*(j/3.0-1),th) for j in range(7)]
        if all(r_ is not None for r_ in row): rows.append(row)
    bmT=bmesh.new(); vr=[[bmT.verts.new(p) for p in r_] for r_ in rows]
    for a,b2 in zip(vr,vr[1:]):
        for j in range(6): bmT.faces.new((a[j],a[j+1],b2[j+1],b2[j]))
    # hip strings: from the panel's top corners up over the hip bones and round to the back top
    fc=rows[0] if rows else None
    def ring_pt(a,z,o2):
        dr=Vector((math.sin(a),-math.cos(a),0)); h=bvh.ray_cast(Vector((0,cy,z))+dr*0.5,-dr,0.7)
        return (h[0]+h[1].normalized()*o2) if h[0] is not None else None
    ac=math.asin(min(0.9,FW0/max(hx,1e-3)))*0.9; SHt=P.get('STRING_H',0.006); NS=40
    for sg in (1,-1):
        prev=None
        for k in range(NS+1):
            a=ac+(math.pi-ac)*k/NS; t=k/NS
            z=zpt+P.get('STRING_RISE',0.035)*math.sin(min(1,t*2)*math.pi/2) - (P.get('STRING_RISE',0.035)-(zbt-zpt))*max(0,t*2-1)
            p0=ring_pt(sg*a,z-SHt/2,off); p1=ring_pt(sg*a,z+SHt/2,off)
            if p0 is None or p1 is None: continue
            cur=(bmT.verts.new(p0),bmT.verts.new(p1))
            if prev: bmT.faces.new((prev[0],cur[0],cur[1],prev[1]))
            prev=cur
    bmT.loops.layers.uv.new('UVMap')
    me=bpy.data.meshes.new('Thong'); bmT.to_mesh(me); bmT.free(); TH=bpy.data.objects.new('Thong',me); sc.collection.objects.link(TH)
    tm,tnt,tb_=newmat('ThongBlack'); tb_.inputs['Base Color'].default_value=(0.012,0.012,0.013,1); tb_.inputs['Roughness'].default_value=0.42; tb_.inputs['Sheen Weight'].default_value=0.3
    me.materials.append(tm); TH.parent=B
    for p_ in me.polygons: p_.use_smooth=True
    weights_from_body(TH); md=TH.modifiers.new('Armature','ARMATURE'); md.object=B
    log('thong generated rows',len(rows),'tris',tris(TH),'crotch z',round(crz,4),'panel top',round(zpt,4))
    rep['thong']={'rows':len(rows),'crz':crz,'zpt':zpt,'hx':hx}
    bmR=bmesh.new()
    for sg in (1,-1):
        c=ring_pt(sg*ac,zpt,0.0045)
        if c is None: continue
        nrm=(c-Vector((0,cy,c.z))).normalized(); tng=nrm.cross(Vector((0,0,1))).normalized(); up=tng.cross(nrm).normalized(); RR=P.get('RING_R',0.0075)
        pts_=[c+(tng*math.cos(2*math.pi*j/16)+up*math.sin(2*math.pi*j/16))*RR for j in range(17)]
        for j in range(16):
            d=pts_[j+1]-pts_[j]; L=d.length; r=bmesh.ops.create_cube(bmR,size=1.0); rot=d.to_track_quat('X','Z').to_matrix()
            for v in r['verts']: v.co=rot@Vector((v.co.x*L*1.2,v.co.y*0.0022,v.co.z*0.0022))+(pts_[j]+pts_[j+1])/2
    bmR.loops.layers.uv.new('UVMap')
    RINGS=add_mesh('ThongRings',bmR,bpy.data.materials['Silver'],'Hips')
    bpy.data.objects.remove(SH); SH=TH
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
# ---------- v3.2 CRANIUM: close the head behind the face shell (skin), so the neck stump never shows behind the jaw / under the hair
CRAN=None
if P.get('CRANIUM',True):
    FV=wco(FH); fmn=FV.min(0); fmx=FV.max(0); hw_=(fmx[0]-fmn[0])/2; hh_=fmx[2]-HF['target_chin']
    D=P.get('HEAD_DEPTH_K',1.25)*2*hw_
    cc=Vector(((fmn[0]+fmx[0])/2, fmn[1]+D/2+P.get('CRAN_DY',0.0), HF['target_chin']+P.get('CRAN_ZC',0.56)*hh_))
    rad=Vector((hw_*P.get('CRAN_RX',0.92), D/2, hh_*P.get('CRAN_RZ',0.44)))
    bm=bmesh.new(); r=bmesh.ops.create_uvsphere(bm,u_segments=28,v_segments=18,radius=1.0)
    for v in r['verts']: v.co=Vector((v.co.x*rad.x,v.co.y*rad.y,v.co.z*rad.z))+cc
    from mathutils.bvhtree import BVHTree as _BVH
    hb=_BVH.FromObject(FH,bpy.context.evaluated_depsgraph_get()); pushed=0
    for v in bm.verts:
        if v.co.y>fmx[1]: continue
        fwd=hb.ray_cast(v.co,Vector((0,-1,0)),0.5); back=hb.ray_cast(v.co,Vector((0,1,0)),0.5)
        if fwd[0] is None and back[0] is not None:  # in front of the face shell -> tuck it behind
            v.co.y=back[0].y+0.004; pushed+=1
    uvl=bm.loops.layers.uv.new('UVMap')
    cm=bpy.data.materials.new('HeadSkin'); cm.use_nodes=True; q=cm.node_tree.nodes['Principled BSDF']
    pk=P.get('PINK',(1,0.92,0.91)); sk_=(skin[0]*pk[0],skin[1]*pk[1],skin[2]*pk[2],1); q.inputs['Roughness'].default_value=0.4
    cnt_=cm.node_tree; tc_=cnt_.nodes.new('ShaderNodeTexCoord'); sp_=cnt_.nodes.new('ShaderNodeSeparateXYZ'); cnt_.links.new(tc_.outputs['Generated'],sp_.inputs[0])
    cr_=cnt_.nodes.new('ShaderNodeValToRGB'); e_=cr_.color_ramp.elements; e_[0].position=P.get('CRAN_SKIN_TO',0.42); e_[0].color=sk_; e_[1].position=P.get('CRAN_DARK_FROM',0.55); e_[1].color=(0.015,0.015,0.016,1)
    cnt_.links.new(sp_.outputs['Z'],cr_.inputs[0]); cnt_.links.new(cr_.outputs[0],q.inputs['Base Color'])
    q.inputs['Subsurface Weight'].default_value=0.1; q.inputs['Subsurface Radius'].default_value=(1.0,0.35,0.25); q.inputs['Subsurface Scale'].default_value=0.01
    CRAN=add_mesh('Cranium',bm,cm,'Head')
    HF['cranium']={'centre':list(cc),'radii':list(rad),'pushed_behind_face':pushed,'neck_top_z':ztop+LIFT,'cranium_z':[cc.z-rad.z,cc.z+rad.z]}; log('cranium',HF['cranium'])
# ---------- v3.2 VARIANT B: her Meshy model's head + hair grafted onto this rigged body at the same measured size (comparison only)
if VARIANT=='B':
    MB=None
    for cand in (IN+'/meshy/meshy-jena.blend',IN+'/meshy-jena.blend'):
        if os.path.exists(cand): MB=cand; break
    log('meshy blend',MB)
    before=set(bpy.data.objects)
    with bpy.data.libraries.load(MB,link=False) as (df,dt): dt.objects=list(df.objects)
    for o in dt.objects:
        if o is not None: sc.collection.objects.link(o)
    newo=[o for o in bpy.data.objects if o not in before]; mm=[o for o in newo if o.type=='MESH']
    log('meshy objects',[(o.name,o.type,len(o.data.vertices) if o.type=='MESH' else 0) for o in newo])
    for o in newo:
        if o.type!='MESH': 
            for c in mm:
                if c.parent is o: mw=c.matrix_world.copy(); c.parent=None; c.matrix_world=mw
    for o in newo:
        if o.type!='MESH': bpy.data.objects.remove(o)
    for o in mm:
        for m_ in list(o.modifiers): o.modifiers.remove(m_)
        if o.data.shape_keys: o.shape_key_clear()
    if len(mm)>1: sel(mm,mm[0]); bpy.ops.object.join()
    MH=mm[0]; MH.name='MeshyHead'; sel([MH]); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    V=wco(MH); ext=V.max(0)-V.min(0); log('meshy bb',V.min(0).tolist(),V.max(0).tolist())
    up=int(np.argmax(ext))
    if up==1: MH.data.transform(Matrix.Rotation(math.radians(90),4,'X')); V=wco(MH)
    elif up==0: MH.data.transform(Matrix.Rotation(math.radians(90),4,'Y')); V=wco(MH)
    H0=V[:,2].max()-V[:,2].min(); z0=V[:,2].min()
    bot=V[V[:,2]<z0+0.03*H0]; shin=V[(V[:,2]>z0+0.06*H0)&(V[:,2]<z0+0.10*H0)]
    dv=bot[:,:2].mean(0)-shin[:,:2].mean(0); ang=math.atan2(dv[1],dv[0]); snap_=round((ang-(-math.pi/2))/(math.pi/2))*(math.pi/2)
    MH.data.transform(Matrix.Rotation(-snap_,4,'Z')); V=wco(MH)
    log('meshy facing: toes dir',dv.tolist(),'rot deg',-math.degrees(snap_))
    total=HF['target_chin']+HF['target_head_total']
    s=total/(V[:,2].max()-V[:,2].min()); c0=Vector(((V[:,0].min()+V[:,0].max())/2,(V[:,1].min()+V[:,1].max())/2,V[:,2].min()))
    MH.data.transform(Matrix.Scale(s,4)@Matrix.Translation(-c0)); V=wco(MH); Hm=V[:,2].max()
    # texture colour per vertex -> hair (neutral grey/black/white) vs skin (warm)
    me=MH.data; img_=None
    for sl in MH.material_slots:
        if sl.material and sl.material.use_nodes:
            for n_ in sl.material.node_tree.nodes:
                if n_.type=='TEX_IMAGE' and n_.image and n_.image.size[0]>0 and any(l.to_socket.name=='Base Color' for l in n_.outputs[0].links): img_=n_.image
    warm=np.zeros(len(me.vertices)); lum=np.zeros(len(me.vertices))
    if img_ is not None and me.uv_layers:
        W_,H_=img_.size; px=np.empty(W_*H_*4,dtype=np.float32); img_.pixels.foreach_get(px); px=px.reshape(H_,W_,4)
        nl=len(me.loops); uv=np.empty(nl*2,dtype=np.float32); me.uv_layers.active.data.foreach_get('uv',uv); uv=uv.reshape(-1,2)
        lv=np.empty(nl,dtype=np.int64); me.loops.foreach_get('vertex_index',lv)
        xs=np.clip(((uv[:,0]%1)*W_).astype(int),0,W_-1); ys=np.clip(((uv[:,1]%1)*H_).astype(int),0,H_-1); col=px[ys,xs,:3]
        cnt=np.bincount(lv,minlength=len(me.vertices)).clip(1)
        cv=np.stack([np.bincount(lv,col[:,k],minlength=len(me.vertices)) for k in range(3)],1)/cnt[:,None]
        warm=cv[:,0]-cv[:,2]; lum=cv.mean(1)
    skinv=(warm>P.get('MB_WARM',0.06))&(lum>0.25)
    log('meshy texture',img_.name if img_ else None,'skin-coloured verts',int(skinv.sum()),'of',len(warm))
    # chin + neck of the Meshy head (front profile on the centre line)
    cxm=0.0; ctr_=V[np.abs(V[:,0]-cxm)<0.012]
    hb_=ctr_[ctr_[:,2]>Hm-0.25*total]
    zz=np.arange(Hm-0.25*total,Hm,0.004); prof=[]
    for z in zz:
        s_=hb_[(hb_[:,2]>=z)&(hb_[:,2]<z+0.004)]
        prof.append(s_[:,1].min() if len(s_) else np.nan)
    prof=np.array(prof); upper=(zz>Hm-0.16*total)&(zz<Hm-0.05*total)
    ny=np.nanmin(np.where(upper,prof,np.nan)); nzi=int(np.nanargmin(np.where(upper,prof,np.nan)))
    neckz=Hm-0.20*total; nfy=np.nanmin(prof[np.abs(zz-neckz)<0.006]) if np.any(np.abs(zz-neckz)<0.006) else ny+0.05
    thr=(ny+nfy)/2; chin_m=None
    for i in range(nzi,-1,-1):
        if not np.isnan(prof[i]) and prof[i]>thr: chin_m=float(zz[i]+0.004); break
    if chin_m is None or abs(chin_m-HF['target_chin'])>0.06: log('meshy chin guess off',chin_m); chin_m=HF['target_chin']
    # neck front of the Meshy model (skin verts) and of our body at the same height
    zq=chin_m-0.015
    msk=V[(np.abs(V[:,2]-zq)<0.005)&skinv&(np.abs(V[:,0])<0.05)]
    m_front=float(msk[:,1].min()) if len(msk) else float(V[(np.abs(V[:,2]-zq)<0.005)&(np.abs(V[:,0])<0.03)][:,1].min())
    BVn=wco(BODY); zq2=HF['target_chin']-0.015
    b_n=neck_at(BVn,zq2,0.005,NC,NR*1.5) or neck_at(BVn,zq2,0.01) or nt0
    dz=HF['target_chin']-chin_m; dy=b_n['front']-m_front
    MH.data.transform(Matrix.Translation(Vector((-cxm+b_n['cx'],dy,dz)))); V=wco(MH)
    zc_=HF['target_chin']
    # cut: everything above chin-NECK_KEEP; hair-coloured strands kept further down beside/behind the neck
    r_=np.hypot(V[:,0]-b_n['cx'],V[:,1]-b_n['cy'])
    keep=(V[:,2]>=zc_-P.get('MB_NECK_KEEP',0.03))|((~skinv)&(V[:,2]>=zc_-P.get('MB_HAIR_KEEP',0.11))&(r_>max(b_n['rx'],b_n['ry'])*1.05))
    bm=bmesh.new(); bm.from_mesh(MH.data); bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[bm.verts[i] for i in np.where(~keep)[0]],context='VERTS')
    # drop tiny floating islands left by the cut
    bm.verts.ensure_lookup_table(); seen=set(); small=[]
    for v in bm.verts:
        if v in seen: continue
        st=[v]; comp=[v]; seen.add(v)
        while st:
            a_=st.pop()
            for e in a_.link_edges:
                o_=e.other_vert(a_)
                if o_ not in seen: seen.add(o_); st.append(o_); comp.append(o_)
        if len(comp)<P.get('MB_MIN_ISLAND',200): small+=comp
    bmesh.ops.delete(bm,geom=small,context='VERTS'); bm.to_mesh(MH.data); bm.free(); MH.data.update()
    tr0=tris(MH); r_dec=min(1.0,P.get('MB_TRIS',30000)/max(1,tr0))
    if r_dec<0.999:
        md=MH.modifiers.new('Dec','DECIMATE'); md.ratio=r_dec; sel([MH]); bpy.ops.object.modifier_apply(modifier='Dec')
    for p in MH.data.polygons: p.use_smooth=True
    # rig it to the Head bone (neck stub blends into Neck)
    vg=MH.vertex_groups.new(name='Head'); vn=MH.vertex_groups.new(name='Neck'); V=wco(MH)
    for i,p in enumerate(V):
        t=min(1,max(0,(p[2]-(zc_-0.03))/0.04)); vg.add([i],t,'REPLACE')
        if t<1: vn.add([i],1-t,'REPLACE')
    MH.parent=B; md=MH.modifiers.new('Armature','ARMATURE'); md.object=B
    # tuck our body neck inside the Meshy neck where they overlap
    m2=V[(np.abs(V[:,2]-(zc_-0.005))<0.006)]
    if len(m2):
        mrx=(m2[:,0].max()-m2[:,0].min())/2; mry=(m2[:,1].max()-m2[:,1].min())/2; mcy=(m2[:,1].max()+m2[:,1].min())/2
        BVn=wco(BODY); bq=neck_at(BVn,zc_-0.005,0.006,NC,NR*1.5) or b_n
        f_=min(1.0,0.93*min(mrx/max(bq['rx'],1e-4),mry/max(bq['ry'],1e-4)))
        rr=np.hypot(BVn[:,0]-bq['cx'],BVn[:,1]-bq['cy']); w_=sstep((BVn[:,2]-(zc_-P.get('MB_NECK_KEEP',0.03)-0.01))/0.02)*(rr<NR*1.45)
        Dn=np.zeros_like(BVn); Dn[:,0]=(bq['cx']+(BVn[:,0]-bq['cx'])*f_-BVn[:,0])*w_; Dn[:,1]=(mcy+(BVn[:,1]-bq['cy'])*f_-BVn[:,1])*w_; wdelta(BODY,Dn)
        HF['B_neck_tuck']={'factor':f_,'meshy_neck':[mrx,mry,mcy],'body_neck':bq}
    for o in (FH,UM,BUN,CLIP,CRAN,globals().get('SCALP')):
        if o is not None and o.name in bpy.data.objects: bpy.data.objects.remove(o)
    FH=MH; UM=MH
    HF['B']={'scale':s,'chin_meshy':chin_m,'dz':dz,'dy':dy,'nose_y':float(ny),'tris_before':tr0,'tris':tris(MH),'skin_verts':int(skinv.sum()),'texture':img_.name if img_ else None}
    log('VARIANT B',HF['B']); rep['head_fit']=HF

meshes=[o for o in bpy.data.objects if o.type=='MESH']
tri={o.name:tris(o) for o in meshes}; rep['tris']=tri; rep['tris_total']=sum(tri.values()); rep['bones']=len(B.data.bones)
rep['materials']=sorted(set(s.material.name for o in meshes for s in o.material_slots if s.material))
rep['shapekeys_head']=[k.name for k in FH.data.shape_keys.key_blocks] if FH.data.shape_keys else []
log('head keys',rep['shapekeys_head'])
for k_,v_ in P.get('FACE_KEYS',{}).items():
    if FH.data.shape_keys and k_ in FH.data.shape_keys.key_blocks: FH.data.shape_keys.key_blocks[k_].value=v_; log('face key',k_,v_)
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
SHD=P.get('SHOULDER_DOWN',8)
for name,sgn,deg in (('Left shoulder',1,SHD),('Right shoulder',-1,SHD),('Left arm',1,P['ARM_DOWN']-SHD),('Right arm',-1,P['ARM_DOWN']-SHD)):
    if not deg or name not in B.pose.bones: continue
    pb=B.pose.bones[name]; h=pb.head.copy()
    R=Matrix.Translation(h)@Matrix.Rotation(math.radians(sgn*deg),4,'Y')@Matrix.Translation(-h)
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
    hh_=hmx.z-HF['target_chin']; fc=Vector((0,(hmn.y+hmx.y)/2,HF['target_chin']+0.5*hh_))
    shot('face','front',1024,1024,lens=100,target=fc,h=hh_*P.get('FACE_FRAME',1.75))
    shot('face34','q34',1024,1024,lens=100,target=fc,h=hh_*P.get('FACE_FRAME',1.75))
    # v3.2 head-on-neck close-up from the side (Saidie: head off / not sized)
    shot('neckside','side',1024,1024,lens=100,target=fc-Vector((0,0,0.35*hh_)),h=hh_*2.6)

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
import sys as _s; _s.stdout.flush(); _s.stderr.flush(); os._exit(0)
