
# contact.py: shared vertex-level contact tools for HANDS and FEET (Jena v3.7, worker 41c5b341, Oct 19 2026).
# Everything here is in ARMATURE space (B.matrix_world is not identity on this build).
import re as _re
_MW=B.matrix_world.copy(); _MWI=_MW.inverted(); _A=np.array(_MWI); _A3=_A[:3,:3].T.copy(); _At=_A[:3,3].copy()
log('MW',[[round(x,4) for x in r] for r in _MW])
def arm_co(o):
    return ev_co(o)@_A3+_At
def to_world(p): return _MW@Vector(p)
FING5=('Thumb','IndexFinger','MiddleFinger','RingFinger','LittleFinger')
def _bone_part(n):
    if not n: return None
    m=_re.match(r'(Thumb|IndexFinger|MiddleFinger|RingFinger|LittleFinger)(\d)_([LR])$',n)
    if m: return ('Left' if m.group(3)=='L' else 'Right','hand',m.group(1))
    for sd in ('Left','Right'):
        if n==sd+' wrist': return (sd,'hand','palm')
        if n==sd+' ankle': return (sd,'foot','foot')
        if n==sd+' toe': return (sd,'foot','toe')
    return None
_LIMBC={}
def _limb(n):
    if n in _LIMBC: return _LIMBC[n]
    b=PB.get(n); r='CORE'
    while b is not None:
        hit=None
        for sd in ('Left','Right'):
            if b.name in (sd+' arm',sd+' shoulder'): hit=sd[0]+'ARM'
            elif b.name==sd+' leg': hit=sd[0]+'LEG'
        if hit: r=hit; break
        if b.name in ('Neck','Head'): r='HEAD'; break
        b=b.parent
    _LIMBC[n]=r; return r
def _labels(o):
    vg={g.index:g.name for g in o.vertex_groups}; lim=[]; part=[]
    for v in o.data.vertices:
        best=None; w=0.0
        for g in v.groups:
            if g.weight>w and g.group in vg: w=g.weight; best=vg[g.group]
        lim.append(_limb(best) if best else 'CORE'); part.append(_bone_part(best))
    return lim,part
MESHINFO={}
for _o in MESHES:
    if _o.name in ('Hair',): continue
    try:
        _l,_p=_labels(_o); _pl=[tuple(p.vertices) for p in _o.data.polygons]
        _pls=[frozenset(_l[i] for i in p) for p in _pl]
        MESHINFO[_o.name]=dict(lim=_l,part=_p,polys=_pl,plims=_pls)
    except Exception as ex: log('meshinfo fail',_o.name,repr(ex)[:120])
_BP=MESHINFO['Body']['part']
HANDV={sd:np.array([i for i,p in enumerate(_BP) if p and p[0]==sd and p[1]=='hand'],dtype=np.int64) for sd in ('Left','Right')}
PALMV={sd:np.array([i for i,p in enumerate(_BP) if p and p[0]==sd and p[2]=='palm'],dtype=np.int64) for sd in ('Left','Right')}
FINGV={(sd,f):np.array([i for i,p in enumerate(_BP) if p and p[0]==sd and p[2]==f],dtype=np.int64) for sd in ('Left','Right') for f in FING5}
FOOTV={sd:np.array([i for i,p in enumerate(_BP) if p and p[0]==sd and p[1]=='foot'],dtype=np.int64) for sd in ('Left','Right')}
TOEV={sd:np.array([i for i,p in enumerate(_BP) if p and p[0]==sd and p[2]=='toe'],dtype=np.int64) for sd in ('Left','Right')}
log('contact verts',{k:len(v) for k,v in list(HANDV.items())+list(FOOTV.items())},{f'{k[0][0]}{k[1][:4]}':len(v) for k,v in FINGV.items()},'toe',{k:len(v) for k,v in TOEV.items()})

SHELL={}
def head_shell_bvh():
    """head collider fitted to her real mesh: the convex envelope of her hair + head skin from the skull base up (closed, so signed distance is exact)"""
    import bmesh
    zc=PB['Head'].head.z-0.01; pts=[]
    for nm in ('Hair','Female Head','Cranium','Eyebrows'):
        o=bpy.data.objects.get(nm)
        if o is None or o.hide_render: continue
        co=arm_co(o); pts.append(co[co[:,2]>zc])
    P=np.concatenate(pts) if pts else None
    if P is None or len(P)<10: return None
    if len(P)>40000: P=P[::max(1,len(P)//40000)]
    bm=bmesh.new()
    for p in P: bm.verts.new(tuple(float(x) for x in p))
    res=bmesh.ops.convex_hull(bm,input=bm.verts[:])
    kill=list({g for g in res.get('geom_interior',[])+res.get('geom_unused',[]) if isinstance(g,bmesh.types.BMVert) and g.is_valid})
    if kill: bmesh.ops.delete(bm,geom=kill,context='VERTS')
    bm.normal_update(); T=BVHTree.FromBMesh(bm)
    cen=Vector(tuple(P.mean(axis=0))); loc,nr,_,_=T.find_nearest(cen,1.0)
    if loc is not None and (cen-loc).dot(nr)>0:
        bmesh.ops.reverse_faces(bm,faces=bm.faces[:]); bm.normal_update(); T=BVHTree.FromBMesh(bm)
    mn=P.min(axis=0); mx=P.max(axis=0)
    SHELL['info']={'verts_in':int(len(P)),'hull_faces':len(bm.faces),'size_cm':[round(float(x)*100,1) for x in (mx-mn)]}
    bm.free(); return T
def target_bvh(meshes,excl=frozenset(),near=None,rad=0.30,extra=None,incl=None):
    """BVH over the given meshes' polys (armature space), dropping polys that touch an excluded limb, kept within rad of `near`."""
    if list(meshes)==['HeadShell']: return head_shell_bvh()
    V=[];P=[]
    for nm in meshes:
        o=bpy.data.objects.get(nm)
        if o is None or (o.hide_render and nm!='TestSeat'): continue
        co=arm_co(o)
        mi=MESHINFO.get(nm)
        if mi is None:
            pl=[tuple(p.vertices) for p in o.data.polygons]; pls=[frozenset() for _ in pl]
        else: pl,pls=mi['polys'],mi['plims']
        if near is not None and mi is not None:
            ok=np.linalg.norm(co-np.array(tuple(near)),axis=1)<rad
        else: ok=None
        idx={}
        for p,ls in zip(pl,pls):
            if ls & excl: continue
            if incl is not None and mi is not None and not (ls <= incl): continue
            if ok is not None and not all(ok[i] for i in p): continue
            q=[]
            for i in p:
                j=idx.get(i)
                if j is None: j=len(V); idx[i]=j; V.append(Vector(tuple(co[i])))
                q.append(j)
            P.append(q)
    if not P: return None
    return BVHTree.FromPolygons(V,P)
def sdist(T,pts,maxd=0.08):
    """signed distance (m) of each point to the BVH surface: + outside, - inside; None if farther than maxd."""
    out=[]
    for p in pts:
        loc,nr,i,d=T.find_nearest(Vector(tuple(p)),maxd)
        if loc is None: out.append(None); continue
        s=(Vector(tuple(p))-loc).dot(nr); out.append(d if s>=0 else -d)
    return out
def body_co(): return arm_co(BODY)
def hand_stats(sd,T,co=None,which=None):
    co=body_co() if co is None else co
    vi=HANDV[sd] if which is None else which
    if T is None or len(vi)==0: return dict(gap_mm=None,pen_verts=0,pen_mm=0.0)
    d=[x for x in sdist(T,co[vi]) if x is not None]
    if not d: return dict(gap_mm=None,pen_verts=0,pen_mm=0.0)
    d=np.array(d); return dict(gap_mm=round(float(d.min())*1000,1),pen_verts=int((d<-0.0008).sum()),pen_mm=round(float(max(0.0,-d.min()))*1000,1),touch_verts=int(((d>-0.0008)&(d<0.003)).sum()))
def _fing_bones(sd,f):
    s=sd[0]
    if f=='Thumb': return [n for n in (f'Thumb1_{s}',f'Thumb2_{s}') if n in PB]
    return [n for n in (f'{f}1_{s}',f'{f}2_{s}',f'{f}3_{s}') if n in PB]
_CURLW={'Thumb':(0.6,0.8),'IndexFinger':(0.8,0.9,0.5),'MiddleFinger':(0.8,0.9,0.5),'RingFinger':(0.8,0.9,0.5),'LittleFinger':(0.8,0.9,0.5)}
def finger_curl(sd,f,deg):
    sgn=FSIGN[(sd[0],f)] if FSIGN else 1
    for n,w in zip(_fing_bones(sd,f),_CURLW[f]): wrot_v(n,sgn*deg*w,_lx(n))
def finger_spread(sd,amt=1.0):
    """splay (amt>0) or close up (amt<0) the long fingers about their own side axis, direction checked by the tip gaps to the middle finger"""
    s=sd[0]
    for f,a_ in (('IndexFinger',4.0),('RingFinger',3.0),('LittleFinger',7.0)):
        n=f'{f}1_{s}'
        if n not in PB: continue
        mid=PB[f'MiddleFinger3_{s}'].tail.copy(); d0=(PB[f'{f}3_{s}'].tail-mid).length
        ax=PB[n].matrix.to_3x3().col[2].normalized()
        base={k:PB[k].matrix_basis.copy() for k in _fing_bones(sd,f)}
        wrot_v(n,2.0,ax); apart=1.0 if (PB[f'{f}3_{s}'].tail-mid).length>d0 else -1.0
        for k,m in base.items(): PB[k].matrix_basis=m
        upd(); wrot_v(n,apart*a_*amt,ax)
def settle_fingers(sd,T,lo=-12.0,hi=26.0,goal=0.0012,rest_hover=12.0):
    """drape each finger onto the surface: curl until its closest skin point sits 0-3 mm off the surface, never inside."""
    rep={}
    for f in FING5:
        vi=FINGV[(sd,f)]
        if len(vi)==0: continue
        bones=_fing_bones(sd,f); base={k:PB[k].matrix_basis.copy() for k in bones}
        def at(deg):
            for k,m in base.items(): PB[k].matrix_basis=m
            upd(); finger_curl(sd,f,deg); meshes_eval(True); d=[x for x in sdist(T,body_co()[vi],0.06) if x is not None]; meshes_eval(False)
            return min(d) if d else 9.0
        d0=at(0.0)
        if d0<0.0:      # inside: uncurl (or curl, whichever clears) by bisection toward 0 penetration
            a,b=0.0,lo; db=at(b)
            if db<0.0: a,b=0.0,hi; db=at(b)
            if db<0.0: at(0.0); rep[f]={'deg':0.0,'gap_mm':round(d0*1000,1),'stuck':True}; continue
            for _ in range(9):
                m=(a+b)/2; dm=at(m)
                if dm<0.0: a=m
                else: b=m
            d=at(b); rep[f]={'deg':round(b,1),'gap_mm':round(d*1000,1)}
        elif d0>0.0025 and (f!='Thumb' or d0<0.020):   # hovering: curl toward the surface until it touches (0-3 mm)
            a,b=0.0,hi; db=at(b)
            if db>0.003:   # can't reach the surface without hooking: leave it softly curled in the air (natural), not a claw
                d=at(rest_hover if f!='Thumb' else 0.0); rep[f]={'deg':rest_hover if f!='Thumb' else 0.0,'gap_mm':round(d*1000,1),'hover':True}; continue
            for _ in range(9):
                m=(a+b)/2; dm=at(m)
                if dm>goal: a=m
                else: b=m
            # b is the first angle at/inside goal; make sure it is not inside
            d=at(b)
            if d<0.0: d=at(a); b=a
            rep[f]={'deg':round(b,1),'gap_mm':round(d*1000,1)}
        else:
            at(0.0); rep[f]={'deg':0.0,'gap_mm':round(d0*1000,1)}
    return rep
PALM_LOCAL={}
def palm_init():
    """palm normal in the wrist bone's frame, read once from the relaxed pose (fingers curl toward the palm)"""
    for sd in ('Left','Right'):
        s=sd[0]; w=PB[sd+' wrist']; ax=(PB[f'MiddleFinger1_{s}'].head-w.head).normalized()
        p=(PB[f'MiddleFinger3_{s}'].tail-PB[f'MiddleFinger1_{s}'].head)+(PB[f'IndexFinger3_{s}'].tail-PB[f'IndexFinger1_{s}'].head); p=(p-ax*p.dot(ax)).normalized()
        PALM_LOCAL[sd]=w.matrix.to_3x3().inverted()@p
def palm_normal(sd): return (PB[sd+' wrist'].matrix.to_3x3()@PALM_LOCAL[sd]).normalized()
def _palm_roll(sd,want):
    """signed angle (deg) about the hand axis that turns the palm normal onto `want`"""
    s=sd[0]; w=PB[sd+' wrist'].head; ax=(PB[f'MiddleFinger1_{s}'].head-w).normalized()
    p=palm_normal(sd); p=p-ax*p.dot(ax)
    q=want-ax*want.dot(ax)
    if p.length<1e-6 or q.length<1e-6: return 0.0,ax
    p.normalize(); q.normalize(); return math.degrees(math.atan2(p.cross(q).dot(ax),p.dot(q))),ax
def ik_hand_to(sd,tgt,elbow_pole,fingers_dir,palm_want=None,roll_off=0.0):
    ik2(sd+' arm',sd+' elbow',tgt,PB[sd+' arm'].head+elbow_pole); align(sd+' wrist',fingers_dir,cap=180)
    if palm_want is not None:
        a,_=_palm_roll(sd,palm_want)
        el=PB[sd+' elbow']; fa=(el.tail-el.head).normalized()
        wrot_v(sd+' elbow',max(-80.0,min(80.0,a*0.7)),fa); align(sd+' wrist',fingers_dir,cap=180)
        a2,ax=_palm_roll(sd,palm_want); wrot_v(sd+' wrist',max(-45.0,min(45.0,a2))+roll_off,ax)
def fingers_flat(sd,c1=6.0,c2=10.0,c3=6.0):
    """long fingers nearly straight (a soft 6/10/6 deg curl) before they are draped onto a surface"""
    s=sd[0]
    for f in ('IndexFinger','MiddleFinger','RingFinger','LittleFinger'):
        for j,a_ in ((1,c1),(2,c2),(3,c3)):
            n=f'{f}{j}_{s}'
            if n in PB: PB[n].matrix_basis=BASE[n]
        upd()
        for j,a_ in ((1,c1),(2,c2),(3,c3)):
            n=f'{f}{j}_{s}'
            if n in PB: wrot_v(n,FSIGN[(s,f)]*a_,_lx(n))
def place_hand(sd,query,meshes,excl,elbow_pole,fingers_dir,gap=0.0012,maxd=0.30,palm_only=True,unsigned=False,palm_toward=None,incl=None,settle=True):
    """IK the hand so its PALM (palm facing the surface) rests on the nearest surface to `query`: closest palm skin 0-3 mm off, 0 inside; then drape the fingers."""
    meshes_eval(True); T=target_bvh(meshes,excl,near=query,rad=0.35,incl=incl); meshes_eval(False)
    if T is None: return None
    if settle and not unsigned: fingers_flat(sd)
    loc,nr,_,_=T.find_nearest(Vector(tuple(query)),maxd)
    if loc is None: return None
    wr=PB[sd+' wrist']; tgt=loc+nr*0.03-(wr.tail-wr.head)*0.3; n2=nr
    def want(): return (Vector(palm_toward)-PB[sd+' wrist'].head).normalized() if palm_toward is not None else -n2
    def fdir():
        if unsigned: return fingers_dir
        f_=Vector(fingers_dir).normalized(); t_=f_-n2*f_.dot(n2)
        if t_.length<1e-4: return f_
        return t_.normalized()
    thv=set(FINGV[(sd,'Thumb')].tolist()); pv=np.array([i for i in HANDV[sd].tolist() if i not in thv],dtype=np.int64) if settle else HANDV[sd]
    ROLL=[0.0]
    def seat_hand(nit=10):
        nonlocal tgt,n2
        for k in range(nit):
            ik_hand_to(sd,tgt,elbow_pole,fdir(),want(),ROLL[0])
            meshes_eval(True); co=body_co(); d=[x for x in sdist(T,co[pv],0.12) if x is not None]
            if unsigned: d=[abs(x) for x in d]
            pc=Vector(tuple(co[pv].mean(axis=0))); l2,nn,_,dl=T.find_nearest(pc,0.5); meshes_eval(False)
            if l2 is None: break
            n2=nn; dm=min(d) if d else dl; step=gap-dm
            if abs(step)<0.0007 and k>1: break
            tan=(l2+n2*(pc-l2).dot(n2))-pc
            tgt=tgt+n2*step+tan*0.5
    def side_diff():
        meshes_eval(True); co=body_co(); r={}
        for grp,fs_ in (('i',('IndexFinger','MiddleFinger')),('p',('RingFinger','LittleFinger'))):
            vi=np.concatenate([FINGV[(sd,f)] for f in fs_]); d=[x for x in sdist(T,co[vi],0.08) if x is not None]; r[grp]=min(d) if d else 0.08
        meshes_eval(False); return r['p']-r['i']
    seat_hand()
    if settle and not unsigned:
        # roll the hand about its own axis until the index side and the little-finger side sit at the same height off the surface
        df=side_diff(); a=0.0
        for r_it in range(6):
            if abs(df)<0.003: break
            st_=max(-20.0,min(20.0,math.degrees(math.atan2(df,0.06))))
            ROLL[0]+=st_; seat_hand(5); d2=side_diff()
            if abs(d2)>abs(df): ROLL[0]-=2*st_; seat_hand(5); d2=side_diff()
            df=d2
        ROLL.append(round(df*1000,1))
    rep={}
    meshes_eval(True); rep['palm']=hand_stats(sd,T,which=pv); meshes_eval(False)
    if not settle and not unsigned: finger_spread(sd,-1.0)
    if settle and not unsigned:
        finger_spread(sd,-1.0); rep['fingers']=settle_fingers(sd,T)
    meshes_eval(True); rep['hand']=hand_stats(sd,T); meshes_eval(False)
    # last guard: any hand skin still inside -> lift the whole hand off along the normal, 1 mm steps (finger poses kept)
    k=0
    while not unsigned and rep['hand']['pen_verts']>0 and k<12:
        tgt=tgt+n2*(rep['hand']['pen_mm']*0.001+0.0006); fb={pb.name:pb.matrix_basis.copy() for pb in PB if _bone_part(pb.name) and _bone_part(pb.name)[2]!='palm'}
        ik_hand_to(sd,tgt,elbow_pole,fdir(),want(),ROLL[0])
        for n_,m_ in fb.items(): PB[n_].matrix_basis=m_
        upd(); meshes_eval(True); rep['hand']=hand_stats(sd,T); meshes_eval(False); k+=1
    rep['lift_mm']=k; rep['T']=T; rep['roll_off_deg']=round(ROLL[0],1); rep['side_diff_mm']=ROLL[1] if len(ROLL)>1 else None
    pr,_=_palm_roll(sd,want()); rep['palm_roll_err_deg']=round(pr,1); rep['palm_normal_vs_surface_deg']=round(math.degrees(palm_normal(sd).angle(-n2)),1) if not unsigned else None
    return rep
# ---------- feet
def foot_co(sd,co=None):
    co=body_co() if co is None else co; return co[FOOTV[sd]]
def foot_stats(sd,FLOOR_,co=None):
    fc=foot_co(sd,co); z=fc[:,2]; zmin=float(z.min())
    # sole thirds along the foot's own forward axis (ankle -> toe tail), heel = back third, ball = front third
    a_=np.array(tuple(PB[sd+' ankle'].head)); t_=np.array(tuple(PB[sd+' toe'].tail)) if sd+' toe' in PB else np.array(tuple(PB[sd+' ankle'].tail))
    fw=t_-a_; fw[2]=0; n_=np.linalg.norm(fw); fw=fw/n_ if n_>1e-6 else np.array([0,-1,0])
    s=(fc-a_)@fw; lo_,hi_=s.min(),s.max(); L_=hi_-lo_
    heel=float(z[s<lo_+L_*0.30].min()); ball=float(z[s>lo_+L_*0.62].min())
    return dict(min_mm=round((zmin-FLOOR_)*1000,1),below_verts=int((z<FLOOR_-0.001).sum()),heel_mm=round((heel-FLOOR_)*1000,1),ball_mm=round((ball-FLOOR_)*1000,1))
def toe_pitch(sd):
    a_=PB[sd+' ankle']; d=(a_.tail-a_.head).normalized(); return round(math.degrees(math.asin(max(-1,min(1,-d.z)))),1)
