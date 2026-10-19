# rev 182938

# Jena v3.7 dance4 big-fix (D4=1: rig27, One-Euro, face/head track, leg capsules, 120 fps) on top of run-10c ANIMATION clips (Saidie 9:47 PM Oct 18): talk/blink/expressions, dance retargeted from her TikTok ref, with bone-track export.
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
D4=E.get('D4')=='1'
if D4: exec(open('avatar-v3/d4/rig27.py').read(),globals())
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
    ang=math.degrees(q.angle); ax=q.axis
    if ang>180.0: ang=360.0-ang; ax=-ax      # shortest way round (a quaternion and its negative are the same turn)
    if ang<1e-3: return
    wrot_v(name,min(ang*frac,cap),ax)
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
if E.get('GPU')=='1':
    try:
        _pr=bpy.context.preferences.addons['cycles'].preferences
        for _typ in ('OPTIX','CUDA'):
            try: _pr.compute_device_type=_typ; _pr.get_devices(); _dv=[d for d in _pr.devices if d.type==_typ]
            except Exception: _dv=[]
            if _dv:
                for d in _pr.devices: d.use=(d.type==_typ)
                sc.cycles.device='GPU'; log('GPU',_typ,[d.name for d in _dv]); break
    except Exception as ex: log('GPU setup failed',ex)
sc.render.resolution_x,sc.render.resolution_y=RW,RH; sc.render.resolution_percentage=100
sc.render.image_settings.file_format='JPEG'; sc.render.image_settings.quality=92
_RF=[0]
def render(path):
    # the first render of a shard came out from a stale mesh (head on her shoulder while the bones read level): warm it once, throw that one away
    meshes_eval(True); bpy.context.view_layer.update()
    if _RF[0]==0:
        sc.render.filepath='/tmp/_warm_render.jpg'; bpy.ops.render.render(write_still=True); _RF[0]=1
    sc.render.filepath=path; bpy.ops.render.render(write_still=True)
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


def radial_push(sd,deg,joint='arm'):
    # rotate the upper arm (joint='arm') or forearm (joint='elbow') so its end point moves straight AWAY from her torso axis
    bn=sd+(' arm' if joint=='arm' else ' elbow'); pb=PB[bn]; end=pb.tail.copy()
    a=PB['Hips'].head; b=PB['Neck'].head; ab=b-a; t=max(0.0,min(1.0,(end-a).dot(ab)/ab.length_squared)); c=a+ab*t
    out=end-c; out=out-ab.normalized()*out.dot(ab.normalized())
    if out.length<1e-5: return
    d=(pb.tail-pb.head).normalized(); ax=d.cross(out.normalized())
    if ax.length<1e-4: return
    wrot_v(bn,deg,ax.normalized())
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
# ======================= CATWALK4: a real runway model's walk (MediaPipe, walkref.json) retargeted onto Jena, gated =======================
elif MODE=='catwalk4':
    WR=json.load(open(DATA)); CV=WR.get('curves') or {}; NPH=WR.get('phase_samples',50); fps=30; WARM=30
    NF=int(E.get('CW_NF','150'))
    def cur(name,ph,default=0.0):
        c=CV.get(name)
        if not c: return default
        x=(ph%1.0)*NPH; i0=int(x)%NPH; i1=(i0+1)%NPH; a_=x-int(x); return c[i0]*(1-a_)+c[i1]*a_
    def centred(name,ph): return cur(name,ph)-(sum(CV[name])/len(CV[name]) if CV.get(name) else 0.0)
    def amp(name):
        c=CV.get(name); return (max(c)-min(c))/2 if c else 0.0
    def scale_to(name,lo,hi):   # keep the real curve's SHAPE + timing, bring its amplitude inside the gate
        a_=amp(name); return 1.0 if a_<1e-6 else max(lo,min(hi,a_))/a_
    Tsrc=WR.get('cycle_s') or 1.05; T_=Tsrc if 0.85<=Tsrc<=1.3 else 1.05      # slow-motion / odd footage -> normal runway cadence
    info['source']={'clip':WR.get('src'),'t0':WR.get('t0'),'t1':WR.get('t1'),'cycle_s_src':Tsrc,'n_cycles':WR.get('n_cycles'),'ranges':WR.get('ranges')}
    rest(); H0=PB['Hips'].head.z
    LEGX=abs(PB['Left leg'].head.x-PB['Hips'].head.x); Lt=PB['Left leg'].length; Ls=PB['Left knee'].length; LEG=Lt+Ls
    meshes_eval(True); mnr,mxr=bbox(MESHES); FLW=mnr.z; meshes_eval(False); rest()
    MWi=B.matrix_world.inverted(); FLOOR=(MWi@Vector((0,0,FLW))).z
    log('mw',[list(r) for r in B.matrix_world],'H0',H0,'LEGX',LEGX,'Lt',Lt,'Ls',Ls,'floor arm-space',FLOOR)
    # rest foot geometry (armature space): ankle, ball (toe head), toe tip, heel point on the floor
    GEO={}
    for sd in ('Left','Right'):
        an=PB[sd+' ankle']; to=PB[sd+' toe']; ah=an.head.copy(); bh_=to.head.copy(); tt=to.tail.copy()
        heel=Vector((ah.x,ah.y+0.045,FLOOR)); ballf=bh_.copy()
        GEO[sd]=dict(ankle=ah,ball=ballf,tip=tt,heel=heel,adir=(an.tail-an.head),tdir=(to.tail-to.head),h_off=ah-heel,b_off=ah-ballf)
        GEO[sd]['heel_local']=(B.matrix_world@an.matrix).inverted()@(B.matrix_world@heel)
        log('foot',sd,'ankle',tuple(round(x,3) for x in ah),'ball',tuple(round(x,3) for x in bh_),'heel',tuple(round(x,3) for x in heel),'ankle h',round(ah.z-FLOOR,3))
    STEPW=float(E.get('CW_STEPW','0.12'))           # foot centre lines 11 cm apart (gate 6-12 cm), never crossing
    S_=float(E.get('CW_STEP',str(round(0.78*LEG,3))))  # runway step ~0.78 leg length
    v=2*S_/T_; Y0=1.5; SF=0.62; relaxed()
    info['gait']={'cycle_s':round(T_,3),'step_m':round(S_,3),'speed_mps':round(v,3),'step_width_m':STEPW,'stance_frac':SF}
    def PR(th): return Matrix.Rotation(math.radians(-th),3,'X')   # + = toes up
    def pitch_stance(u):
        if u<0.15: return 16.0*(1-u/0.15)**1.6
        if u<0.55: return 0.0
        x_=(u-0.55)/0.45; return -42.0*(x_*x_*(3-2*x_))
    def pitch_swing(u):
        if u<0.35: return -42.0+30.0*(u/0.35)
        return -12.0+28.0*(((u-0.35)/0.65)**1.3)
    def ease(x): x=max(0.0,min(1.0,x)); return x*x*(3-2*x)
    def hipy(t): return Y0-v*t
    def lift_profile(u):
        # toe clearance shape from her knee/thigh curves (swing part), normalised; fallback sine
        if CV.get('knee_L'):
            ph=SF+u*(1-SF); k_=cur('knee_L',ph); k0=min(CV['knee_L']); k1=max(CV['knee_L'])
            return max(0.0,(k_-k0)/max(1e-3,k1-k0))*math.sin(math.pi*u)**0.5
        return math.sin(math.pi*u)
    def foot_state(sd,t):
        off=0.0 if sd=='Left' else 0.5; x_=t/T_-off; n=math.floor(x_); ph=x_-n
        g=GEO[sd]; fx=(STEPW/2)*(1 if sd=='Left' else -1)
        def heel_at(k): ts=(k+off)*T_; return Vector((fx,hipy(ts)-0.42*S_,FLOOR))
        if ph<SF:
            u=ph/SF; th=pitch_stance(u); hp=heel_at(n)
            if th>=0: piv=hp; A=piv+PR(th)@g['h_off']
            else: piv=hp+(g['ball']-g['heel']); A=piv+PR(th)@g['b_off']
            return dict(mode='stance',u=u,th=th,ankle=A,heel=hp,ball=hp+(g['ball']-g['heel']),ph=ph)
        u=(ph-SF)/(1-SF); th=pitch_swing(u)
        hp0=heel_at(n); b0=hp0+(g['ball']-g['heel']); A0=b0+PR(-42.0)@g['b_off']
        hp1=heel_at(n+1); A1=hp1+PR(16.0)@g['h_off']
        s_=ease(u); A=A0.lerp(A1,s_); A.z+=0.075*lift_profile(u)
        return dict(mode='swing',u=u,th=th,ankle=A,ph=ph)
    def Kst(ph):   # stance knee flex from her curve (clamped 4-22 deg)
        return max(6.0,min(15.0,cur('knee_L',ph,10.0))) if CV.get('knee_L') else 10.0
    def pelvis(t):
        ph=(t/T_)%1.0
        roll=max(-4.5,min(4.5,centred('pelvis_roll',ph))) if CV.get('pelvis_roll') else -2.5*math.cos(2*math.pi*ph)
        yaw=max(-8.0,min(8.0,centred('pelvis_yaw',ph))) if CV.get('pelvis_yaw') else 6*math.sin(2*math.pi*ph)
        sway=max(-0.015,min(0.015,centred('sway_m',ph)*0.6)) if CV.get('sway_m') else 0.008*math.cos(2*math.pi*ph)
        shy=(centred('shoulder_yaw',ph) if CV.get('shoulder_yaw') else -9*math.sin(2*math.pi*ph))
        return roll,yaw,sway,max(-11.0,min(11.0,shy-yaw)),ph
    def pose_pelvis(t,dz):
        relaxed(); roll,yaw,sway,chy,ph=pelvis(t)
        hip_drop(dz,sway,hipy(t)); wrot('Hips',-yaw,'Z'); wrot('Hips',-roll,'Y')
        return roll,yaw,sway,chy,ph
    # pre-pass: hip height each frame so every stance leg reaches its planted foot with her stance knee bend
    NT=NF+WARM+12; HZ=[]
    for f in range(NT):
        t=max(f-WARM,0)/fps; pose_pelvis(t,0.0); best=9.0
        for sd in ('Left','Right'):
            st_=foot_state(sd,t)
            if st_['mode']!='stance': continue
            hj=PB[sd+' leg'].head; D_=math.sqrt(Lt*Lt+Ls*Ls+2*Lt*Ls*math.cos(math.radians(Kst(st_['ph'])))); D_=min(D_,0.995*LEG)
            h=math.hypot(hj.x-st_['ankle'].x,hj.y-st_['ankle'].y); need=st_['ankle'].z+math.sqrt(max(D_*D_-h*h,0.01))
            best=min(best,need-(hj.z-PB['Hips'].head.z)-H0)
        HZ.append(best if best<5 else (HZ[-1] if HZ else 0.0))
    HZ=np.array(HZ); kk=np.exp(-0.5*(np.arange(-4,5)/1.8)**2); kk/=kk.sum(); HZs=np.minimum(np.convolve(np.pad(HZ,4,mode='edge'),kk,'valid'),HZ)-0.002
    info['hip_dz_range_m']=[round(float(HZs.min()),3),round(float(HZs.max()),3)]
    REST_HEAD=None
    def elbow_angle(sd):
        a_=PB[sd+' arm']; e_=PB[sd+' elbow']; u1=(a_.tail-a_.head).normalized(); u2=(e_.tail-e_.head).normalized(); return math.degrees(u1.angle(u2))
    def set_elbow(sd,target):
        for _ in range(3):
            cu=elbow_angle(sd); dlt=target-cu
            if abs(dlt)<0.5: break
            a_=PB[sd+' arm']; e_=PB[sd+' elbow']; u1=(a_.tail-a_.head).normalized(); u2=(e_.tail-e_.head).normalized(); ax=u1.cross(u2)
            if ax.length<1e-4: ax=Vector((-1,0,0))
            wrot_v(sd+' elbow',dlt,ax.normalized())
    def walk(f):
        t=max(f-WARM,0)/fps; dz=float(HZs[min(f,NT-1)])
        roll,yaw,sway,chy,ph=pose_pelvis(t,dz)
        wrot('Spine',0.4*chy,'Z'); wrot('Chest',-0.6*chy*0+0.6*chy,'Z'); wrot('Chest',-2.0,'X')     # chest lifted a touch, shoulders counter the hips
        st={}
        for sd in ('Left','Right'):
            s_=foot_state(sd,t); hj=PB[sd+' leg'].head.copy(); sg=1 if sd=='Left' else -1
            pole=hj+Vector((sg*0.07,-1.0,0.0))                          # knee points forward over the toes, a hair outward (no knock-knee)
            ik2(sd+' leg',sd+' knee',s_['ankle'],pole)
            g=GEO[sd]; d0=g['adir'].copy(); d0.x=0.0; align(sd+' ankle',PR(s_['th'])@d0,cap=80)
            if sd+' toe' in PB:
                td=g['tdir'].copy(); td.x=0.0
                if s_['th']<0 and s_['mode']=='stance': align(sd+' toe',td,cap=60)            # toes stay flat on the floor through heel-off
                elif s_['mode']=='swing' and s_['u']<0.25: align(sd+' toe',PR(-42.0*(1-s_['u']/0.25)*0.5)@td,cap=60)
            st[sd]=s_
        # arms: her swing curve (shape + timing) scaled into 10-20 deg, elbows 10-20 deg, relaxed curled fingers (from relaxed())
        for sd in ('Left','Right'):
            key='arm_'+sd[0]
            if CV.get(key): a_=centred(key,ph)*scale_to(key,10.0,16.0)
            else: a_=15*math.sin(2*math.pi*(ph+(0.5 if sd=='Left' else 0.0)))
            wrot(sd+' arm',-a_,'X')
            ek='elbow_'+sd[0]; tgt=max(10.0,min(20.0,cur(ek,ph,14.0)+ (0.25*max(0.0,a_)) )) if CV.get(ek) else 12+4*max(0.0,math.sin(2*math.pi*ph))
            set_elbow(sd,tgt)
        # shoulders level over the rolling pelvis (runway posture), then head level and looking down the runway
        la=PB['Left arm'].head; ra=PB['Right arm'].head; wrot('Chest',math.degrees(math.atan2(la.z-ra.z,la.x-ra.x))*0.9,'Y')
        hq=(B.matrix_world.to_3x3()@PB['Head'].matrix.to_3x3()).to_quaternion()
        if REST_HEAD is not None:
            q=REST_HEAD@hq.inverted(); qrot('Neck',q,0.5); hq=(B.matrix_world.to_3x3()@PB['Head'].matrix.to_3x3()).to_quaternion(); q=REST_HEAD@hq.inverted(); qrot('Head',q,1.0)

        return st
    relaxed(); REST_HEAD=(B.matrix_world.to_3x3()@PB['Head'].matrix.to_3x3()).to_quaternion()
    # framing: fixed runway camera at the end of the runway, she walks toward it
    pts=[]
    for f in range(0,NF+WARM,10):
        walk(f); pts+=[B.matrix_world@PB['Head'].tail,B.matrix_world@PB['Left toe'].tail,B.matrix_world@PB['Right toe'].tail]
    meshes_eval(True); relaxed(); mnr,mxr=bbox(MESHES); FL_=mnr.z; top=mxr.z
    yend=min(p.y for p in pts); ystart=max(p.y for p in pts); Hh=top-FL_+0.12
    AZ=float(E.get('CW_AZ','-5')); LENS=float(E.get('CW_LENS','50')); dist=Hh*1.08/(24/LENS)
    HXW=(B.matrix_world@Vector((0,0,0))).x; YW0=(B.matrix_world@Vector((0,Y0,0))).y; YW1=(B.matrix_world@Vector((0,Y0-1.0,0))).y; VW=YW0-YW1      # world metres per armature metre along the walk
    def cam_at(t):
        hy=YW0-VW*v*t; aim=Vector((HXW,hy,FL_+Hh/2-0.04)); ca=math.radians(AZ)
        cam.location=aim+Vector((math.sin(ca)*dist,-math.cos(ca)*dist,Hh*0.04)); cam.rotation_euler=(aim-cam.location).to_track_quat('-Z','Y').to_euler()
        cam.data.lens=LENS; cam.data.sensor_fit='VERTICAL'; cam.data.sensor_height=24; cam.data.clip_start=0.01; cam.data.clip_end=200; upd()
    def cam_fixed(): cam_at(0.0)
    meshes_eval(False); bones=phys_bones(); SIM=spring_sim(walk,NF+WARM,fps,bones)
    meshes_eval(True); cam_fixed()
    info['cam']={'mode':'tracking dolly at her speed','az_deg':AZ,'lens':LENS,'dist_m':round(dist,3),'floor_world_z':FL_}
    # floor grid (world) for the overlay: 25 cm cells
    gx=[]; 
    for i in range(-6,7): gx.append([[HXW+i*0.25,ystart+0.6,FL_],[HXW+i*0.25,yend-0.6,FL_]])
    yy=ystart+0.6
    while yy>yend-0.6: gx.append([[HXW-1.5,yy,FL_],[HXW+1.5,yy,FL_]]); yy-=0.25
    info['floor_grid_world']=gx
    # face points rigid to the head (from her head mesh at rest), heels rigid to the ankles
    relaxed(); meshes_eval(True)
    HW=B.matrix_world@PB['Head'].matrix; HWi=HW.inverted(); co=ev_co(FH)
    try:
        le=B.matrix_world@PB['LeftEye'].head if 'LeftEye' in PB else None; re_=B.matrix_world@PB['RightEye'].head if 'RightEye' in PB else None
        cx_=float((le.x+re_.x)/2) if le else float(np.median(co[:,0])); ez=float((le.z+re_.z)/2) if le else float(np.percentile(co[:,2],75))
        mid=co[np.abs(co[:,0]-cx_)<0.006]; band=mid[(mid[:,2]<ez)&(mid[:,2]>ez-0.07)]; nose=band[np.argmin(band[:,1])] if len(band) else mid[np.argmin(mid[:,1])]
        fr_=mid[(mid[:,1]<nose[1]+0.03)&(mid[:,2]<nose[2])&(mid[:,2]>nose[2]-0.10)]; chin=fr_[np.argmin(fr_[:,2])] if len(fr_) else nose-np.array([0,0,0.06])
        eb=co[np.abs(co[:,2]-ez)<0.012]; earL=eb[np.argmax(eb[:,0])]; earR=eb[np.argmin(eb[:,0])]
        mo=nose+(chin-nose)*0.42; FACEW={'nose':nose,'chin':chin,'earL':earL,'earR':earR,'mouthL':mo+np.array([0.021,0.004,0]),'mouthR':mo-np.array([0.021,-0.004,0])}
        if le:
            for nm_,p_ in (('eyeL',le),('eyeR',re_)): FACEW[nm_]=np.array(tuple(p_))
    except Exception as ex:
        log('face pts fallback',repr(ex)[:200]); hh=B.matrix_world@PB['Head'].head; ht=B.matrix_world@PB['Head'].tail; c_=hh+(ht-hh)*0.35
        FACEW={'nose':np.array(tuple(c_+Vector((0,-0.09,0)))),'chin':np.array(tuple(c_+Vector((0,-0.07,-0.07)))),'earL':np.array(tuple(c_+Vector((0.075,0,0.01)))),'earR':np.array(tuple(c_+Vector((-0.075,0,0.01)))),
               'mouthL':np.array(tuple(c_+Vector((0.02,-0.085,-0.035)))),'mouthR':np.array(tuple(c_+Vector((-0.02,-0.085,-0.035))))}
    FACEL={k:(HWi@Vector(tuple(map(float,p_)))) for k,p_ in FACEW.items()}
    log('face pts',{k:[round(float(x),3) for x in p_] for k,p_ in FACEW.items()})
    HEELL={sd:GEO[sd]['heel_local'] for sd in ('Left','Right')}
    def W(n,which='h'): return B.matrix_world@(PB[n].head if which=='h' else PB[n].tail)
    def mp33():
        HWc=B.matrix_world@PB['Head'].matrix; fw={k:HWc@v_ for k,v_ in FACEL.items()}
        eyeL=fw.get('eyeL',fw['nose']); eyeR=fw.get('eyeR',fw['nose']); dx=Vector((0.012,0,0))
        heelL=(B.matrix_world@PB['Left ankle'].matrix)@HEELL['Left']; heelR=(B.matrix_world@PB['Right ankle'].matrix)@HEELL['Right']
        if D4 and 'Heel_L' in PB: heelL=W('Heel_L','t'); heelR=W('Heel_R','t')
        P=[fw['nose'],eyeL-dx,eyeL,eyeL+dx,eyeR+dx,eyeR,eyeR-dx,fw['earL'],fw['earR'],fw['mouthL'],fw['mouthR'],
           W('Left arm'),W('Right arm'),W('Left elbow'),W('Right elbow'),W('Left wrist'),W('Right wrist'),
           W('LittleFinger1_L'),W('LittleFinger1_R'),W('IndexFinger1_L'),W('IndexFinger1_R'),W('Thumb1_L'),W('Thumb1_R'),
           W('Left leg'),W('Right leg'),W('Left knee'),W('Right knee'),W('Left ankle'),W('Right ankle'),heelL,heelR,W('Left toe','t'),W('Right toe','t')]
        return P,fw
    def hand21(s):
        P=[W(('Left' if s=='L' else 'Right')+' wrist')]
        P+=[W(f'Thumb0_{s}'),W(f'Thumb1_{s}'),W(f'Thumb2_{s}'),W(f'Thumb2_{s}','t')]
        for fn in ('IndexFinger','MiddleFinger','RingFinger','LittleFinger'): P+=[W(f'{fn}1_{s}'),W(f'{fn}2_{s}'),W(f'{fn}3_{s}'),W(f'{fn}3_{s}','t')]
        return P
    def px(p): c=w2c(sc,cam,p); return [round(c.x,5),round(1-c.y,5)]
    trk={}; M={'slide_mm':0.0,'foot_line_gap_cm':[],'cross':0,'knee_gap_midstance_cm':[],'knee_over_toe_cm':[],'elbow_deg':[],'hip_sway_cm':[],'head_roll_deg':[],'head_pitch_deg':[],'heel_strike_deg':[],'toe_off_deg':[]}
    PL={}
    for f in frames_of(NF):
        t0_=time.time(); meshes_eval(False); st=walk(f+WARM); ang=apply_springs(SIM,f+WARM); cam_at(f/fps)
        e={'stance':[sd for sd in st if st[sd]['mode']=='stance']}
        for sd in ('Left','Right'):
            s_=st[sd]
            if s_['mode']=='stance':
                key=(sd,round(s_['heel'].y,4))
                # the pivot that should be fixed: heel during heel-rocker, ball after (measured from the real bones)
                if s_['th']>0: cur_p=(B.matrix_world@PB[sd+' ankle'].matrix)@HEELL[sd]; ref=B.matrix_world@s_['heel']; tag='heel'
                else: cur_p=W(sd+' toe'); ref=B.matrix_world@Vector((s_['ball'].x,s_['ball'].y,PB[sd+' toe'].head.z)) if False else None; tag='ball'
                if tag=='ball':
                    k2=key+('ball',)
                    if k2 not in PL: PL[k2]=cur_p.copy()
                    ref=PL[k2]
                dxy=(Vector((cur_p.x,cur_p.y))-Vector((ref.x,ref.y))).length*1000; M['slide_mm']=max(M['slide_mm'],dxy); e.setdefault('slide_mm',{})[sd]=round(dxy,2)
                if s_['u']<0.03: M['heel_strike_deg'].append(round(s_['th'],1))
                if s_['u']>0.97: M['toe_off_deg'].append(round(s_['th'],1))
        aL=W('Left ankle'); aR=W('Right ankle'); gap=(aL.x-aR.x)*100; e['foot_line_gap_cm']=round(gap,2); M['foot_line_gap_cm'].append(round(gap,2))
        if gap<=0: M['cross']+=1
        kL=W('Left knee'); kR=W('Right knee'); kg=(kL-kR).length*100; e['knee_gap_cm']=round(kg,2)
        for sd in ('Left','Right'):
            s_=st[sd]
            if s_['mode']=='stance' and 0.35<s_['u']<0.6: M['knee_gap_midstance_cm'].append(round(kg,2))
            kn=W(sd+' knee'); tmid=(W(sd+' ankle')+W(sd+' toe','t'))/2; M['knee_over_toe_cm'].append(round(abs(kn.x-tmid.x)*100,2))
        ea=[round(elbow_angle(sd),1) for sd in ('Left','Right')]; e['elbow_deg']=ea; M['elbow_deg']+=ea
        hx=W('Hips').x*100; M['hip_sway_cm'].append(round(hx,2))
        HWc=(B.matrix_world.to_3x3()@PB['Head'].matrix.to_3x3()); upv=HWc@Vector((0,1,0)); fv=HWc@Vector((0,0,1))
        e['head_up']=[round(x,3) for x in upv]
        nk=(B.matrix_world.to_3x3()@PB['Neck'].matrix.to_3x3())@Vector((0,1,0)); e['neck_tilt_deg']=round(math.degrees(math.acos(max(-1,min(1,nk.normalized().z)))),1); hp_=W('Head'); e['head_off_cm']=round((hp_.x-(W('Left arm').x+W('Right arm').x)/2)*100,1)
        xv=HWc@Vector((1,0,0)); xv0=(B.matrix_world.to_3x3()@REST_HEAD.to_matrix())@Vector((1,0,0)) if False else None
        M['head_roll_deg'].append(round(math.degrees(math.asin(max(-1,min(1,xv.normalized().z)))),2))
        la_=W('Left arm'); ra_=W('Right arm'); M.setdefault('shoulder_roll_deg',[]).append(round(math.degrees(math.atan2(la_.z-ra_.z,la_.x-ra_.x)),2)); M['head_pitch_deg'].append(round(math.degrees(math.atan2(upv.y,upv.z)),2))
        render(OUT+f'/f{f:03d}.jpg')
        e['max_back_hair_deg']=round(max([v_ for k_,v_ in ang.items() if k_.startswith('Back hair')] or [0]),1); e['s']=round(time.time()-t0_,1)
        if f%3==0:
            try: meshes_eval(True); e['clip']=clip_flags()
            except Exception as ex: e['clip_error']=str(ex)[:200]
        P33,fw=mp33()
        trk[f]={'mp33_px':[px(p) for p in P33],'mp33_w':[[round(c,4) for c in p] for p in P33],'hands':{s:[px(p) for p in hand21(s)] for s in 'LR'},
                'contact':{'L':st['Left']['mode']=='stance','R':st['Right']['mode']=='stance'},'pitch':{'L':round(st['Left']['th'],1),'R':round(st['Right']['th'],1)},
                'face':{k:px(v_) for k,v_ in fw.items()},'grid_px':[[px(Vector(a_)),px(Vector(b_))] for a_,b_ in gx],'cam':[round(c,4) for c in cam.location],'hips_w':[round(c,4) for c in W('Hips')],'yaw':round(pelvis(max(f,0)/fps)[1],2),'roll':round(pelvis(max(f,0)/fps)[0],2)}
        info['frames'][f]=e; log('frame',f,{k:e[k] for k in e if k!='head_up'})
    info['metrics_raw']=M
    json.dump(trk,open(OUT+f'/track-shard{SH}.json','w'))
# ======================= DANCE2: her V4 mocap of the TikTok (body world points + contacts) -> Jena, arms kept out of the torso, planted feet IK-locked =======================
elif MODE=='dance2':
    LM=json.load(open(DATA)); FR=LM['w']; NF=len(FR); fps=LM['fps']; WARM=30
    if D4: exec(open('avatar-v3/d4/filt.py').read(),globals())
    exec(open('avatar-v3/anim10c/contact.py').read(),globals())   # dance3 (worker 41c5b341): vertex-level hand/foot contact tools
    PMIN=float(E.get('HEAD_PITCH_MIN','3.0'))   # chin never below level+3 deg, so her bangs don't hide her face
    rest(); HEAD0=PB['Head'].matrix.to_3x3().copy(); _tf=(PB['Left toe'].tail-PB['Left ankle'].head); _tf.z=0; HEADF0=_tf.normalized()
    log('head fwd0 (arm space, from the feet)',[round(x,3) for x in HEADF0])
    # ---- dance3 #11 tracking: every channel the V4 mocap file has (audit Oct 19: pelvis track, 2D hip travel, hand landmarks, shoulder shrug were unused) ----
    _k5=np.ones(5)/5; _sm5=lambda a: np.convolve(np.pad(np.asarray(a,dtype=float),2,mode='edge'),_k5,mode='valid')
    _k31=np.ones(31)/31; _mm31=lambda a: np.convolve(np.pad(np.asarray(a,dtype=float),15,mode='edge'),_k31,mode='valid')
    _PR=LM.get('pelvis_rpy') or [{'roll':0,'pitch':0,'yaw':0}]*NF
    _pp=np.array([d['pitch'] for d in _PR],dtype=float); _pr=np.array([d['roll'] for d in _PR],dtype=float)
    PELV={'pitch':(_pp-np.median(_pp))*1.15,'roll':(_pr-np.median(_pr))*1.15}
    _B2=np.array(LM.get('body2d_px') or [[[0,0]]*33]*NF,dtype=float); _W3=np.array(FR,dtype=float)
    _tpx=np.linalg.norm((_B2[:,11]+_B2[:,12])/2-(_B2[:,23]+_B2[:,24])/2,axis=1).mean(); _tm=np.linalg.norm((_W3[:,11]+_W3[:,12])/2-(_W3[:,23]+_W3[:,24])/2,axis=1).mean()
    _mpp=_tm/max(_tpx,1e-6); _hy=(_B2[:,23,1]+_B2[:,24,1])/2
    BOUNCE=np.clip(-(_hy-_mm31(_hy))*_mpp,-0.20 if D4 else -0.12,0.10 if D4 else 0.03)      # m, + = up (image y is down); 1 s moving mean removed
    log('tracking: pelvis pitch/roll delta ranges',round(float(np.ptp(PELV['pitch'])),1),round(float(np.ptp(PELV['roll'])),1),'bounce range cm',round(float(np.ptp(BOUNCE))*100,1),'m/px',round(float(_mpp),5))
    _HP=LM.get('hands_px') or [{}]*NF; FCURL={}
    _FI={'Thumb':(1,2,3,4),'IndexFinger':(5,6,7,8),'MiddleFinger':(9,10,11,12),'RingFinger':(13,14,15,16),'LittleFinger':(17,18,19,20)}
    def _ang2(a,b):
        na=np.linalg.norm(a); nb=np.linalg.norm(b)
        if na<1e-6 or nb<1e-6: return 0.0
        return float(np.degrees(np.arccos(np.clip(np.dot(a,b)/(na*nb),-1,1))))
    for _sd,_k in (('Left','L'),('Right','R')):
        for _fn,_ix in _FI.items():
            A=[[],[],[]]
            for f_ in range(NF):
                h_=_HP[f_].get(_k) if isinstance(_HP[f_],dict) else None
                if not h_ or len(h_)<21:
                    for j in range(3): A[j].append(np.nan)
                    continue
                P=np.array(h_,dtype=float); ch=[0]+list(_ix)
                for j in range(3): A[j].append(_ang2(P[ch[j+1]]-P[ch[j]],P[ch[j+2]]-P[ch[j+1]]))
            for j in range(3):
                a_=np.array(A[j]); m_=np.isnan(a_)
                if m_.all(): a_[:]=15.0
                elif m_.any(): a_[m_]=np.interp(np.flatnonzero(m_),np.flatnonzero(~m_),a_[~m_])
                A[j]=np.clip(a_ if D4 else _sm5(a_),3.0,95.0)
            FCURL[(_sd,_fn)]=A
    if D4:
        # D5 hands: a relaxed hand moves its fingers together (each long finger 50% toward the four-finger mean: no spider splay),
        # never flatter than a resting hand (MCP>=20, PIP>=28, DIP>=15; thumb >=8), and a light zero-phase smoothing (sigma 1 frame) against flicker
        _K5=np.array([0.054,0.244,0.404,0.244,0.054])
        def _gf5(a,s,mode=None): return np.convolve(np.pad(np.asarray(a,float),2,mode='edge'),_K5,'valid')
        LONG5=('IndexFinger','MiddleFinger','RingFinger','LittleFinger'); FLOOR5=(20.0,28.0,15.0)
        for _sd in ('Left','Right'):
            if not all((_sd,f_) in FCURL for f_ in LONG5): continue
            for j in range(3):
                Mn=np.mean([np.asarray(FCURL[(_sd,f_)][j],float) for f_ in LONG5],axis=0)
                for f_ in LONG5:
                    a_=0.5*np.asarray(FCURL[(_sd,f_)][j],float)+0.5*Mn; FCURL[(_sd,f_)][j]=np.maximum(_gf5(a_,1.0,mode='nearest'),FLOOR5[j])
            if (_sd,'Thumb') in FCURL:
                for j in range(3): FCURL[(_sd,'Thumb')][j]=np.maximum(_gf5(np.asarray(FCURL[(_sd,'Thumb')][j],float),1.0,mode='nearest'),8.0)
    log('tracking: finger curl means (deg)',{f'{k[0][0]}{k[1][:3]}':[round(float(np.mean(x)),1) for x in v] for k,v in FCURL.items()})
    _ms3=(_W3[:,11]+_W3[:,12])/2; _hm3=(_W3[:,23]+_W3[:,24])/2; _up3=_ms3-_hm3; _up3=_up3/np.linalg.norm(_up3,axis=1)[:,None]
    SHRUG={}
    for _sd,_i in (('Left',11),('Right',12)):
        r_=np.einsum('ij,ij->i',_W3[:,_i]-_ms3,_up3); SHRUG[_sd]=_sm5(r_-np.median(r_))   # MP units ~ m, + = shoulder risen along the torso (sign checked at use)
    log('tracking: shrug ranges cm',{k:round(float(np.ptp(v))*100,1) for k,v in SHRUG.items()})
    def finger_drive(f):
        for sd in ('Left','Right'):
            s_=sd[0]
            for fn in ('Thumb','IndexFinger','MiddleFinger','RingFinger','LittleFinger'):
                A=FCURL.get((sd,fn))
                if A is None: continue
                for j,a_ in enumerate((A[0][f],A[1][f],A[2][f])):
                    n_=f'{fn}{j+1}_{s_}'
                    if n_ not in PB: continue
                    if fn=='Thumb' and j==2: continue
                    sg=FSIGN.get((s_,fn),FSIGN.get((sd,fn),1.0)) if isinstance(FSIGN,dict) else 1.0
                    wrot_v(n_,sg*float(a_)*(0.6 if fn=='Thumb' else 1.0),_lx(n_))
    SEG_GAIN={'chest':float(E.get('CHEST_GAIN','1.0'))}
    CUR_F=[0]
    def clavicles():
        # loose shoulders: each clavicle lifts with its arm (0.3 x elevation past 40 deg, <=18 deg)
        for sd in ('Left','Right'):
            n=sd+' shoulder'
            if n not in PB: continue
            ad=(PB[sd+' elbow'].head-PB[sd+' arm'].head).normalized(); el=math.degrees(math.asin(max(-1,min(1,ad.z))))+90.0
            lift=max(0.0,min(18.0,0.3*(el-40.0)))+max(-8.0,min(15.0,math.degrees(math.atan2(float(SHRUG[sd][CUR_F[0]])*1.3,0.15))))   # arm elevation + the source's own shrug
            if abs(lift)<0.5: continue
            ax=(PB[n].tail-PB[n].head).normalized().cross(Vector((0,0,1)))
            if ax.length<1e-5: continue
            ax.normalize(); z0=PB[sd+' arm'].head.z; wrot_v(n,lift,ax)
            if PB[sd+' arm'].head.z<z0: wrot_v(n,-2*lift,ax)
    def seg_rec(f,w_=None):
        # segment angles (deg) for the STIFF detector: hips yaw/roll, chest yaw/roll, shoulders (L/R elevation vs chest), neck pitch/roll, head
        def yr(v): return (math.degrees(math.atan2(v.y,v.x)),math.degrees(math.asin(max(-1,min(1,v.z/max(v.length,1e-6))))))
        hl=PB['Left leg'].head-PB['Right leg'].head; sl=PB['Left arm'].head-PB['Right arm'].head; ms_=(PB['Left arm'].head+PB['Right arm'].head)/2
        nk=PB['Head'].head-ms_; sh_=(PB['Left arm'].head.z-ms_.z,PB['Right arm'].head.z-ms_.z)
        J={'hips':yr(hl),'chest':yr(sl),'shoulders':(sh_[0]*100,sh_[1]*100),'neck':(tuple(head_rel_jena()[::2]) if D4 else yr(Vector((nk.y,nk.x,nk.z))))}
        w_=FR[f]; LH_,RH_,LS_,RS_=L(w_,23),L(w_,24),L(w_,11),L(w_,12); ms2=(LS_+RS_)/2; em=(L(w_,7)+L(w_,8))/2; nk2=em-ms2
        S={'hips':yr(LH_-RH_),'chest':yr(LS_-RS_),'shoulders':((LS_.z-ms2.z)*100,(RS_.z-ms2.z)*100),'neck':((float(SRC_HPYR[f][0]),float(SRC_HPYR[f][2])) if D4 else yr(Vector((nk2.y,nk2.x,nk2.z))))}
        return {k:[round(x,2) for x in v] for k,v in J.items()},{k:[round(x,2) for x in v] for k,v in S.items()}
    def pelvis_rec(f):
        # her pelvis: yaw/roll of the hip line (deg) + hips position (cm) ; the source's hip line yaw/roll + mid-hip relative to the mid-ankle (cm)
        hl=PB['Left leg'].head-PB['Right leg'].head; hp=(PB['Left leg'].head+PB['Right leg'].head)/2; an=(PB['Left ankle'].head+PB['Right ankle'].head)/2
        w_=FR[f]; LH_,RH_=L(w_,23),L(w_,24); sh_=LH_-RH_; mh_=(LH_+RH_)/2; ma_=(L(w_,27)+L(w_,28))/2
        dg=lambda v: (round(math.degrees(math.atan2(v.y,v.x)),1),round(math.degrees(math.asin(max(-1,min(1,v.z/max(v.length,1e-6))))),1))
        return {'yaw_roll':dg(hl),'sway_cm':(round((hp.x-an.x)*100,1),round((hp.y-an.y)*100,1)),'src_yaw_roll':dg(sh_),'src_sway_cm':(round((mh_.x-ma_.x)*100,1),round((mh_.y-ma_.y)*100,1))}
    KF0={}; UP0={}
    for _sd in ('Left','Right'):
        KF0[_sd]=PB[_sd+' knee'].matrix.to_3x3().inverted()@HEADF0; UP0[_sd]=PB[_sd+' ankle'].matrix.to_3x3().inverted()@Vector((0,0,1))
    exec(open('avatar-v3/selfmodel/selfmodel.py').read(),globals()); sm_init()   # body self-model (rest pose)
    log('RIG BONES',len(B.pose.bones),[b_.name for b_ in B.pose.bones])
    meshes_eval(True); HH={}
    for _sd in ('Left','Right'):
        _fs=foot_stats(_sd,0.0); HH[_sd]=float(_fs['heel_mm']-_fs['ball_mm'])
    meshes_eval(False); log('high-heel foot: bind-pose heel lift above the ball (mm)',HH)
    if D4:
        HH={k:max(v,30.0) for k,v in HH.items()}; log('D5 high-heel: bind lift ~5 mm is flat-looking, planted feet hold a 30 mm heel lift (ball + toes down)',HH)
        _vgn5={g.index:g.name for g in BODY.vertex_groups}
        def _dom5(bn):
            out=[]
            for v in BODY.data.vertices:
                best=None; w=0.0
                for ge in v.groups:
                    if ge.weight>w: w=ge.weight; best=_vgn5.get(ge.group)
                if best==bn: out.append(v.index)
            return np.array(out,dtype=int)
        TOEV5={sd:_dom5(sd+' toe') for sd in ('Left','Right')}
        def toe_settle5(sd,lo=0.0003,hi=0.0022):
            n=sd+' toe'
            if n not in PB or len(TOEV5[sd])==0: return None
            d=(PB[n].tail-PB[n].head); fl=Vector((d.x,d.y,0.0))
            if fl.length>1e-6: align(n,fl.normalized(),cap=60)
            lat=fl.normalized().cross(Vector((0,0,1))) if fl.length>1e-6 else Vector((1,0,0)); hist=[]
            for k in range(12):
                meshes_eval(True); z=float(body_co()[TOEV5[sd]][:,2].min())-FLOOR; meshes_eval(False); hist.append(round(z*1000,1))
                if lo<=z<=hi: break
                st=1.5 if z<lo else -1.5; z0=PB[n].tail.z; wrot_v(n,st,lat)
                if (PB[n].tail.z-z0)*(1 if z<lo else -1)<0: wrot_v(n,-2*st,lat)
            return hist
        def toe_free5(sd,lim=10.0):
            n=sd+' toe'
            if n not in PB: return None
            q=PB[n].matrix_basis.to_quaternion(); ang=math.degrees(2*math.acos(min(1.0,abs(q.w))))
            if ang<=lim: return round(ang,1)
            PB[n].matrix_basis=Quaternion().slerp(q,lim/ang).to_matrix().to_4x4(); upd(); return (round(ang,1),lim)
    def ankle_angles(sd):
        # twist: foot direction vs the knee's facing, about the shin; inv: shin leaning across the sole (+ = toward her outside = inversion); flex: ankle bend vs rest
        a=(PB[sd+' knee'].tail-PB[sd+' knee'].head).normalized()
        kf=PB[sd+' knee'].matrix.to_3x3()@KF0[sd]; ff=(PB[sd+' toe'].tail-PB[sd+' ankle'].head) if sd+' toe' in PB else (PB[sd+' ankle'].tail-PB[sd+' ankle'].head)
        kp=(kf-a*kf.dot(a)); fp=(ff-a*ff.dot(a))
        if kp.length<1e-6 or fp.length<1e-6: return 0.0,0.0
        kp.normalize(); fp.normalize(); tw=math.degrees(math.atan2(kp.cross(fp).dot(a),kp.dot(fp)))
        n=PB[sd+' ankle'].matrix.to_3x3()@UP0[sd]; lat=ff.normalized().cross(n).normalized(); sgo=1.0 if sd=='Left' else -1.0
        inv=math.degrees(math.asin(max(-1,min(1,a.dot(lat)))))*sgo
        return round(tw,1),round(inv,1)
    def head_pitch():
        f_=(PB['Head'].matrix.to_3x3()@HEAD0.inverted())@HEADF0; return math.degrees(math.asin(max(-1,min(1,f_.z)))),f_
    def head_up():
        for _ in range(3):
            p_,f_=head_pitch()
            if p_>=PMIN-0.05: return
            ax=f_.cross(Vector((0,0,1)))
            if ax.length<1e-5: return
            ax.normalize(); need=PMIN-p_; wrot_v('Neck',need*0.4,ax); wrot_v('Head',need*0.6,ax)
    SRCH=[None]
    def src_head():
        # source dancer's head per frame, from her ears and nose: roll (ear line tilt), yaw (ear line heading), pitch (ears->nose), 5-frame smoothed
        if SRCH[0] is None:
            R_=[];Y_=[];P__=[]
            for w_ in FR:
                e7=L(w_,7); e8=L(w_,8); nz=L(w_,0); lat=e7-e8; em=(e7+e8)/2; fw=nz-em
                R_.append(math.degrees(math.asin(max(-1,min(1,lat.z/max(lat.length,1e-6))))))
                Y_.append(math.degrees(math.atan2(lat.y,lat.x)))
                P__.append(math.degrees(math.atan2(fw.z,math.hypot(fw.x,fw.y))))
            def sm(a):
                a=np.array(a,dtype=float); a=np.unwrap(np.radians(a)); a=np.degrees(a); k_=np.ones(5)/5; pad=np.pad(a,2,mode='edge'); return np.convolve(pad,k_,mode='valid')
            R_,Y_,P__=sm(R_),sm(Y_),sm(P__)
            E7=np.array([tuple(L(w_,7)) for w_ in FR]); E8=np.array([tuple(L(w_,8)) for w_ in FR]); k5=np.ones(5)/5
            sm3=lambda A: np.stack([np.convolve(np.pad(A[:,i],2,mode='edge'),k5,mode='valid') for i in range(3)],axis=1)
            SRCH[0]=dict(roll=R_,yaw=Y_-float(np.median(Y_)),pitch=P__,pmed=float(np.median(P__)),e7=sm3(E7),e8=sm3(E8))
            log('source head ranges roll',round(float(R_.min()),1),round(float(R_.max()),1),'yaw',round(float(SRCH[0]['yaw'].min()),1),round(float(SRCH[0]['yaw'].max()),1),'pitch',round(float(P__.min()),1),round(float(P__.max()),1),'median pitch',round(SRCH[0]['pmed'],1))
        return SRCH[0]
    def head_follow(f):
        # pitch = a lifted base (PMIN+5) plus the source's own nod about its median; never below PMIN. roll/yaw stay as the ears drove them.
        sh_=src_head(); nod=max(-40.0,min(40.0,float(sh_['pitch'][f])-sh_['pmed'])); tgt=max(-8.0,PMIN+6.0+nod)   # 1.0x the source nod; floor -8 deg = only where bangs would hide her face
        for _ in range(3):
            p_,f_=head_pitch(); need=tgt-p_
            if abs(need)<0.1: break
            ax=f_.cross(Vector((0,0,1)))
            if ax.length<1e-5: break
            ax.normalize(); wrot_v('Neck',need*0.4,ax); wrot_v('Head',need*0.6,ax)
        return tgt
    def head_rpy():
        Rd=PB['Head'].matrix.to_3x3()@HEAD0.inverted(); f_=Rd@HEADF0; lat0=Vector((0,0,1)).cross(HEADF0).normalized(); l_=Rd@lat0
        yaw=math.degrees(math.atan2(f_.y,f_.x)-math.atan2(HEADF0.y,HEADF0.x)); yaw=(yaw+180)%360-180
        return round(math.degrees(math.asin(max(-1,min(1,l_.z)))),1),round(yaw,1),round(math.degrees(math.asin(max(-1,min(1,f_.z)))),1)
    def set_rot(n,R):
        if n not in PB: return
        q=(R@PB[n].matrix.to_3x3().inverted()).to_quaternion(); qrot(n,q)
    def mp2b(p): return Vector((p[0],p[2],-p[1]))
    # MediaPipe sometimes swaps her left/right for a few frames (she spins round 180 deg for no reason): detect by hip-line yaw and swap back
    PAIRS=[(1,4),(2,5),(3,6),(7,8),(9,10),(11,12),(13,14),(15,16),(17,18),(19,20),(21,22),(23,24),(25,26),(27,28),(29,30),(31,32)]
    def hyaw(w): h=mp2b(w[23])-mp2b(w[24]); return math.degrees(math.atan2(h.y,h.x))
    ys=[hyaw(w) for w in FR]; ref=float(np.median(ys[:15])); nsw=0; CT0=LM.get('contact')
    for k_ in range(NF):
        d_=(ys[k_]-ref+180)%360-180
        if abs(d_)>110:
            w=FR[k_]=[list(p) for p in FR[k_]]
            for a_,b_ in PAIRS: w[a_],w[b_]=w[b_],w[a_]
            if CT0 and CT0[k_]: CT0[k_]={'L':CT0[k_].get('R'),'R':CT0[k_].get('L'),**{kk:vv for kk,vv in CT0[k_].items() if kk not in('L','R')}}
            nsw+=1; ys[k_]=hyaw(FR[k_])
        ref=0.85*ref+0.15*ys[k_] if abs((ys[k_]-ref+180)%360-180)<60 else ref
    info['lr_swaps_fixed']=nsw; log('lr swaps fixed',nsw)
    ups=[];rts=[]
    for w in FR:
        P_l=[mp2b(p) for p in w]; ups.append(((P_l[11]+P_l[12])/2-(P_l[23]+P_l[24])/2).normalized()); rts.append((P_l[23]-P_l[24]).normalized())
    up=sum(ups,Vector()).normalized(); rt=sum(rts,Vector()); rt=(rt-up*rt.dot(up)).normalized(); fw=up.cross(rt)
    Mc=Matrix((rt,fw,up)).to_3x3()
    info['source_level_correction_deg']=round(math.degrees(Mc.to_quaternion().angle),1)
    def L(w,i): return Mc@mp2b(w[i])
    def rest_rot(n): return PB[n].bone.matrix_local.to_3x3()
    def cur_rot(n): return PB[n].matrix.to_3x3()@rest_rot(n).inverted()
    def frame_rot(xv,zv):
        x=xv.normalized(); z=(zv-x*zv.dot(x)).normalized(); y=z.cross(x); return Matrix((x,y,z)).transposed()
    def set_world_rot(n,Rt,frac=1.0,cap=180.0):
        d=(Rt@cur_rot(n).inverted()).to_quaternion(); qrot(n,d,frac,cap)
    # rest foot geometry (bind pose: feet flat)
    rest(); GEO={}
    meshes_eval(True); FLOORW=bbox([BODY])[0].z; meshes_eval(False); rest(); FLOOR=(B.matrix_world.inverted()@Vector((0,0,FLOORW))).z
    for sd in ('Left','Right'):
        an=PB[sd+' ankle']; ah=an.head.copy(); heel=Vector((ah.x,ah.y+0.045,FLOOR))
        GEO[sd]=dict(ankle_h=ah.z-FLOOR,adir=(an.tail-an.head),tdir=(PB[sd+' toe'].tail-PB[sd+' toe'].head),heel_local=(B.matrix_world@an.matrix).inverted()@(B.matrix_world@heel))
    def torso_pts(sd):
        el=PB[sd+' elbow']; wr=PB[sd+' wrist']; pts=[el.head.copy()]
        for k in (0.25,0.5,0.75,1.0): pts.append(el.head.lerp(el.tail,k))
        pts+=[wr.tail.copy(),PB['MiddleFinger3_'+sd[0]].tail.copy() if 'MiddleFinger3_'+sd[0] in PB else wr.tail.copy()]
        return pts
    def arm_out_needed(sd,margin):
        # exact mesh test (arm tris inside her torso), pushing the arm straight out from her body in 3 deg steps
        key='Larm_vs_torso_tris' if sd=='Left' else 'Rarm_vs_torso_tris'; n=0
        meshes_eval(True); c0=clip_flags().get(key) or 0
        while c0>0 and n<16:
            meshes_eval(False); radial_push(sd,3,'arm'); n+=1; meshes_eval(True); c0=clip_flags().get(key) or 0
        meshes_eval(False); return n
    if D4: exec(open('avatar-v3/d4/d4core.py').read(),globals())
    ABD=None; CROTCH=[0]
    def pose_dance(f,offs=None,locks=None):
        rest(); CUR_F[0]=f; finger_drive(f)
        w=FR[f]; G=lambda i: L(w,i)
        LS,RS,LH,RH=G(11),G(12),G(23),G(24); mh=(LH+RH)/2; ms=(LS+RS)/2; upt=(ms-mh)
        # dance3 #10 (Saidie 11:17 "hips and head still stiff"): pelvis 1.15x the source roll, spine chain pelvis->lumbar->thoracic->neck->head with 2-4 frame overlap
        hlx=(LH-RH); hlx.z*=1.15
        Rh=frame_rot(hlx,Vector((0,0,1)).lerp(upt.normalized(),0.6)); set_world_rot('Hips',Rh)
        if D4: pelvis_yaw_extra(f)
        # pelvis track (V4 pelvis_rpy, 1.15x about its median): forward/back tilt (thrust) + extra side roll, signs checked on her own bones
        lat_=(PB['Left leg'].head-PB['Right leg'].head).normalized(); fwd_=lat_.cross(Vector((0,0,1))).normalized()
        dp=float(PELV['pitch'][f]); y0=PB['Spine'].head.y; wrot_v('Hips',dp,lat_)
        if dp!=0 and ((PB['Spine'].head.y-y0)*(1 if dp>0 else -1))>0: wrot_v('Hips',-2*dp,lat_)   # + pitch = top of pelvis forward (toward -Y, her front)
        dr=float(PELV['roll'][f])-(math.degrees(math.asin(max(-1,min(1,hlx.normalized().z))))-math.degrees(math.asin(max(-1,min(1,(LH-RH).normalized().z)))))*0.0
        z0=PB['Left leg'].head.z; wrot_v('Hips',dr*0.5,fwd_)
        if dr!=0 and ((PB['Left leg'].head.z-z0)*(1 if dr>0 else -1))<0: wrot_v('Hips',-dr,fwd_)   # + roll = her left hip up
        wl=FR[max(0,f-2)]; LSl,RSl=L(wl,11),L(wl,12); msl=(LSl+RSl)/2; uptl=(msl-(L(wl,23)+L(wl,24))/2)   # chest/shoulders lag the hips by 2 frames (overlap / follow-through)
        d0=(PB['Spine'].tail-PB['Spine'].head).normalized(); q=d0.rotation_difference(upt.normalized()); ql=d0.rotation_difference(uptl.normalized())
        qrot('Spine',q,0.40,60); qrot('Chest',ql,0.60,60)
        sl=(LSl-RSl); hl=(LH-RH); n_=upt.normalized(); sl_=(sl-n_*sl.dot(n_)).normalized(); hl_=(hl-n_*hl.dot(n_)).normalized()
        tw=math.degrees(math.atan2(hl_.cross(sl_).dot(n_),hl_.dot(sl_))); tw=max(-55,min(55,tw*SEG_GAIN['chest'])); wrot_v('Spine',tw*0.45,n_); wrot_v('Chest',tw*0.55,n_)
        if D4:
            spine_split(); head_drive(f)
        else:
            _sh=src_head(); fh_=max(0,f-3); e7=Vector(tuple(_sh['e7'][fh_])); e8=Vector(tuple(_sh['e8'][fh_]));   # head lags 3 frames
            ear=(e7+e8)/2; Rhd=frame_rot(e7-e8,n_.lerp((ear-ms).normalized(),0.6))   # 5-frame smoothed ears (no jitter overshoot)
            set_world_rot('Neck',Rhd,0.4,25); set_world_rot('Head',Rhd,1.0,40); head_follow(max(0,f-3))
        clavicles()
        for sd,(s,e_,wr,ix,px_) in (('Left',(11,13,15,19,17)),('Right',(12,14,16,20,18))):
            align(sd+' arm',G(e_)-G(s)); align(sd+' elbow',G(wr)-G(e_)); align(sd+' wrist',(G(ix)+G(px_))/2-G(wr),cap=40)
            if ABD is not None:
                radial_push(sd,ABD[sd][f],'arm')
            # never a hand in front of her crotch: if the source puts it there (her proportions differ), slide it out to her hip side
            hc_=(PB['Left leg'].head+PB['Right leg'].head)/2; hw_=(PB['Left leg'].head-PB['Right leg'].head).length
            hp_=(PB[sd+' wrist'].head+PB[sd+' wrist'].tail)/2; sg_=1 if sd=='Left' else -1
            if abs(hp_.x-hc_.x)<0.9*hw_ and hc_.z-0.28<hp_.z<hc_.z+0.10 and hp_.y<hc_.y+0.06:
                tgt_=PB[sd+' wrist'].head.copy(); tgt_.x=hc_.x+sg_*1.15*hw_
                ik2(sd+' arm',sd+' elbow',tgt_,PB[sd+' arm'].head+Vector((sg_*0.5,0.25,-0.2)))
                align(sd+' wrist',Vector((0,-0.2,-1)),cap=40); CROTCH[0]+=1
        if D4: wrist_twist(); upper_twist()
        for sd,(h_,k_,an,he,ft) in (('Left',(23,25,27,29,31)),('Right',(24,26,28,30,32))):
            align(sd+' leg',G(k_)-G(h_)); align(sd+' knee',G(an)-G(k_))
            fd=G(ft)-G(an); fd.z=min(fd.z,0.35*fd.length); align(sd+' ankle',fd,cap=55)
        if offs is not None:
            dx,dy,dz=offs[f]; hp=PB['Hips']; hp.matrix=Matrix.Translation(Vector((dx,dy,dz)))@hp.matrix; upd()
        if locks is not None:
            need=0.0   # a planted foot the leg can't reach would slide: lower her hips just enough first
            for sd in ('Left','Right'):
                lk=locks[sd][f]
                if lk is None or lk[1]<0.99: continue
                S0=PB[sd+' leg'].head; reach=(PB[sd+' leg'].length+PB[sd+' knee'].length)*0.985
                need=max(need,(lk[0]-S0).length-reach)
            if need>0: hip_drop(-min(need*1.2,0.15))
            lk_=[sd for sd in ('Left','Right') if locks[sd][f] is not None and locks[sd][f][1]>0.99]
            if len(lk_)==1:   # weight shift: the free side's hip drops ~4 deg (loaded leg takes the weight)
                fr_=('Right' if lk_[0]=='Left' else 'Left'); fwd_=(PB['Left leg'].head-PB['Right leg'].head).cross(Vector((0,0,1))).normalized()
                z0=PB[fr_+' leg'].head.z; wrot_v('Hips',4.0,fwd_)
                if PB[fr_+' leg'].head.z>z0: wrot_v('Hips',-8.0,fwd_)
            for sd in ('Left','Right'):
                lk=locks[sd][f]
                if lk is None: continue
                tgt,wgt,yawdir=lk; cur=PB[sd+' ankle'].head.copy(); T_=cur.lerp(tgt,wgt)
                kn=PB[sd+' knee'].head.copy(); hj=PB[sd+' leg'].head.copy(); pole=kn+(kn-(hj+T_)/2).normalized()*0.5
                ik2(sd+' leg',sd+' knee',T_,pole)
                if wgt>0.99:
                    d0=GEO[sd]['adir'].copy(); hz=Vector((yawdir.x,yawdir.y,0)).normalized(); hz0=Vector((d0.x,d0.y,0)).normalized()
                    q=hz0.rotation_difference(hz); align(sd+' ankle',q@d0,cap=60)
                    if sd+' toe' in PB: align(sd+' toe',q@GEO[sd]['tdir'],cap=60)
        if D4: face_drive(f); leg_capsules(locks,f)
    FOOT={'Left':('Left ankle','Left toe'),'Right':('Right ankle','Right toe')}
    def foot_pts(sd):
        a_,t_=FOOT[sd]; return [PB[a_].head.copy(),PB[t_].head.copy(),PB[t_].tail.copy()]
    rest(); REST_H={sd:[p.z for p in foot_pts(sd)] for sd in FOOT}
    # 1) arm abduction needed per frame (torso proxy with margin), smoothed + held so arms never pop
    raw={'Left':[0.0]*NF,'Right':[0.0]*NF}
    for f in range(0,NF,2):
        for sd in ('Left','Right'):
            pose_dance(f); v_=arm_out_needed(sd,0.055)*3.0; raw[sd][f]=v_
            if f+1<NF: raw[sd][f+1]=v_
    log('abd prepass done',{sd:max(raw[sd]) for sd in raw})
    ABD={}
    for sd in raw:
        a_=np.array(raw[sd]); mx=np.array([a_[max(0,i-5):i+6].max() for i in range(NF)]); k_=np.exp(-0.5*(np.arange(-5,6)/2.0)**2); k_/=k_.sum()
        ABD[sd]=np.maximum(np.convolve(np.pad(mx,5,mode='edge'),k_,'valid'),a_).tolist()
    info['arm_abduction_deg_max']={sd:round(max(ABD[sd]),1) for sd in ABD}
    # 2) grounding + stance root lock (as dance v1) on the corrected pose
    offs=[]; prev=None; off=Vector((0,0,0)); stance=[]; CT=LM.get('contact') or [None]*NF
    for f in range(NF):
        pose_dance(f)
        ch={sd:min(p.z-h for p,h in zip(foot_pts(sd),REST_H[sd])) for sd in FOOT}
        c_=CT[f] or {}; cs=[sd for sd in FOOT if c_.get(sd[0])]
        s=cs[0] if len(cs)==1 else min(ch,key=ch.get); dz=-ch[min(ch,key=ch.get)]; ball=PB[FOOT[s][1]].head.copy()
        if prev and prev[0]==s: off=Vector((prev[1].x-ball.x,prev[1].y-ball.y,0))
        offs.append([off.x,off.y,dz]); prev=(s,Vector((ball.x+off.x,ball.y+off.y,0))); stance.append(s)
    zz=np.array([o[2] for o in offs]); zs=np.convolve(np.pad(zz,2,mode='edge'),np.ones(5)/5,mode='valid'); zs=np.maximum(zs,zz)
    for i in range(NF): offs[i][2]=float(zs[i])
    # hips 1.15x the source sway: horizontal root offsets scaled about their 1 s moving mean (no extra smoothing on the pelvis)
    _ox=np.array([o[0] for o in offs]); _oy=np.array([o[1] for o in offs]); _k=np.ones(31)/31
    _mx=np.convolve(np.pad(_ox,15,mode='edge'),_k,mode='valid'); _my=np.convolve(np.pad(_oy,15,mode='edge'),_k,mode='valid')
    for i in range(NF): offs[i][0]=float(_mx[i]+1.15*(_ox[i]-_mx[i])); offs[i][1]=float(_my[i]+1.15*(_oy[i]-_my[i]))
    if D4:
        _zg=np.array([o[2] for o in offs]); _mg=_mm31(_zg)
        for i in range(NF): offs[i][2]=float(min(_zg[i],_mg[i]+BOUNCE[i]))
        info['d4_bounce_cm']={'source_2d_range':round(float(np.ptp(BOUNCE))*100,1),'grounding_only_range':round(float(np.ptp(_zg))*100,1),'applied_range':round(float(np.ptp([o[2] for o in offs]))*100,1)}; log('D4 bounce',info['d4_bounce_cm'])
    else:
        for i in range(NF): offs[i][2]=float(offs[i][2]+BOUNCE[i])   # the source's real hip bounce (2D track), knees absorb it on planted feet
    # 3) planted-foot spans: foot on the floor (<=12 mm) and slow (<0.35 m/s) for >=3 frames, or V4 says contact -> ankle IK-locked
    H_={sd:[] for sd in FOOT}; P_={sd:[] for sd in FOOT}; Y_={sd:[] for sd in FOOT}
    for f in range(NF):
        pose_dance(f,offs)
        for sd in FOOT:
            H_[sd].append(min(p.z-h for p,h in zip(foot_pts(sd),REST_H[sd]))); P_[sd].append(PB[FOOT[sd][0]].head.copy()); Y_[sd].append(PB[FOOT[sd][1]].tail-PB[FOOT[sd][0]].head)
    locks={sd:[None]*NF for sd in FOOT}; spans={}
    for sd in FOOT:
        pl=[]
        for f in range(NF):
            sp=(P_[sd][f]-P_[sd][max(f-1,0)]).length*fps if f>0 else 0.0
            c_=CT[f] or {}; pl.append((H_[sd][f]<=0.012 and sp<0.35) or bool(c_.get(sd[0])) or stance[f]==sd)
        f=0; S=[]
        while f<NF:
            if pl[f]:
                g=f
                while g+1<NF and pl[g+1]: g+=1
                if g-f+1>=3: S.append((f,g))
                f=g+1
            else: f+=1
        spans[sd]=S
        for a_,b_ in S:
            tgt=P_[sd][a_].copy(); tgt.z=FLOOR+GEO[sd]['ankle_h']; yd=Y_[sd][a_]
            for f in range(max(0,a_-2),min(NF,b_+3)):
                wgt=1.0 if a_<=f<=b_ else (1.0-abs(f-(a_ if f<a_ else b_))/3.0)
                if locks[sd][f] is None or wgt>locks[sd][f][1]: locks[sd][f]=(tgt,wgt,yd)
    info['planted_spans']={sd:spans[sd] for sd in spans}
    pts_all=[]; HXs=[]; HFs=[]
    for f in range(0,NF,3):
        pose_dance(f,offs,locks); hx_=(B.matrix_world@PB['Hips'].head).x; HXs.append(hx_); HFs.append(f)
        for n in ('Head','Hips','Left wrist','Right wrist','Left toe','Right toe','Left ankle','Right ankle'):
            p_=B.matrix_world@PB[n].tail; pts_all.append(Vector((p_.x-hx_,p_.y,p_.z)))
    mn=Vector([min(p[i] for p in pts_all) for i in range(3)]); mx=Vector([max(p[i] for p in pts_all) for i in range(3)])
    meshes_eval(True); relaxed(); mnr,mxr=bbox(MESHES); top=max(mx.z+0.15,mxr.z+0.02)
    lo=FLOORW-0.05; Hh=(top-lo); wid=(mx.x-mn.x)+0.3; need=max(Hh*1.08,wid*RH/RW); tgt=Vector(((mn.x+mx.x)/2,(mn.y+mx.y)/2,(top+lo)/2))
    # camera follows her hips sideways (smoothed), so she stays centred and big in frame
    hxi=np.interp(np.arange(NF),HFs,HXs); kk_=np.exp(-0.5*(np.arange(-90,91)/45.0)**2); kk_/=kk_.sum(); CAMX=np.convolve(np.pad(hxi,90,mode='edge'),kk_,'valid')   # slow follow (~1.5 s) so her sway reads
    if D4:
        NOUT=int(E.get('NOUT','1200')); TG=np.arange(NOUT)*(NF-1)/(NOUT-1); FPS_OUT=NOUT/(NF/fps)
        CAMX120=crit_spring(np.interp(TG,np.arange(NF),hxi),FPS_OUT,float(E.get('CAM_OMEGA','2.67'))); CAMX=np.interp(np.arange(NF),TG,CAMX120)
        info['d4_out']={'nout':NOUT,'fps_out':FPS_OUT,'camera':'critically damped spring, omega 2.67 rad/s (~1.5 s settle)'}
    info['cam_track_x_range_m']=[round(float(CAMX.min()),3),round(float(CAMX.max()),3)]
    CAM=(tgt,0,3,need/(24/50),50); info['camera']={'tgt':list(tgt),'az':0,'el':3,'dist':CAM[3],'lens':50}
    meshes_eval(False); bones=phys_bones()
    SIM=spring_sim(lambda f: pose_dance(max(f-WARM,0),offs,locks),NF+WARM,fps,bones)
    meshes_eval(True); setcam(*CAM)
    _me=bpy.data.meshes.new('Floor4'); _me.from_pydata([(tgt.x+x_,tgt.y+y_,FLOORW) for x_,y_ in ((-4,-4),(4,-4),(4,4),(-4,4))],[],[(0,1,2,3)]); _me.update()
    _fo=bpy.data.objects.new('Floor4',_me); sc.collection.objects.link(_fo); _fm=bpy.data.materials.new('Floor4M'); _fm.use_nodes=True
    _fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(0.46,0.46,0.48,1); _fm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=0.9; _me.materials.append(_fm)
    CLOSE=[int(x) for x in E.get('CLOSE','5,28,67,100,160,188,233,265').split(',')]
    gx=[]
    for i in range(-6,7):
        gx.append([[tgt.x+i*0.25,tgt.y-1.5,FLOORW],[tgt.x+i*0.25,tgt.y+1.5,FLOORW]]); gx.append([[tgt.x-1.5,tgt.y+i*0.25,FLOORW],[tgt.x+1.5,tgt.y+i*0.25,FLOORW]])
    # face points rigid to the head (from her head mesh at rest), heels rigid to the ankles
    relaxed(); meshes_eval(True)
    HW=B.matrix_world@PB['Head'].matrix; HWi=HW.inverted(); co=ev_co(FH)
    try:
        le=B.matrix_world@PB['LeftEye'].head if 'LeftEye' in PB else None; re_=B.matrix_world@PB['RightEye'].head if 'RightEye' in PB else None
        cx_=float((le.x+re_.x)/2) if le else float(np.median(co[:,0])); ez=float((le.z+re_.z)/2) if le else float(np.percentile(co[:,2],75))
        mid=co[np.abs(co[:,0]-cx_)<0.006]; band=mid[(mid[:,2]<ez)&(mid[:,2]>ez-0.07)]; nose=band[np.argmin(band[:,1])] if len(band) else mid[np.argmin(mid[:,1])]
        fr_=mid[(mid[:,1]<nose[1]+0.03)&(mid[:,2]<nose[2])&(mid[:,2]>nose[2]-0.10)]; chin=fr_[np.argmin(fr_[:,2])] if len(fr_) else nose-np.array([0,0,0.06])
        eb=co[np.abs(co[:,2]-ez)<0.012]; earL=eb[np.argmax(eb[:,0])]; earR=eb[np.argmin(eb[:,0])]
        mo=nose+(chin-nose)*0.42; FACEW={'nose':nose,'chin':chin,'earL':earL,'earR':earR,'mouthL':mo+np.array([0.021,0.004,0]),'mouthR':mo-np.array([0.021,-0.004,0])}
        if le:
            for nm_,p_ in (('eyeL',le),('eyeR',re_)): FACEW[nm_]=np.array(tuple(p_))
    except Exception as ex:
        log('face pts fallback',repr(ex)[:200]); hh=B.matrix_world@PB['Head'].head; ht=B.matrix_world@PB['Head'].tail; c_=hh+(ht-hh)*0.35
        FACEW={'nose':np.array(tuple(c_+Vector((0,-0.09,0)))),'chin':np.array(tuple(c_+Vector((0,-0.07,-0.07)))),'earL':np.array(tuple(c_+Vector((0.075,0,0.01)))),'earR':np.array(tuple(c_+Vector((-0.075,0,0.01)))),
               'mouthL':np.array(tuple(c_+Vector((0.02,-0.085,-0.035)))),'mouthR':np.array(tuple(c_+Vector((-0.02,-0.085,-0.035))))}
    FACEL={k:(HWi@Vector(tuple(map(float,p_)))) for k,p_ in FACEW.items()}
    log('face pts',{k:[round(float(x),3) for x in p_] for k,p_ in FACEW.items()})
    HEELL={sd:GEO[sd]['heel_local'] for sd in ('Left','Right')}
    def W(n,which='h'): return B.matrix_world@(PB[n].head if which=='h' else PB[n].tail)
    def mp33():
        HWc=B.matrix_world@PB['Head'].matrix; fw={k:HWc@v_ for k,v_ in FACEL.items()}
        eyeL=fw.get('eyeL',fw['nose']); eyeR=fw.get('eyeR',fw['nose']); dx=Vector((0.012,0,0))
        heelL=(B.matrix_world@PB['Left ankle'].matrix)@HEELL['Left']; heelR=(B.matrix_world@PB['Right ankle'].matrix)@HEELL['Right']
        if D4 and 'Heel_L' in PB: heelL=W('Heel_L','t'); heelR=W('Heel_R','t')
        P=[fw['nose'],eyeL-dx,eyeL,eyeL+dx,eyeR+dx,eyeR,eyeR-dx,fw['earL'],fw['earR'],fw['mouthL'],fw['mouthR'],
           W('Left arm'),W('Right arm'),W('Left elbow'),W('Right elbow'),W('Left wrist'),W('Right wrist'),
           W('LittleFinger1_L'),W('LittleFinger1_R'),W('IndexFinger1_L'),W('IndexFinger1_R'),W('Thumb1_L'),W('Thumb1_R'),
           W('Left leg'),W('Right leg'),W('Left knee'),W('Right knee'),W('Left ankle'),W('Right ankle'),heelL,heelR,W('Left toe','t'),W('Right toe','t')]
        return P,fw
    def hand21(s):
        P=[W(('Left' if s=='L' else 'Right')+' wrist')]
        P+=[W(f'Thumb0_{s}'),W(f'Thumb1_{s}'),W(f'Thumb2_{s}'),W(f'Thumb2_{s}','t')]
        for fn in ('IndexFinger','MiddleFinger','RingFinger','LittleFinger'): P+=[W(f'{fn}1_{s}'),W(f'{fn}2_{s}'),W(f'{fn}3_{s}'),W(f'{fn}3_{s}','t')]
        return P
    def px(p): c=w2c(sc,cam,p); return [round(c.x,5),round(1-c.y,5)]
    trk={}; slide={'Left':0.0,'Right':0.0}; prevA={}
    if D4:
        per_=(NOUT+SHN-1)//SHN; G_SH=list(range(SH*per_,min(NOUT,(SH+1)*per_)))
        KEYS_SH=sorted({k for g in G_SH for k in (int(math.floor(TG[g])),min(int(math.floor(TG[g]))+1,NF-1))}); SNAP={}
        if E.get('POSE_SMOOTH','1')=='1': _k0,_k1=KEYS_SH[0],KEYS_SH[-1]; KEYS_CORE=set(KEYS_SH); KEYS_SH=list(range(max(0,_k0-2),min(NF,_k1+3)))   # D6: 2 extra keyframes each side for the cross-keyframe smoothing
        CLOSE_SH={c for c in CLOSE if int(round(c*(NOUT-1)/(NF-1))) in G_SH}; log('D4 shard',SH,'out',G_SH[:1],G_SH[-1:],'keys',len(KEYS_SH),'close',sorted(CLOSE_SH))
    for f in (KEYS_SH if D4 else frames_of(NF)):
        t0_=time.time(); meshes_eval(False); pose_dance(f,offs,locks); ang=apply_springs(SIM,f+WARM); setcam(Vector((float(CAMX[f])+tgt.x,tgt.y,tgt.z)),CAM[1],CAM[2],CAM[3],CAM[4])
        e={'stance':stance[f],'locked':[sd for sd in FOOT if locks[sd][f] is not None and locks[sd][f][1]>0.99]}
        for sd in e['locked']:
            a_=W(sd+' ankle'); tg=B.matrix_world@locks[sd][f][0]; d_=(Vector((a_.x,a_.y))-Vector((tg.x,tg.y))).length*1000; slide[sd]=max(slide[sd],d_)
        try:
            meshes_eval(True); cf=clip_flags(); e['clip']=cf
            # last-resort per-frame fix if the exact mesh test still finds an arm inside her torso
            for sd,key in (('Left','Larm_vs_torso_tris'),('Right','Rarm_vs_torso_tris')):
                k_=0
                best=(cf.get(key) or 0,{n_:PB[n_].matrix_basis.copy() for n_ in (sd+' arm',sd+' elbow')})
                while (cf.get(key) or 0)>0 and k_<10:
                    meshes_eval(False)
                    wr_in=_torso_in(PB[sd+' wrist'].head,0.03)[0] or _torso_in(PB[sd+' elbow'].tail,0.03)[0]
                    radial_push(sd,3,'arm')
                    if wr_in: radial_push(sd,5,'elbow')
                    k_+=1; meshes_eval(True); cf=clip_flags()
                    if (cf.get(key) or 0)<best[0]: best=(cf.get(key) or 0,{n_:PB[n_].matrix_basis.copy() for n_ in (sd+' arm',sd+' elbow')})
                if k_ and (cf.get(key) or 0)>best[0]:   # keep the best try, never a worse one
                    meshes_eval(False)
                    for n_,m_ in best[1].items(): PB[n_].matrix_basis=m_
                    upd(); meshes_eval(True); cf=clip_flags()
                if k_: e.setdefault('extra_push_steps',{})[sd]=k_
            # legs through each other: swing the knees apart, each about its own hip->ankle line (the ankle, and so a planted foot, does not move)
            nll=cf.get('leg_vs_leg_tris') or 0
            if nll>0:
                meshes_eval(False)
                names=[n_ for sd_ in ('Left','Right') for n_ in (sd_+' leg',sd_+' knee',sd_+' ankle',sd_+' toe') if n_ in PB]
                best=(nll,{n_:PB[n_].matrix_basis.copy() for n_ in names}); tried=0
                def swing(sdl,deg):
                    o_='Right' if sdl=='Left' else 'Left'
                    hip=PB[sdl+' leg'].head.copy(); ank=PB[sdl+' ankle'].head.copy(); ax=(ank-hip).normalized(); K=PB[sdl+' knee'].head; O=PB[o_+' knee'].head
                    sg_=1.0 if ax.cross(K-hip).dot(K-O)>=0 else -1.0
                    Ra={n_:PB[n_].matrix.to_3x3().copy() for n_ in (sdl+' ankle',sdl+' toe') if n_ in PB}
                    wrot_v(sdl+' leg',sg_*deg,ax)
                    for n_,R_ in Ra.items(): set_rot(n_,R_)
                for k in range(16):
                    for sdl in ('Left','Right'): swing(sdl,2.5)
                    meshes_eval(True); c_=clip_flags().get('leg_vs_leg_tris') or 0; meshes_eval(False); tried+=1
                    if c_<best[0]: best=(c_,{n_:PB[n_].matrix_basis.copy() for n_ in names})
                    if c_==0: break
                for n_,m_ in best[1].items(): PB[n_].matrix_basis=m_
                upd(); meshes_eval(True); cf=clip_flags(); e['leg_swing']={'tries':tried,'before':nll,'after':cf.get('leg_vs_leg_tris')}
            # hands: never inside her thighs/hips/chest (vertex test), pushed out along the surface normal by the depth + 1 mm, contact kept
            for sd in ('Left','Right'):
                meshes_eval(True); hc=Vector(tuple(body_co()[HANDV[sd]].mean(axis=0)))
                T_=target_bvh(['Body','Shorts','Shirt','Bra'],frozenset({sd[0]+'ARM'}),near=hc,rad=0.25)
                if T_ is None: continue
                hs=hand_stats(sd,T_); hs0=dict(hs); k=0
                while hs['pen_verts']>0 and k<70:
                    hv=body_co()[HANDV[sd]]; d=sdist(T_,hv,0.08); j=int(np.argmin([x if x is not None else 9 for x in d])); p=Vector(tuple(hv[j]))
                    loc,nr,_,_=T_.find_nearest(p,0.08); meshes_eval(False)
                    if loc is None: break
                    r=p-PB[sd+' arm'].head; disp=nr*((hs['pen_mm']*2.0+1.0)/1000.0); ax=r.cross(disp)
                    if ax.length<1e-10: break
                    wrot_v(sd+' arm',math.degrees(disp.length/max(r.length,0.1)),ax.normalized())
                    k+=1; meshes_eval(True); hs=hand_stats(sd,T_)
                if k: e.setdefault('hand_push',{})[sd]={'steps':k,'pen_before':hs0['pen_verts'],'pen_mm_before':hs0['pen_mm']}
                e.setdefault('hand_body',{})[sd]=hs
            # planted feet: sole level (heel and ball both on the floor) and resting ON it, the ankle's floor position (x,y) kept
            for sd in e['locked']:
                pole_=PB[sd+' knee'].head+(PB[sd+' knee'].head-(PB[sd+' leg'].head+PB[sd+' ankle'].head)/2).normalized()*0.5
                for it_ in range(4):
                    meshes_eval(True); fs=foot_stats(sd,FLOOR); meshes_eval(False)
                    fw_=PB[sd+' toe'].tail-PB[sd+' ankle'].head; fw_.z=0; lat=fw_.normalized().cross(Vector((0,0,1)))
                    dh=(fs['heel_mm']-fs['ball_mm']-HH[sd])/1000.0   # high-heel foot: hold the model's own heel lift, never force flat
                    if abs(dh)>0.0012:
                        a0=math.degrees(math.atan2(abs(dh),0.15)); wrot_v(sd+' ankle',a0,lat)
                        meshes_eval(True); f2=foot_stats(sd,FLOOR); meshes_eval(False)
                        if abs(f2['heel_mm']-f2['ball_mm']-HH[sd])>abs(fs['heel_mm']-fs['ball_mm']-HH[sd]): wrot_v(sd+' ankle',-2*a0,lat)
                        meshes_eval(True); fs=foot_stats(sd,FLOOR); meshes_eval(False)
                    dz=(0.6-fs['min_mm'])/1000.0
                    if abs(dz)<0.0004 and abs(fs['heel_mm']-fs['ball_mm']-HH[sd])<1.5: break
                    Ra={n_:PB[n_].matrix.to_3x3().copy() for n_ in (sd+' ankle',sd+' toe') if n_ in PB}
                    ik2(sd+' leg',sd+' knee',PB[sd+' ankle'].head+Vector((0,0,dz)),pole_)
                    for n_,R_ in Ra.items(): set_rot(n_,R_)
                e.setdefault('plant_level_iters',{})[sd]=it_
            # feet point the way the knees point (<=15 deg): a planted foot brings its knee round (leg swung about hip->ankle, foot untouched); a free foot turns at the ankle
            for sd in ('Left','Right'):
                tw0,inv0=ankle_angles(sd); hist=[(tw0,inv0)]
                for it_ in range(4):
                    tw,inv=ankle_angles(sd)
                    if abs(tw)<=15.0: break
                    exc=tw-math.copysign(13.0,tw)
                    if sd in e['locked']:
                        hip=PB[sd+' leg'].head.copy(); ax=(PB[sd+' ankle'].head-hip).normalized()
                        Ra={n_:PB[n_].matrix.to_3x3().copy() for n_ in (sd+' ankle',sd+' toe') if n_ in PB}
                        wrot_v(sd+' leg',exc,ax)
                        for n_,R_ in Ra.items(): set_rot(n_,R_)
                        if abs(ankle_angles(sd)[0])>abs(tw):
                            wrot_v(sd+' leg',-2*exc,ax)
                            for n_,R_ in Ra.items(): set_rot(n_,R_)
                    else:
                        a=(PB[sd+' knee'].tail-PB[sd+' knee'].head).normalized()
                        wrot_v(sd+' ankle',-exc,a)
                        if abs(ankle_angles(sd)[0])>abs(tw): wrot_v(sd+' ankle',2*exc,a)
                    hist.append(ankle_angles(sd))
                # planted foot with the shin leaning across it: the foot rolls onto its edge (as a real ankle does) until inversion <=15 / eversion <=10, then is re-grounded (ball/edge 0.6 mm)
                if sd in e['locked']:
                    roll_=0.0
                    for it_ in range(4):
                        tw,inv=ankle_angles(sd)
                        if -10.0<=inv<=15.0: break
                        lim=13.0 if inv>0 else -8.0; d_=inv-lim
                        ff=((PB[sd+' toe'].tail if sd+' toe' in PB else PB[sd+' ankle'].tail)-PB[sd+' ankle'].head).normalized()
                        wrot_v(sd+' ankle',d_,ff)
                        if abs(ankle_angles(sd)[1]-lim)>abs(d_): wrot_v(sd+' ankle',-2*d_,ff); roll_-=d_
                        else: roll_+=d_
                    if roll_!=0.0:
                        pole_=PB[sd+' knee'].head+(PB[sd+' knee'].head-(PB[sd+' leg'].head+PB[sd+' ankle'].head)/2).normalized()*0.5
                        for k_ in range(4):
                            meshes_eval(True); fs_=foot_stats(sd,FLOOR); meshes_eval(False); dz=(0.6-fs_['min_mm'])/1000.0
                            if abs(dz)<0.0004: break
                            Ra={n_:PB[n_].matrix.to_3x3().copy() for n_ in (sd+' ankle',sd+' toe') if n_ in PB}
                            ik2(sd+' leg',sd+' knee',PB[sd+' ankle'].head+Vector((0,0,dz)),pole_)
                            for n_,R_ in Ra.items(): set_rot(n_,R_)
                    e.setdefault('foot_edge_roll_deg',{})[sd]=round(roll_,1)
                    hist.append(ankle_angles(sd))
                # free foot: no rolled ankle (inversion <=15, eversion <=10) - turn the foot about its own length
                if sd not in e['locked']:
                    for it_ in range(3):
                        tw,inv=ankle_angles(sd)
                        lim=15.0 if inv>0 else -10.0
                        if (inv>0 and inv<=15.0) or (inv<=0 and inv>=-10.0): break
                        ff=(PB[sd+' toe'].tail-PB[sd+' ankle'].head).normalized() if sd+' toe' in PB else (PB[sd+' ankle'].tail-PB[sd+' ankle'].head).normalized()
                        d_=inv-lim; wrot_v(sd+' ankle',d_,ff)
                        if abs(ankle_angles(sd)[1]-lim)>abs(d_): wrot_v(sd+' ankle',-2*d_,ff)
                        hist.append(ankle_angles(sd))
                upd(); e.setdefault('ankle',{})[sd]={'before':hist[0],'after':ankle_angles(sd)}
            # feet never through each other: push the free foot sideways off the other leg (ankle moved, orientation kept)
            meshes_eval(True)
            A_={sd:PB[sd+' ankle'].head.copy() for sd in ('Left','Right')}
            hz=(A_['Left']-A_['Right']); hz.z=0
            if hz.length<0.22:
                fr_=[sd for sd in ('Right','Left') if sd not in e['locked']]
                if fr_:
                    sd=fr_[0]; o_='Left' if sd=='Right' else 'Right'
                    exl=frozenset({'LARM','RARM','CORE','HEAD',sd[0]+'LEG'})
                    pole_=PB[sd+' knee'].head+(PB[sd+' knee'].head-(PB[sd+' leg'].head+PB[sd+' ankle'].head)/2).normalized()*0.5
                    hist=[]
                    for it_ in range(10):
                        meshes_eval(True)
                        T_=target_bvh(['Body'],exl,near=PB[o_+' ankle'].head,rad=0.25)
                        if T_ is None: break
                        dd=[x for x in sdist(T_,body_co()[FOOTV[sd]],0.05) if x is not None]
                        pen=-min(dd) if dd else 0.0; hist.append(round(pen*1000,1))
                        if pen<0.0008: break
                        dv=PB[sd+' ankle'].head-PB[o_+' ankle'].head; dv.z=0
                        if dv.length<1e-4: dv=(PB[sd+' leg'].head-PB[o_+' leg'].head); dv.z=0
                        dv.normalize()
                        meshes_eval(False); Ra={n_:PB[n_].matrix.to_3x3().copy() for n_ in (sd+' ankle',sd+' toe') if n_ in PB}
                        ik2(sd+' leg',sd+' knee',PB[sd+' ankle'].head+dv*(pen+0.004),pole_)
                        for n_,R_ in Ra.items(): set_rot(n_,R_)
                    upd(); meshes_eval(True); e['foot_foot_pen_mm']={sd:hist}
            # feet: no skin through the floor; a free foot that dips is tilted (2 deg steps) until it clears
            for sd in ('Left','Right'):
                meshes_eval(True); fs=foot_stats(sd,FLOOR); k=0
                if fs['below_verts']>0 and sd not in e['locked']:
                    # a free foot under the floor: lift the whole foot with the leg (ankle up by the depth), its orientation kept
                    pole_=PB[sd+' knee'].head+(PB[sd+' knee'].head-(PB[sd+' leg'].head+PB[sd+' ankle'].head)/2).normalized()*0.5
                    for _ in range(3):
                        dz=(0.8-fs['min_mm'])/1000.0
                        if fs['below_verts']==0: break
                        meshes_eval(False); Ra={n_:PB[n_].matrix.to_3x3().copy() for n_ in (sd+' ankle',sd+' toe') if n_ in PB}
                        ik2(sd+' leg',sd+' knee',PB[sd+' ankle'].head+Vector((0,0,dz)),pole_)
                        for n_,R_ in Ra.items(): set_rot(n_,R_)
                        meshes_eval(True); fs=foot_stats(sd,FLOOR); k+=1
                    e.setdefault('foot_lift_steps',{})[sd]=k
                if fs['below_verts']>0 and sd not in e['locked']:
                    fw_=PB[sd+' toe'].tail-PB[sd+' ankle'].head; fw_.z=0; lat=fw_.normalized().cross(Vector((0,0,1)))
                    sgn=1.0
                    while fs['below_verts']>0 and k<14:
                        meshes_eval(False); wrot_v(sd+' ankle',sgn*2.0,lat); meshes_eval(True); f2=foot_stats(sd,FLOOR); k+=1
                        if k==1 and f2['min_mm']<fs['min_mm']:
                            meshes_eval(False); wrot_v(sd+' ankle',-4.0,lat); sgn=-1.0; meshes_eval(True); f2=foot_stats(sd,FLOOR)
                        fs=f2
                    e.setdefault('foot_tilt_steps',{})[sd]=k
                a_=PB[sd+' ankle']; t_=PB[sd+' toe']; e.setdefault('toe_rel_deg',{})[sd]=round(math.degrees((a_.tail-a_.head).angle(t_.tail-t_.head)),1)
                e.setdefault('feet',{})[sd]=fs
            e['head_pitch_deg']=round(head_pitch()[0],1); e['head_rpy']=head_rpy(); e['pelvis']=pelvis_rec(f); e['seg'],e['src_seg']=seg_rec(f); _sh=src_head(); e['src_rpy']=(round(float(_sh['roll'][f]),1),round(float(_sh['yaw'][f]),1),round(float(_sh['pitch'][f]),1))
            if D4:
                # D5 toes: planted toes lie on the floor (no claw), the foot re-seated 0.6 mm above it; free toes in line with the foot (<=10 deg)
                for sd in ('Left','Right'):
                    if sd in e['locked']:
                        e.setdefault('toe_settle',{})[sd]=toe_settle5(sd)
                        pole_=PB[sd+' knee'].head+(PB[sd+' knee'].head-(PB[sd+' leg'].head+PB[sd+' ankle'].head)/2).normalized()*0.5
                        for k_ in range(3):
                            meshes_eval(True); fs_=foot_stats(sd,FLOOR); meshes_eval(False); dz=(0.6-fs_['min_mm'])/1000.0
                            if abs(dz)<0.0004: break
                            Ra={n_:PB[n_].matrix.to_3x3().copy() for n_ in (sd+' ankle',sd+' toe') if n_ in PB}
                            ik2(sd+' leg',sd+' knee',PB[sd+' ankle'].head+Vector((0,0,dz)),pole_)
                            for n_,R_ in Ra.items(): set_rot(n_,R_)
                    else: e.setdefault('toe_free',{})[sd]=toe_free5(sd)
            if D4: e['leg_cap_pass2_mm']=round(leg_capsules(locks,f)*1000,1); upd()
            if D4: e['head_rel']=[round(x,2) for x in head_rel_jena()]; e['src_head_rel']=[round(float(x),2) for x in SRC_HPYR[f]]; e['leg_cap_pen_mm']=round(leg_pen()[0]*1000,1)
            meshes_eval(True); cf=clip_flags()
            e['clip_final']=cf
        except Exception as ex: e['clip_error']=str(ex)[:200]
        # body self-model (selfmodel.py): every detector each frame, the view that caught it; full measures + 9 views on the close-up frames
        try:
            meshes_eval(True); Mq,Fq=sm_selfcheck(FLOOR,seated=False)
            e['brot']={n_.name:round(math.degrees(2*math.acos(min(1.0,abs(n_.matrix_basis.to_quaternion().w)))),1) for n_ in B.pose.bones}; e['bloc']={n_.name:round(n_.matrix_basis.to_translation().length*100,1) for n_ in B.pose.bones if n_.matrix_basis.to_translation().length>1e-5}
            e['qc_flags']=Fq; e['qc']={k:Mq.get(k) for k in ('balance_margin_cm','com','front_knee_minus_ankle_gap_cm','side_spine_bends','side_knee_bend_L','side_knee_bend_R','ankle_twist_L','ankle_inv_L','ankle_twist_R','ankle_inv_R')}
            if f in CLOSE: json.dump({'frame':f,'measures':Mq,'flags':Fq},open(OUT+f'/q{f:03d}_selfcheck.json','w'),default=str)
        except Exception as ex: e['qc_error']=repr(ex)[:200]
        if D4: upper_twist(); SNAP[f]=snap()
        else: render(OUT+f'/f{f:03d}.jpg')
        if f in CLOSE and (not D4 or f in CLOSE_SH):
            try:
                sc.render.resolution_x,sc.render.resolution_y=640,640; cw=ev_co(BODY); bc=Vector(tuple(cw.mean(axis=0)))
                for sd in ('Left','Right'):
                    hw=cw[HANDV[sd]]; c_=Vector(tuple(hw.mean(axis=0))); ext=float((hw.max(axis=0)-hw.min(axis=0)).max())
                    setcam(c_,40 if c_.x>bc.x else -40,10,max(ext*2.0,0.26)/(24/85),85); render(OUT+f'/c{f:03d}_hand{sd[0]}.jpg')
                fw=np.concatenate([cw[FOOTV['Left']],cw[FOOTV['Right']]]); c_=Vector(tuple(fw.mean(axis=0))); ext=float((fw.max(axis=0)-fw.min(axis=0)).max())
                setcam(c_+Vector((0,0,0.03)),0,7,max(ext*1.5,0.36)/(24/70),70); render(OUT+f'/c{f:03d}_feet.jpg')
                mn_,mx_=bbox(MESHES); mn_.z=min(mn_.z,FLOORW); ext_=mx_-mn_; VVq=sm_render_views(OUT+f'/q{f:03d}_qc_{{}}.jpg',(mn_+mx_)/2,max(ext_.x,ext_.y,ext_.z)*1.12,floor_obj=bpy.data.objects.get('Floor4'))
                json.dump(VVq,open(OUT+f'/q{f:03d}_views.json','w'))
            except Exception as ex_: e['close_error']=repr(ex_)[:200]
            sc.render.resolution_x,sc.render.resolution_y=RW,RH; setcam(Vector((float(CAMX[f])+tgt.x,tgt.y,tgt.z)),CAM[1],CAM[2],CAM[3],CAM[4])
        e['max_back_hair_deg']=round(max([v for k_,v in ang.items() if k_.startswith('Back hair')] or [0]),1); e['s']=round(time.time()-t0_,1)
        if not D4:
            P33,fw=mp33()
            trk[f]={'mp33_px':[px(p) for p in P33],'mp33_w':[[round(c,4) for c in p] for p in P33],'hands':{s:[px(p) for p in hand21(s)] for s in 'LR'},
                    'contact':{'L':'Left' in e['locked'],'R':'Right' in e['locked']},'face':{k:px(v_) for k,v_ in fw.items()},'grid_px':[[px(Vector(a_)),px(Vector(b_))] for a_,b_ in gx],
                    'hips_w':[round(c,4) for c in W('Hips')]}
        info['frames'][f]=e; log('frame',f,e)
    if D4:
        info['d4_leg_capsule_fix']=dict(LEGFIX); info['d4_rig']={'body_bones':len(RIG27_BODY),'mocap_driven':RIG27_DRIVEN['mocap'],'derived':RIG27_DRIVEN['derived']}
        if E.get('POSE_SMOOTH','1')=='1':
            # D6: arms, hands, spine, neck and head smoothed across solved keyframes (binomial 1-4-6-4-1, quaternion sign-aligned) - the solver's per-frame
            # pushes added wrist noise above the filtered source; hips and legs are left as solved so planted feet keep their floor contact
            SM6=[n for n in PB.keys() if not any(t in n for t in ('leg','knee','ankle','toe','Hip_','Heel_','Ball_','Sacrum')) and n!='Hips']
            ks6=sorted(SNAP); W6=(1.0,4.0,6.0,4.0,1.0); NEW6={}
            for i,k in enumerate(ks6):
                b_,kv_=SNAP[k]; nb=dict(b_)
                for n in SM6:
                    if n not in b_: continue
                    l0,q0,s0=b_[n]; acc=np.zeros(4); wt=0.0
                    for d,w in zip(range(-2,3),W6):
                        j=i+d
                        if j<0 or j>=len(ks6) or ks6[j]-k!=d: continue
                        q2=SNAP[ks6[j]][0][n][1]; v=np.array([q2.w,q2.x,q2.y,q2.z])
                        if np.dot(v,[q0.w,q0.x,q0.y,q0.z])<0: v=-v
                        acc+=w*v; wt+=w
                    if wt>0: acc/=np.linalg.norm(acc); nb[n]=(l0,Quaternion(acc.tolist()),s0)
                NEW6[k]=(nb,kv_)
            SNAP.update(NEW6); info['d6_pose_smooth']={'bones':len(SM6),'kernel':W6,'keyframes':len(ks6)}
        for g in G_SH:
            t=float(TG[g]); k0=int(math.floor(t)); k1=min(k0+1,NF-1); a=t-k0
            if k0 not in SNAP or k1 not in SNAP: log('D4 missing snap',g,k0,k1); continue
            meshes_eval(False); apply_interp(SNAP[k0],SNAP[k1],a)
            setcam(Vector((float(CAMX120[g])+tgt.x,tgt.y,tgt.z)),CAM[1],CAM[2],CAM[3],CAM[4])
            t1_=time.time(); render(OUT+f'/g{g:04d}.jpg')
            P33,fw=mp33(); kk=k0 if a<0.5 else k1; lk=(info['frames'].get(kk) or {}).get('locked',[])
            trk[g]={'t':round(t,4),'k':kk,'mp33_px':[px(p) for p in P33],'mp33_w':[[round(c,4) for c in p] for p in P33],'hands':{s:[px(p) for p in hand21(s)] for s in 'LR'},
                    'contact':{'L':'Left' in lk,'R':'Right' in lk},'face':{k:px(v_) for k,v_ in fw.items()},'grid_px':[[px(Vector(a_)),px(Vector(b_))] for a_,b_ in gx],
                    'hips_w':[round(c,4) for c in W('Hips')],'bones_px':bone_px(),'head_axes_px':head_axes_px(),'head_rel':[round(x,2) for x in head_rel_jena()],
                    'src_head_rel':[round(float(x),2) for x in (SRC_HPYR[k0]*(1-a)+SRC_HPYR[k1]*a)],'keys':{k:round(KB[k].value,3) for k in FKEYS},
                    'cap_pen_mm':round(leg_pen()[0]*1000,1),'rs':round(time.time()-t1_,1),
                    'w':{n:[round(c,4) for c in (B.matrix_world@PB[n].head)] for n in ('Hips','Head','Left wrist','Right wrist','Left ankle','Right ankle')}}
            if g%10==0: log('D4 out',g,trk[g]['rs'])
    info['crotch_hand_fixes']=CROTCH[0]
    info['locked_foot_slide_mm']={k:round(v,2) for k,v in slide.items()}
    json.dump(trk,open(OUT+f'/track-shard{SH}.json','w'))
json.dump(info,open(OUT+f'/{MODE}-shard{SH}.json','w'),indent=0,default=str)
log('DONE'); sys.stdout.flush(); os._exit(0)
