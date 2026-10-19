
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
P_=dict(ARM_DOWN=40,SHOULDER_DOWN=10,ELBOW_BEND=-12,WRIST_BEND=8,RELAX=True)   # run 10c build-report pose params
def fingers_relaxed(scale=1.0):
    for sd,sgn in (('Left',1),('Right',-1)):
        for f_ in ('IndexFinger','MiddleFinger','RingFinger','LittleFinger'):
            for j,a_ in ((1,18),(2,26),(3,18)): wrot(f'{f_}{j}_{sd[0]}',sgn*a_*scale,'Y')
        for j in (1,2): wrot(f'Thumb{j}_{sd[0]}',sgn*14*scale,'Y')
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
json.dump(info,open(OUT+f'/{MODE}-shard{SH}.json','w'),indent=0,default=str)
log('DONE'); sys.stdout.flush(); os._exit(0)
