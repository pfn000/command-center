
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
VRAW=os.environ.get('VARIANT',P.get('VARIANT','A'))
# v3.5: matrix variants share code: B2.. = B or C with param overrides from params.json VARIANTS
if VRAW in P.get('VARIANTS',{}): P.update(P['VARIANTS'][VRAW]); log('variant overrides',VRAW,P['VARIANTS'][VRAW])
VARIANT=P.get('VARIANT_AS',VRAW) if VRAW in P.get('VARIANTS',{}) else VRAW
rep['variant']=VARIANT; rep['variant_raw']=VRAW; log('VARIANT',VARIANT,'raw',VRAW)
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

def eye_tex_v35(TW,TH_,P,iris_img):
    # v3.5 painted doe eye: half-lidded (upper lid over the iris top), grey-toned sclera, soft taupe eyeshadow + smoky outer wing, smudged lower liner; alpha fades to 0 at the edges
    tex=np.zeros((TH_,TW,4),np.float32); HW=TW//2
    yy,xx=np.mgrid[0:TH_,0:HW].astype(np.float32)
    MARG=P.get('EYE_MARG',1.9); EHU=P.get('EYE_UP',0.30); EHL=P.get('EYE_LO',0.24); TILT=P.get('EYE_TILT',0.10); IR=P.get('IRIS_R',0.44)
    if iris_img is not None:
        ih,iw=iris_img.shape[:2]; al=iris_img[:,:,3]>0.5; ys_,xs_=np.nonzero(al)
        icx,icy,irr=(xs_.mean(),ys_.mean(),max(xs_.max()-xs_.min(),ys_.max()-ys_.min())/2) if len(xs_) else (iw/2,ih/2,iw/2)
        if P.get('IRIS_SRC'): icx,icy,irr=P['IRIS_SRC'][0]*iw,P['IRIS_SRC'][1]*ih,P['IRIS_SRC'][2]*iw   # the doe texture's iris disc (the PNG is opaque edge to edge)
    def over(dst_c,dst_a,c,a):
        a=a[...,None] if a.ndim==2 else a; oa=a+dst_a[...,None]*(1-a); oc=(c*a+dst_c*dst_a[...,None]*(1-a))/np.maximum(oa,1e-6); return oc,oa[...,0]
    for half,outer in ((0,-1),(1,1)):
        sx=((xx-HW/2)/(HW/2))*MARG                 # screen x (+ = image right)
        u=sx*outer                                  # -1 inner corner .. +1 outer corner
        v=((yy-TH_/2)/(TH_/2))*MARG*(TH_/HW)        # same units as u, + = up
        c=np.clip(1-u*u,0,1)
        up=EHU*np.power(c,P.get('UP_POW',0.45))+TILT*(u+1)/2*0.25
        lo=-EHL*np.power(c,P.get('LO_POW',1.0))+TILT*(u+1)/2*0.12
        inside=(v<up)&(v>lo)&(np.abs(u)<1)
        col=np.zeros(u.shape+(3,),np.float32); a=np.zeros(u.shape,np.float32)
        # eyeshadow above the crease side of the lid (wider/darker toward the outer corner) + smoky wing past the corner
        LT=P.get('LASH_T',0.075); th=LT*(0.5+1.0*np.clip((u+0.3)/1.3,0,1))
        esh=P.get('ES_H',0.34)*np.power(c,0.35)+P.get('ES_OUT',0.16)*np.clip(u,0,1)
        dv=v-(up+th*0.6); es=np.where((dv>0)&(np.abs(u)<1.0),np.power(np.clip(1-dv/np.maximum(esh,1e-3),0,1),1.4),0)
        es*=np.clip(0.55+0.45*(u+1)/2,0,1)
        wy=EHU*0+TILT*0.25+(u-0.85)*P.get('WING_UP',0.45)   # smoky wing centre line past the outer corner
        dw=np.hypot(np.clip(u-0.9,0,None)*0.9,(v-wy)); wing_s=np.clip(1-dw/P.get('SMOKE_R',0.32),0,1)**1.5*np.clip((u-0.55)/0.35,0,1)
        es=np.maximum(es,wing_s*0.9)
        # soft shadow under the outer two thirds of the lower lid
        dl=(lo-0.02)-v; ls=np.where(dl>0,np.clip(1-dl/P.get('LS_H',0.15),0,1)**1.5,0)*np.clip((u+0.4)/1.3,0,1)*np.clip((1.25-np.abs(u))/0.3,0,1)*P.get('LS_A',0.45)
        es=np.maximum(es*P.get('ES_A',0.55),ls)
        # inner-corner fade (no shadow block at the nose side)
        es*=np.clip((u+1.15)/0.35,0,1)
        esc=np.array(P.get('ES_COL',(0.33,0.23,0.23)),np.float32)
        col,a=over(col,a,np.broadcast_to(esc,col.shape),es)
        # eye white: grey-toned, shadowed under the upper lid and toward the corners, pink inner corner
        sh=np.clip((up-v)/P.get('SCL_SH',0.24),0,1); cs=np.clip(1-np.abs(u)**3*0.45,0,1)
        sb=np.array(P.get('SCL_COL',(0.80,0.77,0.76)),np.float32)
        scl=sb[None,None,:]*((0.50+0.50*sh)*cs)[...,None]
        pk=np.clip((-u-0.72)/0.28,0,1)[...,None]; scl=scl*(1-pk)+np.array([0.72,0.46,0.46])*pk
        ecol=scl.copy()
        icv=P.get('IRIS_DZ',-0.02); isx=P.get('IRIS_DX',-0.03)*outer
        du=sx-isx; dvv=v-icv; rr=np.sqrt(du*du+dvv*dvv)/IR
        if iris_img is not None:
            sxp=np.clip(icx+du/IR*irr,0,iw-1).astype(int); syp=np.clip(icy+dvv/IR*irr,0,ih-1).astype(int); ic=iris_img[syp,sxp,:3]*P.get('IRIS_GAIN',1.0)
        else: ic=np.stack([0.42+0*rr,0.47+0*rr,0.52+0*rr],-1)
        ic=ic*np.clip(1.12-0.35*rr,0.6,1.1)[...,None]
        ring=np.clip((rr-0.84)/0.16,0,1); ic=ic*(1-0.7*ring[...,None])
        ic[rr<P.get('PUPIL',0.0)]=(0.015,0.015,0.018)
        ae=np.clip((1.0-rr)*IR*(HW/2)/MARG/1.5,0,1)[...,None]
        ecol=np.where((rr<1.0)[...,None],ic*ae+scl*(1-ae),ecol)
        ecol=ecol*(1-P.get('LID_SH',0.5)*np.clip(1-(up-v)/0.15,0,1))[...,None]
        cl=((du+0.15)**2+(dvv-0.12)**2)<(P.get('CATCH_R',0.055)**2)
        ecol=np.where((cl&inside)[...,None],np.array([0.93,0.93,0.95]),ecol)
        # anti-aliased lid edges
        ain=np.clip(np.minimum(up-v,v-lo)*(HW/2)/MARG/1.2,0,1)*(np.abs(u)<1)
        col,a=over(col,a,ecol,ain)
        # lower liner (smudged brown, stronger outward)
        ll=np.clip(1-np.abs(v-(lo-0.008))/P.get('LOWLASH_T',0.022),0,1)*(np.abs(u)<0.97)*(0.35+0.5*np.clip((u+0.2)/1.0,0,1))
        col,a=over(col,a,np.broadcast_to(np.array([0.20,0.15,0.15],np.float32),col.shape),ll)
        # sharp upper lash line, thicker outward, with a wing
        ul=np.clip(np.minimum(v-(up-0.012),(up+th)-v)*(HW/2)/MARG/1.0,0,1)*(u>-0.97)*(u<1.0)
        uc=0.85; upc=EHU*(1-uc*uc)**P.get('UP_POW',0.45)+TILT*(uc+1)/2*0.25; thc=LT*(0.5+1.0*min(1,(uc+0.3)/1.3)); W_=P.get('WING',0.28)
        top=upc+thc+(u-uc)*P.get('WING_UP',0.45); up1=TILT*0.25; tip=upc+thc+(1+W_-uc)*P.get('WING_UP',0.45)
        bot=np.where(u<1.0,up-0.012,up1+(u-1.0)/W_*(tip-up1))
        wg=np.clip(np.minimum(v-bot,top-v)*(HW/2)/MARG/1.0,0,1)*(u>=uc)*(u<1.0+W_)
        ul=ul*(u<uc)
        lash=np.maximum(ul,wg)
        col,a=over(col,a,np.broadcast_to(np.array([0.016,0.014,0.018],np.float32),col.shape),lash)
        # fade everything to 0 at the decal border
        bx=np.clip((MARG-np.abs(sx))/0.12,0,1); by=np.clip((MARG*(TH_/HW)-np.abs(v))/0.10,0,1); a=a*bx*by
        tex[:,half*HW:(half+1)*HW,:3]=col; tex[:,half*HW:(half+1)*HW,3]=a
    return tex

def bonew(n): return B.matrix_world@B.data.bones[n].head_local if n in B.data.bones else None
BV=wco(BODY); ztop=float(BV[:,2].max())
def neck_at(V,z,h=0.006,c=None,r=None):
    s=V[(V[:,2]>z-h)&(V[:,2]<z+h)]
    if c is not None: s=s[np.hypot(s[:,0]-c[0],s[:,1]-c[1])<r]
    if len(s)==0: return None
    return dict(cx=float((s[:,0].min()+s[:,0].max())/2),cy=float((s[:,1].min()+s[:,1].max())/2),rx=float((s[:,0].max()-s[:,0].min())/2),ry=float((s[:,1].max()-s[:,1].min())/2),front=float(s[:,1].min()),n=len(s))
nt0=neck_at(BV,ztop-0.025,0.012); NC=(nt0['cx'],nt0['cy']); NRAD=max(nt0['rx'],nt0['ry'])
zb=bonew('Neck').z; zhb=bonew('Head').z
LIFT=P.get('NECK_LIFT',0.035)
HF={'body_top':ztop,'neck_top_slice':nt0,'neck_bone_z':zb,'head_bone_z0':zhb,'lift':LIFT}
if LIFT:
    r_=np.hypot(BV[:,0]-NC[0],BV[:,1]-NC[1]); w_=sstep((BV[:,2]-zb)/P.get('NECK_BLEND',0.06))*(r_<NRAD*1.45)*(BV[:,2]>zb)
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
nz_=neck_at(BV,zc+0.012,0.008,NC,NRAD*1.5) or nt0
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
if P.get('CRANIUM',True): yc=hmn.y+P.get('HEAD_DEPTH_K',1.1)*(hmx.x-hmn.x)/2  # v3.2: centre of face shell + cranium
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
    hb=_BVH.FromObject(FH,bpy.context.evaluated_depsgraph_get())
    fmn_,fmx_=wbb([FH]); hwf=(fmx_.x-fmn_.x)/2; fw=P.get('FRINGE_XW',0.62)*hwf; fo=P.get('FRINGE_XFADE',0.75)*hwf
    mw=O.matrix_world; mwi=mw.inverted(); n=0; sq=P.get('FRINGE_SQ',0.2)
    for v in O.data.vertices:
        p=mw@v.co
        if p.z>=browz or abs(p.x)>fo: continue
        h=hb.ray_cast(p,Vector((0,1,0)),P.get('BANG_DEPTH',0.05))
        if h[0] is None: continue
        wx=1.0 if abs(p.x)<=fw else max(0.0,1-(abs(p.x)-fw)/max(1e-6,fo-fw))
        nz=browz-(browz-p.z)*sq
        v.co=mwi@Vector((p.x,p.y-P.get('FRINGE_FWD',0.004)*wx,p.z+(nz-p.z)*wx)); n+=1
    O.data.update()
    FRINGE[tag]={'browz':browz,'squashed_verts':n,'x_full':fw,'x_fade':fo,'sq':sq}
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
    skin_detail(mat)
    log('pinkify',mat.name,tint,sat)
def skin_detail(mat,ao=None):
    # v3.2 shared skin: cavity/AO darkening (collarbones, under-bust, abs, knees) + fine pore bump, same on head and body
    nt=mat.node_tree; b=[n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'][0]
    lk=[l for l in nt.links if l.to_socket==b.inputs['Base Color']]
    aon=nt.nodes.new('ShaderNodeAmbientOcclusion'); aon.inputs['Distance'].default_value=P.get('AO_DIST',0.05); aon.samples=8
    _loc=P.get('AO_LOCAL_HEAD',False) and not mat.name.startswith('Skin')
    if _loc: aon.only_local=True
    mx=nt.nodes.new('ShaderNodeMix'); mx.data_type='RGBA'; mx.blend_type='MULTIPLY'; mx.inputs['Factor'].default_value=P.get('AO_STR',0.55) if ao is None else ao
    if lk: src_=lk[0].from_socket; nt.links.remove(lk[0]); nt.links.new(src_,mx.inputs['A'])
    else: mx.inputs['A'].default_value=b.inputs['Base Color'].default_value
    if P.get('AO_COOL'):
        # v3.4: crevices/shadow side go to a cool neutral (not salmon): AO drives a ramp from a cool grey-mauve to white
        _cr=nt.nodes.new('ShaderNodeValToRGB'); _e=_cr.color_ramp.elements; _e[0].position=0.0; _e[0].color=(*P['AO_COOL'],1); _e[1].position=1.0; _e[1].color=(1,1,1,1)
        nt.links.new(aon.outputs['AO'],_cr.inputs[0]); nt.links.new(_cr.outputs[0],mx.inputs['B'])
    else: nt.links.new(aon.outputs['AO'],mx.inputs['B'])
    nt.links.new(mx.outputs['Result'],b.inputs['Base Color'])
    if P.get('AO2_STR',0):
        # v3.5 form shading: a second, broad occlusion (abs groove, under-bust, lower back, hip crease, between thighs, knees, jaw) in a soft warm-neutral
        ao2=nt.nodes.new('ShaderNodeAmbientOcclusion'); ao2.inputs['Distance'].default_value=P.get('AO2_DIST',0.2); ao2.samples=8
        if _loc: ao2.only_local=True
        c2=nt.nodes.new('ShaderNodeValToRGB'); e2=c2.color_ramp.elements; e2[0].position=P.get('AO2_LO',0.35); e2[0].color=(*P.get('AO2_COL',(0.62,0.52,0.52)),1); e2[1].position=1.0; e2[1].color=(1,1,1,1)
        nt.links.new(ao2.outputs['AO'],c2.inputs[0])
        m2=nt.nodes.new('ShaderNodeMix'); m2.data_type='RGBA'; m2.blend_type='MULTIPLY'; m2.inputs['Factor'].default_value=P['AO2_STR']*(1.0 if mat.name.startswith('Skin') else P.get('AO2_HEAD_K',0.5))
        nt.links.new(mx.outputs['Result'],m2.inputs['A']); nt.links.new(c2.outputs[0],m2.inputs['B']); nt.links.new(m2.outputs['Result'],b.inputs['Base Color'])
    nz=nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value=P.get('PORE_SCALE',900.0); nz.inputs['Detail'].default_value=2.0
    bp=nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value=P.get('PORE_BUMP',0.06); bp.inputs['Distance'].default_value=0.0005
    nl=[l for l in nt.links if l.to_socket==b.inputs['Normal']]
    if nl: nt.links.new(nl[0].from_socket,bp.inputs['Normal']); nt.links.remove(nl[0])
    nt.links.new(nz.outputs['Fac'],bp.inputs['Height']); nt.links.new(bp.outputs['Normal'],b.inputs['Normal'])
    b.inputs['Roughness'].default_value=P.get('SKIN_ROUGH_ALL',0.5); b.inputs['Coat Weight'].default_value=P.get('SKIN_COAT_ALL',0.05); b.inputs['Specular IOR Level'].default_value=0.45
    b.inputs['Subsurface Weight'].default_value=P.get('SSS_W',0.15); b.inputs['Subsurface Radius'].default_value=tuple(P.get('SSS_RAD',(1.0,0.4,0.25))); b.inputs['Subsurface Scale'].default_value=P.get('SSS_SCALE',0.012)
    if P.get('COAT_R') is not None: b.inputs['Coat Roughness'].default_value=P['COAT_R']
    if mat.name.lower().startswith('face'): b.inputs['Coat Weight'].default_value*=P.get('FACE_COAT_K',1.0)
    if P.get('SIDE_COOL'):
        # v3.4: surfaces turning away from the camera/key (limb sides, under-curves) shift to a cooler, less saturated tint -> no salmon falloff
        lw=nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value=0.5
        mr=nt.nodes.new('ShaderNodeMapRange'); mr.inputs[1].default_value=P.get('SIDE_LO',0.25); mr.inputs[2].default_value=0.95; mr.inputs[4].default_value=P['SIDE_COOL']; nt.links.new(lw.outputs['Facing'],mr.inputs[0])
        lk2=[l for l in nt.links if l.to_socket==b.inputs['Base Color']]
        if lk2:
            src2=lk2[0].from_socket; nt.links.remove(lk2[0])
            hs2=nt.nodes.new('ShaderNodeHueSaturation'); hs2.inputs['Saturation'].default_value=P.get('SIDE_SAT',0.7); nt.links.new(src2,hs2.inputs['Color'])
            ml=nt.nodes.new('ShaderNodeMix'); ml.data_type='RGBA'; ml.blend_type='MULTIPLY'; ml.inputs['Factor'].default_value=1.0; ml.inputs['B'].default_value=(*P.get('SIDE_TINT',(0.86,0.9,1.0)),1); nt.links.new(hs2.outputs['Color'],ml.inputs['A'])
            mx2=nt.nodes.new('ShaderNodeMix'); mx2.data_type='RGBA'; nt.links.new(mr.outputs[0],mx2.inputs['Factor']); nt.links.new(src2,mx2.inputs['A']); nt.links.new(ml.outputs['Result'],mx2.inputs['B'])
            nt.links.new(mx2.outputs['Result'],b.inputs['Base Color'])
    if P.get('SKIN_SPEC') is not None: b.inputs['Specular IOR Level'].default_value=P['SKIN_SPEC']
def img_skin_median(im):
    if im is None or im.size[0]==0: return None
    n=im.size[0]*im.size[1]; a=np.empty(n*4,dtype=np.float32); im.pixels.foreach_get(a); a=a.reshape(-1,4)[::53,:3]
    l=a.mean(1); w=(a[:,0]-a[:,2]); s=a[(l>0.35)&(l<0.97)&(w>0.03)]
    return np.median(s,0) if len(s)>50 else None
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
def _mimg(m):
    if not m or not m.use_nodes: return None
    t_=[n for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and n.image.size[0]>0]; return t_[0].image if t_ else None
BODY_MED=img_skin_median(_mimg(SKIN_M)); FACE_MED=img_skin_median(_mimg(FACE_M)); FTINT=(1,1,1)
if BODY_MED is not None and FACE_MED is not None: FTINT=tuple(float(min(1.25,max(0.8,BODY_MED[k]/max(FACE_MED[k],1e-3)))) for k in range(3))
log('skin medians body',None if BODY_MED is None else BODY_MED.tolist(),'face',None if FACE_MED is None else FACE_MED.tolist(),'face tint',FTINT); rep['skin_match']={'body':None if BODY_MED is None else BODY_MED.tolist(),'face':None if FACE_MED is None else FACE_MED.tolist(),'face_tint':FTINT}
for m_ in set([FACE_M]+[s_.material for s_ in BODY.material_slots if s_.material]):
    if m_: pinkify(m_,tuple(PINK[k]*(FTINT[k] if m_ is FACE_M else 1.0) for k in range(3)),SAT)
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
wv=nt.nodes.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value=P.get('RIB_SCALE',180); wv.wave_type='BANDS'; wv.bands_direction='X'
if P.get('RIB_UV',False):
    _tc=nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(_tc.outputs['UV'],wv.inputs['Vector']); wv.wave_profile='SIN'
    _rr=nt.nodes.new('ShaderNodeMapRange'); _rr.inputs[3].default_value=P.get('RIB_DARK',0.72); _rr.inputs[4].default_value=1.0; nt.links.new(wv.outputs['Fac'],_rr.inputs[0])
    _mm=nt.nodes.new('ShaderNodeMix'); _mm.data_type='RGBA'; _mm.blend_type='MULTIPLY'; _mm.inputs['Factor'].default_value=1.0; _mm.inputs['A'].default_value=b.inputs['Base Color'].default_value[:]
    nt.links.new(_rr.outputs[0],_mm.inputs['B']); nt.links.new(_mm.outputs['Result'],b.inputs['Base Color'])
bp=nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value=P.get('RIB_BUMP',0.25); nt.links.new(wv.outputs['Fac'],bp.inputs['Height']); nt.links.new(bp.outputs[0],b.inputs['Normal'])
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

from mathutils.bvhtree import BVHTree
# ---------- v3.3 CURVY SHAPE KEY on her Panda body (the .blend ships no shape keys: sculpted here as key 'Curvy' and baked):
# her sheet = thighs that meet from the crotch to the knee, hip shelf, round high glutes, fuller bust. Same field moves the bra/shorts.
if P.get('SHAPE',True):
    BV3=wco(BODY); zmin3=float(BV3[:,2].min()); zmax3=float(BV3[:,2].max()); Hb=zmax3-zmin3
    def bz(n,f):
        b_=bonew(n); return float(b_.z) if b_ is not None else zmin3+f*Hb
    log('leg bones',[b_.name for b_ in B.data.bones if any(k in b_.name.lower() for k in ('leg','knee','ankle','foot','toe','breast','hip','spine','chest'))])
    zH=bz('Left leg',0.50); zK=bz('Left knee',0.28); zCh=bz('Chest',0.70)
    _hb=bonew('Hips'); hy=float(_hb.y) if _hb is not None else float(np.median(BV3[:,1]))
    _bv3=BVHTree.FromObject(BODY,bpy.context.evaluated_depsgraph_get())
    _hc=_bv3.ray_cast(Vector((0,hy,zmin3+0.05)),Vector((0,0,1)),2.0); zC=float(_hc[0].z) if _hc[0] is not None else zH-0.04
    tor=BV3[np.abs(BV3[:,0])<0.16]; zz3=np.arange(zC+0.08,zC+0.36,0.01); wd3=[]
    for z_ in zz3:
        q_=tor[np.abs(tor[:,2]-z_)<0.005]; wd3.append(q_[:,0].max()-q_[:,0].min() if len(q_)>10 else 9)
    zW=float(zz3[int(np.argmin(wd3))])
    ch=BV3[(BV3[:,2]>zW+0.06)&(BV3[:,2]<zmin3+0.80*Hb)]; apex=[]
    for s in (1,-1):
        q_=ch[(ch[:,0]*s>0.02)&(ch[:,0]*s<0.16)]
        if len(q_): apex.append(q_[int(np.argmin(q_[:,1]))])
    SHP=dict(zC=zC,zH=zH,zK=zK,zW=zW,zCh=zCh,hy=hy,apex=[a_.tolist() for a_ in apex],Hb=Hb); log('SHAPE landmarks',SHP); rep['shape_landmarks']=SHP
    # thigh axes per height (each side), from the body itself
    zb3=np.arange(zK-0.02,zC+0.08,0.01); TAX={}
    for s in (1,-1):
        cx_,cy_=[],[]
        for z_ in zb3:
            q_=BV3[(np.abs(BV3[:,2]-z_)<0.006)&(BV3[:,0]*s>0)&(np.abs(BV3[:,0])<0.3)]
            cx_.append((q_[:,0].min()+q_[:,0].max())/2 if len(q_) else s*0.08); cy_.append((q_[:,1].min()+q_[:,1].max())/2 if len(q_) else hy)
        TAX[s]=(np.array(cx_),np.array(cy_))
    def shape_field(V):
        D=np.zeros_like(V); x=V[:,0]; y=V[:,1]; z=V[:,2]
        # 1) hip shelf: widen |x| about the centre line, peak just above the crotch
        zp=zC+P.get('HIP_PEAK',0.05); dn=P.get('HIP_DN',0.14)
        wh=np.where(z<zp,sstep((z-(zp-dn))/dn),1-sstep((z-zp)/max(0.03,zW-zp)))*(np.abs(x)<0.25)
        D[:,0]+=x*P.get('HIP_W',0.06)*wh
        # 2) thighs: radial about each thigh's axis, more toward the inside so they meet like her sheet; 0 at the knee
        u=np.clip((z-zK)/max(0.05,zC-zK),0,1)
        wt=np.sin(u*math.pi/2)**P.get('THIGH_POW',1.2)*(1-sstep((z-zC)/0.06))*(z>zK)
        for s in (1,-1):
            m_=(x*s>0)&(wt>0)&(np.abs(x)<0.3)
            if not m_.any(): continue
            cx_=np.interp(z[m_],zb3,TAX[s][0]); cy_=np.interp(z[m_],zb3,TAX[s][1])
            dx=x[m_]-cx_; dy=y[m_]-cy_; r=np.hypot(dx,dy)+1e-6
            inner=np.clip(-s*dx/r,0,1); front=np.clip(-dy/r,0,1); back=np.clip(dy/r,0,1)
            f=P.get('THIGH_K',0.10)*(1+P.get('THIGH_INNER',0.8)*inner+P.get('THIGH_FRONT',0.3)*front+P.get('THIGH_BACK',0.2)*back)*wt[m_]
            nx=x[m_]+dx*f; nx=np.where(s*nx<0.002,s*0.002,nx)
            D[m_,0]+=nx-x[m_]; D[m_,1]+=dy*f
        # 3) glutes: rounder + higher, pushed back
        zg=zC+P.get('GLUTE_PEAK',0.035); wg=np.exp(-((z-zg)/P.get('GLUTE_SZ',0.075))**2)
        lat=np.exp(-((np.abs(x)-P.get('GLUTE_X',0.065))/0.065)**2); bk=sstep((y-hy)/0.06)
        D[:,1]+=P.get('GLUTE_D',0.02)*wg*lat*bk
        # 4) bust: fuller + a little lift, about each breast's centre
        RB=P.get('BUST_R',0.09)
        for a_ in apex:
            c=np.array([a_[0],a_[1]+0.55*RB,a_[2]]); d=V-c; r=np.linalg.norm(d,axis=1)
            w=(1-sstep(r/RB))*(y<a_[1]+1.2*RB)
            D+=d*(P.get('BUST_K',0.12)*w)[:,None]; D[:,2]+=P.get('BUST_LIFT',0.006)*w
        return D
    D_b=shape_field(BV3)
    try:
        BODY.shape_key_add(name='Basis',from_mix=False); kb_=BODY.shape_key_add(name='Curvy',from_mix=False)
        Mi=np.array(BODY.matrix_world.inverted())[:3,:3]; n_=len(BODY.data.vertices); a_=np.empty(n_*3); kb_.data.foreach_get('co',a_)
        kb_.data.foreach_set('co',(a_.reshape(-1,3)+D_b@Mi.T).ravel()); kb_.value=1.0; BODY.data.update()
        sel([BODY]); bpy.ops.object.shape_key_remove(all=True,apply_mix=True); log('shape key Curvy sculpted + baked, max move',float(np.linalg.norm(D_b,axis=1).max()))
    except Exception as e:
        log('shape key path failed',e); 
        if BODY.data.shape_keys: BODY.shape_key_clear()
        wdelta(BODY,D_b)
    for o in (BRA,SH): wdelta(o,shape_field(wco(o)))
    rep['shape']={k:P.get(k) for k in ('HIP_W','THIGH_K','THIGH_INNER','GLUTE_D','BUST_K','LEG_IN')}
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
# v3.2: bra hem up to just under the cups (it read as a crop top)
if P.get('BRA_HEM_UP',0.0) and not P.get('BRA_GEN',True):
    _mn,_mx=wbb([BRA]); zt_=_mn.z+P['BRA_HEM_UP']; mw=BRA.matrix_world; mwi=mw.inverted(); hm_=0
    for v in BRA.data.vertices:
        p=mw@v.co
        if p.z<zt_: v.co=mwi@Vector((p.x,p.y,zt_-(zt_-p.z)*P.get('BRA_HEM_SQ',0.25))); hm_+=1
    BRA.data.update(); log('bra hem raised',P['BRA_HEM_UP'],hm_)
# ---------- v3.3 BRA rebuilt ON her body like her sheet: balconette knit cups that end at the under-bust crease (no separate band strip),
# low centre gore with the bow, top edge just over the nipple line rising to the strap points, narrow side wings + back band
BRA_ATT={}
if P.get('BRA_GEN',True):
    _ch=B.matrix_world@B.data.bones['Chest'].head_local if 'Chest' in B.data.bones else Vector((0,0,0)); tcy_=float(_ch.y)
    BVb=wco(BODY); zmin_=float(BVb[:,2].min()); Hb_=float(BVb[:,2].max())-zmin_
    ap_=[]
    for s in (1,-1):
        q_=BVb[(BVb[:,0]*s>0.02)&(BVb[:,0]*s<0.16)&(BVb[:,2]>zmin_+0.62*Hb_)&(BVb[:,2]<zmin_+0.80*Hb_)]
        ap_.append(q_[int(np.argmin(q_[:,1]))])
    zn=float((ap_[0][2]+ap_[1][2])/2); xn=float((abs(ap_[0][0])+abs(ap_[1][0]))/2); yn=float((ap_[0][1]+ap_[1][1])/2)
    def fr(z,x=xn):
        h=bvh.ray_cast(Vector((x,-1.0,z)),Vector((0,1,0)),2.0); return h[0].y if h[0] is not None else None
    yrib=fr(zn-0.14) or yn+0.08; crease=zn-0.05
    for k in range(1,80):
        z_=zn-0.002*k; y_=fr(z_)
        if y_ is not None and y_>=yrib-0.25*(yrib-yn): crease=z_; break
    crease-=P.get('CUP_UNDER',0.006)
    an=math.atan2(xn,-(yn-tcy_)); asd=an+P.get('STRAP_DA',0.55)
    GH=P.get('GORE_H',0.028); TN=P.get('TOP_N',0.006); TS=P.get('TOP_S',0.035); WG=P.get('WING_H',0.028); BK=P.get('BACK_H',0.018)
    def cup_top(a):
        a=abs(a); ag=P.get('GORE_A',0.07)
        if a<ag: return crease+GH
        if a<an: return crease+GH+(zn+TN-crease-GH)*sstep((a-ag)/(an-ag))
        if a<asd: return zn+TN+(TS-TN)*float(sstep((a-an)/(asd-an)))
        if a<math.pi/2+0.25: return zn+TS+(crease+WG-zn-TS)*float(sstep((a-asd)/(math.pi/2+0.25-asd)))
        return crease+WG+(BK-WG)*float(sstep((a-math.pi/2-0.25)/(math.pi/2-0.25)))
    def zbot(a): return crease
    NRb=P.get('BRA_NR',120); NVb=P.get('BRA_NV',12); offb=P.get('BRA_OFF',0.0035)
    def cast_(a,z,off):
        dr=Vector((math.sin(a),-math.cos(a),0)); o_=Vector((0,tcy_,z))+dr*0.5
        h=bvh.ray_cast(o_,-dr,0.6)
        return (h[0]+h[1].normalized()*off) if h[0] is not None else None
    bmB=bmesh.new(); uvB=bmB.loops.layers.uv.new('UVMap'); grid=[]
    for k in range(NRb):
        a=-math.pi+2*math.pi*k/NRb; lo,hi=zbot(a),cup_top(a); col=[]
        for j in range(NVb+1):
            p_=cast_(a,lo+(hi-lo)*j/NVb,offb); col.append(bmB.verts.new(p_) if p_ is not None else None)
        grid.append(col)
    for k in range(NRb):
        a_,b_=grid[k],grid[(k+1)%NRb]
        for j in range(NVb):
            q4=(a_[j],b_[j],b_[j+1],a_[j+1])
            if all(v is not None for v in q4):
                f_=bmB.faces.new(q4)
                for li,(uu,vv) in zip(f_.loops,((k,j),(k+1,j),(k+1,j+1),(k,j+1))): li[uvB].uv=(uu/NRb,vv/NVb)
    # lace trim along the top edge (darker grey, see-through lace like her sheet)
    bmL=bmesh.new(); uvL=bmL.loops.layers.uv.new('UVMap'); prevL=None; LH=P.get('LACE_H',0.007)
    for k in range(NRb+1):
        a=-math.pi+2*math.pi*k/NRb; hi=cup_top(a)
        if abs(a)>math.pi/2+0.3: prevL=None; continue
        p0=cast_(a,hi-0.002,offb+0.0006); p1=cast_(a,hi+LH,offb*0.7)
        if p0 is None or p1 is None: prevL=None; continue
        cur=(bmL.verts.new(p0),bmL.verts.new(p1))
        if prevL: 
            f_=bmL.faces.new((prevL[0],cur[0],cur[1],prevL[1]))
            for li,(uu,vv) in zip(f_.loops,((k-1,0),(k,0),(k,1),(k-1,1))): li[uvL].uv=(uu/NRb*6,vv)
        prevL=cur
    for s in (1,-1):
        pa=cast_(s*asd,cup_top(asd)-0.002,offb); pb_=cast_(s*(math.pi-0.5),crease+BK-0.003,offb)
        BRA_ATT[s]=(pa,pb_)
    def strap_path(s):
        # v3.4: straight strap. Front: casts at a FIXED x from the outer cup top straight up to mid-shoulder (no angle -> no halter read);
        # top: vertical casts over the trapezius at that x; back: straight down at the same x to the back band.
        XS0=P.get('STRAP_X0',0)
        if XS0:
            # the strap foot is the point on the cup top edge whose x is XS0 (search the angle between apex and strap point)
            best_=None
            for k_ in range(41):
                a_=an*0.5+(asd-an*0.5)*k_/40; q_=cast_(s*a_,cup_top(a_)-0.003,0.0025)
                if q_ is not None and (best_ is None or abs(abs(q_.x)-XS0)<abs(abs(best_[1].x)-XS0)): best_=(a_,q_)
            if best_ is None: return []
            z0=cup_top(best_[0])-0.003; pa_=best_[1]; xa=XS0; xt=XS0+P.get('STRAP_XOUT',0.0)
        else:
            z0=cup_top(asd)-0.003; pa_=cast_(s*asd,z0,0.0025)
            if pa_ is None: return []
            xa=abs(pa_.x); xt=max(xa+P.get('STRAP_XOUT',0.0),P.get('STRAP_XMIN',0.0))
        xb=xt
        hf=bvh.ray_cast(Vector((s*xt,tcy_,2.5)),Vector((0,0,-1)),3.0); zsh=float(hf[0].z) if hf[0] is not None else z0+0.2
        def fcast(x,z,sgn_y):
            h_=bvh.ray_cast(Vector((x,tcy_-sgn_y*0.6,z)),Vector((0,sgn_y,0)),0.6)
            return (h_[0]+h_[1].normalized()*0.0025) if h_[0] is not None else None
        pts_=[pa_]; NF=16
        for i in range(1,NF+1):
            t_=i/NF; z_=z0+(zsh-0.015-z0)*t_; q=fcast(s*(xa+(xt-xa)*t_),z_,1)
            if q is not None: pts_.append(q)
        yf=pts_[-1].y
        qb=fcast(s*xb,zsh-0.015,-1); yb=qb.y if qb is not None else tcy_+0.08
        for i in range(1,8):
            y_=yf+(yb-yf)*i/8; h_=bvh.ray_cast(Vector((s*xt,y_,zsh+0.3)),Vector((0,0,-1)),0.6)
            if h_[0] is not None: pts_.append(h_[0]+h_[1].normalized()*0.0025)
        zbk=crease+BK-0.003; xbk=abs(BRA_ATT[s][1].x) if BRA_ATT.get(s) and BRA_ATT[s][1] is not None else xb
        if P.get('STRAP_BACK_STRAIGHT'): xbk=xb*P.get('STRAP_BACK_XK',1.0)  # v3.5: parallel straps straight down the back (no inward V)
        for i in range(NF+1):
            t_=i/NF; z_=zsh-0.015+(zbk-(zsh-0.015))*t_; q=fcast(s*(xb+(xbk-xb)*t_**2),z_,-1)
            if q is not None: pts_.append(q)
        rep.setdefault('straps',{})[s]={'x_cup':xa,'x_top':xt,'z_cup':z0,'z_sh':zsh,'n':len(pts_)}
        return pts_
    old=BRA; bpy.data.objects.remove(old)
    me=bpy.data.meshes.new('Bra'); bmB.to_mesh(me); bmB.free(); BRA=bpy.data.objects.new('Bra',me); sc.collection.objects.link(BRA)
    me.materials.append(bpy.data.materials['BraKnit']); BRA.parent=B
    for p_ in me.polygons: p_.use_smooth=True
    lm,lnt,lb=newmat('BraLace'); lb.inputs['Base Color'].default_value=(0.16,0.155,0.165,1); lb.inputs['Roughness'].default_value=0.6
    vo=lnt.nodes.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value=P.get('LACE_SCALE',260.0); tc=lnt.nodes.new('ShaderNodeTexCoord'); lnt.links.new(tc.outputs['UV'],vo.inputs['Vector'])
    cr=lnt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position=0.25; cr.color_ramp.elements[1].position=0.45
    lnt.links.new(vo.outputs['Distance'],cr.inputs[0]); lnt.links.new(cr.outputs[0],lb.inputs['Alpha'])
    try: lm.blend_method='HASHED'
    except Exception: pass
    meL=bpy.data.meshes.new('BraLace'); bmL.to_mesh(meL); bmL.free(); LACE=bpy.data.objects.new('BraLace',meL); sc.collection.objects.link(LACE)
    meL.materials.append(lm); LACE.parent=B
    for p_ in meL.polygons: p_.use_smooth=True
    if P.get('CLASP',False):
        # v3.5: narrow back band closes with a small dark hook clasp at the centre back (her sheet's back view)
        cq=cast_(math.pi,crease+BK*0.5,offb+0.0015)
        if cq is not None:
            bmC=bmesh.new(); r_=bmesh.ops.create_cube(bmC,size=1.0); CW,CH,CT=P.get('CLASP_W',0.026),BK*0.85,0.003
            for v in r_['verts']: v.co=Vector((v.co.x*CW,v.co.y*CT,v.co.z*CH))+cq
            bmC.loops.layers.uv.new('UVMap'); clm,_n,_b=solidmat('ClaspDark',(0.05,0.05,0.055),0.35,0.5)
            CLASP=add_mesh('BraClasp',bmC,clm,'Chest'); log('bra clasp',list(cq))
    rep['bra']={'apex':[list(map(float,a_)) for a_ in ap_],'crease':crease,'zn':zn,'apex_angle':an,'strap_angle':asd,'tris':tris(BRA),'lace_tris':tris(LACE)}
    log('BRA generated',rep['bra'])
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
    att=BRA_ATT.get(sgn)
    if att and att[0] is not None and 'strap_path' in globals():
        pts=strap_path(sgn)
    else:
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
    g=min(gv,key=lambda p:p.y); gc=Vector((0,g.y-0.004,(max(p.z for p in gv)+min(p.z for p in gv))/2+0.01)); _bs=P.get('BOW_S',1.0)
    if P.get('BOW_V2',False):
        # v3.4 bow: two flat tapered loops angled up-out, a knot, two short tails angled down-out (not two buttons)
        def ell(c,sx_,sy_,sz_,ang):
            r=bmesh.ops.create_uvsphere(bm,u_segments=10,v_segments=6,radius=1.0); R=Matrix.Rotation(ang,3,'Y')
            for v in r['verts']: v.co=R@Vector((v.co.x*sx_,v.co.y*sy_,v.co.z*sz_))+c
        for sx in (-1,1):
            ell(gc+Vector((sx*0.0052*_bs,0,0.0012*_bs)),0.0050*_bs,0.0012*_bs,0.0024*_bs,-sx*0.30)
            ell(gc+Vector((sx*0.0030*_bs,0.0002,-0.0052*_bs)),0.0011*_bs,0.0009*_bs,0.0045*_bs,sx*0.35)
        ell(gc+Vector((0,-0.0008,0)),0.0016*_bs,0.0014*_bs,0.0018*_bs,0.0)
    else:
        for sx in (-1,1):
            r=bmesh.ops.create_uvsphere(bm,u_segments=8,v_segments=6,radius=1.0)
            for v in r['verts']: v.co=Vector((v.co.x*0.0038*_bs,v.co.y*0.0016*_bs,v.co.z*0.0026*_bs))+gc+Vector((sx*0.0038*_bs,0,0))
        r=bmesh.ops.create_uvsphere(bm,u_segments=8,v_segments=6,radius=0.0016*_bs)
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
if not P.get('BRA_GEN',True):
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
    zpt=crz+P.get('PANEL_H',0.085); zO=crz+max(0.11,P.get('PANEL_H',0.085)+0.035); zbt=zpt+P.get('BACK_UP',0.045)
    FW0,FW1,BW0,BW1=[hx*v for v in P.get('THONG_W',(0.40,0.09,0.07,0.11))]
    off=0.0022; rows=[]; rows_back=[]
    def cast(x,th):
        d=Vector((0,-math.cos(th),-math.sin(th))); o_=Vector((x,cy,zO))+d*0.5; h=bvh.ray_cast(o_,-d,0.7)
        return (h[0]+h[1].normalized()*off) if h[0] is not None else None
    NTH=90
    for k in range(NTH+1):
        th=math.radians(-10+200*k/NTH); c=cast(0,th)
        if c is None: continue
        front=th<math.radians(90)
        if front and c.z>zpt: continue
        if (not front) and c.z>zbt+P.get('PANEL_TOP_DZ',0.0): continue
        if front: t=max(0,min(1,(zpt-c.z)/max(1e-4,zpt-crz))); hw=FW0+(FW1-FW0)*t**0.75
        else: t=max(0,min(1,(c.z-crz)/max(1e-4,zbt-crz))); hw=BW0+(BW1-BW0)*t**P.get('BACK_POW',1.0)
        row=[cast(hw*(j/3.0-1),th) for j in range(7)]
        if all(r_ is not None for r_ in row): rows.append(row); rows_back.append(not front)
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
            if P.get('BAND_V35'):
                # v3.5: ONE continuous curved band: up over the hip bone, then a gentle curve down to the back panel top (no V / X at the back)
                tp=P.get('PEAK_T',0.35); R_=P.get('STRING_RISE',0.035)
                zbe=zbt+P.get('BAND_BACK_DZ',0.0); z=zpt+R_*math.sin(min(1,t/tp)*math.pi/2) if t<tp else zpt+R_-(R_-(zbe-zpt))*float(sstep((t-tp)/(1-tp)))
                sh_=SHt*(1+(P.get('BAND_K',1.0)-1)*float(sstep((t-0.3)/0.5)))
            else:
                z=zpt+P.get('STRING_RISE',0.035)*math.sin(min(1,t*2)*math.pi/2) - (P.get('STRING_RISE',0.035)-(zbt-zpt))*max(0,t*2-1); sh_=SHt
            p0=ring_pt(sg*a,z-sh_/2,off); p1=ring_pt(sg*a,z+sh_/2,off)
            if p0 is None or p1 is None: continue
            cur=(bmT.verts.new(p0),bmT.verts.new(p1))
            if prev: bmT.faces.new((prev[0],cur[0],cur[1],prev[1]))
            prev=cur
    if P.get('PANEL_CLAMP_BAND') and P.get('BAND_V35'):
        # v3.6: clamp the back panel's top edge to just under the band at every x -> panel and band meet across the whole width (no hip-corner slits)
        tp=P.get('PEAK_T',0.35); R_=P.get('STRING_RISE',0.035); zbe=zbt+P.get('BAND_BACK_DZ',0.0); ncl=0
        for rw,isb in zip(vr,rows_back):
            if not isb: continue
            for v_ in rw:
                p=v_.co; a=math.atan2(p.x,-(p.y-cy)); aa=abs(a); t=max(0.0,min(1.0,(aa-ac)/max(1e-4,math.pi-ac)))
                z=zpt+R_*math.sin(min(1,t/tp)*math.pi/2) if t<tp else zpt+R_-(R_-(zbe-zpt))*float(sstep((t-tp)/(1-tp)))
                sh_=SHt*(1+(P.get('BAND_K',1.0)-1)*float(sstep((t-0.3)/0.5)))
                lim=z-sh_/2+P.get('PANEL_UNDER',0.004)
                if p.z>lim:
                    q=ring_pt(math.copysign(aa,a) if a!=0 else aa,lim,off)
                    if q is not None: v_.co=q; ncl+=1
        if P.get('PANEL_EXTEND'):
            # run 2: the back rows top out below the band at the hip corners -> extra rows from the top back row up to under the band, per column
            top=[rw for rw,isb in zip(vr,rows_back) if isb]
            if top:
                prevr=top[-1]; cols=[]
                for v_ in prevr:
                    p=v_.co.copy(); a=math.atan2(p.x,-(p.y-cy)); aa=abs(a); t=max(0.0,min(1.0,(aa-ac)/max(1e-4,math.pi-ac)))
                    z=zpt+R_*math.sin(min(1,t/tp)*math.pi/2) if t<tp else zpt+R_-(R_-(zbe-zpt))*float(sstep((t-tp)/(1-tp)))
                    sh_=SHt*(1+(P.get('BAND_K',1.0)-1)*float(sstep((t-0.3)/0.5)))
                    cols.append((math.copysign(aa,a) if a!=0 else aa,p.z,max(p.z,z-sh_/2+P.get('PANEL_UNDER',0.004))))
                NX=P.get('PANEL_EXT_N',6); nadd=0
                for k in range(1,NX+1):
                    pts=[ring_pt(a_,z0+(z1-z0)*k/NX,off) for a_,z0,z1 in cols]
                    if any(q is None for q in pts): break
                    cur=[bmT.verts.new(q) for q in pts]
                    for j in range(len(cur)-1): bmT.faces.new((prevr[j],prevr[j+1],cur[j+1],cur[j]))
                    prevr=cur; nadd+=1
                log('panel extended to band',{'rows':nadd,'dz':[round(c[2]-c[1],4) for c in cols]})
        log('panel clamped to band',ncl)
    bmT.loops.layers.uv.new('UVMap')
    me=bpy.data.meshes.new('Thong'); bmT.to_mesh(me); bmT.free(); TH=bpy.data.objects.new('Thong',me); sc.collection.objects.link(TH)
    tm,tnt,tb_=newmat('ThongBlack'); tb_.inputs['Base Color'].default_value=(0.012,0.012,0.013,1); tb_.inputs['Roughness'].default_value=P.get('THONG_ROUGH',0.42); tb_.inputs['Sheen Weight'].default_value=P.get('THONG_SHEEN',0.3); tb_.inputs['Specular IOR Level'].default_value=P.get('THONG_SPEC',0.5)
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
if P.get('BRA_GEN',True):
    for o_ in (BRA,globals().get('LACE'),globals().get('STR')):
        if o_ is None: continue
        has_arm=any(m_.type=='ARMATURE' for m_ in o_.modifiers)
        if has_arm:
            for g_ in list(o_.vertex_groups): o_.vertex_groups.remove(g_)
        weights_from_body(o_)
        if not has_arm: md=o_.modifiers.new('Armature','ARMATURE'); md.object=B
    if P.get('STRAP_CHEST_W',True) and globals().get('STR') is not None and rep.get('straps'):
        # v3.4: strap below the shoulder top rides the Chest only (arm/shoulder weights dragged the front strap into the body when the arms come down)
        zsh_=min(v_['z_sh'] for v_ in rep['straps'].values()); gch=STR.vertex_groups.get('Chest') or STR.vertex_groups.new(name='Chest'); mwS=STR.matrix_world; nch=0
        for v in STR.data.vertices:
            z_=(mwS@v.co).z; ws=float(sstep((z_-(zsh_-P.get('STRAP_W_LO',0.06)))/P.get('STRAP_W_H',0.05)))
            for gg in v.groups:
                if gg.group!=gch.index: gg.weight*=ws
            gch.add([v.index],1-ws,'ADD'); nch+=1
        log('strap chest weights',nch,'shoulder z',zsh_)
    log('generated bra weighted from body')
# ---------- keep clothes outside the (curvier) skin
for o,off in ((SH,0.0016),(BRA,P.get('BRA_OFF',0.0035))):
    mw=o.matrix_world; mwi=mw.inverted(); pushed=0
    for v in o.data.vertices:
        p=mw@v.co; h=bvh.find_nearest(p)
        if h and h[0] is not None:
            n_=h[1].normalized()
            if (p-h[0]).dot(n_)<off: v.co=mwi@(h[0]+n_*off); pushed+=1
    o.data.update(); log('pushed outside skin',o.name,pushed)
# ---------- v3.2 hair never lies inside the back/shoulders (stray grey strands were stuck on the upper back)
if P.get('HAIR_PUSH',True):
    mw=UM.matrix_world; mwi=mw.inverted(); hp_=0; off=P.get('HAIR_OFF',0.006)
    for v in UM.data.vertices:
        p=mw@v.co
        if p.z>HF['target_chin']: continue
        h=bvh.find_nearest(p)
        if h and h[0] is not None:
            n_=h[1].normalized()
            if (p-h[0]).dot(n_)<off: v.co=mwi@(h[0]+n_*off); hp_+=1
    UM.data.update(); log('hair pushed outside skin',hp_); HF['hair_pushed']=hp_
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
if VARIANT in ('B','C'):
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
    skinv=(warm>P.get('MB_WARM',0.06))&(lum>0.25); warm_v=warm.copy(); lum_v=lum.copy()   # per-vertex (the eye probe below reuses the names warm/lum)
    log('meshy texture',img_.name if img_ else None,'skin-coloured verts',int(skinv.sum()),'of',len(warm))
    # chin + neck of the Meshy head (front profile on the centre line)
    def mprof(V):
        ctr_=V[np.abs(V[:,0])<0.012]; Hm_=V[:,2].max(); hb_=ctr_[ctr_[:,2]>Hm_-0.25*total]
        zz=np.arange(Hm_-0.25*total,Hm_,0.004); pr=[]
        for z in zz:
            q_=hb_[(hb_[:,2]>=z)&(hb_[:,2]<z+0.004)]; pr.append(q_[:,1].min() if len(q_) else np.nan)
        pr=np.array(pr); up_=(zz>Hm_-0.16*total)&(zz<Hm_-0.05*total)
        ny_=np.nanmin(np.where(up_,pr,np.nan)); ni_=int(np.nanargmin(np.where(up_,pr,np.nan)))
        nb_=(zz>Hm_-P.get('MB_NECK_LO',0.21)*total)&(zz<Hm_-P.get('MB_NECK_HI',0.135)*total); nf_=np.nanmax(np.where(nb_,pr,np.nan))
        ch_=None
        for i in range(ni_,-1,-1):
            if not np.isnan(pr[i]) and pr[i]>nf_-P.get('MB_CHIN_TOL',0.012): ch_=float(zz[i]+0.004); break
        return ny_,nf_,ch_,zz,pr
    cxm=0.0
    ny,nfy,chin_m,zz,prof=mprof(V)
    log('meshy profile',[(round(float(a_),3),None if np.isnan(b_) else round(float(b_),3)) for a_,b_ in zip(zz[::2],prof[::2])])
    log('meshy nose/bangs',float(ny),'neck front',float(nfy),'chin',chin_m)
    MBP=P.get('MB_PITCH',20.0)
    if MBP and chin_m is not None:
        nk_=V[(np.abs(V[:,2]-(chin_m-0.01))<0.004)&skinv]; pcy=float((nk_[:,1].min()+nk_[:,1].max())/2) if len(nk_) else float(nfy)+0.04
        pv=Vector((0,pcy,chin_m)); MH.data.transform(Matrix.Translation(pv)@Matrix.Rotation(math.radians(-MBP),4,'X')@Matrix.Translation(-pv)); V=wco(MH)
        ny,nfy,chin_m,zz,prof=mprof(V); log('meshy pitched up',MBP,'deg; chin now',chin_m,'neck front',float(nfy))
    if chin_m is None or abs(chin_m-HF['target_chin'])>0.06: log('meshy chin guess off',chin_m); chin_m=HF['target_chin']
    # neck front of the Meshy model (skin verts) and of our body at the same height
    zq=chin_m-0.015
    msk=V[(np.abs(V[:,2]-zq)<0.005)&skinv&(np.abs(V[:,0])<0.05)]
    m_front=float(msk[:,1].min()) if len(msk) else float(V[(np.abs(V[:,2]-zq)<0.005)&(np.abs(V[:,0])<0.03)][:,1].min())
    BVn=wco(BODY); zq2=HF['target_chin']-0.015
    b_n=neck_at(BVn,zq2,0.005,NC,NRAD*1.5) or neck_at(BVn,zq2,0.01) or nt0
    dz=HF['target_chin']-chin_m; dy=b_n['front']-m_front
    MH.data.transform(Matrix.Translation(Vector((-cxm+b_n['cx'],dy,dz)))); V=wco(MH)
    zc_=HF['target_chin']
    if P.get('MB_HEAD_SCALE',1.0)!=1.0:
        pv=Vector((b_n['cx'],b_n['cy'],zc_)); MH.data.transform(Matrix.Translation(pv)@Matrix.Scale(P['MB_HEAD_SCALE'],4)@Matrix.Translation(-pv)); V=wco(MH)
    # v3.5: the Meshy face is turned (eyes, nose and mouth sit ~15-20 mm right of the head/neck centre while the face outline is centred): un-yaw it
    def mh_feats(V):
        if len(V)!=len(skinv): return None,None,0
        lumv=lum_v
        nz_=V[(V[:,2]>zc_+0.04)&(V[:,2]<zc_+0.10)&(np.abs(V[:,0]-b_n['cx'])<0.04)&skinv&(lumv>0.45)]
        nose=nz_[int(np.argmin(nz_[:,1]))] if len(nz_) else None
        rd=(warm_v>P.get('LIP_WARM',0.16))&(V[:,2]>zc_+0.012)&(V[:,2]<zc_+0.05)&(np.abs(V[:,0]-b_n['cx'])<0.035)&(V[:,1]<(float(nose[1])+0.035 if nose is not None else b_n['cy']))
        lips=V[rd]; lx=float(np.median(lips[:,0])) if len(lips)>20 else None
        return nose,lx,int(rd.sum())
    try:
        _nf,_lf,_nl=mh_feats(V); HF['B_feats']={'nose':None if _nf is None else [float(q) for q in _nf],'lips_x':_lf,'lip_verts':_nl}; log('B feats',HF['B_feats'])
    except Exception as e: log('FEATS ERR',repr(e))
    if P.get('MB_YAW_FIX',False):
        nose_,lx_,nl_=mh_feats(V)
        if nose_ is not None:
            fx_=float(nose_[0]) if lx_ is None else 0.5*(float(nose_[0])+lx_); dyf=float(nose_[1])-float(b_n['cy'])
            yaw=math.atan((fx_-b_n['cx'])/dyf) if abs(dyf)>0.02 else 0.0; yaw=max(-math.radians(P.get('MB_YAW_MAX',14)),min(math.radians(P.get('MB_YAW_MAX',14)),yaw))*P.get('MB_YAW_K',1.0)
            pv=Vector((b_n['cx'],b_n['cy'],zc_)); MH.data.transform(Matrix.Translation(pv)@Matrix.Rotation(yaw,4,'Z')@Matrix.Translation(-pv)); V=wco(MH)
            n2_,lx2_,_=mh_feats(V)
            HF['B_yaw']={'deg':math.degrees(yaw),'nose_x':float(nose_[0]),'lips_x':lx_,'lip_verts':nl_,'nose_y':float(nose_[1]),'after_nose_x':None if n2_ is None else float(n2_[0]),'after_lips_x':lx2_}
            log('B yaw fix',HF['B_yaw'])

    # ---------- v3.4: probe the Meshy face from INSIDE the head (rays from the head centre out through the face hit the skin, never the strands in front)
    from mathutils.bvhtree import BVHTree as _BVHm
    def mh_bvh():
        Vb=wco(MH); return _BVHm.FromPolygons([tuple(p) for p in Vb],[tuple(p.vertices) for p in MH.data.polygons]),Vb
    def floats_fwd(bvh_,p,D=0.05,gap=0.0025):
        # v3.6: march +y (into the head); skip back-facing hits (the strand's own far side / head interior); a point is a FLOATING strand
        # when the first front-facing (-y normal) surface behind it is more than gap away. Face skin never has a front-facing surface behind it.
        o_=Vector((float(p[0]),float(p[1])+0.0015,float(p[2]))); left=D
        for _k in range(8):
            h=bvh_.ray_cast(o_,Vector((0,1,0)),left)
            if h[0] is None: return False
            if h[1].y<0: return (h[0].y-float(p[1]))>gap
            left-=(h[0].y-o_.y)+0.0005; o_=Vector((o_.x,h[0].y+0.0005,o_.z))
            if left<=0: return False
        return False
    MEYE=None
    try:
        _bv,_Vb=mh_bvh(); Ht_=HF['target_head_total']; cy0=float(b_n['cy']); cx0=float(b_n['cx'])
        _uvd=MH.data.uv_layers.active.data if MH.data.uv_layers else None
        def uv_at(fi,hp):
            poly=MH.data.polygons[fi]; vs=[Vector(_Vb[v]) for v in poly.vertices]; li=list(poly.loop_indices)
            from mathutils.interpolate import poly_3d_calc
            w=poly_3d_calc(vs,hp); u=sum(_uvd[l].uv[0]*w_ for l,w_ in zip(li,w)); v=sum(_uvd[l].uv[1]*w_ for l,w_ in zip(li,w)); return u,v
        ctr=_Vb[(np.abs(_Vb[:,0]-cx0)<0.006)&(_Vb[:,2]>zc_+0.02)&(_Vb[:,2]<zc_+0.6*Ht_)&skinv[:len(_Vb)]] if len(skinv)==len(_Vb) else _Vb[:0]
        zn_=float(ctr[np.argmin(ctr[:,1]),2]) if len(ctr) else zc_+0.30*Ht_
        STEP=0.001; xs=np.arange(cx0-0.09,cx0+0.10+1e-9,STEP); zs=np.arange(zc_+P.get('EYE_PZ0',0.03),zc_+P.get('EYE_PZ1',0.16),STEP)
        G=np.zeros((len(zs),len(xs),3),np.float32)
        Wt,Hh_=img_.size
        for iz,z in enumerate(zs):
            for ix,x in enumerate(xs):
                h=_bv.ray_cast(Vector((x,cy0,z)),Vector((0,-1,0)),0.25)
                if h[0] is None or _uvd is None: continue
                u,v=uv_at(h[2],h[0]); G[iz,ix]=px[min(Hh_-1,int((v%1)*Hh_)),min(Wt-1,int((u%1)*Wt)),:3]
        np.save(OUT+'/proof/eyemap.npy',G[::-1]); log('eye probe grid',G.shape,'x0',float(xs[0]),'z top',float(zs[-1]))
        Gt=G[::-1]; lum=Gt.mean(2); warm=Gt[:,:,0]-Gt[:,:,2]; Hg,Wg=lum.shape
        dark=(lum>0.005)&(lum<P.get('LASH_LUM',0.14))&(warm<0.06); lab=np.zeros((Hg,Wg),np.int32); comps=[]; kk=0
        for i in range(Hg):
            for j in range(Wg):
                if dark[i,j] and not lab[i,j]:
                    kk+=1; st=[(i,j)]; lab[i,j]=kk; pp=[]
                    while st:
                        a_,b_=st.pop(); pp.append((a_,b_))
                        for da,db in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1)):
                            aa,bb=a_+da,b_+db
                            if 0<=aa<Hg and 0<=bb<Wg and dark[aa,bb] and not lab[aa,bb]: lab[aa,bb]=kk; st.append((aa,bb))
                    if len(pp)>=20:
                        pp=np.array(pp); r0,r1=pp[:,0].min(),pp[:,0].max(); c0,c1=pp[:,1].min(),pp[:,1].max()
                        comps.append({'n':int(len(pp)),'x':float(xs[0]+(c0+c1)/2*STEP),'w':float((c1-c0+1)*STEP),'ztop':float(zs[-1]-r0*STEP),'zbot':float(zs[-1]-r1*STEP),'h':float((r1-r0+1)*STEP)})
        cs_=[c for c in comps if 0.012<c['w']<0.055 and c['h']<0.022]
        best=None
        for a_ in cs_:
            for b_ in cs_:
                dx_=b_['x']-a_['x']
                if 0.045<dx_<0.10 and abs(b_['ztop']-a_['ztop'])<0.02:
                    sc_=a_['n']+b_['n']-2000*abs(a_['w']-b_['w'])
                    if best is None or sc_>best[0]: best=(sc_,a_,b_)
        log('eye comps',sorted(cs_,key=lambda c:-c['n'])[:8])
        cand={'pair':best[1:] if best else None}
        if best:
            eL_,eR_=best[1],best[2]; src_='texture'
            WK=P.get('EYE_WK',1.0); ew_=WK*(eL_['w']+eR_['w'])/2
            eyes_=[]
            for c,od in ((eL_,-1),(eR_,1)):
                xc=c['x']-od*0.06*c['w']; zc=c['ztop']-P.get('EYE_TOPK',0.55)*ew_/2; eyes_.append((xc,zc))
            roll=math.atan2(eyes_[1][1]-eyes_[0][1],eyes_[1][0]-eyes_[0][0])
        else:
            src_='fallback'; ew_=0.03; eyes_=[(cx0-0.033,zc_+0.08),(cx0+0.033,zc_+0.08)]; roll=0.0
        if P.get('EYE_DEC'): eyes_=[tuple(P['EYE_DEC'][0]),tuple(P['EYE_DEC'][1])]; ew_=P['EYE_DEC'][2]; roll=P['EYE_DEC'][3] if len(P['EYE_DEC'])>3 else 0.0; src_='param'
        ex=(eyes_[0][0]+eyes_[1][0])/2; ez=(eyes_[0][1]+eyes_[1][1])/2; ipd=eyes_[1][0]-eyes_[0][0]
        MEYE={'cx':ex,'z':ez,'ipd':ipd,'eyes':eyes_,'ew':ew_,'roll':roll,'nose_z':zn_,'src':src_,'cand':cand}
        log('MEYE',MEYE); HF['B_eyes']=MEYE
    except Exception as e:
        import traceback; log('EYEPROBE ERR',repr(e),traceback.format_exc()[-600:])
    # v3.5 B2 (C geometry): fit the Meshy FACE onto her own head's frame (eye line, nose depth, centre) so her Blowout hair, bun, clip and cranium fit it
    if VARIANT=='C' and P.get('MC_FIT',True) and MEYE:
        try:
            FVc=wco(FH); fe=FVc[eidx] if eidx else None
            fez=float(fe[:,2].mean()) if fe is not None else HF['eye_z']; fcx=float(fe[:,0].mean()) if fe is not None else 0.0
            cenF=FVc[(np.abs(FVc[:,0]-fcx)<0.012)&(FVc[:,2]>zc_+0.15*(fez-zc_))&(FVc[:,2]<fez)]; fny=float(cenF[:,1].min()) if len(cenF) else HF['nose_y']
            nose_,_lx,_n=mh_feats(V); mny=float(nose_[1]) if nose_ is not None else float(ny); mcx=float(nose_[0]) if nose_ is not None else MEYE['cx']
            sM=(fez-zc_)/max(1e-3,MEYE['z']-zc_); sM=max(0.85,min(1.2,sM))*P.get('MC_FIT_K',1.0)
            pv=Vector((mcx,b_n['cy'],zc_)); T_=Matrix.Translation(Vector((fcx-mcx,0,0)))@Matrix.Translation(pv)@Matrix.Scale(sM,4)@Matrix.Translation(-pv)
            MH.data.transform(T_); V=wco(MH)
            nose2,_l2,_n2=mh_feats(V); dyF=(fny-float(nose2[1]))*P.get('MC_FIT_DY_K',1.0)+P.get('MC_FIT_DY',0.0) if nose2 is not None else 0.0
            MH.data.transform(Matrix.Translation(Vector((0,dyF,0)))); V=wco(MH)
            def _tp(x,z): q=T_@Vector((x,b_n['cy'],z)); return (q.x,q.z)
            MEYE['eyes']=[_tp(*e_) for e_ in MEYE['eyes']]; cxz=_tp(MEYE['cx'],MEYE['z']); MEYE['cx'],MEYE['z']=cxz; MEYE['ipd']*=sM; MEYE['ew']*=sM
            HF['C_fit']={'cx':fcx,'scale':sM,'dx':fcx-mcx,'dy':dyF,'her_eye_z':fez,'her_nose_y':fny,'meshy_nose_y_before':mny}; log('C fit to her head frame',HF['C_fit'])
        except Exception as e:
            import traceback; log('C FIT ERR',repr(e),traceback.format_exc()[-600:])
    # cut: everything above chin-NECK_KEEP; hair-coloured strands kept further down beside/behind the neck
    r_=np.hypot(V[:,0]-b_n['cx'],V[:,1]-b_n['cy'])
    keep=(V[:,2]>=zc_-P.get('MB_NECK_KEEP',0.03))|((~skinv)&(V[:,2]>=zc_-P.get('MB_HAIR_KEEP',0.11))&(r_>max(b_n['rx'],b_n['ry'])*1.05))
    if VARIANT=='C' and P.get('MC_GEOM',False):
        # v3.5 B2: keep ONLY the Meshy face by GEOMETRY (no colour test: her white hair ends are skin-coloured, which is why v3.2-v3.4 C stripped the face):
        # front half of the head, inside a face ellipse from chin to the hairline; minus strands floating in front of the face (a ray behind them hits the face)
        _bv2,_V2=mh_bvh(); Ht_=HF['target_head_total']; ezM=MEYE['z'] if MEYE else zc_+0.075; cxF=MEYE['cx'] if MEYE else b_n['cx']
        zH=ezM+P.get('MC_HL_K',0.62)*(ezM-zc_); zm=(zc_+zH)/2; bz=(zH-zc_)/2+P.get('MC_ZMARG',0.008)
        lv_=V[(np.abs(V[:,2]-ezM)<0.006)&skinv&(V[:,1]<b_n['cy'])]
        ax_=float(np.percentile(np.abs(lv_[:,0]-cxF),97)) if len(lv_)>20 else 0.062; ax_=min(0.075,max(0.05,ax_))*P.get('MC_AX_K',1.02)
        inell=((V[:,0]-cxF)/ax_)**2+((V[:,2]-zm)/bz)**2<1.0
        front=V[:,1]<b_n['cy']+P.get('MC_YBACK',-0.01)
        face=inell&front&(V[:,2]>zc_-0.004)
        fl=np.zeros(len(V),bool)
        for i in np.where(face)[0]:
            h=_bv2.ray_cast(Vector(V[i])+Vector((0,0.0015,0)),Vector((0,1,0)),P.get('MC_FLOAT',0.03))
            if h[0] is not None and (h[0].y-V[i][1])>0.0025: fl[i]=True
        rn=np.hypot(V[:,0]-b_n['cx'],V[:,1]-b_n['cy'])
        neck=(V[:,2]>=zc_-P.get('MB_NECK_KEEP',0.03))&(V[:,2]<zc_+0.03)&skinv&(rn<max(b_n['rx'],b_n['ry'])*P.get('MC_NECK_R',1.6))
        keep=(face&~fl)|(neck&~fl)
        HF['C_geom']={'hairline_z':zH,'eye_z':ezM,'ax':ax_,'bz':bz,'face':int(face.sum()),'strands':int(fl.sum()),'neck':int(neck.sum()),'kept':int(keep.sum())}; log('C geometric face keep',HF['C_geom'])
    elif VARIANT=='C':
        # v3.4 C: strip the Meshy hair shell; keep non-skin paint that lies ON the face (eyes/brows/lashes). A non-skin vertex is a floating
        # strand when a ray from it into the head (+y) hits the face surface within MC_FLOAT; above the brow line everything non-skin is shell.
        _bv2,_V2=mh_bvh(); Ht_=HF['target_head_total']
        ezb=(MEYE['z'] if MEYE else zc_+0.42*Ht_)+P.get('MC_BROW_DZ',0.028)
        fl=np.zeros(len(V),bool)
        cand_=np.where((~skinv)&(V[:,2]<ezb)&(V[:,2]>zc_-0.005)&(np.abs(V[:,0]-b_n['cx'])<P.get('MC_FACE_HW',0.06))&(V[:,1]<b_n['cy']))[0]
        for i in cand_:
            h=_bv2.ray_cast(Vector(V[i])+Vector((0,0.0015,0)),Vector((0,1,0)),P.get('MC_FLOAT',0.03))
            if h[0] is not None and (h[0].y-V[i][1])>0.0025: fl[i]=True
        onface=np.zeros(len(V),bool); onface[cand_]=True; onface&=~fl
        strip_=(~skinv)&(~onface); keep=keep&~strip_; log('C v3.4: hair verts stripped',int(strip_.sum()),'floating strands',int(fl.sum()),'face paint kept',int(onface.sum()),'brow z',ezb)
    if VARIANT=='B' and P.get('MB_LOOP_CUT',True):
        # v3.4 B: remove the thin 'wire loop' strand sticking up over the crown: anything far above the local hair-dome height
        Ht_=HF['target_head_total']; top=V[:,2]>zc_+0.45*Ht_; CS=0.006
        if top.sum()>50:
            ix_=np.floor((V[:,0]-V[:,0].min())/CS).astype(int); iy_=np.floor((V[:,1]-V[:,1].min())/CS).astype(int)
            nx_,ny_=ix_.max()+1,iy_.max()+1; zmx=np.full((nx_,ny_),np.nan)
            for i in np.where(top&keep)[0]:
                a_,b2_=ix_[i],iy_[i]; zmx[a_,b2_]=V[i,2] if np.isnan(zmx[a_,b2_]) else max(zmx[a_,b2_],V[i,2])
            R_=int(P.get('LOOP_R',0.024)/CS); med=np.full_like(zmx,np.nan)
            for a_ in range(nx_):
                for b2_ in range(ny_):
                    if np.isnan(zmx[a_,b2_]): continue
                    blk_=zmx[max(0,a_-R_):a_+R_+1,max(0,b2_-R_):b2_+R_+1]; med[a_,b2_]=np.nanpercentile(blk_,P.get('LOOP_PCT',60))
            mv=med[ix_,iy_]; lp=top&keep&(~np.isnan(mv))&(V[:,2]>mv+P.get('LOOP_TOL',0.010))
            # also the thin arc of the loop above the crown: everything over the dome's 97th-percentile top + tol
            ztop_=np.nanpercentile(zmx,97); lp|=top&keep&(V[:,2]>ztop_+P.get('LOOP_TOL',0.010))
            keep=keep&~lp; HF['B_loop_cut']={'verts':int(lp.sum()),'dome_top':float(ztop_)}; log('B wire loop cut',HF['B_loop_cut'])
    if VARIANT=='B' and P.get('MB_STRAND_CUT',False) and MEYE:
        # v3.5: hair strands hanging IN FRONT of the face (over the eyes / nose) are cut at the brow line -> bangs that end above the eyes
        _bvs,_Vs=mh_bvh(); ezS=MEYE['z']; cxS=MEYE['cx']
        _dx=np.abs(V[:,0]-cxS)/P.get('MB_SC_HW',0.05); zcut=ezS+P.get('MB_SC_ZUP',0.022)+P.get('MB_SC_CURVE',0.0)*np.clip(1-_dx*_dx,0,1)   # curtain bangs: shorter at the centre part
        cand=np.where(keep&(V[:,1]<b_n['cy']-0.03)&(_dx<1)&(V[:,2]>zc_+0.005)&(V[:,2]<zcut)&((warm_v<0.07)|(lum_v<0.4)))[0]
        cut=np.zeros(len(V),bool)
        for i in cand:
            h=_bvs.ray_cast(Vector(V[i])+Vector((0,0.0015,0)),Vector((0,1,0)),P.get('MB_SC_D',0.04))
            if h[0] is not None and (h[0].y-V[i][1])>0.003: cut[i]=True
        keep=keep&~cut; HF['B_strand_cut']={'cand':int(len(cand)),'cut':int(cut.sum())}; log('B face strands cut',HF['B_strand_cut'])
    if VARIANT=='B' and P.get('MB_LOCK_CUT',False) and MEYE:
        # v3.6: remove ONLY the lock hanging over the face (uncut hair otherwise). Seeds = floating strand verts below the eye line near the
        # centre; grow through floating verts inside a narrow band around them up to brow+ZUP. No colour test (its light tips go too).
        try:
            _bvl,V_=mh_bvh(); ezS=MEYE['z']; cxS=MEYE['cx']; nzS=MEYE.get('nose_z',ezS-0.02); cyS=float(b_n['cy'])
            zup=ezS+P.get('MB_LC_ZUP',0.03)
            reg=keep&(V_[:,1]<cyS)&(np.abs(V_[:,0]-cxS)<P.get('MB_LC_HW',0.045))&(V_[:,2]>nzS-P.get('MB_LC_ZDN',0.03))&(V_[:,2]<zup)
            fl=np.zeros(len(V_),bool)
            for i in np.where(reg)[0]: fl[i]=floats_fwd(_bvl,V_[i],P.get('MB_LC_D',0.05),P.get('MB_LC_GAP',0.0025))
            seed=fl&(V_[:,2]<ezS+P.get('MB_LC_SEEDZ',0.004))&(np.abs(V_[:,0]-cxS)<P.get('MB_LC_SEEDX',0.035))
            ne_=len(MH.data.edges); ev_=np.empty(ne_*2,np.int64); MH.data.edges.foreach_get('vertices',ev_); ev_=ev_.reshape(-1,2)
            adj={}
            ok_=fl
            for a_,b_ in ev_[ok_[ev_[:,0]]&ok_[ev_[:,1]]]:
                adj.setdefault(int(a_),[]).append(int(b_)); adj.setdefault(int(b_),[]).append(int(a_))
            lock=np.zeros(len(V_),bool); st=[int(i) for i in np.where(seed)[0]]; lock[st]=True
            if P.get('MB_LC_MODE','band')=='comp':
                # run 2: connected pieces of floating strand inside the slab (below brow+ZUP); only those reaching DROP below the eye line
                # near the face centre are the lock -> the fringe/bang sheet above and beside it is never touched (no holes)
                st=[]; lock[:]=False; seen_=np.zeros(len(V_),bool); ncomp=0
                for s0 in np.where(fl)[0]:
                    if seen_[s0]: continue
                    comp=[int(s0)]; seen_[s0]=True; q_=[int(s0)]
                    while q_:
                        a_=q_.pop()
                        for b_ in adj.get(a_,()):
                            if not seen_[b_]: seen_[b_]=True; q_.append(b_); comp.append(b_)
                    ci=np.array(comp)
                    if V_[ci,2].min()<ezS-P.get('MB_LC_DROP',0.01) and np.abs(V_[ci,0]-cxS).min()<P.get('MB_LC_SEEDX',0.035):
                        lo_=ci[V_[ci,2]<ezS-0.004]; xl_,xh_=float(V_[lo_,0].min()),float(V_[lo_,0].max())
                        w_=P.get('MB_LC_XMARG',0.006)+P.get('MB_LC_XSLOPE',0.4)*np.clip(V_[ci,2]-(ezS-0.004),0,None)
                        ci=ci[(V_[ci,0]>=xl_-w_)&(V_[ci,0]<=xh_+w_)]; lock[ci]=True; ncomp+=1
                HF['B_lock_comps']=ncomp
            # x band: seeds' x range (+ margin) widened linearly with height (the lock runs diagonally up to the part)
            if len(st):
                sx0,sx1=float(V_[seed,0].min()),float(V_[seed,0].max()); mg=P.get('MB_LC_XMARG',0.008); slope=P.get('MB_LC_XSLOPE',0.6)
                while st:
                    a_=st.pop()
                    for b_ in adj.get(a_,()):
                        if lock[b_]: continue
                        wid=mg+slope*max(0.0,V_[b_,2]-ezS)
                        if sx0-wid<=V_[b_,0]<=sx1+wid: lock[b_]=True; st.append(b_)
            # every floating fragment left below the eye line near the centre (tips resting on the nose) is the lock too
            lock|=fl&(V_[:,2]<ezS-0.004)&(np.abs(V_[:,0]-cxS)<P.get('MB_LC_SEEDX',0.035))
            keep=keep&~lock
            zl=zup-P.get('INP_LOCK_ZTOP',0.006); lp_=V_[lock]; HF['lock_pts']=lp_[lp_[:,2]<zl][:,[0,2]] if len(lp_) else np.zeros((0,2))
            HF['B_lock_cut']={'region':int(reg.sum()),'floating':int(fl.sum()),'seeds':int(seed.sum()),'cut':int(lock.sum()),
                              'x':[float(lp_[:,0].min()),float(lp_[:,0].max())] if len(lp_) else None,'z':[float(lp_[:,2].min()),float(lp_[:,2].max())] if len(lp_) else None}
            log('B lock cut',HF['B_lock_cut'])
        except Exception as e:
            import traceback; log('LOCK CUT ERR',repr(e),traceback.format_exc()[-600:])
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
        if len(comp)<P.get('MB_MIN_ISLAND',200) or max(q_.co.z for q_ in comp)<zc_+P.get('MB_ISLAND_ZMIN',0.0): small+=comp  # floating bits (necklace/strap/chest fragments) that never reach the head
    bmesh.ops.delete(bm,geom=small,context='VERTS')
    if VARIANT=='B' and P.get('MB_CROWN_FILL',False):
        # v3.5: close the bare patch the crown-loop cut leaves (new faces get a dark hair material, not a random texel)
        zt_=zc_+P.get('MB_FILL_ZK',0.5)*HF['target_head_total']
        be=[e for e in bm.edges if e.is_boundary and all(v.co.z>zt_ for v in e.verts)]
        nf0=len(bm.faces)
        if be:
            try:
                res_=bmesh.ops.holes_fill(bm,edges=be,sides=P.get('MB_FILL_SIDES',400)); nfil=res_['faces']
                if nfil:
                    hdm=bpy.data.materials.new('CrownDark'); hdm.use_nodes=True; qd=hdm.node_tree.nodes['Principled BSDF']; qd.inputs['Base Color'].default_value=(0.025,0.024,0.026,1); qd.inputs['Roughness'].default_value=0.55
                    MH.data.materials.append(hdm); mi_=len(MH.data.materials)-1
                    for f_ in nfil: f_.material_index=mi_
                HF['B_crown_fill']={'boundary_edges':len(be),'faces':len(nfil)}; log('B crown fill',HF['B_crown_fill'])
            except Exception as e: log('CROWN FILL ERR',repr(e))
    bm.to_mesh(MH.data); bm.free(); MH.data.update()
    tr0=tris(MH); r_dec=min(1.0,P.get('MB_TRIS',30000)/max(1,tr0))
    if r_dec<0.999:
        md=MH.modifiers.new('Dec','DECIMATE'); md.ratio=r_dec; sel([MH]); bpy.ops.object.modifier_apply(modifier='Dec')
    for p in MH.data.polygons: p.use_smooth=True
    # v3.3 neck seam: the Meshy neck's cut edge flares/tucks onto our body's neck ellipse (+1.5%), fading out over MB_SEAM_H
    if P.get('MB_SEAM',True):
        zb_=zc_-P.get('MB_NECK_KEEP',0.03); V=wco(MH); BVs=wco(BODY); SH_=P.get('MB_SEAM_H',0.022)
        bqs=neck_at(BVs,zb_+0.003,0.004,NC,NRAD*1.5) or b_n
        skin2=np.ones(len(V),bool)
        if img_ is not None and MH.data.uv_layers:
            me2=MH.data; W2,H2=img_.size; px2=np.empty(W2*H2*4,dtype=np.float32); img_.pixels.foreach_get(px2); px2=px2.reshape(H2,W2,4)
            nl2=len(me2.loops); uv2=np.empty(nl2*2,dtype=np.float32); me2.uv_layers.active.data.foreach_get('uv',uv2); uv2=uv2.reshape(-1,2)
            lv2=np.empty(nl2,dtype=np.int64); me2.loops.foreach_get('vertex_index',lv2)
            c2=px2[np.clip(((uv2[:,1]%1)*H2).astype(int),0,H2-1),np.clip(((uv2[:,0]%1)*W2).astype(int),0,W2-1),:3]
            n2=np.bincount(lv2,minlength=len(V)).clip(1); cv2=np.stack([np.bincount(lv2,c2[:,k],minlength=len(V)) for k in range(3)],1)/n2[:,None]
            skin2=((cv2[:,0]-cv2[:,2])>P.get('MB_WARM',0.06))&(cv2.mean(1)>0.25); del px2
        Vs_=V[skin2]
        ms=neck_at(Vs_,zb_+0.006,0.006,(bqs['cx'],bqs['cy']),max(bqs['rx'],bqs['ry'])*P.get('MB_SEAM_R',1.3)) if len(Vs_) else None
        if ms:
            dx=V[:,0]-ms['cx']; dy_=V[:,1]-ms['cy']; th=np.arctan2(dy_/max(ms['ry'],1e-4),dx/max(ms['rx'],1e-4))
            k_=P.get('MB_SEAM_OUT',1.015); mixk=P.get('MB_SEAM_MIX',0.5)
            T_=dict(cx=bqs['cx']+(ms['cx']-bqs['cx'])*mixk,cy=bqs['cy']+(ms['cy']-bqs['cy'])*mixk,rx=bqs['rx']+(ms['rx']-bqs['rx'])*mixk,ry=bqs['ry']+(ms['ry']-bqs['ry'])*mixk)
            tx=T_['cx']+np.cos(th)*T_['rx']*k_; ty=T_['cy']+np.sin(th)*T_['ry']*k_
            # body neck flares up to the same ellipse below the seam (so neither side steps)
            if mixk>0:
                rb_=np.hypot(BVs[:,0]-bqs['cx'],BVs[:,1]-bqs['cy']); FH_=P.get('MB_FLARE_H',0.045)
                wb=sstep((BVs[:,2]-(zb_-FH_))/FH_)*(BVs[:,2]<=zb_+0.004)*(rb_<NRAD*1.45)
                thb=np.arctan2((BVs[:,1]-bqs['cy'])/max(bqs['ry'],1e-4),(BVs[:,0]-bqs['cx'])/max(bqs['rx'],1e-4))
                rel=np.hypot((BVs[:,0]-bqs['cx'])/max(bqs['rx'],1e-4),(BVs[:,1]-bqs['cy'])/max(bqs['ry'],1e-4))
                bx=T_['cx']+np.cos(thb)*T_['rx']*rel; by=T_['cy']+np.sin(thb)*T_['ry']*rel
                Db=np.zeros_like(BVs); Db[:,0]=(bx-BVs[:,0])*wb; Db[:,1]=(by-BVs[:,1])*wb; wdelta(BODY,Db)
            tt=1-sstep((V[:,2]-zb_)/SH_)
            nr=np.hypot(dx/max(ms['rx'],1e-4),dy_/max(ms['ry'],1e-4))
            sk=(nr<1.6)&(V[:,2]>zb_-P.get('MB_SEAM_ZLO',0.004))&(V[:,2]<zb_+SH_)&(skin2|((nr<P.get('MB_SEAM_NR',0.0))&(dy_<0.3*ms['ry'])))
            # scale each point about the neck centre by (target ellipse / Meshy ellipse) along its angle -> keeps the jaw/neck shape, no snapping
            fx=T_['rx']*k_/max(ms['rx'],1e-4); fy=T_['ry']*k_/max(ms['ry'],1e-4)
            nx_=T_['cx']+dx*fx; ny_=T_['cy']+dy_*fy
            Ds=np.zeros_like(V); Ds[:,0]=(nx_-V[:,0])*tt*sk; Ds[:,1]=(ny_-V[:,1])*tt*sk; wdelta(MH,Ds); V=wco(MH)
            HF['B_seam']={'body':bqs,'meshy':ms,'verts':int(sk.sum()),'max_move':float(np.abs(Ds).max())}; log('B neck seam',HF['B_seam'])
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
        BVn=wco(BODY); bq=neck_at(BVn,zc_-0.005,0.006,NC,NRAD*1.5) or b_n
        f_=min(1.0,0.93*min(mrx/max(bq['rx'],1e-4),mry/max(bq['ry'],1e-4)))
        rr=np.hypot(BVn[:,0]-bq['cx'],BVn[:,1]-bq['cy']); w_=(sstep((BVn[:,2]-(zc_-P.get('MB_NECK_KEEP',0.03)+P.get('MB_TUCK_PRE',0.002)))/P.get('MB_TUCK_RAMP',0.018)) if P.get('MB_SEAM',True) else sstep((BVn[:,2]-(zc_-P.get('MB_NECK_KEEP',0.03)-0.01))/0.02))*(rr<NRAD*1.45)
        Dn=np.zeros_like(BVn); Dn[:,0]=(bq['cx']+(BVn[:,0]-bq['cx'])*f_-BVn[:,0])*w_; Dn[:,1]=(mcy+(BVn[:,1]-bq['cy'])*f_-BVn[:,1])*w_; wdelta(BODY,Dn)
        HF['B_neck_tuck']={'factor':f_,'meshy_neck':[mrx,mry,mcy],'body_neck':bq}


    # ---------- v3.5: LEVEL, symmetric eyes (the Meshy texture's own eyes are rolled ~10 deg and uneven while the face is straight) + inpaint the Meshy
    # eye paint (and the smear past the right outer corner) with the surrounding skin, so the painted decal is the only eye that shows
    if MEYE and P.get('EYE_LEVEL',False):
        try:
            Vn=wco(MH); nose_,_lx,_n=mh_feats(Vn) if len(Vn)==len(skinv) else (None,None,0)
            cxE=MEYE['cx'] if (nose_ is None or not P.get('EYE_CX_NOSE',True)) else 0.5*(MEYE['cx']+float(nose_[0]))
            if nose_ is None and HF.get('B_yaw',{}).get('after_nose_x') is not None and P.get('EYE_CX_NOSE',True): cxE=0.5*(MEYE['cx']+HF['B_yaw']['after_nose_x'])
            elif nose_ is None and (HF.get('B_feats') or {}).get('nose') and P.get('EYE_CX_NOSE',True):
                _fx=[HF['B_feats']['nose'][0]]+([HF['B_feats']['lips_x']] if HF['B_feats'].get('lips_x') is not None else []); cxE=0.5*(MEYE['cx']+float(np.mean(_fx)))
            if VARIANT=='C' and HF.get('C_fit'): cxE=0.5*(MEYE['cx']+HF['C_fit']['cx'])
            ezE=MEYE['z']+P.get('EYE_ZOFF2',0.0); ipdE=MEYE['ipd']*P.get('EYE_IPD_K',1.0)
            MEYE['eyes_meshy']=list(MEYE['eyes']); MEYE['eyes']=[(cxE-ipdE/2,ezE),(cxE+ipdE/2,ezE)]; MEYE['roll_meshy']=MEYE.get('roll',0.0); MEYE['roll']=0.0
            HF['B_eyes_level']={'cx':cxE,'z':ezE,'ipd':ipdE,'meshy_eyes':MEYE['eyes_meshy']}; log('eyes levelled',HF['B_eyes_level'])
        except Exception as e:
            import traceback; log('EYE LEVEL ERR',repr(e),traceback.format_exc()[-500:])
    if MEYE and P.get('EYE_INPAINT',False) and img_ is not None and MH.data.uv_layers:
        try:
            me_=MH.data; Vw=wco(MH); W_,H_=img_.size; pa=np.empty(W_*H_*4,np.float32); img_.pixels.foreach_get(pa); pa=pa.reshape(H_,W_,4)
            uvd=me_.uv_layers.active.data; ewm=MEYE['ew']; cyH=float(b_n['cy'])
            em_=MEYE.get('eyes_meshy') or MEYE['eyes']; cxm=MEYE['cx']
            pc=np.array([p.center for p in me_.polygons]); pn=np.array([p.normal for p in me_.polygons])
            Mw=np.array(MH.matrix_world); pc=pc@Mw[:3,:3].T+Mw[:3,3]; pn=pn@Mw[:3,:3].T
            # v3.5 run 2: per-TEXEL mask from the interpolated 3D position (the decimated head has too few vertices around the eyes for a vertex mask)
            ells=[]
            for (ex,ez),ev in zip(em_,MEYE['eyes']):
                outer=1 if ex>cxm else -1
                for (x0_,z0_) in ((ex,ez),ev): ells.append((x0_,z0_,outer))
            AO_,AI_,BZ_=ewm*P.get('INP_AOUT',1.0),ewm*P.get('INP_AIN',0.72),ewm*P.get('INP_B',0.5)
            BR_=P.get('INP_BRIDGE')   # [ax, bz, dz]: painted hair streaks over the nose bridge / between the eyes
            cxB=0.5*(MEYE['eyes'][0][0]+MEYE['eyes'][1][0]); ezB=0.5*(MEYE['eyes'][0][1]+MEYE['eyes'][1][1])
            LK_=HF.get('lock_pts') if P.get('INP_LOCK',False) else None
            if LK_ is not None and not len(LK_): LK_=None
            LR_=P.get('INP_LOCK_R',0.004)
            def lockd(X,Z):
                q=LK_[(LK_[:,0]>X.min()-3*LR_)&(LK_[:,0]<X.max()+3*LR_)&(LK_[:,1]>Z.min()-3*LR_)&(LK_[:,1]<Z.max()+3*LR_)]
                if not len(q): return np.full(X.shape,9.0,np.float32)
                d=np.full(X.shape,9.0,np.float32)
                for k0 in range(0,len(q),256):
                    qq=q[k0:k0+256]; d=np.minimum(d,np.sqrt((X[...,None]-qq[:,0])**2+(Z[...,None]-qq[:,1])**2).min(-1))
                return d
            def emask(X,Z):
                m=np.zeros(X.shape,np.float32)
                if LK_ is not None:
                    m=np.maximum(m,(1-sstep((lockd(X,Z)-LR_)/LR_)).astype(np.float32))
                if BR_:
                    d=np.sqrt(((X-cxB)/BR_[0])**2+((Z-(ezB+BR_[2]))/BR_[1])**2); m=np.maximum(m,1-sstep((d-0.7)/0.4))
                for (x0_,z0_,outer) in ells:
                    ax=np.where((X-x0_)*outer>0,AO_,AI_); d=np.sqrt(((X-x0_)/ax)**2+((Z-z0_)/BZ_)**2); m=np.maximum(m,1-sstep((d-0.72)/0.38))
                return m
            nl=len(me_.loops); uvs=np.empty(nl*2,np.float32); uvd.foreach_get('uv',uvs); uvs=uvs.reshape(-1,2); lvx=np.empty(nl,np.int64); me_.loops.foreach_get('vertex_index',lvx)
            fr=(Vw[:,1]<cyH-P.get('INP_FRONT_DY',0.03))
            if P.get('INP_FRONT_NY') is not None:
                # v3.6: the Meshy face sits only ~2 cm ahead of the neck centre, so 'front' = facing the camera, not a 3 cm depth cut
                vn_=np.empty(len(me_.vertices)*3); me_.vertices.foreach_get('normal',vn_); vn_=vn_.reshape(-1,3)@Mw[:3,:3].T
                vn_/=np.linalg.norm(vn_,axis=1,keepdims=True).clip(1e-9); fr&=(vn_[:,1]<-P['INP_FRONT_NY'])
            nfr0=int(fr.sum()); nst=0
            if P.get('INP_STRAND_TEST',True):
                _bvi,_=mh_bvh()
                for i in np.where(fr&(emask(Vw[:,0],Vw[:,2])>0.0)|fr&(np.abs(Vw[:,0]-cxm)<0.09)&(np.abs(Vw[:,2]-MEYE['z'])<0.03))[0]:
                    if P.get('INP_ST_NRM',False):
                        if floats_fwd(_bvi,Vw[i],0.03,0.0025): fr[i]=False; nst+=1
                        continue
                    h=_bvi.ray_cast(Vector(Vw[i])+Vector((0,0.0015,0)),Vector((0,1,0)),0.03)
                    if h[0] is not None and (h[0].y-Vw[i][1])>0.0025: fr[i]=False; nst+=1   # a strand floating in front of the face keeps its hair colour
            # fill colour: texels of front skin vertices in a ring around the eyes
            dmin=np.full(len(Vw),9.0)
            for (x0_,z0_,outer) in ells: dmin=np.minimum(dmin,np.sqrt(((Vw[:,0]-x0_)/AO_)**2+((Vw[:,2]-z0_)/BZ_)**2))
            rgm=fr&(dmin>1.15)&(dmin<2.2)&(Vw[:,2]<MEYE['z']+0.004)
            li=np.where(rgm[lvx])[0]
            cs_=pa[np.clip((uvs[li,1]%1*H_).astype(int),0,H_-1),np.clip((uvs[li,0]%1*W_).astype(int),0,W_-1),:3] if len(li) else np.zeros((0,3))
            ok_=(cs_.mean(1)>0.55)&((cs_[:,0]-cs_[:,2])>0.08)&((cs_[:,0]-cs_[:,2])<0.3) if len(cs_) else np.zeros(0,bool)
            fill=np.percentile(cs_[ok_],P.get('INP_PCT',60),axis=0) if ok_.sum()>10 else np.array([0.88,0.72,0.68])
            npx=0; npoly=0
            dl_=lockd(Vw[:,0],Vw[:,2]) if LK_ is not None else None
            for p in me_.polygons:
                vs=list(p.vertices)
                if not any(fr[v] for v in vs): continue
                if min(dmin[v] for v in vs)>2.5 and (LK_ is None or min(dl_[v] for v in vs)>3*LR_): continue
                lis=list(p.loop_indices); uv_=[(uvs[l][0]%1*W_,uvs[l][1]%1*H_) for l in lis]; X_=[Vw[v] for v in vs]
                if max(q[0] for q in uv_)-min(q[0] for q in uv_)>W_*0.5 or max(q[1] for q in uv_)-min(q[1] for q in uv_)>H_*0.5: continue
                npoly+=1
                for t_ in range(1,len(vs)-1):
                    (x0,y0),(x1,y1),(x2,y2)=uv_[0],uv_[t_],uv_[t_+1]; P0,P1,P2=X_[0],X_[t_],X_[t_+1]
                    bx0,bx1=int(max(0,math.floor(min(x0,x1,x2)))),int(min(W_-1,math.ceil(max(x0,x1,x2)))); by0,by1=int(max(0,math.floor(min(y0,y1,y2)))),int(min(H_-1,math.ceil(max(y0,y1,y2))))
                    if bx1<bx0 or by1<by0: continue
                    gy,gx=np.mgrid[by0:by1+1,bx0:bx1+1].astype(np.float32); gx+=0.5; gy+=0.5
                    den=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2)
                    if abs(den)<1e-9: continue
                    w0=((y1-y2)*(gx-x2)+(x2-x1)*(gy-y2))/den; w1=((y2-y0)*(gx-x2)+(x0-x2)*(gy-y2))/den; w2=1-w0-w1
                    ins=(w0>=-0.03)&(w1>=-0.03)&(w2>=-0.03)
                    if not ins.any(): continue
                    X=w0*P0[0]+w1*P1[0]+w2*P2[0]; Z=w0*P0[2]+w1*P1[2]+w2*P2[2]
                    mm=emask(X,Z)*ins
                    if mm.max()<=0.001: continue
                    blk=pa[by0:by1+1,bx0:bx1+1,:3]; pa[by0:by1+1,bx0:bx1+1,:3]=blk*(1-mm[...,None])+fill[None,None,:]*mm[...,None]; npx+=int((mm>0.01).sum())
            vm=dmin
            img_.pixels.foreach_set(pa.ravel()); img_.update(); img_.pack()
            HF['B_inpaint']={'fill':fill.tolist(),'ring_texels':int(ok_.sum()),'polys':npoly,'px':npx,'front_verts':nfr0,'strand_excluded':nst,'lock_pts':0 if LK_ is None else int(len(LK_))}; log('eye inpaint',HF['B_inpaint'])
        except Exception as e:
            import traceback; log('INPAINT ERR',repr(e),traceback.format_exc()[-800:])
    # ---------- v3.4 crisp hand-painted eyes for the Meshy face: a thin decal that follows the face skin, painted here (sclera, her Doe gray iris,
    # pupil, limbal ring, sharp winged upper lash line, lower lash line, catchlight); the Meshy texture's soft eyes sit underneath
    if MEYE and P.get('EYE_DECAL',True):
        try:
            TW,TH_=(2048,512) if P.get('DECAL_V35') else (1024,256); ET=IN+'/ZinPia_Doe Eyes (Sunny Head)/'+P.get('EYE_TEX','doe 1.png'); iris_img=None
            if os.path.exists(ET):
                _ii=bpy.data.images.load(ET); iw,ih=_ii.size; ia=np.empty(iw*ih*4,np.float32); _ii.pixels.foreach_get(ia); iris_img=ia.reshape(ih,iw,4)
                al=iris_img[:,:,3]>0.5; ys_,xs_=np.nonzero(al)
                if len(xs_): icx,icy,irr=xs_.mean(),ys_.mean(),max(xs_.max()-xs_.min(),ys_.max()-ys_.min())/2
                else: icx,icy,irr=iw/2,ih/2,iw/2
            tex=np.zeros((TH_,TW,4),np.float32)
            yy,xx=np.mgrid[0:TH_,0:TW].astype(np.float32)
            EH=P.get('EYE_OPEN',0.42); TILT=P.get('EYE_TILT',0.10); IR=P.get('IRIS_R',0.40); MARG=P.get('EYE_MARG',1.30)
            if P.get('DECAL_V35'): tex=eye_tex_v35(TW,TH_,P,iris_img)
            for half,outer in (() if P.get('DECAL_V35') else ((0,-1),(1,1))):
                u=((xx-(half*512+256))/256.0)*MARG*outer   # u: -1 inner corner .. +1 outer corner
                v=((yy-128)/128.0)*MARG*0.5/1.0            # v up = positive (image row 0 = v<0? rows go top->bottom in Blender pixels: row 0 = bottom)
                v=-v if False else v
                c=np.clip(1-u*u,0,1)
                up=EH*np.power(c,0.62)+TILT*(u+1)/2*0.25; lo=-EH*0.55*np.power(c,1.05)+TILT*(u+1)/2*0.12
                inside=(v<up)&(v>lo)&(np.abs(u)<1)
                # sclera with a soft shadow under the upper lid and toward the corners
                sh=np.clip((up-v)/0.18,0,1); cs=np.clip(1-np.abs(u)**4,0,1)
                scl=np.stack([0.88-0.30*(1-sh),0.86-0.30*(1-sh),0.87-0.26*(1-sh)],-1)*(0.85+0.15*cs)[...,None]
                col=scl.copy()
                # iris centred slightly above mid, clipped by the lids
                icv=EH*0.12; du=u-P.get('IRIS_DX',-0.05); dv=v-icv; rr=np.sqrt(du*du+dv*dv)/IR
                if iris_img is not None:
                    sx=np.clip(icx+du/IR*irr,0,iw-1).astype(int); sy=np.clip(icy+dv/IR*irr,0,ih-1).astype(int)
                    ic=iris_img[sy,sx,:3]
                else:
                    ic=np.stack([0.42+0*rr,0.47+0*rr,0.52+0*rr],-1)
                ic=ic*np.clip(1.15-0.35*rr,0.6,1.1)[...,None]
                ring=np.clip((rr-0.86)/0.14,0,1); ic=ic*(1-0.75*ring[...,None])
                pup=rr<P.get('PUPIL',0.36); ic[pup]=(0.015,0.015,0.018)
                isin=(rr<1.0)&inside
                # anti-aliased iris edge
                ae=np.clip((1.0-rr)*IR*256/MARG/1.5,0,1)[...,None]
                col=np.where(isin[...,None],ic*ae+scl*(1-ae),col)
                # lid shadow on the iris top
                col=col*(1-0.45*np.clip(1-(up-v)/0.10,0,1)*inside)[...,None]
                # catchlight (key light comes from image-left in both eyes)
                cl=((u*outer- P.get('IRIS_DX',-0.05)*outer+0.16*outer*outer*0 -(-0.17))**2+(v-icv-0.13)**2)<(0.075**2)
                cl=(((xx-(half*512+256))/256.0*MARG - (P.get('IRIS_DX',-0.05)*outer) + 0.16)**2+(v-icv-0.12)**2)<(0.07**2)
                col=np.where((cl&inside)[...,None],np.array([0.97,0.97,0.98]),col)
                # sharp upper lash line: thick at the outer half, with a wing past the outer corner
                LT=P.get('LASH_T',0.06); th=LT*(0.55+0.9*np.clip((u+0.2)/1.2,0,1))
                ul=(v>=up-0.012)&(v<up+th)&(u>-1.02)&(u<1.0)
                wing=(u>=0.92)&(u<1.0+P.get('WING',0.22))&(np.abs(v-(EH*(1-0.92**2)**0.62+TILT*0.96*0.25+0.5*LT+(u-0.92)*P.get('WING_UP',0.55)))<th*np.clip(1-(u-0.92)/(P.get('WING',0.22)+0.08),0,1)*0.9)
                ll=(v<=lo+0.006)&(v>lo-P.get('LOWLASH_T',0.022))&(np.abs(u)<0.95)
                lash=ul|wing; col=np.where(lash[...,None],np.array([0.018,0.016,0.02]),col); col=np.where((ll&~lash)[...,None],np.array([0.20,0.17,0.17]),col)
                a=(inside|lash|ll).astype(np.float32)
                sl=slice(half*512,half*512+512); tex[:,sl,:3]=col[:,sl]; tex[:,sl,3]=a[:,sl]
            # soften the alpha edge by 1 px
            if P.get('DECAL_V35'): pass
            else: a=tex[:,:,3]; a2=(a+np.roll(a,1,0)+np.roll(a,-1,0)+np.roll(a,1,1)+np.roll(a,-1,1))/5; tex[:,:,3]=np.maximum(a*0.6,a2)
            dimg=bpy.data.images.new('eye_decal',TW,TH_,alpha=True); dimg.pixels.foreach_set(tex.ravel()); dimg.update(); dimg.pack()
            try:
                os.makedirs(OUT+'/tex',exist_ok=True); dimg.filepath_raw=OUT+'/tex/eye_decal.png'; dimg.file_format='PNG'; dimg.save(); dimg.pack()
            except Exception as e3: log('decal save',e3)
            _bv3,_V3=mh_bvh(); ipd=MEYE['ipd']; ew=MEYE.get('ew') or ipd*P.get('EYE_W',0.56); eh=ew*0.5*MARG; rl=MEYE.get('roll',0.0)*P.get('ROLL_K',1.0)
            bmD=bmesh.new(); uvD=bmD.loops.layers.uv.new('UVMap'); NXd,NZd=P.get('DEC_NX',26),P.get('DEC_NZ',12)
            for half,sx_ in ((0,-1),(1,1)):
                exx,ezz=MEYE['eyes'][half] if MEYE.get('eyes') else (MEYE['cx']+sx_*ipd/2,MEYE['z'])
                ezz+=P.get('EYE_ZOFF',0.0)
                g=[[None]*(NXd+1) for _ in range(NZd+1)]
                for iz in range(NZd+1):
                    for ix in range(NXd+1):
                        lu=(ix/NXd-0.5)*ew*MARG; lv=(iz/NZd-0.5)*eh
                        x=exx+lu*math.cos(rl)-lv*math.sin(rl); z=ezz+lu*math.sin(rl)+lv*math.cos(rl)
                        h=_bv3.ray_cast(Vector((x,float(b_n['cy']),z)),Vector((0,-1,0)),0.25)
                        if h[0] is None: continue
                        g[iz][ix]=bmD.verts.new(h[0]+Vector((0,-P.get('DECAL_OFF',0.0006),0)))
                for iz in range(NZd):
                    for ix in range(NXd):
                        q=(g[iz][ix],g[iz][ix+1],g[iz+1][ix+1],g[iz+1][ix])
                        if any(v_ is None for v_ in q): continue
                        f_=bmD.faces.new(q)
                        for li,(a_,b_) in zip(f_.loops,((ix,iz),(ix+1,iz),(ix+1,iz+1),(ix,iz+1))):
                            li[uvD].uv=(half*0.5+0.5*a_/NXd,b_/NZd)
            dm,dnt,db=newmat('EyeDecal'); dt_=dnt.nodes.new('ShaderNodeTexImage'); dt_.image=dimg; dt_.interpolation='Cubic'
            dnt.links.new(dt_.outputs[0],db.inputs['Base Color']); dnt.links.new(dt_.outputs[1],db.inputs['Alpha'])
            db.inputs['Roughness'].default_value=P.get('DEC_ROUGH',0.12); db.inputs['Coat Weight'].default_value=P.get('DEC_COAT',0.8); db.inputs['Coat Roughness'].default_value=0.03
            if P.get('DEC_MIX',False):
                # v3.5 r3: explicit alpha mix (transparent where alpha=0, so no coat sheen/AO veil over the skin around the eyes)
                _out=[n for n in dnt.nodes if n.type=='OUTPUT_MATERIAL'][0]; _tr=dnt.nodes.new('ShaderNodeBsdfTransparent'); _mx=dnt.nodes.new('ShaderNodeMixShader')
                for l_ in list(dnt.links):
                    if l_.to_node==_out: dnt.links.remove(l_)
                dnt.links.new(dt_.outputs[1],_mx.inputs[0]); dnt.links.new(_tr.outputs[0],_mx.inputs[1]); dnt.links.new(db.outputs[0],_mx.inputs[2]); dnt.links.new(_mx.outputs[0],_out.inputs[0])
            try: dm.blend_method='HASHED'
            except Exception: pass
            DEC=add_mesh('EyeDecal',bmD,dm,'Head')
            if P.get('DEC_MIX',False):
                try: DEC.visible_shadow=False; DEC.visible_diffuse=False; DEC.visible_glossy=False; DEC.visible_transmission=False; DEC.visible_volume_scatter=False
                except Exception as e: log('decal vis',e)
            HF['B_eye_decal']={'tris':tris(DEC),'eye_w':ew,'ipd':ipd,'z':MEYE['z']}; log('eye decal',HF['B_eye_decal'])
        except Exception as e:
            import traceback; log('DECAL ERR',repr(e),traceback.format_exc()[-800:])
    KEEP_HAIR=(VARIANT=='C')
    for o in ((FH,globals().get('SCALP')) if KEEP_HAIR else (FH,UM,BUN,CLIP,CRAN,globals().get('SCALP'))):
        if o is not None and o.name in bpy.data.objects: bpy.data.objects.remove(o)
    FH=MH
    # Meshy skin tone -> our body's, same skin shader; sharpen its soft texture (unsharp mask)
    try:
        mmat=[sl.material for sl in MH.material_slots if sl.material and sl.material.use_nodes][0]
        _a0=None
        if img_ is not None:
            _a0=np.empty(img_.size[0]*img_.size[1]*4,dtype=np.float32); img_.pixels.foreach_get(_a0); _a0=_a0.reshape(img_.size[1],img_.size[0],4)
        if img_ is not None and P.get('MB_SHARPEN',1.2):
            W_,H_=img_.size; a=np.empty(W_*H_*4,dtype=np.float32); img_.pixels.foreach_get(a); a=a.reshape(H_,W_,4)
            k=np.array([1,4,6,4,1],dtype=np.float32); k/=k.sum(); bl=a[:,:,:3].copy()
            for ax in (0,1):
                bl=sum(np.roll(bl,s-2,axis=ax)*k[s] for s in range(5))
            bl2=bl
            for ax in (0,1):
                bl2=sum(np.roll(bl2,s-2,axis=ax)*k[s] for s in range(5))
            a[:,:,:3]=np.clip(a[:,:,:3]+P.get('MB_SHARPEN',1.2)*(a[:,:,:3]-bl2),0,1)
            img_.pixels.foreach_set(a.ravel()); img_.update(); img_.pack(); log('meshy texture sharpened',W_,H_)
        # v3.3 crisp face: learned 4x super-resolution of the Meshy FACE area of its texture (eyes/brows/lips), blended back by a UV mask
        if _a0 is not None and P.get('MB_SR',True):
            try:
                import subprocess, tempfile
                W_,H_=img_.size; me_=MH.data; Mw=np.array(MH.matrix_world); Ht_=HF['target_head_total']
                pc=np.array([Mw[:3,:3]@np.array(p.center)+Mw[:3,3] for p in me_.polygons]); pn=np.array([Mw[:3,:3]@np.array(p.normal) for p in me_.polygons])
                zlo=zc_-0.012; zhi=zc_+P.get('MB_SR_TOP',0.66)*Ht_
                fz=(pc[:,2]>zlo)&(pc[:,2]<zhi)&(np.abs(pc[:,0]-b_n['cx'])<P.get('MB_SR_HW',0.075))
                nose_=pc[fz&(np.abs(pc[:,0]-b_n['cx'])<0.02)]; fy=float(nose_[:,1].min()) if len(nose_) else float(pc[fz][:,1].min())
                sel_=fz&(pn[:,1]<-0.15)&(pc[:,1]<fy+P.get('MB_SR_DEPTH',0.07))
                uvd=me_.uv_layers.active.data; tri_=[]
                for pi_ in np.where(sel_)[0]:
                    p=me_.polygons[int(pi_)]; uvs=[(uvd[li].uv[0]%1*W_,uvd[li].uv[1]%1*H_) for li in p.loop_indices]
                    for t_ in range(1,len(uvs)-1): tri_.append([uvs[0],uvs[t_],uvs[t_+1]])
                tri_=np.array(tri_,dtype=np.float32)
                if len(tri_):
                    pad=24; x0=max(0,int(tri_[:,:,0].min())-pad); y0=max(0,int(tri_[:,:,1].min())-pad); x1=min(W_,int(tri_[:,:,0].max())+pad); y1=min(H_,int(tri_[:,:,1].max())+pad)
                    td=tempfile.mkdtemp(); np.save(td+'/crop.npy',_a0[y0:y1,x0:x1]); tri_[:,:,0]-=x0; tri_[:,:,1]-=y0; np.save(td+'/tris.npy',tri_)
                    env_={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':os.environ.get('HOME','/home/runner'),'LANG':'C.UTF-8'}
                    srp=os.path.join(os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else 'avatar-v3','sr.py')
                    if not os.path.exists(srp): srp='avatar-v3/sr.py'
                    import shutil as _sh; _sh.copy(srp,td+'/sr_run.py'); srp=td+'/sr_run.py'  # run outside avatar-v3/ (its inspect.py shadows the stdlib)
                    r_=subprocess.run(['/usr/bin/python3',srp,td,str(P.get('MB_SR_F',3)),P.get('MB_SR_MODEL','/tmp/sr/realesr-general-x4v3.pth'),str(P.get('MB_SR_MIX',1.0))],capture_output=True,text=True,timeout=600,env=env_)
                    log('SR',r_.returncode,(r_.stdout+r_.stderr)[-900:])
                    if os.path.exists(td+'/out.npy'):
                        o_=np.load(td+'/out.npy'); cur=np.empty(W_*H_*4,dtype=np.float32); img_.pixels.foreach_get(cur); cur=cur.reshape(H_,W_,4)
                        m_=o_[:,:,4:5]; cur[y0:y1,x0:x1,:3]=cur[y0:y1,x0:x1,:3]*(1-m_)+o_[:,:,:3]*m_
                        img_.pixels.foreach_set(cur.ravel()); img_.update(); img_.pack()
                        try:
                            import shutil; os.makedirs(OUT+'/tex',exist_ok=True); shutil.copy(td+'/before.jpg',OUT+'/tex/meshy_face_before.jpg'); shutil.copy(td+'/after.jpg',OUT+'/tex/meshy_face_after.jpg')
                        except Exception as e2: log('SR copy',e2)
                        HF['B_sr']={'tris':int(len(tri_)),'box':[x0,y0,x1,y1],'tex':[W_,H_]}; log('meshy face SR applied',HF['B_sr'])
            except Exception as e: log('SRERR',repr(e))
        sk_m=np.median(cv[skinv],0) if 'cv' in dir() and skinv.sum()>50 else None
        mt=(1,1,1)
        if sk_m is not None and BODY_MED is not None: mt=tuple(float(min(1.25,max(0.8,BODY_MED[k_]/max(sk_m[k_],1e-3))))*PINK[k_] for k_ in range(3))
        _tm=P.get('MB_TONE_MUL',[1,1,1]); mt=tuple(float(mt[k_]*_tm[k_]) for k_ in range(3))
        nt_=mmat.node_tree; bb_=[n for n in nt_.nodes if n.type=='BSDF_PRINCIPLED'][0]; lk_=[l for l in nt_.links if l.to_socket==bb_.inputs['Base Color']]
        if lk_:
            s_=lk_[0].from_socket; nt_.links.remove(lk_[0]); mx_=nt_.nodes.new('ShaderNodeMix'); mx_.data_type='RGBA'; mx_.blend_type='MULTIPLY'; mx_.inputs['Factor'].default_value=1.0; mx_.inputs['B'].default_value=(*mt,1)
            nt_.links.new(s_,mx_.inputs['A']); nt_.links.new(mx_.outputs['Result'],bb_.inputs['Base Color'])
        skin_detail(mmat); HF['B_tone']={'meshy_skin':None if sk_m is None else sk_m.tolist(),'tint':mt}; log('meshy tone',HF['B_tone'])
        if P.get('MB_GLOSS_MASK',True):
            # v3.4: the dewy coat only on SKIN texels (warm), the Meshy hair stays matte-satin
            tn_=[n for n in nt_.nodes if n.type=='TEX_IMAGE' and n.image is img_]
            if tn_:
                spc=nt_.nodes.new('ShaderNodeSeparateColor'); nt_.links.new(tn_[0].outputs[0],spc.inputs[0])
                sb_=nt_.nodes.new('ShaderNodeMath'); sb_.operation='SUBTRACT'; nt_.links.new(spc.outputs[0],sb_.inputs[0]); nt_.links.new(spc.outputs[2],sb_.inputs[1])
                mr_=nt_.nodes.new('ShaderNodeMapRange'); mr_.inputs[1].default_value=0.015; mr_.inputs[2].default_value=0.07; nt_.links.new(sb_.outputs[0],mr_.inputs[0])
                cw_=nt_.nodes.new('ShaderNodeMath'); cw_.operation='MULTIPLY'; cw_.inputs[1].default_value=bb_.inputs['Coat Weight'].default_value*P.get('MB_COAT_K',1.0); nt_.links.new(mr_.outputs[0],cw_.inputs[0]); nt_.links.new(cw_.outputs[0],bb_.inputs['Coat Weight'])
                rg_=nt_.nodes.new('ShaderNodeMapRange'); rg_.inputs[3].default_value=P.get('MB_HAIR_ROUGH',0.55); rg_.inputs[4].default_value=bb_.inputs['Roughness'].default_value; nt_.links.new(mr_.outputs[0],rg_.inputs[0]); nt_.links.new(rg_.outputs[0],bb_.inputs['Roughness'])
                log('meshy gloss masked to skin')
    except Exception as e: log('MBTONEERR',e)
    if KEEP_HAIR:
        # our shoulder-length cards over the Meshy head: keep them just outside its surface, fringe squashed above its brows
        from mathutils.bvhtree import BVHTree as _BVH
        mb_=_BVH.FromObject(MH,bpy.context.evaluated_depsgraph_get()); mw=UM.matrix_world; mwi=mw.inverted(); pu=0
        for v in UM.data.vertices:
            p=mw@v.co; h=mb_.find_nearest(p)
            if h and h[0] is not None:
                n_=h[1].normalized()
                if (p-h[0]).length<0.03 and (p-h[0]).dot(n_)<P.get('MB_HAIR_OFF',0.004): v.co=mwi@(h[0]+n_*P.get('MB_HAIR_OFF',0.004)); pu+=1
        UM.data.update(); log('B hair pushed outside Meshy head',pu)
        fringe(UM,'B')
        if CRAN is not None and P.get('MC_CRAN_TUCK',True):
            # v3.5: the cranium never pokes through the Meshy face: any cranium vertex in front of the face surface goes just behind it
            cw_=CRAN.matrix_world; cwi=cw_.inverted(); tk=0
            for v in CRAN.data.vertices:
                p=cw_@v.co; fwd=mb_.ray_cast(p,Vector((0,-1,0)),0.3); back=mb_.ray_cast(p,Vector((0,1,0)),0.3)
                if fwd[0] is None and back[0] is not None and p.y<b_n['cy']: v.co=cwi@Vector((p.x,back[0].y+P.get('MC_CRAN_GAP',0.005),p.z)); tk+=1
            CRAN.data.update(); log('C cranium tucked behind the Meshy face',tk)
    else: UM=MH
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
# v3.2 relaxed arms + natural hands: slight elbow bend forward, fingers curled toward the palm, thumb in
def wrot(name,deg,axis):
    if not deg or name not in B.pose.bones: return
    pb=B.pose.bones[name]; h=pb.head.copy()
    pb.matrix=Matrix.Translation(h)@Matrix.Rotation(math.radians(deg),4,axis)@Matrix.Translation(-h)@pb.matrix; bpy.context.view_layer.update()
for sd,sgn in (('L',1),('R',-1)):
    wrot(('Left' if sd=='L' else 'Right')+' elbow',P.get('ELBOW_BEND',-12),'X')
    if P.get('WRIST_BEND',0): wrot(('Left' if sd=='L' else 'Right')+' wrist',sgn*P['WRIST_BEND'],'Y')  # v3.5 relaxed wrist (hand flexes toward the thigh, not a straight paddle)
    if P.get('WRIST_TWIST',0): wrot(('Left' if sd=='L' else 'Right')+' wrist',sgn*P['WRIST_TWIST'],'Z')
    for f_ in ('IndexFinger','MiddleFinger','RingFinger','LittleFinger'):
        for j,a_ in ((1,P.get('CURL1',14)),(2,P.get('CURL2',24)),(3,P.get('CURL3',16))):
            wrot(f'{f_}{j}_{sd}',sgn*a_*(1.0+0.15*('Ring' in f_ or 'Little' in f_)),'Y')
    for j in (1,2): wrot(f'Thumb{j}_{sd}',sgn*P.get('THUMB_CURL',10),'Y')
# v3.3 legs closer together like her sheet (knees nearly touch): adduct each thigh about its hip, feet back to flat
LGI=P.get('LEG_IN',0.0)
if LGI:
    KO=P.get('KNEE_OUT',0.0)
    for nm_,sgn in (('Left leg',1),('Right leg',-1)): wrot(nm_,sgn*LGI,'Y')
    for nm_,sgn in (('Left knee',1),('Right knee',-1)): wrot(nm_,-sgn*KO,'Y')
    for sd_,sgn in (('Left',1),('Right',-1)):
        for nm_ in (sd_+' ankle',sd_+' foot'):
            if nm_ in B.pose.bones: wrot(nm_,-sgn*(LGI-KO),'Y'); break
    log('legs adducted',LGI)

bpy.ops.object.mode_set(mode='OBJECT')
if P['RENDER']:
    sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=P['SAMPLES']; sc.cycles.use_denoising=True
    sc.render.film_transparent=True; sc.render.image_settings.file_format='PNG'; sc.render.image_settings.color_mode='RGBA'
    sc.view_settings.view_transform='AgX'; sc.view_settings.look='AgX - Medium High Contrast'; sc.view_settings.exposure=P.get('EXPOSURE',-0.45)
    w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; bg=w.node_tree.nodes['Background']; bg.inputs[0].default_value=(0.06,0.06,0.065,1); bg.inputs[1].default_value=P.get('WORLD_E',1.0)
    if P.get('GROUND',True):
        bpy.ops.mesh.primitive_plane_add(size=6,location=(0,0,0)); gp=bpy.context.active_object; gp.is_shadow_catcher=True; gp.name='ShadowCatcher'
    def area(name,loc,energy,size,col=(1,1,1)):
        L=bpy.data.lights.new(name,'AREA'); L.energy=energy; L.size=size; L.color=col; o=bpy.data.objects.new(name,L); sc.collection.objects.link(o); o.location=loc
        o.rotation_euler=(Vector((0,0,0.75))-Vector(loc)).to_track_quat('-Z','Y').to_euler(); return o
    area('key',(-1.6,-2.2,2.0),P.get('KEY_E',190),P.get('KEY_SIZE',1.6),(1,0.93,0.90)); area('fill',(1.8,-1.8,1.2),P.get('FILL_E',70),2.0,tuple(P.get('FILL_COL',(0.95,0.93,1)))); area('rim',(0.4,2.4,2.0),P.get('RIM_E',220),1.4,tuple(P.get('RIM_COL',(1,1,1)))); area('rim2',(-1.2,2.0,1.4),P.get('RIM2_E',120),1.2,tuple(P.get('RIM_COL',(1,1,1))))
    if P.get('SPEC_E',90): area('spec',(2.2,-1.0,1.6),P.get('SPEC_E',90),0.5,(1,0.96,0.95))
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
    w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; bg=w.node_tree.nodes['Background']; bg.inputs[0].default_value=(0.05,0.05,0.052,1); bg.inputs[1].default_value=P.get('WORLD_E',1.0)
    if P.get('GROUND',True):
        bpy.ops.mesh.primitive_plane_add(size=6,location=(0,0,0)); gp=bpy.context.active_object; gp.name='Floor'; fm=bpy.data.materials.new('Floor'); fm.use_nodes=True; fb=fm.node_tree.nodes['Principled BSDF']; fb.inputs['Base Color'].default_value=(0.05,0.05,0.052,1); fb.inputs['Roughness'].default_value=0.9; gp.data.materials.append(fm)
    dg=bpy.context.evaluated_depsgraph_get(); pts=[]
    for o in meshes:
        e=o.evaluated_get(dg); vv=e.data.vertices; pts+=[e.matrix_world@vv[i].co for i in range(0,len(vv),7)]
    mn=Vector([min(p[i] for p in pts) for i in range(3)]); mx=Vector([max(p[i] for p in pts) for i in range(3)]); ce=(mn+mx)/2; Hh=(mx.z-mn.z)*1.08
    rig=bpy.data.objects.new('ttrig',None); sc.collection.objects.link(rig); rig.location=(ce.x,ce.y,0)
    def area(name,loc,energy,size,col=(1,1,1)):
        L=bpy.data.lights.new(name,'AREA'); L.energy=energy; L.size=size; L.color=col; o=bpy.data.objects.new(name,L); sc.collection.objects.link(o); o.location=loc
        o.rotation_euler=(Vector((0,0,0.75))-Vector(loc)).to_track_quat('-Z','Y').to_euler(); o.parent=rig; return o
    area('key',(-1.6,-2.2,2.0),P.get('KEY_E',190),P.get('KEY_SIZE',1.6),(1,0.93,0.90)); area('fill',(1.8,-1.8,1.2),P.get('FILL_E',70),2.0,tuple(P.get('FILL_COL',(0.95,0.93,1)))); area('rim',(0.4,2.4,2.0),P.get('RIM_E',220),1.4,tuple(P.get('RIM_COL',(1,1,1)))); area('rim2',(-1.2,2.0,1.4),P.get('RIM2_E',120),1.2,tuple(P.get('RIM_COL',(1,1,1))))
    if P.get('SPEC_E',90): area('spec',(2.2,-1.0,1.6),P.get('SPEC_E',90),0.5,(1,0.96,0.95))
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
