
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
    def curl_signs():
        relaxed(); S={}
        for sd in 'LR':
            w=PB[('Left' if sd=='L' else 'Right')+' wrist'].head.copy()
            for f_ in FING:
                n=f'{f_}1_{sd}'; tip=lambda: PB[f'{f_}3_{sd}'].tail.copy(); d0=(tip()-w).length; base={pb.name:pb.matrix_basis.copy() for pb in PB}
                wrot_v(n,40,lx(n)); d1=(tip()-w).length
                for pb in PB: pb.matrix_basis=base[pb.name]
                upd(); S[(sd,f_)]=1 if d1<d0 else -1
        return S
    meshes_eval(False); SG=curl_signs(); log('curl signs',SG)
    ANG=(80,100,72)
    def fist(a):
        relaxed()
        for sd in 'LR':
            for f_ in FING:
                for j in (1,2,3):
                    n=f'{f_}{j}_{sd}'; base_rel=(14,22,14)[j-1]   # undo part of the relaxed curl already applied
                    wrot_v(n,SG[(sd,f_)]*max(0,ANG[j-1]-base_rel)*a,lx(n))
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
        e['tip_to_wrist_mm']=tips
        for sd,az in (('Left',62),('Right',-62)):
            wv=PB[sd+' wrist'].head; t_=PB['MiddleFinger3_'+sd[0]].tail; c=B.matrix_world@((wv+t_)*0.5); setcam(c,az,8,dist,85); render(OUT+f'/f{f:03d}_{sd[0]}.jpg')
        info['frames'][f]=e; log('fist',f,lab)

# ======================= CATWALK (real forward travel, planted feet) =======================
elif MODE=='catwalk':
    T_=1.0; S_=0.36; v=2*S_/T_; NF=int(E.get('CW_NF','120')); fps=30; Y0=1.6; WARM=30
    relaxed(); ANK=PB['Left ankle'].head.z; LX=PB['Left leg'].head.x
    def foot_target(sd,t):
        off=0.0 if sd=='Left' else 0.5; ph=((t/T_)+off)%1.0; n=math.floor((t/T_)+off)
        land_t=(n-off)*T_; yl=Y0-v*land_t-S_/2; x=0.04 if sd=='Left' else -0.04
        if ph<0.6:
            heel=max(0.0,(ph-0.45)/0.15); return Vector((x,yl,ANK+0.035*heel)),ph,'stance',heel
        u=(ph-0.6)/0.4; s_=u*u*(3-2*u); y1=yl-2*S_; return Vector((x,yl+(y1-yl)*s_,ANK+0.035*(1-u)+0.09*math.sin(math.pi*u))),ph,'swing',u
    def walk(f):
        t=max(f-WARM,0)/fps if f>=0 else 0; relaxed(); ph=(t/T_)%1.0; c=math.cos(2*math.pi*ph)
        sway=0.028*c   # toward the stance foot
        hip_drop(-0.05+0.01*math.cos(4*math.pi*ph),sway,Y0-v*t)
        wrot('Hips',7*math.sin(2*math.pi*ph),'Z'); wrot('Hips',-5*c,'Y'); wrot('Chest',-9*math.sin(2*math.pi*ph),'Z'); wrot('Chest',3*c,'Y')
        st={}
        for sd in ('Left','Right'):
            tg,p_,mode_,u=foot_target(sd,t); hip=PB[sd+' leg'].head
            ik2(sd+' leg',sd+' knee',tg,hip+Vector((0,-1.0,0))+(tg-hip)*0.5)
            if mode_=='stance': align(sd+' ankle',Vector((0,-0.89,-0.45-1.3*u)),cap=70)
            else: align(sd+' ankle',Vector((0,-0.89,-0.6+0.15*u)),cap=70)
            st[sd]=(mode_,tg)
        for sd,sg in (('Left',1),('Right',-1)):
            sw=math.sin(2*math.pi*(ph+(0.5 if sd=='Left' else 0.0)))
            wrot(sd+' arm',-17*sw,'X'); wrot(sd+' elbow',-6-8*max(0,sw),'X')
        wrot('Head',-2*c,'Y'); return st
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
json.dump(info,open(OUT+f'/{MODE}-shard{SH}.json','w'),indent=0,default=str)
log('DONE'); sys.stdout.flush(); os._exit(0)
