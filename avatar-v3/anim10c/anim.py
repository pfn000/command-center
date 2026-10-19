
# Jena v3.7 run-10c ANIMATION clips (Saidie 9:47 PM Oct 18): talk/blink/expressions, dance retargeted from her TikTok ref, with bone-track export.
# Renders from the SAVED run-10c .blend as built (no model edits). Face uses her existing shape keys only.
import bpy, os, sys, math, json, time
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from bpy_extras.object_utils import world_to_camera_view as w2c
a=sys.argv[sys.argv.index('--')+1:]; BLEND,OUT,DATA=a[0],a[1],a[2]
E=os.environ; MODE=E['ANIM']; SH=int(E.get('SHARD','0')); SHN=int(E.get('SHARDS','1')); SAMP=int(E.get('SAMPLES','8'))
RW,RH=[int(x) for x in E.get('RES','720x1280').split('x')]
def log(*x): print('[anim]',*x,flush=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
sc=bpy.context.scene; B=bpy.data.objects['Armature']; PB=B.pose.bones
MESHES=[o for o in sc.objects if o.type=='MESH' and not o.hide_render]
FH=bpy.data.objects['Female Head']; BODY=bpy.data.objects['Body']; HAIR=bpy.data.objects.get('Hair'); SHIRT=bpy.data.objects.get('Shirt')
log('meshes',[o.name for o in MESHES],'B.mw identity',B.matrix_world==Matrix.Identity(4))
BASE={pb.name:pb.matrix_basis.copy() for pb in PB}
KB=FH.data.shape_keys.key_blocks; KBASE={k.name:k.value for k in KB}
log('base nonzero keys',{k:round(v,3) for k,v in KBASE.items() if v>1e-4})
def upd(): bpy.context.view_layer.update()
def meshes_eval(on):
    for o in MESHES: o.hide_viewport=not on
    upd()
def rest():
    for pb in PB: pb.matrix_basis=BASE[pb.name]
    upd()
def wrot_v(name,deg,axis):
    if abs(deg)<1e-4 or name not in PB: return
    pb=PB[name]; h=pb.head.copy(); pb.matrix=Matrix.Translation(h)@Matrix.Rotation(math.radians(deg),4,Vector(axis).normalized())@Matrix.Translation(-h)@pb.matrix; upd()
def wrot(name,deg,ax): wrot_v(name,deg,{'X':(1,0,0),'Y':(0,1,0),'Z':(0,0,1)}[ax])
def qrot(name,q,frac=1.0,cap=180.0):
    ang=math.degrees(q.angle)
    if ang<1e-3: return
    wrot_v(name,min(ang*frac,cap),q.axis)
def align(name,target,cap=180.0,frac=1.0):
    if name not in PB or target.length<1e-6: return
    pb=PB[name]; d0=(pb.tail-pb.head)
    if d0.length<1e-7: return
    qrot(name,d0.normalized().rotation_difference(target.normalized()),frac,cap)
P_=dict(ARM_DOWN=float(E.get('ARM_DOWN','76')),SHOULDER_DOWN=10,ELBOW_BEND=-14,WRIST_BEND=8,RELAX=True)   # arms down at her sides (~12-14 deg from body); 10c build used 40 (shirt proof angle)
FING4=('IndexFinger','MiddleFinger','RingFinger','LittleFinger')
def _lx(n): return PB[n].matrix.to_3x3().col[0].normalized()
def _finger_signs():
    S={}; rest()
    for sd in 'LR':
        w=PB[('Left' if sd=='L' else 'Right')+' wrist'].head.copy()
        for f_ in FING4+('Thumb',):
            n=f'{f_}1_{sd}' if f_!='Thumb' else f'Thumb1_{sd}'
            if n not in PB: continue
            tipn=f'{f_}3_{sd}' if f_!='Thumb' else f'Thumb2_{sd}'
            ref=w if f_!='Thumb' else PB[f'IndexFinger1_{sd}'].head.copy()
            d0=(PB[tipn].tail-ref).length; wrot_v(n,30,_lx(n)); d1=(PB[tipn].tail-ref).length; rest(); S[(sd,f_)]=1 if d1<d0 else -1
    return S
FSIGN=None
def fingers_relaxed(scale=1.0):
    # natural relaxed curl, each phalanx about its OWN bend axis (local X) toward the palm
    global FSIGN
    for sd in 'LR':
        for f_ in FING4:
            for j,a_ in ((1,14),(2,22),(3,14)): wrot_v(f'{f_}{j}_{sd}',FSIGN[(sd,f_)]*a_*scale,_lx(f'{f_}{j}_{sd}')) if f'{f_}{j}_{sd}' in PB else None
        for j in (1,2): wrot_v(f'Thumb{j}_{sd}',FSIGN[(sd,'Thumb')]*10*scale,_lx(f'Thumb{j}_{sd}')) if f'Thumb{j}_{sd}' in PB else None
def pose_relaxed_compute():
    rest(); SHD=P_['SHOULDER_DOWN']
    for name,sgn,deg in (('Left shoulder',1,SHD),('Right shoulder',-1,SHD),('Left arm',1,P_['ARM_DOWN']-SHD),('Right arm',-1,P_['ARM_DOWN']-SHD)): wrot(name,sgn*deg,'Y')
    for sd,sgn in (('Left',1),('Right',-1)):
        wrot(sd+' elbow',P_['ELBOW_BEND'],'X'); wrot(sd+' wrist',sgn*P_['WRIST_BEND'],'Y')
    fingers_relaxed()
    if P_['RELAX']:
        wrot('Right leg',-6,'X'); wrot('Right knee',14,'X')
        for nm_ in ('Right ankle','Right foot'):
            if nm_ in PB: wrot(nm_,-6,'X'); break
    return {pb.name:pb.matrix_basis.copy() for pb in PB}
meshes_eval(False)
FSIGN=_finger_signs(); log('finger signs',FSIGN)
RELAXED=pose_relaxed_compute()
def relaxed():
    for pb in PB: pb.matrix_basis=RELAXED[pb.name]
    upd()
# ---------- hair springs (same model as the run-10b tests: k=70/s^2, c=5/s; back hair capped 15 deg, bangs 14, others 30)
def _hair_bones(): return [b.name for b in PB if ('hair' in b.name.lower() or b.name.startswith('Bangs') or b.name.startswith('piggy') or b.name.startswith('Blw_')) and b.name!='Hair Root']
def _depth(n):
    d=0; b=PB[n]
    while b.parent: d+=1; b=b.parent
    return d
def phys_bones():
    L=[]
    for n in _hair_bones():
        lim=14.0 if n.startswith('Bangs') else (15.0 if n.startswith('Back hair') else 30.0); L.append((n,70.0,5.0,lim))
    return sorted(L,key=lambda j:_depth(j[0]))
def spring_sim(base_fn,NF,fps,bones,sub=4):
    T={}
    for f in range(NF):
        base_fn(f)
        for b,_,_,_ in bones: T.setdefault(b,[]).append(np.array(tuple(PB[b].tail)))
    out={}; dt=1.0/fps; h=dt/sub
    for b,k,cdm,lim in bones:
        tg=np.array(T[b]); x=tg[0].copy(); v=np.zeros(3); res=[]
        for f in range(NF):
            for s in range(sub):
                tt=tg[max(f-1,0)]+(tg[f]-tg[max(f-1,0)])*((s+1)/sub) if f>0 else tg[0]
                a_=k*(tt-x)-cdm*v; v=v+a_*h; x=x+v*h
            res.append(x.copy())
        out[b]=(np.array(res),lim)
    return out,bones
def apply_springs(SIM,f):
    OUTA,bones=SIM; ang={}
    for b,k,cdm,lim in bones:
        pb=PB[b]; hd=pb.head.copy(); tl=pb.tail.copy(); x=Vector(tuple(OUTA[b][0][f])); d0=tl-hd; d1=x-hd
        if d0.length<1e-6 or d1.length<1e-6: continue
        q=d0.normalized().rotation_difference(d1.normalized()); an=min(math.degrees(q.angle),lim)
        if an>0.01: wrot_v(b,an,q.axis)
        ang[b]=an
    return ang
# ---------- camera / render
cam=sc.camera
def setcam(tgt,az,el,dist,lens):
    d=Vector((math.sin(math.radians(az))*math.cos(math.radians(el)),-math.cos(math.radians(az))*math.cos(math.radians(el)),math.sin(math.radians(el))))
    cam.location=tgt+d*dist; cam.rotation_euler=(tgt-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.lens=lens; cam.data.sensor_fit='VERTICAL'; cam.data.sensor_height=24; cam.data.clip_start=0.01; cam.data.clip_end=200; upd()
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=SAMP; sc.cycles.use_denoising=True
try: sc.cycles.denoiser='OPENIMAGEDENOISE'
except Exception as e: log('denoiser',e)
sc.render.use_persistent_data=True; sc.render.film_transparent=False
sc.render.resolution_x,sc.render.resolution_y=RW,RH; sc.render.resolution_percentage=100
sc.render.image_settings.file_format='JPEG'; sc.render.image_settings.quality=92
def render(path):
    meshes_eval(True); sc.render.filepath=path; bpy.ops.render.render(write_still=True)
def bbox(objs):
    dg=bpy.context.evaluated_depsgraph_get(); pts=[]
    for o in objs:
        e=o.evaluated_get(dg); vv=e.data.vertices; st=max(1,len(vv)//4000); mw=e.matrix_world; pts+=[mw@vv[i].co for i in range(0,len(vv),st)]
    mn=Vector([min(p[i] for p in pts) for i in range(3)]); mx=Vector([max(p[i] for p in pts) for i in range(3)]); return mn,mx
def proj_all():
    R={}
    for pb in PB:
        h=w2c(sc,cam,B.matrix_world@pb.head); t=w2c(sc,cam,B.matrix_world@pb.tail); R[pb.name]=[round(h.x,4),round(1-h.y,4),round(t.x,4),round(1-t.y,4)]
    return R
def proj_pts(pts): return [[round(w2c(sc,cam,Vector(p)).x,4),round(1-w2c(sc,cam,Vector(p)).y,4)] for p in pts]
def bones_world():
    return {pb.name:{'h':[round(x,4) for x in B.matrix_world@pb.head],'t':[round(x,4) for x in B.matrix_world@pb.tail],'q':[round(x,4) for x in pb.matrix.to_quaternion()]} for pb in PB}
# ---------- clipping checks on her evaluated meshes
def _cls():
    vg={g.index:g.name for g in BODY.vertex_groups}; anc={}
    def side(n):
        if n in anc: return anc[n]
        b=PB.get(n); r=None; seen=[]
        while b is not None:
            seen.append(b.name)
            if b.name in ('Left leg','Right leg'): r='LL' if b.name.startswith('Left') else 'RL'; break
            if b.name in ('Left elbow','Right elbow'): r='LA' if b.name.startswith('Left') else 'RA'; break
            if b.name in ('Left arm','Right arm'): r='UA'; break
            if b.name in ('Neck','Head','Left shoulder','Right shoulder'): r='X'; break
            if b.name in ('Spine','Chest','Hips'): r='T'; break
            b=b.parent
        anc[n]=r; return r
    lab=[]
    for v in BODY.data.vertices:
        best=None; w=0
        for g in v.groups:
            if g.weight>w and g.group in vg: w=g.weight; best=vg[g.group]
        lab.append(side(best) if best else None)
    polys={}
    for p in BODY.data.polygons:
        ls={lab[i] for i in p.vertices}
        if len(ls)==1: polys.setdefault(ls.pop(),[]).append(tuple(p.vertices))
    return polys
CLS=None; TB_polys=[tuple(p.vertices) for p in BODY.data.polygons]
def ev_co(o):
    dg=bpy.context.evaluated_depsgraph_get(); e=o.evaluated_get(dg); n=len(e.data.vertices); a_=np.empty(n*3,dtype=np.float32); e.data.vertices.foreach_get('co',a_); a_=a_.reshape(-1,3)
    M=np.array(e.matrix_world); return a_@M[:3,:3].T+M[:3,3]
def clip_flags():
    global CLS
    if CLS is None: CLS=_cls()
    co=ev_co(BODY); V=[Vector(tuple(x)) for x in co]; T={k:BVHTree.FromPolygons(V,ps) for k,ps in CLS.items() if k in ('LL','RL','LA','RA','T')}
    def ov(a_,b_):
        if a_ not in T or b_ not in T: return None
        pr=T[a_].overlap(T[b_]); pa,pb_=CLS[a_],CLS[b_]
        return sum(1 for i,j in pr if not (set(pa[i])&set(pb_[j])))
    f={'leg_vs_leg_tris':ov('LL','RL'),'Larm_vs_torso_tris':ov('LA','T'),'Rarm_vs_torso_tris':ov('RA','T'),'Larm_vs_legs_tris':(ov('LA','LL') or 0)+(ov('LA','RL') or 0),'Rarm_vs_legs_tris':(ov('RA','LL') or 0)+(ov('RA','RL') or 0)}
    if SHIRT is not None and not SHIRT.hide_render:
        TBq=BVHTree.FromPolygons(V,TB_polys); c3=0
        for p in ev_co(SHIRT)[::2]:
            loc,nr,idx,d=TBq.find_nearest(Vector(tuple(p)),0.03)
            if loc is not None and (Vector(tuple(p))-loc).dot(nr)<-0.003: c3+=1
        f['shirt_inside_body_gt3mm_x2']=c3
    return f
os.makedirs(OUT,exist_ok=True); info={'anim':MODE,'shard':SH,'shards':SHN,'res':[RW,RH],'samples':SAMP,'frames':{}}
def frames_of(NF):
    per=(NF+SHN-1)//SHN; return list(range(SH*per,min(NF,(SH+1)*per)))

def _torso_in(p,margin=0.0):
    a=PB['Hips'].head; b=PB['Neck'].head; ab=b-a; t=max(0.0,min(1.0,(p-a).dot(ab)/ab.length_squared)); c=a+ab*t
    M=PB['Chest'].matrix.to_3x3() if t>0.45 else PB['Spine'].matrix.to_3x3()
    X=M.col[0].normalized(); Z=ab.normalized(); Y=Z.cross(X).normalized(); X=Y.cross(Z)
    q=p-c; rl=(0.165 if t>0.45 else 0.135)+margin; rd=(0.15 if t>0.45 else 0.125)+margin
    return (q.dot(X)/rl)**2+(q.dot(Y)/rd)**2<1.0, X, Y
def arm_clear(sd):
    # keep elbow + wrist (and the hand) outside her torso volume: abduct the upper arm, then the forearm, in 4 deg steps
    sg=1 if sd=='Left' else -1
    def pts(): return [PB[sd+' elbow'].head.copy(),PB[sd+' wrist'].head.copy(),PB[sd+' wrist'].tail.copy()]
    for _ in range(12):
        ins=[_torso_in(p,0.035) for p in pts()]
        if not any(i[0] for i in ins[:1]): break
        fwd=ins[0][2]; wrot_v(sd+' arm',sg*4,-fwd if sg>0 else -fwd)
    for _ in range(14):
        ins=[_torso_in(p,0.035) for p in pts()[1:]]
        if not any(i[0] for i in ins): break
        # swing the forearm forward/outward, away from the body
        el=PB[sd+' elbow']; d=(el.tail-el.head).normalized(); out=(ins[0][1]*sg+ins[0][2]*-0.6).normalized(); ax=d.cross(out)
        if ax.length<1e-4: break
        wrot_v(sd+' elbow',5,ax)
# ======================= TALK =======================
if MODE=='talk':
    TL=json.load(open(DATA)); NF=TL['nf']; fps=TL['fps']
    def base(f):
        relaxed(); nod,tilt,turn=TL['head'][f]; br=math.sin(2*math.pi*f/fps/3.6)
        wrot('Chest',0.8*br,'X'); wrot('Neck',0.4*nod,'X'); wrot('Head',0.6*nod,'X'); wrot('Neck',0.4*tilt,'Y'); wrot('Head',0.6*tilt,'Y'); wrot('Head',turn,'Z')
    bones=phys_bones(); WARM=45; SIM=spring_sim(lambda f: base(max(f-WARM,0)),NF+WARM,fps,bones)
    meshes_eval(True); relaxed(); mnh,mxh=bbox([FH]); mna,mxa=bbox(MESHES); top=max(mxh.z,bbox([HAIR])[1].z if HAIR else mxh.z)
    hc=(mnh+mxh)/2; info['head_bbox']=[list(mnh),list(mxh)]
    face_h=(top-(mnh.z-0.05))*1.12; face_t=Vector((hc.x,hc.y,(top+(mnh.z-0.05))/2))
    mid_lo=float((B.matrix_world@PB['Hips'].head).z)+0.02; mid_h=(top-mid_lo)*1.08; mid_t=Vector((hc.x,hc.y,(top+mid_lo)/2))
    shots={'face':(face_t,0,2,face_h/(24/85),85),'mid':(mid_t,0,3,mid_h/(24/50),50)}
    def shot_of(f):
        for a_,b_,nm in TL['shots']:
            if a_<=f<b_: return nm
        return 'face'
    for f in frames_of(NF):
        t0=time.time(); meshes_eval(False); base(f); ang=apply_springs(SIM,f+WARM)
        for k in KB: k.value=KBASE[k.name]
        for k,arr in TL['keys'].items():
            if k in KB: KB[k].value=min(1.0,KBASE.get(k,0)+arr[f])
        upd(); nm=shot_of(f); setcam(*shots[nm]); render(OUT+f'/f{f:03d}.jpg')
        e={'shot':nm,'label':TL['labels'][f],'max_back_hair_deg':round(max([v for k_,v in ang.items() if k_.startswith('Back hair')] or [0]),1),
           'keys':{k:round(KB[k].value,3) for k in TL['keys'] if k in KB and KB[k].value>0.02},'s':round(time.time()-t0,1)}
        info['frames'][f]=e; log('frame',f,nm,e['label'],e['s'],'s')
# ======================= DANCE =======================
elif MODE=='dance':
    LM=json.load(open(DATA)); FR=LM['w']; NF=len(FR); fps=LM['fps']
    def mp2b(p): return Vector((p[0],p[2],-p[1]))
    ups=[];rts=[]
    for w in FR:
        P_l=[mp2b(p) for p in w]; ups.append(((P_l[11]+P_l[12])/2-(P_l[23]+P_l[24])/2).normalized()); rts.append((P_l[23]-P_l[24]).normalized())
    up=sum(ups,Vector()).normalized(); rt=sum(rts,Vector()); rt=(rt-up*rt.dot(up)).normalized(); fw=up.cross(rt)
    Mc=Matrix((rt,fw,up)).to_3x3()   # rows: maps source to her frame (rt->X, up->Z)
    info['source_level_correction_deg']=round(math.degrees(Mc.to_quaternion().angle),1)
    def L(w,i): return Mc@mp2b(w[i])
    def rest_rot(n): return PB[n].bone.matrix_local.to_3x3()
    def cur_rot(n): return PB[n].matrix.to_3x3()@rest_rot(n).inverted()
    def frame_rot(xv,zv):
        x=xv.normalized(); z=(zv-x*zv.dot(x)).normalized(); y=z.cross(x); return Matrix((x,y,z)).transposed()
    def set_world_rot(n,Rt,frac=1.0,cap=180.0):
        d=(Rt@cur_rot(n).inverted()).to_quaternion(); qrot(n,d,frac,cap)
    def pose_dance(f,offs=None):
        rest(); fingers_relaxed()
        w=FR[f]; G=lambda i: L(w,i)
        LS,RS,LH,RH=G(11),G(12),G(23),G(24); mh=(LH+RH)/2; ms=(LS+RS)/2; upt=(ms-mh)
        # pelvis: hip line + 40 % of the torso lean; spine/chest take the rest (+ shoulder twist)
        Rh=frame_rot(LH-RH,Vector((0,0,1)).lerp(upt.normalized(),0.4)); set_world_rot('Hips',Rh,cap=60)
        d0=(PB['Spine'].tail-PB['Spine'].head).normalized(); q=d0.rotation_difference(upt.normalized())
        qrot('Spine',q,0.5,40); qrot('Chest',q,0.5,40)
        sl=(LS-RS); hl=(LH-RH); n_=upt.normalized(); sl_=(sl-n_*sl.dot(n_)).normalized(); hl_=(hl-n_*hl.dot(n_)).normalized()
        tw=math.degrees(math.atan2(hl_.cross(sl_).dot(n_),hl_.dot(sl_))); tw=max(-35,min(35,tw)); wrot_v('Spine',tw*0.45,n_); wrot_v('Chest',tw*0.55,n_)
        # head from ears + nose, max 35 deg relative swing
        ear=(G(7)+G(8))/2; fwd=(G(0)-ear); Rhd=frame_rot(G(7)-G(8),-fwd.cross(G(7)-G(8)) if False else n_.lerp((ear-ms).normalized(),0.6))
        set_world_rot('Neck',Rhd,0.4,20); set_world_rot('Head',Rhd,1.0,30)
        # limbs: bone directions from the source joints
        for sd,(s,e_,wr,ix,px_) in (('Left',(11,13,15,19,17)),('Right',(12,14,16,20,18))):
            align(sd+' arm',G(e_)-G(s)); align(sd+' elbow',G(wr)-G(e_)); align(sd+' wrist',(G(ix)+G(px_))/2-G(wr),cap=40)
            arm_clear(sd)
        for sd,(h_,k_,an,he,ft) in (('Left',(23,25,27,29,31)),('Right',(24,26,28,30,32))):
            align(sd+' leg',G(k_)-G(h_)); align(sd+' knee',G(an)-G(k_))
            fd=G(ft)-G(an); fd.z=min(fd.z,0.35*fd.length) ; align(sd+' ankle',fd,cap=55)
        if offs is not None:
            dx,dy,dz=offs[f]; hp=PB['Hips']; hp.matrix=Matrix.Translation(Vector((dx,dy,dz)))@hp.matrix; upd()
    FOOT={'Left':('Left ankle','Left toe'),'Right':('Right ankle','Right toe')}
    def foot_pts(sd):
        a_,t_=FOOT[sd]; pts=[PB[a_].head.copy()]
        if t_ in PB: pts+= [PB[t_].head.copy(),PB[t_].tail.copy()]
        return pts
    rest(); REST_H={sd:[p.z for p in foot_pts(sd)] for sd in FOOT}
    meshes_eval(True); rest(); FLOOR=bbox([BODY])[0].z; meshes_eval(False)
    info['floor_z']=round(FLOOR,4); info['foot_rest_h']=REST_H
    # pre-pass: ground the lowest foot, lock the stance foot (no sliding), collect root offsets
    offs=[]; prev=None; off=Vector((0,0,0)); stance=[]
    for f in range(NF):
        pose_dance(f)
        ch={sd:min(p.z-h for p,h in zip(foot_pts(sd),REST_H[sd])) for sd in FOOT}
        s=min(ch,key=ch.get); dz=-ch[s]; ball=PB[FOOT[s][1]].head.copy() if FOOT[s][1] in PB else PB[FOOT[s][0]].head.copy()
        if prev and prev[0]==s: off=Vector((prev[1].x-ball.x,prev[1].y-ball.y,0))
        offs.append([off.x,off.y,dz]); prev=(s,Vector((ball.x+off.x,ball.y+off.y,0))); stance.append(s)
    zz=np.array([o[2] for o in offs]); zs=np.convolve(np.pad(zz,2,mode='edge'),np.ones(5)/5,mode='valid'); zs=np.maximum(zs,zz)   # never into the floor
    for i in range(NF): offs[i][2]=float(zs[i])
    # foot slide audit + bounds for the camera
    pts_all=[]; slide={'stance_max_mm':0.0,'other_foot_on_floor_max_mm':0.0}; prevW=None
    for f in range(NF):
        pose_dance(f,offs); W_={sd:[B.matrix_world@p for p in foot_pts(sd)] for sd in FOOT}
        for n in ('Head','Hips','Left wrist','Right wrist','Left toe','Right toe','Left ankle','Right ankle'):
            if n in PB: pts_all.append(B.matrix_world@PB[n].tail)
        if prevW:
            for sd in FOOT:
                mv=max((Vector((a_.x,a_.y,0))-Vector((b_.x,b_.y,0))).length for a_,b_ in zip(W_[sd],prevW[sd]))*1000
                onf=min(p.z-h for p,h in zip(W_[sd],REST_H[sd]))<0.012
                if sd==stance[f] and stance[f-1]==sd: slide['stance_max_mm']=max(slide['stance_max_mm'],round(mv,1))
                elif onf and sd!=stance[f]: slide['other_foot_on_floor_max_mm']=max(slide['other_foot_on_floor_max_mm'],round(mv,1))
        prevW=W_
    info['foot_slide']=slide; info['stance']=stance; info['root_offsets']=[[round(x,4) for x in o] for o in offs]
    mn=Vector([min(p[i] for p in pts_all) for i in range(3)]); mx=Vector([max(p[i] for p in pts_all) for i in range(3)])
    meshes_eval(True); relaxed(); mnr,mxr=bbox(MESHES); top=max(mx.z+0.18,mxr.z+0.02)
    lo=FLOOR-0.06; Hh=(top-lo); wid=(mx.x-mn.x)+0.5; need=max(Hh,wid*RH/RW)*1.06; tgt=Vector(((mn.x+mx.x)/2,(mn.y+mx.y)/2,(top+lo)/2))
    CAM=(tgt,0,3,need/(24/50),50); info['camera']={'tgt':list(tgt),'az':0,'el':3,'dist':CAM[3],'lens':50}
    meshes_eval(False); bones=phys_bones(); WARM=30
    SIM=spring_sim(lambda f: pose_dance(max(f-WARM,0),offs),NF+WARM,fps,bones)
    meshes_eval(True); setcam(*CAM)
    grid=[]
    for i in range(-6,7):
        grid.append([[tgt.x+i*0.25,tgt.y-1.5,FLOOR],[tgt.x+i*0.25,tgt.y+1.5,FLOOR]]); grid.append([[tgt.x-1.5,tgt.y+i*0.25,FLOOR],[tgt.x+1.5,tgt.y+i*0.25,FLOOR]])
    info['floor_grid_px']=[proj_pts(s_) for s_ in grid]
    trk={}
    for f in frames_of(NF):
        t0=time.time(); meshes_eval(False); pose_dance(f,offs); ang=apply_springs(SIM,f+WARM); render(OUT+f'/f{f:03d}.jpg')
        e={'stance':stance[f],'max_back_hair_deg':round(max([v for k_,v in ang.items() if k_.startswith('Back hair')] or [0]),1),'max_hair_deg':round(max(ang.values() or [0]),1),'s':round(time.time()-t0,1)}
        if f%3==0:
            try: meshes_eval(True); e['clip']=clip_flags()
            except Exception as ex: e['clip_error']=str(ex)[:200]
        info['frames'][f]=e; trk[f]={'px':proj_all(),'bones':bones_world() if f%2==0 else None}; log('frame',f,e)
    json.dump(trk,open(OUT+f'/track-shard{SH}.json','w'))
    if SH==0:
        # rest-pose clipping baseline (her own mesh touching itself standing relaxed)
        meshes_eval(True); relaxed(); upd()
        try: info['clip_baseline_relaxed']=clip_flags()
        except Exception as ex: info['clip_baseline_error']=str(ex)[:200]

# ======================= shared IK =======================
def ik2(upper,lower,target,pole,cap_frac=0.999):
    S=PB[upper].head.copy(); a_=PB[upper].length; b_=PB[lower].length; d=target-S; L=max(min(d.length,(a_+b_)*cap_frac),abs(a_-b_)+1e-3)
    dn=d.normalized(); ca=(a_*a_+L*L-b_*b_)/(2*a_*L); ca=max(-1,min(1,ca)); sa=math.sqrt(1-ca*ca)
    pv=pole-S; pv=pv-dn*pv.dot(dn)
    if pv.length<1e-6: pv=Vector((0,-1,0))-dn*dn.y
    pv.normalize(); Ept=S+dn*a_*ca+pv*a_*sa
    align(upper,Ept-S); align(lower,target-PB[lower].head)
def hip_drop(dz,dx=0.0,dy=0.0):
    hp=PB['Hips']; hp.matrix=Matrix.Translation(Vector((dx,dy,dz)))@hp.matrix; upd()
def seat(on,top=0.30,cx=0.0,cy=0.06):
    o=bpy.data.objects.get('TestSeat')
    if o is None:
        me=bpy.data.meshes.new('TestSeat'); import bmesh; bm_=bmesh.new(); bmesh.ops.create_cube(bm_,size=1.0); bm_.to_mesh(me); bm_.free()
        o=bpy.data.objects.new('TestSeat',me); sc.collection.objects.link(o); m=bpy.data.materials.new('SeatGrey'); m.use_nodes=True
        m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(0.30,0.30,0.33,1); o.data.materials.append(m)
    o.scale=(0.46,0.40,top); o.location=(cx,cy,top/2); o.hide_render=not on; o.hide_viewport=not on; return o
# ======================= POSES2 =======================
if MODE=='poses2':
    NAMES=['sit: knee over knee','sit: ankles crossed','sit: side-saddle','stand: hand on hip','stand: contrapposto','stand: hand behind head']
    relaxed(); H0=PB['Left leg'].head.z; FLOORZ=0.0; ANK=PB['Left ankle'].head.z
    def lap_hands(lk,rk,raise_=0.0):
        mid=(lk+rk)/2
        ik2('Left arm','Left elbow',mid+Vector((0.06,-0.02,0.07+raise_)),PB['Left arm'].head+Vector((0.35,0.15,-0.1)))
        ik2('Right arm','Right elbow',mid+Vector((-0.06,-0.02,0.07+raise_)),PB['Right arm'].head+Vector((-0.35,0.15,-0.1)))
        for sd,sg in (('Left',1),('Right',-1)): align(sd+' wrist',Vector((-sg*0.25,-0.9,-0.35)),cap=70)
    def sit_base(a,hz=0.375):
        relaxed(); drop=-(H0-hz)*a; hip_drop(drop,0,0.0)
    def pose(name,a,tw=None):
        tw=tw or {}; e={}
        if name.startswith('sit'):
            sit_base(a); LH,RH=PB['Left leg'].head.copy(),PB['Right leg'].head.copy()
            def L_(p,q): return p.lerp(q,a)
            thigh=PB['Left leg'].length; shin=PB['Left knee'].length
            if name.endswith('knee over knee'):
                la=Vector((LH.x+0.01,LH.y-thigh-0.02,ANK)); ik2('Left leg','Left knee',L_(Vector((LH.x,LH.y-0.01,ANK)),la),LH+Vector((0,-1,0.3)))
                lk=PB['Left knee'].head.copy(); up=tw.get('cross_up',0.12); fw=tw.get('cross_fw',0.0)
                rk=Vector((lk.x+0.01,lk.y-0.03-fw,lk.z+up)); ra=rk+Vector((0.08,-0.15-fw,-0.27))
                ank=L_(Vector((RH.x,RH.y-0.01,ANK)),ra); kn=L_(Vector((RH.x,RH.y-0.3,ANK+shin)),rk)
                ik2('Right leg','Right knee',ank,kn+(kn-(RH+ank)/2)*1.0)
                align('Right ankle',Vector((0.15,-0.7,-0.75)),cap=50)
                lap_hands(lk,PB['Right knee'].head.copy(),tw.get('hand_up',0.0)+0.03)
            elif name.endswith('ankles crossed'):
                sp=tw.get('spread',0.0)
                ik2('Left leg','Left knee',L_(Vector((LH.x,LH.y-0.01,ANK)),Vector((-0.025,LH.y-thigh-0.08,ANK))),LH+Vector((-0.02,-1,0.3)))
                ik2('Right leg','Right knee',L_(Vector((RH.x,RH.y-0.01,ANK)),Vector((0.035,LH.y-thigh-0.13-2*sp,ANK+0.045+sp))),RH+Vector((0.02,-1,0.3)))
                align('Right ankle',Vector((0.1,-0.8,-0.6)),cap=40)
                lap_hands(PB['Left knee'].head.copy(),PB['Right knee'].head.copy(),tw.get('hand_up',0.0))
            else:
                dx=tw.get('spread',0.0)
                ik2('Left leg','Left knee',L_(Vector((LH.x,LH.y-0.01,ANK)),Vector((-0.10+dx,LH.y-thigh-0.02,ANK))),LH+Vector((-0.6,-1,0.3)))
                ik2('Right leg','Right knee',L_(Vector((RH.x,RH.y-0.01,ANK)),Vector((-0.27-dx,LH.y-thigh+0.06,ANK))),RH+Vector((-0.6,-1,0.3)))
                wrot_v('Chest',4*a,(0,0,1)); wrot_v('Head',-6*a,(0,0,1))
                lap_hands(PB['Left knee'].head.copy(),PB['Right knee'].head.copy(),tw.get('hand_up',0.0))
        else:
            relaxed()
            if name.endswith('hand on hip'):
                wrot('Hips',3*a,'Y'); wrot('Chest',-3*a,'Y')
                hipR=Vector((-0.150-tw.get('out',0.0),0.015,0.835))
                ik2('Right arm','Right elbow',PB['Right arm'].head.lerp(Vector((0,0,0)),0)+(hipR-PB['Right arm'].head)*a+((PB['Right elbow'].tail-PB['Right arm'].head)*(1-a)),PB['Right arm'].head+Vector((-0.6,0.5,-0.2)))
                align('Right wrist',Vector((0.15,-0.85,-0.5)).lerp(PB['Right wrist'].tail-PB['Right wrist'].head,1-a),cap=90)
                wrot('Left leg',-5*a,'X'); wrot('Left knee',10*a,'X'); wrot('Head',5*a,'Y')
            elif name.endswith('contrapposto'):
                wrot('Hips',-5*a,'Y'); wrot('Spine',3*a,'Y'); wrot('Chest',4*a,'Y'); wrot('Head',-3*a,'Y')
                wrot('Left leg',-10*a,'X'); wrot('Left leg',4*a,'Y'); wrot('Left knee',20*a,'X'); wrot('Left ankle',-8*a,'X')
                wrot('Right arm',-6*a,'Y'); wrot('Left arm',8*a,'X')
            elif name.endswith('hand behind head'):
                hb=PB['Head'].head+Vector((0.03,0.11+tw.get('back',0.0),0.12))
                st=PB['Left elbow'].tail.copy(); ik2('Left arm','Left elbow',st.lerp(hb,a),PB['Left arm'].head+Vector((0.4,0.3,0.7)))
                align('Left wrist',Vector((-0.8,0.3,0.3)).lerp(PB['Left wrist'].tail-PB['Left wrist'].head,1-a),cap=90)
                wrot('Head',-6*a,'Y'); wrot('Hips',-3*a,'Y'); wrot('Right leg',-6*a,'X'); wrot('Right knee',12*a,'X')
        upd(); return e
    meshes_eval(True); relaxed(); mn,mx=bbox(MESHES); Hh=mx.z-mn.z; ctr=Vector(((mn.x+mx.x)/2,(mn.y+mx.y)/2,mn.z+0.5*Hh))
    cams={'front':(ctr,0,3,(Hh+0.14)/(24/50),50),'q34':(ctr,-35,3,(Hh+0.14)/(24/50),50)}
    seq=[0.0,0.3,0.6,0.85,1.0]; ONLYP=[int(x) for x in (E.get('POSES') or '0,1,2,3,4,5').split(',')]; mine=[i for i in ONLYP if ONLYP.index(i)%SHN==SH]
    for pi in mine:
        nm=NAMES[pi]; tw={}; best=None
        # tune: raise the crossing leg / spread / lift hands until no intersection (her own mesh vs itself)
        for it in range(8):
            meshes_eval(False); pose(nm,1.0,tw); meshes_eval(True); fl=clip_flags(); bad=(fl['leg_vs_leg_tris'] or 0)
            armb=(fl['Larm_vs_torso_tris'] or 0)+(fl['Rarm_vs_torso_tris'] or 0)+(fl['Larm_vs_legs_tris'] or 0)+(fl['Rarm_vs_legs_tris'] or 0)
            log('tune',nm,it,tw,fl)
            if best is None or bad+armb<best[0]: best=(bad+armb,dict(tw),fl)
            if bad==0 and armb==0: break
            if bad: 
                if 'knee over' in nm: tw['cross_up']=tw.get('cross_up',0.12)+0.02; tw['cross_fw']=tw.get('cross_fw',0.0)+0.015
                else: tw['spread']=tw.get('spread',0.0)+0.012
            if armb: tw['hand_up']=tw.get('hand_up',0.0)+0.015; tw['out']=tw.get('out',0.0)+0.01; tw['back']=tw.get('back',0.0)+0.01
        tw=best[1]; info['frames'][f'p{pi}']={'pose':nm,'tune':tw,'flags':best[2],'tune_iters':it+1}
        for k,a_ in enumerate(seq):
            meshes_eval(False); pose(nm,a_,tw); on=nm.startswith('sit') and a_>0.5; seat(on,top=max(0.05,PB['Left leg'].head.z-0.075))
            vws=['front','q34'] if a_==1.0 else ['front']
            for vw in vws: setcam(*cams[vw]); render(OUT+f'/p{pi}_{k}_{vw}.jpg')
            log('pose',nm,a_)
        seat(False)
# ======================= FIST =======================
elif MODE=='fist':
    FING=('IndexFinger','MiddleFinger','RingFinger','LittleFinger')
    def lx(n,c=0): return PB[n].matrix.to_3x3().col[c].normalized()
    # FIST by target directions in her own palm frame (planar curl per finger): no per-bone axis/sign guessing, fingers can't cross.
    ANG=(88,100,72)
    def palm_frame(sd):
        w=PB[('Left' if sd=='L' else 'Right')+' wrist'].head.copy()
        u=(PB[f'MiddleFinger1_{sd}'].head-w).normalized(); s=(PB[f'IndexFinger1_{sd}'].head-PB[f'LittleFinger1_{sd}'].head); s=(s-u*s.dot(u)).normalized(); n=u.cross(s)
        # palm side = the side her relaxed fingers already curl toward
        tip=PB[f'MiddleFinger3_{sd}'].tail; k=PB[f'MiddleFinger1_{sd}'].head
        if (tip-k).dot(n)<0: n=-n
        return u,n
    relaxed(); REL={}
    for sd in 'LR':
        u,n=palm_frame(sd)
        for f_ in FING:
            for j in (1,2,3):
                b=PB[f'{f_}{j}_{sd}']; d=(b.tail-b.head).normalized(); REL[(sd,f_,j)]=(d.dot(u),d.dot(n),d)
    log('fist palm-frame ready')
    def fist(a):
        relaxed()
        for sd in 'LR':
            u,n=palm_frame(sd)
            for f_ in FING:
                acc=0.0
                for j in (1,2,3):
                    acc+=ANG[j-1]; th=math.radians(acc)
                    df=(u*math.cos(th)+n*math.sin(th)).normalized()
                    # keep the finger's own small sideways set (from relaxed) so fingers stay side by side
                    du,dn,d0=REL[(sd,f_,j)]; side=d0-u*du-n*dn
                    df=(df+side*0.6).normalized()
                    b=PB[f'{f_}{j}_{sd}']; cur=(b.tail-b.head).normalized()
                    tgt=cur.slerp(df,a) if a<1.0 else df
                    align(f'{f_}{j}_{sd}',tgt)
        return a
    # thumb: search for the fold that lays the thumb tip over the middle phalanx of index/middle (outside the fingers)
    def thumb_fit(sd):
        fist(1.0); tgt=(PB[f'IndexFinger2_{sd}'].head+PB[f'MiddleFinger2_{sd}'].head)/2
        w=PB[('Left' if sd=='L' else 'Right')+' wrist'].head; palm_out=(tgt-w).cross(PB[f'IndexFinger1_{sd}'].head-PB[f'LittleFinger1_{sd}'].head).normalized()
        best=None; base={pb.name:pb.matrix_basis.copy() for pb in PB}
        for a0 in range(-50,51,10):
            for a1 in range(-80,81,10):
                for pb in PB: pb.matrix_basis=base[pb.name]
                upd(); wrot_v(f'Thumb0_{sd}',a0,lx(f'Thumb0_{sd}',2)); wrot_v(f'Thumb1_{sd}',a1,lx(f'Thumb1_{sd}')); wrot_v(f'Thumb2_{sd}',a1*0.8,lx(f'Thumb2_{sd}'))
                tip=PB[f'Thumb2_{sd}'].tail; dd=(tip-(tgt+palm_out*0.012)).length
                if best is None or dd<best[0]: best=(dd,a0,a1)
        for pb in PB: pb.matrix_basis=base[pb.name]
        upd(); return best
    TH={sd:thumb_fit(sd) for sd in 'LR'}; log('thumb',TH); info['thumb_fit']={k:[round(v[0]*1000,1),v[1],v[2]] for k,v in TH.items()}; info['curl_deg']=ANG
    def pose_f(f,NF=72):
        if f<24: a=0.5-0.5*math.cos(math.pi*f/24)
        elif f<48: a=1.0
        else: a=0.5+0.5*math.cos(math.pi*(f-48)/24)
        fist(a)
        for sd in 'LR':
            _,a0,a1=TH[sd]; wrot_v(f'Thumb0_{sd}',a0*a,lx(f'Thumb0_{sd}',2)); wrot_v(f'Thumb1_{sd}',a1*a,lx(f'Thumb1_{sd}')); wrot_v(f'Thumb2_{sd}',a1*0.8*a,lx(f'Thumb2_{sd}'))
        if 24<=f<48:
            r=math.sin(2*math.pi*(f-24)/24)*25
            for sd,sg in (('Left',1),('Right',-1)): wrot_v(sd+' wrist',sg*r,PB[sd+' elbow'].tail-PB[sd+' elbow'].head)
        return 'curl to fist' if f<24 else ('fist hold (wrist turn)' if f<48 else 'open')
    NF=72; dist=0.26/(24/85)
    for f in frames_of(NF):
        meshes_eval(False); lab=pose_f(f); e={'label':lab}
        tips={}
        for sd in 'LR':
            w=PB[('Left' if sd=='L' else 'Right')+' wrist'].head
            tips[sd]={f_:round((PB[f'{f_}3_{sd}'].tail-w).length*1000,1) for f_ in FING}
            pc=(w+PB[f'MiddleFinger1_{sd}'].head)*0.5; e.setdefault('tip_to_palm_mm',{})[sd]={f_:round((PB[f'{f_}3_{sd}'].tail-pc).length*1000,1) for f_ in FING}
        e['tip_to_wrist_mm']=tips
        for sd,az in (('Left',62),('Right',-62)):
            wv=PB[sd+' wrist'].head; t_=PB['MiddleFinger3_'+sd[0]].tail; c=B.matrix_world@((wv+t_)*0.5); setcam(c,az,8,dist,85); render(OUT+f'/f{f:03d}_{sd[0]}.jpg')
        info['frames'][f]=e; log('fist',f,lab)

# ======================= CATWALK (real forward travel, planted feet) =======================
elif MODE=='catwalk':
    T_=1.0; S_=0.36; v=2*S_/T_; NF=int(E.get('CW_NF','120')); fps=30; Y0=1.6; WARM=30
    relaxed(); ANK=PB['Left ankle'].head.z; LX=PB['Left leg'].head.x
    def ease(x): x=max(0.0,min(1.0,x)); return x*x*(3-2*x)
    LEGX=abs(PB['Left leg'].head.x); H0=PB['Left leg'].head.z; DT=float(E.get('CW_DT','0.624'))   # soft knee (~15-18 deg) at full reach
    def foot_target(sd,t):
        off=0.0 if sd=='Left' else 0.5; ph=((t/T_)+off)%1.0; n=math.floor((t/T_)+off)
        land_t=(n-off)*T_; yl=Y0-v*land_t-S_/2; x=0.03 if sd=='Left' else -0.03
        if ph<0.6:
            heel=ease((ph-0.42)/0.18); return Vector((x,yl,ANK+0.05*heel)),ph,'stance',ph/0.6
        u=(ph-0.6)/0.4; s_=ease(u); y1=yl-2*S_; return Vector((x,yl+(y1-yl)*s_,ANK+0.05*(1-ease(u*2.5))+0.065*math.sin(math.pi*u)**1.2)),ph,'swing',u
    def sway_of(t): return 0.008*math.cos(2*math.pi*(t/T_))
    def hip_need(t):
        hy=Y0-v*t; sw=sway_of(t); best=9
        for sd,sg in (('Left',1),('Right',-1)):
            tg,ph,m,u=foot_target(sd,t)
            if m!='stance': continue
            h=math.hypot(sg*LEGX+sw-tg.x,hy-tg.y); best=min(best,tg.z+math.sqrt(max(DT*DT-h*h,0.04)))
        return best
    NT=NF+WARM+12; HZ=np.array([hip_need(max(f-WARM,0)/fps) for f in range(NT)])
    kk=np.exp(-0.5*(np.arange(-4,5)/1.8)**2); kk/=kk.sum(); HZs=np.minimum(np.convolve(np.pad(HZ,4,mode='edge'),kk,'valid'),HZ)-0.003
    info['hip_height_range_m']=[round(float(HZs.min()),3),round(float(HZs.max()),3)]
    def walk(f):
        t=max(f-WARM,0)/fps; relaxed(); ph=(t/T_)%1.0; W2=2*math.pi
        hip_drop(float(HZs[min(f,NT-1)])-H0,sway_of(t),Y0-v*t)
        yaw=6*math.sin(W2*ph); wrot('Hips',yaw,'Z'); wrot('Hips',-2.5*math.cos(W2*ph),'Y')        # pelvis rotation + gentle drop on the swing side
        wrot('Spine',-0.45*yaw*1.0*math.sin(W2*(ph-0.03))/max(1e-6,math.sin(W2*ph)) if abs(math.sin(W2*ph))>0.05 else -0.45*yaw,'Z')
        cyaw=-9*math.sin(W2*(ph-0.05)); wrot('Chest',cyaw+0.0,'Z'); wrot('Chest',1.8*math.cos(W2*(ph-0.05)),'Y'); wrot('Chest',-1.5,'X')
        st={}
        for sd in ('Left','Right'):
            tg,p_,mode_,u=foot_target(sd,t); hip=PB[sd+' leg'].head
            ik2(sd+' leg',sd+' knee',tg,hip+Vector((0,-1.0,0))+(tg-hip)*0.5)
            if mode_=='stance':
                # heel strike (toes up) -> roll to flat -> heel-off/toe-off
                if u<0.18: pz=-0.18-0.27*ease(u/0.18)
                elif u<0.7: pz=-0.45
                else: pz=-0.45-1.25*ease((u-0.7)/0.3)
            else:
                pz=-1.7+1.25*ease(u/0.45) if u<0.45 else -0.45+0.27*ease((u-0.45)/0.55)
            align(sd+' ankle',Vector((0,-0.89,pz)),cap=75)
            if sd+' toe' in PB and mode_=='stance' and u>0.7: wrot(sd+' toe',-28*ease((u-0.7)/0.3),'X')
            st[sd]=(mode_,tg)
        for sd,sg in (('Left',1),('Right',-1)):
            sw=math.sin(W2*(ph-0.06+(0.5 if sd=='Left' else 0.0)))
            wrot(sd+' arm',-15*sw,'X'); wrot(sd+' elbow',-12-9*max(0.0,sw),'X')
        # head steady: cancel most of the torso yaw, tiny nod with the bob
        wrot('Neck',-0.5*(yaw-0.45*yaw+cyaw),'Z'); wrot('Head',-0.4*(yaw-0.45*yaw+cyaw),'Z'); wrot('Head',0.8*math.cos(2*W2*ph),'X')
        return st
    meshes_eval(False)
    # framing: fixed runway camera in front; she walks toward it (from 1.6 m behind to 1.6 m in front of the mark)
    pts=[]
    for f in range(0,NF+WARM,10):
        walk(f); pts+=[PB['Head'].tail.copy(),PB['Left toe'].tail.copy(),PB['Right toe'].tail.copy()]
    meshes_eval(True); relaxed(); mnr,mxr=bbox(MESHES); FLOOR=mnr.z; top=mxr.z
    yend=min(p.y for p in pts); AZ=float(E.get('CW_AZ','-12'))
    Hh=top-FLOOR+0.12; d_end=Hh*1.06/(24/50); tgt=Vector((0,yend,FLOOR+Hh/2-0.03))
    ca=math.radians(AZ); cpos=tgt+Vector((math.sin(ca),-math.cos(ca),math.sin(math.radians(3))))*d_end*1.15
    def cam_fixed():
        cam.location=cpos; aim=Vector((0,0.3,FLOOR+Hh/2-0.03)); cam.rotation_euler=(aim-cpos).to_track_quat('-Z','Y').to_euler()
        cam.data.lens=40; cam.data.sensor_fit='VERTICAL'; cam.data.sensor_height=24; cam.data.clip_start=0.01; cam.data.clip_end=200; upd()
    meshes_eval(False); bones=phys_bones(); SIM=spring_sim(walk,NF+WARM,fps,bones)
    meshes_eval(True); cam_fixed()
    grid=[]
    for i in range(-4,5): grid.append([[i*0.25,-2.6,FLOOR],[i*0.25,2.4,FLOOR]])
    for j in range(-10,10): grid.append([[-1.0,j*0.25,FLOOR],[1.0,j*0.25,FLOOR]])
    info['floor_grid_px']=[proj_pts(s_) for s_ in grid]; info['gait']={'cycle_s':T_,'step_m':S_,'speed_mps':v,'travel_m':round(v*NF/fps,2),'arms_from_body_deg':90-P_['ARM_DOWN'],'arm_swing_deg':17}
    trk={}; prevS=None; slide=0.0
    for f in frames_of(NF):
        t0=time.time(); meshes_eval(False); st=walk(f+WARM); ang=apply_springs(SIM,f+WARM)
        for sd in ('Left','Right'):
            if st[sd][0]=='stance':
                tg=st[sd][1]; ah=PB[sd+' ankle'].head; slide=max(slide,(Vector((ah.x,ah.y))-Vector((tg.x,tg.y))).length*1000)
        render(OUT+f'/f{f:03d}.jpg')
        e={'stance':[sd for sd in st if st[sd][0]=='stance'],'max_back_hair_deg':round(max([v_ for k_,v_ in ang.items() if k_.startswith('Back hair')] or [0]),1),'s':round(time.time()-t0,1)}
        if f%4==0:
            try: meshes_eval(True); e['clip']=clip_flags()
            except Exception as ex: e['clip_error']=str(ex)[:200]
        e['stance']=e['stance'][0] if len(e['stance'])==1 else ('both' if e['stance'] else None)
        info['frames'][f]=e; trk[f]={'px':proj_all(),'bones':bones_world() if f%2==0 else None}; log('frame',f,e)
    info['stance_ankle_vs_target_max_mm']=round(slide,2)
    json.dump(trk,open(OUT+f'/track-shard{SH}.json','w'))

# ======================= POSES3: real reference photos -> MediaPipe -> her joints =======================
elif MODE=='poses3':
    RFS=json.load(open(DATA)); names=sorted(RFS); mine=[n for i,n in enumerate(names) if i%SHN==SH]
    def mp2b(p): return Vector((p[0],p[2],-p[1]))
    def rest_rot(n): return PB[n].bone.matrix_local.to_3x3()
    def cur_rot(n): return PB[n].matrix.to_3x3()@rest_rot(n).inverted()
    def frame_rot(xv,zv):
        x=xv.normalized(); z=(zv-x*zv.dot(x)).normalized(); y=z.cross(x); return Matrix((x,y,z)).transposed()
    def set_world_rot(n,Rt,frac=1.0,cap=180.0): qrot(n,(Rt@cur_rot(n).inverted()).to_quaternion(),frac,cap)
    meshes_eval(True); rest(); FLOOR=bbox([BODY])[0].z; meshes_eval(False)
    FOOT={'Left':('Left ankle','Left toe'),'Right':('Right ankle','Right toe')}
    def foot_pts(sd): a_,t_=FOOT[sd]; return [PB[a_].head.copy(),PB[t_].head.copy(),PB[t_].tail.copy()]
    rest(); REST_H={sd:[p.z for p in foot_pts(sd)] for sd in FOOT}
    def body_bvh(classes):
        co=ev_co(BODY); V=[Vector(tuple(x)) for x in co]; ps=[p for c in classes for p in CLS.get(c,[])]; return BVHTree.FromPolygons(V,ps)
    def pose_ref(w,tw):
        rest(); fingers_relaxed(1.15)
        P=[mp2b(p) for p in w]; hl=(P[23]-P[24]); yaw=math.atan2(hl.y,hl.x); Rz=Matrix.Rotation(-yaw*float(tw.get('yaw_keep',0.0)) - (-yaw),3,'Z') if False else Matrix.Rotation(-yaw*(1-tw.get('yaw_keep',0.25)),3,'Z')
        G=lambda i: Rz@P[i]
        LS,RS,LH,RH=G(11),G(12),G(23),G(24); mh=(LH+RH)/2; ms=(LS+RS)/2; upt=(ms-mh)
        Rh=frame_rot(LH-RH,Vector((0,0,1)).lerp(upt.normalized(),0.45)); set_world_rot('Hips',Rh,cap=70)
        d0=(PB['Spine'].tail-PB['Spine'].head).normalized(); q=d0.rotation_difference(upt.normalized()); qrot('Spine',q,0.5,40); qrot('Chest',q,0.5,40)
        n_=upt.normalized(); sl=(LS-RS); sl_=(sl-n_*sl.dot(n_)).normalized(); hl_=((LH-RH)-n_*(LH-RH).dot(n_)).normalized()
        tw_=max(-35,min(35,math.degrees(math.atan2(hl_.cross(sl_).dot(n_),hl_.dot(sl_))))); wrot_v('Spine',tw_*0.45,n_); wrot_v('Chest',tw_*0.55,n_)
        # chest lifted + slight arch, shoulders relaxed/down (one a bit lower), slight roll back
        wrot('Chest',-4,'X'); wrot('Left shoulder',7,'Y'); wrot('Right shoulder',-7-3*tw.get('drop_r',1),'Y'); wrot('Left shoulder',-3,'X'); wrot('Right shoulder',-3,'X')
        ear=(G(7)+G(8))/2; Rhd=frame_rot(G(7)-G(8),n_.lerp((ear-ms).normalized(),0.6)); set_world_rot('Neck',Rhd,0.4,20); set_world_rot('Head',Rhd,1.0,30)
        for sd,(s,e_,wr,ix,px_) in (('Left',(11,13,15,19,17)),('Right',(12,14,16,20,18))):
            align(sd+' arm',G(e_)-G(s)); align(sd+' elbow',G(wr)-G(e_)); align(sd+' wrist',(G(ix)+G(px_))/2-G(wr),cap=45)
        for sd,(h_,k_,an,he,ft) in (('Left',(23,25,27,29,31)),('Right',(24,26,28,30,32))):
            align(sd+' leg',G(k_)-G(h_)); align(sd+' knee',G(an)-G(k_)); fd=G(ft)-G(an); fd.z=min(fd.z,0.3*fd.length); align(sd+' ankle',fd,cap=55)
        for sd,a_ in tw.get('lift',{}).items(): wrot(sd+' leg',-a_,'X')
        for sd in ('Left','Right'): arm_clear(sd)
        # ground: lowest foot on the floor
        ch={sd:min(p.z-h for p,h in zip(foot_pts(sd),REST_H[sd])) for sd in FOOT}; dz=-min(ch.values()); hip_drop(dz)
        hipz=min(PB['Left leg'].head.z,PB['Right leg'].head.z); seated=hipz<0.56
        if seated:
            # seated: point the feet (ball of foot down), lifted chest
            for sd in ('Left','Right'):
                if ch[sd]-min(ch.values())<0.03: align(sd+' ankle',Vector((0,-0.55,-0.83)),cap=45)
            ch={sd:min(p.z-h for p,h in zip(foot_pts(sd),REST_H[sd])) for sd in FOOT}; hip_drop(-min(ch.values()))
        return seated
    def hand_contact(seated):
        # hands that are near her body rest ON it: wrist to the nearest torso/thigh surface + 2.5 cm
        meshes_eval(True); out={}
        for sd,own in (('Left','LA'),('Right','RA')):
            tgt_cls=['T','LL','RL']; T_=body_bvh(tgt_cls); wv=PB[sd+' wrist'].tail.copy()
            loc,nr,idx,d=T_.find_nearest(wv,0.12)
            if loc is not None:
                meshes_eval(False); ik2(sd+' arm',sd+' elbow',loc+nr*0.03-(PB[sd+' wrist'].tail-PB[sd+' wrist'].head),PB[sd+' elbow'].head+(PB[sd+' elbow'].head-PB[sd+' arm'].head).normalized()*0.2+Vector((0,0.1,0)))
                out[sd]=round(d*1000,1); meshes_eval(True)
        return out
    meshes_eval(True); rest(); mn,mx=bbox(MESHES); Hh=mx.z-mn.z; ctr=Vector(((mn.x+mx.x)/2,(mn.y+mx.y)/2,mn.z+0.5*Hh))
    cams={'front':(ctr,0,3,(Hh+0.14)/(24/50),50),'q34':(ctr,-35,3,(Hh+0.14)/(24/50),50)}
    if CLS is None: CLS=_cls()
    for fn in mine:
        w=RFS[fn]['w']; tw={}; best=None
        for it in range(8):
            meshes_eval(False); seated=pose_ref(w,tw); hc=hand_contact(seated); fl=clip_flags()
            bad=(fl['leg_vs_leg_tris'] or 0); armb=sum((fl[k] or 0) for k in ('Larm_vs_torso_tris','Rarm_vs_torso_tris','Larm_vs_legs_tris','Rarm_vs_legs_tris'))
            log('tune',fn,it,tw,fl,hc)
            if best is None or bad+armb<best[0]: best=(bad+armb,json.loads(json.dumps(tw)),fl,hc,seated)
            if bad==0 and armb==0: break
            if bad:
                kz={sd:PB[sd+' knee'].head.z for sd in ('Left','Right')}; top=max(kz,key=kz.get); L=tw.setdefault('lift',{}); L[top]=L.get(top,0)+3
        tw=best[1]; meshes_eval(False); seated=pose_ref(w,tw); hc=hand_contact(seated); fl=clip_flags()
        on=seated; seat(on,top=max(0.05,min(PB['Left leg'].head.z,PB['Right leg'].head.z)-0.075),cx=PB['Hips'].head.x,cy=PB['Hips'].head.y+0.10)
        info['frames'][fn]={'pose':RFS[fn]['pose'],'tune':tw,'flags':fl,'hand_contact_mm':hc,'seated':seated}
        for vw in ('front','q34'): setcam(*cams[vw]); render(OUT+f'/{fn[:-4]}_{vw}.jpg')
        seat(False); log('pose3',fn,info['frames'][fn])
# ======================= POSES3B: authored model poses with real contact (refs are the thumbnails beside them) =======================
elif MODE=='poses3b':
    from mathutils.bvhtree import BVHTree as _BV
    POSES=['knee_over_knee','ankles_crossed','side_saddle','hand_on_hip','contrapposto','hand_behind_head']
    mine=[n for i,n in enumerate(POSES) if i%SHN==SH]
    relaxed(); meshes_eval(True); FLOOR=bbox([BODY])[0].z; meshes_eval(False); relaxed()
    REST={n:PB[n].head.copy() for n in ('Hips','Left leg','Right leg','Left knee','Right knee','Left ankle','Right ankle','Head','Neck','Left arm','Right arm')}
    ANKH=REST['Left ankle'].z-FLOOR; Lt=PB['Left leg'].length; Ls=PB['Left knee'].length
    if CLS is None: CLS=_cls()
    def bvh(classes):
        co=ev_co(BODY); V=[Vector(tuple(x)) for x in co]; ps=[p for c in classes for p in CLS.get(c,[])]; return _BV.FromPolygons(V,ps)
    def sgn_roll(bone,deg,ax,check):   # rotate, and flip the sign if the check says it went the wrong way
        base={pb.name:pb.matrix_basis.copy() for pb in PB}; wrot(bone,deg,ax)
        if not check():
            for pb in PB: pb.matrix_basis=base[pb.name]
            upd(); wrot(bone,-deg,ax)
    def posture(pop_side=None,pop=6.0):
        # chest lifted, shoulders down and relaxed, pelvis popped to one side (that hip higher)
        wrot('Chest',-5,'X'); wrot('Left shoulder',8,'Y'); wrot('Right shoulder',-8,'Y'); wrot('Left shoulder',-3,'X'); wrot('Right shoulder',-3,'X')
        if pop_side:
            o='Right' if pop_side=='Left' else 'Left'
            sgn_roll('Hips',pop,'Y',lambda: PB[pop_side+' leg'].head.z>PB[o+' leg'].head.z)
            # shoulders tilt the other way (counter), half as much
            sgn_roll('Chest',pop*0.5,'Y',lambda: PB[o+' arm'].head.z>=PB[pop_side+' arm'].head.z-0.002)
    def leg_to(sd,ank,pole_dir,foot_dir):
        hj=PB[sd+' leg'].head.copy(); ik2(sd+' leg',sd+' knee',ank,hj+pole_dir)
        align(sd+' ankle',foot_dir.normalized(),cap=120)
        if sd+' toe' in PB: align(sd+' toe',foot_dir.normalized()+Vector((0,-0.15,0.1)),cap=60)
    def hand_on(sd,query,classes,elbow_pole,fingers_dir,off=0.028,maxd=0.25):
        meshes_eval(True); T_=bvh(classes); loc,nr,idx,d=T_.find_nearest(query,maxd); meshes_eval(False)
        if loc is None: return None
        wr=PB[sd+' wrist']; hand=(wr.tail-wr.head)
        tgt=loc+nr*off-hand*0.45
        for _ in range(3):
            ik2(sd+' arm',sd+' elbow',tgt,PB[sd+' arm'].head+elbow_pole); align(sd+' wrist',fingers_dir,cap=180)
            pc=(PB[f'MiddleFinger1_{sd[0]}'].head+wr.head)*0.5; meshes_eval(True); T_=bvh(classes); l2,n2,_,d2=T_.find_nearest(pc,0.4); meshes_eval(False)
            if l2 is None: break
            tgt=tgt+(l2+n2*off-pc)*0.9
        PLACED.add(sd)
        return True
    def contact_mm(sd,classes):
        meshes_eval(True); T_=bvh(classes); wr=PB[sd+' wrist']; best=9e9
        for p in [(PB[f'MiddleFinger1_{sd[0]}'].head+wr.head)*0.5,PB[f'MiddleFinger2_{sd[0]}'].head,PB[f'IndexFinger2_{sd[0]}'].head,PB[f'RingFinger2_{sd[0]}'].head]:
            l,n,_,d=T_.find_nearest(p,0.5)
            if l is not None: best=min(best,d)
        meshes_eval(False); return round(best*1000,1)
    def seat_hips(top):
        hz=PB['Left leg'].head.z; hip_drop((top+0.085)-hz,0,0.0)
    def toe_point(sd):   # foot pitch: + = toes pointed down
        a_=PB[sd+' ankle']; d=(a_.tail-a_.head).normalized(); return round(math.degrees(math.asin(max(-1,min(1,-d.z)))),1)
    PLACED=set()
    def pose(name,it):
        relaxed(); info_={}; PLACED.clear()
        hipL=REST['Left leg']; hipR=REST['Right leg']; HX=REST['Hips'].x
        if name in ('knee_over_knee','ankles_crossed','side_saddle'):
            top=FLOOR+ANKH+Ls*0.93; seat_hips(top); posture(None)
            wrot('Hips',-4,'X')   # sit tall: tiny forward tilt of the pelvis
            hl=PB['Left leg'].head; hr=PB['Right leg'].head; fwd=Lt*0.95
            if name=='knee_over_knee':
                lift=0.025*it; fw2=0.0
                leg_to('Left',Vector((hl.x+0.01,hl.y-fwd-0.04,FLOOR+ANKH+0.035)),Vector((0.05,-1,0.3)),Vector((0,-0.45,-0.89)))
                leg_to('Right',Vector((hl.x+0.13,hl.y-fwd-0.16-fw2,FLOOR+ANKH+0.19+lift)),Vector((0.35,-1,0.9+lift*4)),Vector((0.15,-0.55,-0.82)))
                q=PB['Right knee'].head+Vector((0.0,-0.02,0.06))
                hand_on('Left',q+Vector((0.04,0,0.05)),['RL'],Vector((0.5,0.1,-0.3)),Vector((-0.3,-0.6,-0.5)))
                hand_on('Right',q+Vector((-0.02,0.02,0.07)),['RL'],Vector((-0.5,0.1,-0.3)),Vector((0.3,-0.6,-0.5)))
            elif name=='ankles_crossed':
                sl=-0.13-0.01*it   # duchess slant: knees together, legs angled to her right, ankles crossed (left over right)
                leg_to('Right',Vector((hr.x+sl,hr.y-fwd-0.02,FLOOR+ANKH+0.04)),Vector((sl*0.5-0.02*it,-1,0.25)),Vector((-0.1,-0.5,-0.86)))
                ra=PB['Right ankle'].head
                leg_to('Left',Vector((ra.x-0.07,ra.y-0.05,ra.z+0.045)),Vector((sl*0.5+0.02*it,-1,0.25)),Vector((-0.1,-0.5,-0.86)))
                hand_on('Left',(PB['Left leg'].tail+PB['Right leg'].tail)*0.5+Vector((0.03,0.02,0.1)),['LL','RL'],Vector((0.5,0.2,-0.3)),Vector((-0.4,-0.6,-0.4)))
                hand_on('Right',(PB['Left leg'].tail+PB['Right leg'].tail)*0.5+Vector((-0.03,0.07,0.11)),['LL','RL'],Vector((-0.5,0.2,-0.3)),Vector((0.4,-0.6,-0.4)))
            else:
                sl=0.16+0.01*it   # side-saddle: knees together to her left, feet tucked back, toes pointed
                leg_to('Left',Vector((hl.x+sl,hl.y-fwd*0.55,FLOOR+ANKH+0.06)),Vector((sl+0.02*it,-1,0.4)),Vector((0.2,-0.4,-0.9)))
                leg_to('Right',Vector((hr.x+sl+0.06,hr.y-fwd*0.45,FLOOR+ANKH+0.04)),Vector((sl-0.02*it,-1,0.4)),Vector((0.2,-0.4,-0.9)))
                hand_on('Left',PB['Left leg'].tail+Vector((0.0,0.03,0.08)),['LL'],Vector((0.5,0.2,-0.3)),Vector((-0.2,-0.7,-0.5)))
                hand_on('Right',PB['Right leg'].head+Vector((-0.17,0.0,-0.05)),['T','RL'],Vector((-0.4,0.3,-0.2)),Vector((0.1,-0.4,-0.9)),off=0.02)
            info_['seat_top']=top
        else:
            w_=('Left' if name!='contrapposto' else 'Right'); f_='Right' if w_=='Left' else 'Left'; sgx=1 if f_=='Left' else -1
            hip_drop(-0.012, (0.03 if w_=='Left' else -0.03), 0)
            posture(w_, 7.0)
            wa=REST[w_+' ankle']; leg_to(w_,Vector((wa.x,wa.y,wa.z)),Vector((0.0,-1,0)),Vector((0.0,-0.5,-0.12)))
            fa=REST[f_+' ankle']; leg_to(f_,Vector((fa.x-sgx*0.05,fa.y-0.10,fa.z+0.055)),Vector((-sgx*0.25,-1,0.1)),Vector((-sgx*0.15,-0.55,-0.8)))
            if name in ('hand_on_hip','hand_behind_head'):
                hipq=PB['Left leg'].head+Vector((0.20,0.01,0.16))
                hand_on('Left',hipq,['T','LL'],Vector((0.6,0.3,-0.1)),Vector((-0.15,-0.35,-0.92)))
            if name=='hand_behind_head':
                hd=PB['Head'].head; q=hd+Vector((-0.04,0.10,0.10))
                ik2('Right arm','Right elbow',q,PB['Right arm'].head+Vector((-0.7,0.1,0.6))); align('Right wrist',Vector((0.4,0.3,0.8)),cap=120); PLACED.add('Right')
            if name=='contrapposto':
                hand_on('Left',PB['Left leg'].head+Vector((0.06,-0.10,-0.14)),['LL'],Vector((0.45,0.25,-0.3)),Vector((0.0,-0.25,-0.97)),off=0.02)
            for sd in ('Left','Right'):
                if sd in PLACED: continue
                sx=1 if sd=='Left' else -1
                hand_on(sd,PB[sd+' leg'].head+Vector((sx*0.14,0.01,-0.10)),['LL' if sd=='Left' else 'RL'],Vector((sx*0.7,0.6,0.0)),Vector((sx*0.06,-0.08,-0.99)),off=0.022)
            # head: level, a touch toward the camera
            wrot('Head',4 if w_=='Left' else -4,'Y')
            ch={sd:min(PB[sd+' ankle'].head.z,PB[sd+' toe'].tail.z if sd+' toe' in PB else 9) for sd in ('Left','Right')}
        for sd in ('Left','Right'):
            if sd not in PLACED and not (name=='hand_behind_head' and sd=='Right'): arm_clear(sd)
        return info_
    def gates(name):
        meshes_eval(True); fl=clip_flags(); meshes_eval(False); g={'flags':fl}
        cls_={'knee_over_knee':['RL'],'ankles_crossed':['LL','RL'],'side_saddle':['LL','T','RL'],'hand_on_hip':['T','LL','RL'],'contrapposto':['LL','RL'],'hand_behind_head':['T','LL','X']}[name]
        g['hand_contact_mm']={sd:contact_mm(sd,cls_) for sd in ('Left','Right')}
        g['toe_point_deg']={sd:toe_point(sd) for sd in ('Left','Right')}
        g['pelvis_roll_deg']=round(math.degrees(math.atan2(PB['Left leg'].head.z-PB['Right leg'].head.z,PB['Left leg'].head.x-PB['Right leg'].head.x)),1)
        g['shoulder_roll_deg']=round(math.degrees(math.atan2(PB['Left arm'].head.z-PB['Right arm'].head.z,PB['Left arm'].head.x-PB['Right arm'].head.x)),1)
        g['ankle_x_order']=round((PB['Left ankle'].head.x-PB['Right ankle'].head.x)*100,1)
        g['knee_z_cm']={sd:round(PB[sd+' knee'].head.z*100,1) for sd in ('Left','Right')}
        return g
    meshes_eval(True); relaxed(); mn,mx=bbox(MESHES); Hh=mx.z-mn.z
    for nm in mine:
        best=None
        NIT=10 if nm=='knee_over_knee' else (8 if nm in ('ankles_crossed','side_saddle') else 1)
        for it in range(NIT):
            meshes_eval(False); inf=pose(nm,it); g=gates(nm)
            bad=5*(g['flags'].get('leg_vs_leg_tris') or 0)+(g['flags'].get('Larm_vs_torso_tris') or 0)+(g['flags'].get('Rarm_vs_torso_tris') or 0)+(g['flags'].get('Larm_vs_legs_tris') or 0)+(g['flags'].get('Rarm_vs_legs_tris') or 0)
            log('pose3b',nm,it,g,inf)
            if best is None or bad<best[0]: best=(bad,it)
            if bad==0 or (nm=='knee_over_knee' and not g['flags'].get('leg_vs_leg_tris') and not g['flags'].get('Rarm_vs_torso_tris') and not g['flags'].get('Larm_vs_torso_tris')): break
        meshes_eval(False); inf=pose(nm,best[1]); g=gates(nm); g.update(inf); g['iter']=best[1]
        seated=nm in ('knee_over_knee','ankles_crossed','side_saddle')
        if seated: seat(True,top=inf['seat_top'],cx=REST['Hips'].x,cy=REST['Hips'].y+0.12)
        meshes_eval(True); mn2,mx2=bbox(MESHES); ctr=Vector(((mn2.x+mx2.x)/2,(mn2.y+mx2.y)/2,(mn2.z+mx2.z)/2)); hh=max(mx2.z-mn2.z,(mx2.x-mn2.x)*RH/RW)+0.16
        for vw,az in (('front',0),('q34',-35)):
            setcam(ctr,az,3,hh/(24/50),50); render(OUT+f'/{nm}_{vw}.jpg')
        if seated: seat(False)
        info['frames'][nm]=g; log('pose3b done',nm,g)
# ======================= POSES4: feet + hands fix pass (worker 41c5b341, Oct 19): vertex-level hand contact (0 inside, <=3 mm), fingers draped,
# feet grounded on a real floor (planted = bind-pose flat, pointed = ball on floor + toes flat), ankles crossed so the shins form an X from the front
elif MODE=='poses4':
    exec(open('avatar-v3/anim10c/contact.py').read(),globals())
    POSES=['knee_over_knee','ankles_crossed','side_saddle','hand_on_hip','contrapposto','hand_behind_head']
    only=E.get('POSES','')
    mine=[n for i,n in enumerate(POSES) if i%SHN==SH] if not only else [p for i,p in enumerate(only.split(',')) if i%SHN==SH]
    rest(); FLAT={n:PB[n].matrix.to_3x3().copy() for n in ('Left ankle','Right ankle','Left toe','Right toe') if n in PB}
    meshes_eval(True); FLOOR=float(arm_co(BODY)[:,2].min()); FLOORW=bbox([BODY])[0].z
    # sanity: sign of the signed distance (outside +, inside -)
    _T=target_bvh(['Body'],frozenset({'LARM','RARM'}))
    _hp=PB['Hips'].head.copy(); log('sdist sanity inside(hips)',sdist(_T,[_hp],0.5),'outside',sdist(_T,[_hp+Vector((0,-0.4,0))],0.6))
    meshes_eval(False); relaxed(); palm_init(); log('palm local',{k:[round(x,3) for x in v] for k,v in PALM_LOCAL.items()})
    REST={n:PB[n].head.copy() for n in ('Hips','Left leg','Right leg','Left knee','Right knee','Left ankle','Right ankle','Head','Neck','Left arm','Right arm')}
    SG=1.0 if REST['Left leg'].x>REST['Right leg'].x else -1.0
    ANKH=REST['Left ankle'].z-FLOOR; Lt=PB['Left leg'].length; Ls=PB['Left knee'].length
    log('poses4 floor arm',round(FLOOR,4),'world',round(FLOORW,4),'SG',SG,'ANKH',round(ANKH,4),'Lt',round(Lt,3),'Ls',round(Ls,3))
    if CLS is None: CLS=_cls()
    def _mk(name,verts,faces,rgb,rough=0.85):
        o=bpy.data.objects.get(name)
        if o is not None: bpy.data.objects.remove(o,do_unlink=True)
        me=bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts],[],faces); me.update()
        o=bpy.data.objects.new(name,me); sc.collection.objects.link(o)
        m=bpy.data.materials.new(name+'M'); m.use_nodes=True; bs=m.node_tree.nodes['Principled BSDF']; bs.inputs['Base Color'].default_value=(*rgb,1); bs.inputs['Roughness'].default_value=rough
        o.data.materials.append(m); return o
    def box_world(name,x0,x1,y0,y1,z0,z1,rgb):
        C=[to_world((x,y,z)) for z in (z0,z1) for y in (y0,y1) for x in (x0,x1)]
        F=[(0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5)]
        return _mk(name,C,F,rgb)
    cx0,cy0=REST['Hips'].x,REST['Hips'].y
    FLOOROBJ=_mk('Floor4',[to_world((cx0+x,cy0+y,FLOOR)) for x,y in ((-3,-3),(3,-3),(3,3),(-3,3))],[(0,1,2,3)],(0.46,0.46,0.48),0.9)
    def seat_on(top):
        o=box_world('TestSeat',cx0-0.23,cx0+0.23,cy0+0.12-0.20,cy0+0.12+0.20,FLOOR,top,(0.30,0.30,0.33)); o.hide_render=False; return o
    def seat_off():
        o=bpy.data.objects.get('TestSeat')
        if o: bpy.data.objects.remove(o,do_unlink=True)
    def sgn_roll(bone,deg,ax,check):
        base={pb.name:pb.matrix_basis.copy() for pb in PB}; wrot(bone,deg,ax)
        if not check():
            for pb in PB: pb.matrix_basis=base[pb.name]
            upd(); wrot(bone,-deg,ax)
    def posture(pop_side=None,pop=6.0):
        wrot('Chest',-5,'X'); wrot('Left shoulder',8,'Y'); wrot('Right shoulder',-8,'Y'); wrot('Left shoulder',-3,'X'); wrot('Right shoulder',-3,'X')
        if pop_side:
            o='Right' if pop_side=='Left' else 'Left'
            sgn_roll('Hips',pop,'Y',lambda: PB[pop_side+' leg'].head.z>PB[o+' leg'].head.z)
            sgn_roll('Chest',pop*0.5,'Y',lambda: PB[o+' arm'].head.z>=PB[pop_side+' arm'].head.z-0.002)
    def set_rot(n,R):
        if n not in PB: return
        q=(R@PB[n].matrix.to_3x3().inverted()).to_quaternion(); qrot(n,q)
    def foot_orient(sd,pitch,yaw,toe='floor'):
        """pitch + = toes down (pointed); yaw + = toes toward +x. Ankle from the flat bind pose; toes: 'floor' = lie flat on the floor, 'line' = in line with the foot, softly curled"""
        Rz=Matrix.Rotation(math.radians(yaw),3,'Z'); Rx=Matrix.Rotation(math.radians(pitch),3,'X')
        set_rot(sd+' ankle',Rz@Rx@FLAT[sd+' ankle'])
        if sd+' toe' in PB:
            tp={'floor':min(pitch,6.0),'line':pitch+10.0,'flat':pitch}[toe]
            set_rot(sd+' toe',Rz@Matrix.Rotation(math.radians(tp),3,'X')@FLAT[sd+' toe'])
    def leg_to(sd,ank,knee_pt,pitch,yaw=0.0,toe='floor'):
        ik2(sd+' leg',sd+' knee',ank,knee_pt); foot_orient(sd,pitch,yaw,toe)
    def ground(sd,ank,knee_pt,pitch,yaw=0.0,toe='floor',z_goal=0.0006,n=4):
        """move the ankle target up/down until the lowest foot skin point sits on the floor (0-1 mm), never through it"""
        a_=Vector(ank)
        for _ in range(n):
            leg_to(sd,a_,knee_pt,pitch,yaw,toe); meshes_eval(True); z=float(foot_co(sd)[:,2].min()); meshes_eval(False)
            dz=(FLOOR+z_goal)-z
            if abs(dz)<0.0004: break
            a_=a_+Vector((0,0,dz))
        return a_
    def leg_flat(sd,ank,knee_pt,yaw=0.0):
        """planted foot: sole flat (heel and ball both on the floor), grounded"""
        pt=0.0; a_=ank
        for _ in range(3):
            a_=ground(sd,a_,knee_pt,pt,yaw,'flat'); meshes_eval(True); fs=foot_stats(sd,FLOOR); meshes_eval(False)
            dh=(fs['heel_mm']-fs['ball_mm'])/1000.0
            if abs(dh)<0.0015: break
            pt-=math.degrees(math.atan2(dh,0.16))   # heel high -> toes up (negative pitch) until the sole is level
        return a_
    def seat_hips(top):
        hz=PB['Left leg'].head.z; hip_drop((top+0.085)-hz,0,0.0)
    def legleg():
        meshes_eval(True); f_=clip_flags(); meshes_eval(False); return f_.get('leg_vs_leg_tris') or 0
    BODYX=['Body','Shorts','Shirt','Bra']
    def ex(sd): return frozenset({sd[0]+'ARM'})
    def legs(name,it):
        """legs + feet only. returns info"""
        relaxed(); inf={}
        hipL=PB['Left leg'].head; hipR=PB['Right leg'].head
        if name in ('knee_over_knee','ankles_crossed','side_saddle'):
            top=FLOOR+ANKH+Ls*0.93; seat_hips(top); posture(None); wrot('Hips',-4,'X'); inf['seat_top']=top
            hl=PB['Left leg'].head.copy(); hr=PB['Right leg'].head.copy(); kc=(hl+hr)/2; fwd=Lt*0.95
            if name=='knee_over_knee':
                # bottom leg (left): shin near vertical, foot pointed a little with the ball on the floor
                kL=Vector((hl.x-SG*0.005,hl.y-fwd,top+0.02)); aL=Vector((hl.x-SG*0.01,hl.y-fwd*0.98,FLOOR+ANKH))
                aL=ground('Left',aL,kL+Vector((0,-0.3,0.1)),28.0,SG*4.0,'floor')
                la=PB['Left ankle'].head.copy(); lk=PB['Left knee'].head.copy()
                # top leg (right): thigh LYING across the left thigh just behind the left knee (near horizontal, like the ref),
                # shin hanging down in front of the left shin, foot softly pointed; only the thigh lift iterates until 0 leg-leg
                K=lk+Vector((SG*0.035,0.035,0.105+0.008*it)); hp_=PB['Right leg'].head.copy()
                align('Right leg',K-hp_)
                kk=PB['Right knee'].head.copy()
                sh_=Vector((SG*0.06,-0.30,-1.0)).normalized(); align('Right knee',sh_)
                foot_orient('Right',50.0,SG*10.0,'line')
                inf['top_foot_kick_cm']=round((la.y-PB['Right ankle'].head.y)*100,1)
                inf['top_thigh_pitch_deg']=round(math.degrees(math.asin(max(-1,min(1,(kk-hp_).normalized().z)))),1)
                inf['top_foot_above_floor_cm']=round((PB['Right toe'].tail.z-FLOOR)*100,1) if 'Right toe' in PB else None
            elif name=='ankles_crossed':
                ks=0.050+0.003*it; dy=0.050+0.010*it
                y0=hl.y-fwd*0.80
                kLp=Vector((kc.x+SG*ks,hl.y-fwd,top+0.03)); kRp=Vector((kc.x-SG*ks,hr.y-fwd,top+0.03))
                # right (back) ankle crosses to her left side, left (front) ankle crosses to her right side -> the shins make an X from the front
                aR=Vector((kc.x+SG*0.035,y0,FLOOR+ANKH)); aR=ground('Right',aR,kRp+Vector((0,-0.3,0.05)),40.0,SG*8.0,'floor')
                aL=Vector((kc.x-SG*0.035,y0-dy,FLOOR+ANKH+0.02+0.004*it)); aL=ground('Left',aL,kLp+Vector((0,-0.3,0.05)),42.0,-SG*8.0,'floor')
            else:
                sl=0.15+0.008*it
                kLp=Vector((hl.x+SG*sl*0.6,hl.y-fwd,top+0.03)); kRp=Vector((hr.x+SG*sl*0.6,hr.y-fwd,top+0.03))
                aL=Vector((hl.x+SG*sl,hl.y-fwd*0.55,FLOOR+ANKH)); aL=ground('Left',aL,kLp+Vector((SG*0.1,-0.3,0.1)),45.0,SG*15.0,'floor')
                aR=Vector((hr.x+SG*(sl+0.06),hr.y-fwd*0.45,FLOOR+ANKH)); aR=ground('Right',aR,kRp+Vector((SG*0.1,-0.3,0.1)),48.0,SG*15.0,'floor')
        else:
            w_=('Left' if name!='contrapposto' else 'Right'); f_='Right' if w_=='Left' else 'Left'; sw=SG if w_=='Left' else -SG
            hip_drop(-0.015,sw*0.025,0); posture(w_,7.0); inf['weight']=w_
            wa=REST[w_+' ankle']; hj=PB[w_+' leg'].head
            leg_flat(w_,Vector((wa.x,wa.y,wa.z)),hj+Vector((0,-0.6,-0.3)),yaw=sw*6.0)
            fa=REST[f_+' ankle']; hf=PB[f_+' leg'].head
            # free leg: knee soft and turned in a little, heel up, ball + toes on the floor
            aF=Vector((fa.x+sw*0.04,fa.y-0.07,fa.z+0.05)); kF=hf+Vector((sw*0.12,-0.7,-0.25))
            ground(f_,aF,kF,32.0,sw*10.0,'floor')
            inf['free']=f_
        return inf
    def hands(name,inf):
        rep={}
        if name=='knee_over_knee':
            kn=PB['Right knee'].head.copy(); th=(PB['Right knee'].head-PB['Right leg'].head).normalized()
            fd=(th+Vector((0,0,-0.6))).normalized()
            rep['Left']=place_hand('Left',PB['Right leg'].head.lerp(kn,0.86)+Vector((0,0.0,0.10)),['Body','Shorts'],ex('Left'),Vector((SG*0.5,0.2,-0.3)),fd,incl=frozenset({'RLEG'}))
            q=PB['Right leg'].head.lerp(PB['Right knee'].head,0.70)+Vector((0,-0.01,0.10))
            rep['Right']=place_hand('Right',q,['Body','Shorts'],ex('Right'),Vector((-SG*0.8,0.1,-0.2)),fd,incl=frozenset({'RLEG'}))
        elif name=='ankles_crossed':
            for sd,sx in (('Left',SG),('Right',-SG)):
                q=PB[sd+' leg'].head.lerp(PB[sd+' knee'].head,0.70)+Vector((0,0,0.10))
                rep[sd]=place_hand(sd,q,['Body','Shorts'],ex(sd),Vector((sx*0.5,0.25,-0.3)),Vector((-sx*0.25,-0.6,-0.75)),incl=frozenset({sd[0]+'LEG'}))
        elif name=='side_saddle':
            q=PB['Left knee'].head+Vector((0,0.03,0.10))
            rep['Left']=place_hand('Left',q,['Body','Shorts'],ex('Left'),Vector((SG*0.5,0.2,-0.3)),Vector((-SG*0.2,-0.7,-0.5)),incl=frozenset({'LLEG'}))
            q=PB['Right leg'].head.lerp(PB['Right knee'].head,0.55)+Vector((0,0,0.10))
            rep['Right']=place_hand('Right',q,['Body','Shorts'],ex('Right'),Vector((-SG*0.6,0.25,-0.3)),Vector((SG*0.3,-0.6,-0.6)),incl=frozenset({'RLEG'}))
        else:
            wrot('Head',4 if inf.get('weight')=='Left' else -4,'Y')
            def on_hip(sd):
                sx=SG if sd=='Left' else -SG
                q=PB[sd+' leg'].head+Vector((sx*0.16,-0.01,0.17))
                return place_hand(sd,q,BODYX,ex(sd),Vector((sx*0.9,0.45,0.15)),Vector((-sx*0.10,-0.85,-0.50)),incl=frozenset({'CORE',sd[0]+'LEG'}))
            def at_side(sd):
                sx=SG if sd=='Left' else -SG
                q=PB[sd+' leg'].head+Vector((sx*0.16,0.01,-0.13))
                return place_hand(sd,q,['Body','Shorts'],ex(sd),Vector((sx*0.7,0.5,0.0)),Vector((sx*0.05,-0.10,-0.99)),gap=0.010,incl=frozenset({sd[0]+'LEG'}),settle=False)
            if name=='hand_on_hip': rep['Left']=on_hip('Left'); rep['Right']=at_side('Right')
            elif name=='contrapposto': rep['Left']=on_hip('Left'); rep['Right']=on_hip('Right')
            else:
                rep['Left']=on_hip('Left')
                hd=PB['Head'].head; q=hd+Vector((-SG*0.03,0.10,0.11))
                r_=place_hand('Right',q,['HeadShell'],frozenset(),Vector((-SG*0.8,0.15,0.6)),Vector((SG*0.55,0.25,0.8)),gap=0.0015)   # head collider: hair+skull envelope fitted to her mesh
                if r_:
                    # never into her skull/face: signed test against the head meshes, lift off in 2 mm steps
                    meshes_eval(True); Th=target_bvh(['Female Head','Cranium','Body'],frozenset({'RARM'}),near=PB['Right wrist'].head,rad=0.3); hs=hand_stats('Right',Th); meshes_eval(False); k=0
                    while Th is not None and hs['pen_verts']>0 and k<10:
                        wrot_v('Right elbow',-2.0,(PB['Right elbow'].tail-PB['Right elbow'].head).cross(Vector((0,0,1))).normalized()); k+=1
                        meshes_eval(True); hs=hand_stats('Right',Th); meshes_eval(False)
                    r_['head_skin']=hs; r_['head_lift_steps']=k
                    meshes_eval(True); Tsh=head_shell_bvh(); r_['head_shell']=hand_stats('Right',Tsh); r_['head_shell_fit']=SHELL.get('info'); meshes_eval(False)
                rep['Right']=r_
        for sd in ('Left','Right'):
            if not rep.get(sd): arm_clear(sd)
        return rep
    def gates(name,inf,hrep):
        meshes_eval(True); fl=clip_flags(); co=body_co(); g={'flags':fl}
        g['feet']={sd:foot_stats(sd,FLOOR,co) for sd in ('Left','Right')}
        g['toe_pitch_deg']={sd:toe_pitch(sd) for sd in ('Left','Right')}
        g['hands']={}
        for sd in ('Left','Right'):
            r_=hrep.get(sd)
            if not r_: g['hands'][sd]=None; continue
            T=r_.get('T'); hs=hand_stats(sd,T,co) if T is not None else None
            g['hands'][sd]={'final':hs,'fingers':r_.get('fingers'),'lift_mm':r_.get('lift_mm'),'head_skin':r_.get('head_skin'),'head_shell':r_.get('head_shell'),'head_shell_fit':r_.get('head_shell_fit'),'palm_vs_surface_deg':r_.get('palm_normal_vs_surface_deg'),'palm':r_.get('palm'),'roll_off_deg':r_.get('roll_off_deg'),'side_diff_mm':r_.get('side_diff_mm')}
        # colliders (QC): every hand vs the head/hair shell and vs the other hand
        try:
            Tsh=head_shell_bvh(); g['qc_hand_vs_head_shell']={sd:hand_stats(sd,Tsh,co) for sd in ('Left','Right')}
            for sd,o_ in (('Left','Right'),('Right','Left')):
                To=target_bvh(['Body'],frozenset({'LARM' if o_=='Right' else 'RARM','CORE','HEAD','LLEG','RLEG'}),near=PB[o_+' wrist'].head,rad=0.16)
                g.setdefault('qc_hand_vs_hand',{})[sd]=hand_stats(sd,To,co) if To is not None else None
        except Exception as ex: g['qc_error']=str(ex)[:200]
        lk,rk,la,ra=PB['Left knee'].head,PB['Right knee'].head,PB['Left ankle'].head,PB['Right ankle'].head
        g['front_X']={'knee_dx_cm':round((lk.x-rk.x)*SG*100,1),'ankle_dx_cm':round((la.x-ra.x)*SG*100,1),'crossed':bool((lk.x-rk.x)*(la.x-ra.x)<0)}
        g['pelvis_roll_deg']=round(math.degrees(math.atan2(PB['Left leg'].head.z-PB['Right leg'].head.z,abs(PB['Left leg'].head.x-PB['Right leg'].head.x))),1)
        g['shoulder_roll_deg']=round(math.degrees(math.atan2(PB['Left arm'].head.z-PB['Right arm'].head.z,abs(PB['Left arm'].head.x-PB['Right arm'].head.x))),1)
        if name=='knee_over_knee': g['top_foot_kick_cm']=inf.get('top_foot_kick_cm'); g['top_thigh_pitch_deg']=inf.get('top_thigh_pitch_deg'); g['top_foot_above_floor_cm']=inf.get('top_foot_above_floor_cm')
        meshes_eval(False); return g
    def views(nm,seated):
        meshes_eval(True); mn2,mx2=bbox(MESHES); mn2.z=min(mn2.z,FLOORW); ctr=Vector(((mn2.x+mx2.x)/2,(mn2.y+mx2.y)/2,(mn2.z+mx2.z)/2)); hh=max(mx2.z-mn2.z,(mx2.x-mn2.x)*RH/RW)+0.14
        sc.render.resolution_x,sc.render.resolution_y=RW,RH
        for vw,az in (('front',0),('q34',-35)):
            setcam(ctr,az,3,hh/(24/50),50); render(OUT+f'/{nm}_{vw}.jpg')
        # close-ups: both hands, both feet (front + 3/4)
        sc.render.resolution_x,sc.render.resolution_y=720,720
        cw=ev_co(BODY); bc=Vector(tuple(cw.mean(axis=0)))
        for sd in ('Left','Right'):
            hw=cw[HANDV[sd]]; c=Vector(tuple(hw.mean(axis=0))); ext=float((hw.max(axis=0)-hw.min(axis=0)).max())
            az=40 if c.x>bc.x else -40
            if nm=='hand_behind_head' and sd=='Right': az=150 if c.x>bc.x else -150
            setcam(c,az,10,max(ext*2.0,0.26)/(24/85),85); render(OUT+f'/{nm}_hand{sd[0]}.jpg')
        fw=np.concatenate([cw[FOOTV['Left']],cw[FOOTV['Right']]]); c=Vector(tuple(fw.mean(axis=0))); ext=float((fw.max(axis=0)-fw.min(axis=0)).max())
        for vw,az in (('front',0),('q34',-35)):
            setcam(c+Vector((0,0,0.03)),az,7,max(ext*1.5,0.36)/(24/70),70); render(OUT+f'/{nm}_feet_{vw}.jpg')
        sc.render.resolution_x,sc.render.resolution_y=RW,RH
    for nm in mine:
        t0=time.time(); seated=nm in ('knee_over_knee','ankles_crossed','side_saddle')
        NIT=16 if nm=='knee_over_knee' else (12 if seated else 1); best=None
        for it in range(NIT):
            meshes_eval(False); inf=legs(nm,it); ll=legleg()
            log('poses4 legs',nm,it,'leg_leg',ll,inf)
            if best is None or ll<best[0]: best=(ll,it)
            if ll==0: break
        meshes_eval(False); inf=legs(nm,best[1]); inf['leg_iter']=best[1]
        if seated: seat_on(inf['seat_top'])
        hrep=hands(nm,inf)
        g=gates(nm,inf,hrep); g.update({k:v for k,v in inf.items()}); g['s_pose']=round(time.time()-t0,1)
        log('poses4 gates',nm,json.dumps(g,default=str)[:3000])
        views(nm,seated)
        if seated: seat_off()
        info['frames'][nm]=g; log('poses4 done',nm,round(time.time()-t0,1),'s')
elif MODE=='hair2':
    NF=120; fps=30
    def base(f):
        relaxed(); fingers_relaxed()
        if f<40: wrot('Neck',14*math.sin(2*math.pi*f/40),'Z'); wrot('Head',22*math.sin(2*math.pi*f/40),'Z'); lab='head turn L/R'
        elif f<80:
            u=(f-40)/40.0; wrot('Neck',6*math.sin(2*math.pi*u),'X'); wrot('Head',10*math.sin(2*math.pi*u),'X'); wrot('Head',8*math.sin(4*math.pi*u),'Y'); lab='nod + tilt'
        else:
            u=(f-80)/40.0; yw=25*math.sin(2*math.pi*u); wrot('Hips',yw,'Z'); wrot('Chest',0.3*yw,'Z'); lab='body turn (hair swing)'
        return lab
    bones=phys_bones(); WARM=45; SIM=spring_sim(lambda f: base(max(f-WARM,0)),NF+WARM,fps,bones)
    meshes_eval(True); relaxed(); mna,mxa=bbox(MESHES); top=mxa.z
    lo=float((B.matrix_world@PB['Hips'].head).z)-0.12; hh=(top-lo)*1.12; tg=Vector(((mna.x+mxa.x)/2,(mna.y+mxa.y)/2,(top+lo)/2))
    CAMS=[(tg,-30,4,hh/(24/50),50),(tg,150,4,hh/(24/50),50)]
    for f in frames_of(NF):
        meshes_eval(False); lab=base(f); ang=apply_springs(SIM,f+WARM)
        setcam(*CAMS[0 if (f//20)%2==0 or f>=80 else 1]); render(OUT+f'/f{f:03d}.jpg')
        info['frames'][f]={'label':lab,'view':'front-3/4' if (f//20)%2==0 or f>=80 else 'back-3/4','max_hair_deg':round(max(ang.values() or [0]),1),'max_back_hair_deg':round(max([v for k_,v in ang.items() if k_.startswith('Back hair')] or [0]),1)}
        log('hair2',f,info['frames'][f])
json.dump(info,open(OUT+f'/{MODE}-shard{SH}.json','w'),indent=0,default=str)
log('DONE'); sys.stdout.flush(); os._exit(0)
