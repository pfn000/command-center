
# ===================== D6 (dance6, worker 92b0eaba, Oct 19 2026) =====================
# full-body collider set fitted to her mesh (stored), world head yaw from the face track, knee spacing, foot/leg/hand/hair collision
# projection after interpolation, finger curl ranges, hip-root smoothing with foot re-IK, Catmull-Rom 120 fps, 720 Hz sub-frame QC with
# up to 6 auto-fix passes, first-person POV camera.
D6INFO=info.setdefault('d6',{})
def _d6_dom(objs):
    Binv=B.matrix_world.inverted(); out=[]
    for o in objs:
        if o is None: continue
        vgn={g.index:g.name for g in o.vertex_groups}; co=[]; dom=[]
        for v in o.data.vertices:
            co.append(tuple(Binv@(o.matrix_world@v.co))); best=None; w=0.0
            for ge in v.groups:
                if ge.weight>w: w=ge.weight; best=vgn.get(ge.group)
            dom.append(best)
        out.append((np.array(co),np.array(dom,dtype=object)))
    return out
FING5=FING4+('Thumb',)
def _tipn(s,f_):
    for j in (3,2,1):
        n=f'{f_}{j}_{s}'
        if n in PB: return n
    return None
COLL_BONES=[n for n in ['Hips','Spine','Spine2','Chest','UpperChest','Neck','Neck2','Head','Left shoulder','Right shoulder','Left arm','Right arm',
    'Left elbow','Right elbow','Left wrist','Right wrist','Left leg','Right leg','Left knee','Right knee','Left ankle','Right ankle','Left toe','Right toe'] if n in PB]
COLL_BONES+=[f'{f_}{j}_{s}' for s in 'LR' for f_ in FING5 for j in (1,2,3) if f'{f_}{j}_{s}' in PB]
def _d6_fit():
    rest(); meshes_eval(False); D=_d6_dom([BODY,FH]); COLL={}
    for n in COLL_BONES:
        P_=np.concatenate([co[dom==n] for co,dom in D]) if D else np.zeros((0,3))
        h=np.array(tuple(PB[n].head)); t=np.array(tuple(PB[n].tail)); d=t-h
        if len(P_)<10:
            if n=='Head' and FH is not None:
                P_=D[1][0] if len(D)>1 else P_
            if len(P_)<10: continue
        u=np.clip((P_-h)@d/max(d@d,1e-9),0,1); rad=np.linalg.norm(P_-(h+u[:,None]*d),axis=1)
        pct=70 if n not in ('Head',) else 60
        r0=float(np.percentile(rad[u<0.5],pct)) if (u<0.5).sum()>5 else float(np.percentile(rad,pct))
        r1=float(np.percentile(rad[u>=0.5],pct)) if (u>=0.5).sum()>5 else float(np.percentile(rad,pct))
        lim=0.012 if ('Finger' in n or 'Thumb' in n) else 0.20
        COLL[n]={'r':(max(0.004,min(lim,r0)),max(0.004,min(lim,r1))),'nverts':int(len(P_))}
    return COLL
try:
    COLL=_d6_fit()
except Exception as ex:
    COLL={}; log('D6 collider fit failed',repr(ex)[:300])
D6INFO['colliders']={n:[round(c['r'][0]*100,2),round(c['r'][1]*100,2)] for n,c in COLL.items()}; log('D6 colliders (cm)',len(COLL),D6INFO['colliders'])
def cap_sd(p,n):
    a=PB[n].head; b=PB[n].tail; ab=b-a; L2=ab.dot(ab)
    s=0.0 if L2<1e-12 else max(0.0,min(1.0,(p-a).dot(ab)/L2)); c=a+ab*s; r0,r1=COLL[n]['r']; v=p-c; d=v.length
    return d-(r0+(r1-r0)*s),(v/d if d>1e-9 else Vector((0,0,1))),c
TORSO_C=[n for n in ('Hips','Spine','Spine2','Chest','UpperChest','Neck','Neck2','Head') if n in COLL]
LEGS_C=[n for n in ('Left leg','Right leg','Left knee','Right knee') if n in COLL]
HAIR_C=[n for n in ('Head','Neck','Neck2','UpperChest','Chest','Left shoulder','Right shoulder','Left arm','Right arm') if n in COLL]
def _hand_pts(s):
    pts=[]
    for f_ in FING5:
        tn=_tipn(s,f_)
        if tn: pts.append((f_+'_tip',tn,'t'))
        if f'{f_}2_{s}' in PB: pts.append((f_+'_pip',f'{f_}2_{s}','h'))
    sd='Left' if s=='L' else 'Right'; pts.append(('palm',sd+' wrist','t')); return pts
HANDP={s:_hand_pts(s) for s in 'LR'}
def _hp(spec): n=spec[1]; return PB[n].tail if spec[2]=='t' else PB[n].head
def _hand_colls(s):
    o='Right' if s=='L' else 'Left'
    return TORSO_C+LEGS_C+[n for n in (o+' arm',o+' elbow') if n in COLL]
HAIRB=[]
try:
    HAIRB=sorted(_hair_bones(),key=_depth)
except Exception as ex: log('D6 hair list',repr(ex)[:200])
# rest baselines: a point already inside a fitted capsule at rest is allowed that much (capsules are approximations of her mesh)
rest()
BASE_H={}; BASE_HAIR={}
for s in 'LR':
    for spec in HANDP[s]:
        for n in _hand_colls(s): BASE_H[(spec[0]+s,n)]=min(0.0,cap_sd(_hp(spec),n)[0])
for hb in HAIRB:
    for n in HAIR_C: BASE_HAIR[(hb,n)]=min(0.0,cap_sd(PB[hb].tail,n)[0])
D6INFO['hair_bones']=len(HAIRB)
# stored collider set (shard 0 writes it; pushed to HF colliders/ afterwards)
if SH==0:
    try:
        cj={'model':'jena-v37r10-final.blend','space':'armature (rest pose), metres','fit':'per-bone capsule head->tail; radius = 70th pct (head 60th) of her own skin verts dominated by that bone, r0 = head half, r1 = tail half',
            'checks_720hz':['hand_vs_body (fingertips, PIP joints, palm vs torso/head/thighs/shins/other arm)','hair_vs_body (every hair bone tail vs head/neck/chest/shoulders/upper arms, rest-relative)',
                            'foot_vs_foot','leg_vs_leg','foot_slide (locked feet)','joint_velocity_spike'],
            'colliders':[{'bone':n,'shape':'capsule','from':'head','to':'tail','r0_m':round(c['r'][0],5),'r1_m':round(c['r'][1],5),'offset_m':[0,0,0],
                          'head_rest':[round(x,5) for x in PB[n].head],'tail_rest':[round(x,5) for x in PB[n].tail],'verts_fitted':c['nverts']} for n,c in COLL.items()],
            'leg_capsules_d4':{f'{k[0]}_{k[1]}':[round(x,5) for x in v] for k,v in CAPR.items()},'hair_bones':HAIRB}
        json.dump(cj,open(OUT+'/jena-colliders.json','w'),indent=1)
    except Exception as ex: log('D6 collider json',repr(ex)[:200])
# ---- finger curl ranges (relaxed hand: MCP 15-30, PIP 20-40, progressive index->little; thumb gentle), measured about each bone's own bend axis
CURL_RNG={'IndexFinger':((15,24),(20,32),(8,22)),'MiddleFinger':((17,26),(23,35),(10,24)),'RingFinger':((19,28),(26,38),(12,26)),'LittleFinger':((21,30),(28,40),(14,28)),'Thumb':((4,18),(6,22),(4,18))}
def _flex_raw(n):
    pb=PB[n]; par=pb.parent
    if par is None: return 0.0
    py=par.matrix.to_3x3().col[1].normalized(); by=pb.matrix.to_3x3().col[1].normalized(); x=pb.matrix.to_3x3().col[0].normalized()
    return math.degrees(math.atan2(py.cross(by).dot(x),py.dot(by)))
FLEX0={}; FLEXS={}
rest()
for s in 'LR':
    for f_ in FING5:
        for j in (1,2,3):
            n=f'{f_}{j}_{s}'
            if n not in PB: continue
            a0=_flex_raw(n); wrot_v(n,FSIGN.get((s,f_),1)*10,_lx(n)); a1=_flex_raw(n); rest()
            FLEX0[n]=a0; FLEXS[n]=1.0 if (a1-a0)>=0 else -1.0
def flex(n): return FLEXS[n]*(_flex_raw(n)-FLEX0[n])
CURLSTAT={'joints_set':0,'max_change':0.0,'pinch_fixes':0}
def finger_curl_clamp():
    for s in 'LR':
        for f_ in FING5:
            for j in (1,2,3):
                n=f'{f_}{j}_{s}'
                if n not in FLEX0: continue
                lo,hi=CURL_RNG[f_][j-1]; c=flex(n); tgt=max(lo,min(hi,c)); dlt=max(-35.0,min(35.0,tgt-c))
                if abs(dlt)>0.3:
                    wrot_v(n,FSIGN.get((s,f_),1)*dlt,_lx(n)); CURLSTAT['joints_set']+=1; CURLSTAT['max_change']=max(CURLSTAT['max_change'],abs(dlt))
        # no pinch: thumb tip vs index tip >= 15 mm (uncurl the thumb a little at a time)
        tt=_tipn(s,'Thumb'); it=_tipn(s,'IndexFinger')
        if tt and it:
            for k in range(6):
                if (PB[tt].tail-PB[it].tail).length>=0.015: break
                for j in (1,2):
                    n=f'Thumb{j}_{s}'
                    if n in PB: wrot_v(n,-FSIGN.get((s,'Thumb'),1)*4,_lx(n))
                CURLSTAT['pinch_fixes']+=1
# ---- world head yaw from the face track (source head forward vs her rest forward HEADF0), about the source's clip median
def _yaw_of(fwd): return math.degrees(math.atan2(fwd.y,fwd.x)-math.atan2(HEADF0.y,HEADF0.x))
HYAW_SRC=None
try:
    _ys=[]
    for k in range(NF):
        Rs=CS[k]@DV[k]@CJ0.transposed(); _ys.append(_yaw_of(Rs@HEADF0))
    _ys=np.degrees(np.unwrap(np.radians(_ys))); HYAW_SRC=_ys-float(np.median(_ys))
    D6INFO['src_world_head_yaw_range']=round(float(np.ptp(HYAW_SRC)),1); log('D6 source world head yaw range',D6INFO['src_world_head_yaw_range'])
except Exception as ex: log('D6 head yaw source failed',repr(ex)[:300])
def _wrap(a): return (a+180.0)%360.0-180.0
def jena_hyaw(): return float(head_rpy()[1])
def src_hyaw(t):
    if HYAW_SRC is None: return None
    k0=int(math.floor(t)); k1=min(k0+1,NF-1); a=t-k0; return float(HYAW_SRC[k0]*(1-a)+HYAW_SRC[min(k1,NF-1)]*a)
def head_world_yaw(t,cap=35.0,gain=1.0):
    s=src_hyaw(t)
    if s is None: return 0.0
    d=max(-cap,min(cap,gain*_wrap(s-jena_hyaw())))
    for n,fr_ in (('Neck',0.3),('Neck2',0.3),('Head',0.4)):
        if n in PB: wrot_v(n,d*fr_,Vector((0,0,1)))
    return d
# ---- knees: never inside the hip->ankle line by more than the margin (valgus), and at least half hip-width apart standing
def knee_spacing(m=0.012):
    tot=0.0; hipw=(PB['Left leg'].head-PB['Right leg'].head); hipw.z=0; hw=hipw.length
    for sd,o in (('Left','Right'),('Right','Left')):
        hip=PB[sd+' leg'].head.copy(); ank=PB[sd+' ankle'].head.copy(); K=PB[sd+' knee'].head.copy(); ax=_nz(ank-hip)
        lat=PB[sd+' leg'].head-PB[o+' leg'].head; lat.z=0; lat=_nz(lat); lat=_nz(lat-ax*lat.dot(ax))
        c=hip+ax*(K-hip).dot(ax); off=(K-c).dot(lat)
        if off<-m:
            r_=(K-c).length
            if r_<0.01: continue
            need=(-m-off); ang=math.degrees(need/max(r_,0.05)); ang=min(ang,20.0)
            tang=ax.cross(_nz(K-c)); sgn=1.0 if tang.dot(lat)>=0 else -1.0
            Ra={n_:_orient(n_).copy() for n_ in (sd+' ankle',sd+' toe') if n_ in PB}
            wrot_v(sd+' leg',sgn*ang,ax)
            if (PB[sd+' knee'].head-c).dot(lat)<off: wrot_v(sd+' leg',-2*sgn*ang,ax)
            for n_,R_ in Ra.items(): _set_orient(n_,R_)
            tot+=ang
    kd=(PB['Left knee'].head-PB['Right knee'].head); kd.z=0
    return tot,kd.length,hw
# ---- feet: L foot vs R foot capsules (ankle->ball, ball->toe tip) with margin; the feet move apart sideways (orientation kept)
def _foot_segs(sd):
    out=[]
    if sd+' ankle' in COLL: out.append((sd+' ankle',PB[sd+' ankle'].head,PB[sd+' ankle'].tail,COLL[sd+' ankle']['r']))
    if sd+' toe' in COLL: out.append((sd+' toe',PB[sd+' toe'].head,PB[sd+' toe'].tail,COLL[sd+' toe']['r']))
    return out
def foot_pen(m=0.0):
    worst=(0.0,None)
    for na,a0,a1,ra in _foot_segs('Left'):
        for nb,b0,b1,rb in _foot_segs('Right'):
            d,c1,c2,s,t=_seg_dist(a0,a1,b0,b1); r=(ra[0]+(ra[1]-ra[0])*s)+(rb[0]+(rb[1]-rb[0])*t)+m; p=r-d
            if p>worst[0]: worst=(p,(na,nb,c1,c2))
    return worst
def foot_fix(m=0.004,iters=4):
    n=0
    for it in range(iters):
        p,hit=foot_pen(m)
        if p<=0.0003: break
        na,nb,c1,c2=hit; sep=c1-c2; sep.z=0
        if sep.length<1e-6: sep=PB['Left leg'].head-PB['Right leg'].head; sep.z=0
        sep=_nz(sep)
        for sd,sg in (('Left',1.0),('Right',-1.0)):
            Ra={n_:_orient(n_).copy() for n_ in (sd+' ankle',sd+' toe') if n_ in PB}
            ank=PB[sd+' ankle'].head.copy(); kn=PB[sd+' knee'].head.copy(); hip=PB[sd+' leg'].head.copy(); pole=kn+_nz(kn-(hip+ank)/2)*0.5
            ik2(sd+' leg',sd+' knee',ank+sep*(sg*(p*0.5+0.0005)),pole)
            for n_,R_ in Ra.items(): _set_orient(n_,R_)
        n+=1
    return n
# ---- hands: fingertips / PIP joints / palm never inside torso, head, thighs, shins or the other arm; pushed out to rest ON the surface
def hand_pen(s,m=0.0):
    worst=(0.0,None)
    for spec in HANDP[s]:
        p=_hp(spec)
        for n in _hand_colls(s):
            sd,nr,c=cap_sd(p,n); pen=(BASE_H.get((spec[0]+s,n),0.0)-m)-sd
            if pen>worst[0]: worst=(pen,(spec[0],n,p.copy(),nr))
    return worst
def hand_fix(m=0.002,iters=4):
    steps={}
    for s,sd in (('L','Left'),('R','Right')):
        k=0
        while k<iters:
            pen,hit=hand_pen(s,m)
            if pen<=0.0003: break
            _,n,p,nr=hit; r=p-PB[sd+' arm'].head; disp=nr*(pen+0.0005); ax=r.cross(disp)
            if ax.length<1e-10: break
            wrot_v(sd+' arm',min(8.0,math.degrees(disp.length/max(r.length,0.1))),ax.normalized()); k+=1
        if k: steps[s]=k
    return steps
# ---- hair: every hair bone tail outside head/neck/chest/shoulder capsules (rest-relative), bone turned about its own head
def hair_pen(m=0.0):
    cnt=0; worst=(0.0,None)
    for hb in HAIRB:
        tl=PB[hb].tail
        for n in HAIR_C:
            sd,nr,c=cap_sd(tl,n); pen=(BASE_HAIR.get((hb,n),0.0)-m)-sd
            if pen>0.0: cnt+=1
            if pen>worst[0]: worst=(pen,(hb,n))
    return cnt,worst
def hair_fix(m=0.003,iters=2):
    fixed=0
    for it in range(iters):
        moved=False
        for hb in HAIRB:
            for n in HAIR_C:
                tl=PB[hb].tail.copy(); sd,nr,c=cap_sd(tl,n); pen=(BASE_HAIR.get((hb,n),0.0)-m)-sd
                if pen>0.0003:
                    hd=PB[hb].head.copy(); v0=tl-hd; v1=(tl+nr*(pen+0.0005))-hd
                    if v0.length>1e-6 and v1.length>1e-6: qrot(hb,v0.rotation_difference(v1)); fixed+=1; moved=True
        if not moved: break
    return fixed
# ---- hip root smoothing (binomial over solved keys) + foot re-IK to the solved ankle pose (planted feet stay planted)
ANK={}
def d6_store_ank(f):
    ANK[f]={sd:(PB[sd+' ankle'].head.copy(),_orient(sd+' ankle').copy(),(_orient(sd+' toe').copy() if sd+' toe' in PB else None)) for sd in ('Left','Right')}
def d6_smooth_hips(SN):
    ks=sorted(SN); Wk=(1.0,4.0,6.0,4.0,1.0); NEW={}
    for i,k in enumerate(ks):
        b_,kv_=SN[k]
        if 'Hips' not in b_: continue
        l0,q0,s0=b_['Hips']; accq=np.zeros(4); accl=Vector((0,0,0)); wt=0.0
        for d,w in zip(range(-2,3),Wk):
            j=i+d
            if j<0 or j>=len(ks) or ks[j]-k!=d: continue
            l2,q2,_=SN[ks[j]][0]['Hips']; v=np.array([q2.w,q2.x,q2.y,q2.z])
            if np.dot(v,[q0.w,q0.x,q0.y,q0.z])<0: v=-v
            accq+=w*v; accl=accl+l2*w; wt+=w
        nb=dict(b_); nb['Hips']=(accl/wt,Quaternion((accq/np.linalg.norm(accq)).tolist()),s0); NEW[k]=(nb,kv_)
    SN.update(NEW); return len(NEW)
def _cr(p0,p1,p2,p3,a):
    a2=a*a; a3=a2*a
    return 0.5*((2*p1)+(-p0+p2)*a+(2*p0-5*p1+4*p2-p3)*a2+(-p0+3*p1-3*p2+p3)*a3)
def _keyset(SN,t):
    k0=int(math.floor(t)); k1=min(k0+1,NF-1); a=t-k0
    km=k0-1 if (k0-1) in SN else k0; k2=k1+1 if (k1+1) in SN else k1
    return km,k0,k1,k2,a
def apply_interp_cr(SN,t):
    km,k0,k1,k2,a=_keyset(SN,t)
    B0,K0=SN[k0]; B1,K1=SN[k1]; Bm=SN[km][0]; B2=SN[k2][0]
    for n,(l0,q0,s0) in B0.items():
        l1,q1,s1=B1[n]; lm=Bm[n][0]; l2=B2[n][0]
        v0=np.array([q0.w,q0.x,q0.y,q0.z]); vs=[]
        for q in (Bm[n][1],q1,B2[n][1]):
            v=np.array([q.w,q.x,q.y,q.z])
            if np.dot(v,v0)<0: v=-v
            vs.append(v)
        qv=_cr(vs[0],v0,vs[1],vs[2],a); qv/=max(1e-9,np.linalg.norm(qv))
        PB[n].matrix_basis=Matrix.LocRotScale(_cr(lm,l0,l1,l2,a),Quaternion(qv.tolist()),s0.lerp(s1,a))
    for k in K0: KB[k].value=K0[k]+(K1[k]-K0[k])*a
    upd()
    # feet back on their solved path
    if ANK and k0 in ANK and k1 in ANK:
        for sd in ('Left','Right'):
            P_=[ANK[kk][sd][0] for kk in (km if km in ANK else k0,k0,k1,k2 if k2 in ANK else k1)]
            tgt=_cr(P_[0],P_[1],P_[2],P_[3],a)
            R0_=ANK[k0][sd][1].to_quaternion().slerp(ANK[k1][sd][1].to_quaternion(),a).to_matrix()
            T0_=ANK[k0][sd][2]; T1_=ANK[k1][sd][2]
            kn=PB[sd+' knee'].head.copy(); hip=PB[sd+' leg'].head.copy(); pole=kn+_nz(kn-(hip+tgt)/2)*0.5
            ik2(sd+' leg',sd+' knee',tgt,pole); _set_orient(sd+' ankle',R0_)
            if T0_ is not None: _set_orient(sd+' toe',T0_.to_quaternion().slerp(T1_.to_quaternion(),a).to_matrix())
P6={'iters':4,'m_foot':0.004,'m_hand':0.002,'m_hair':0.003,'m_knee':0.012,'yaw_cap':10.0,'hair_iters':2}
def _nearest_key(t): return int(round(t))
def d6_pose_at(SN,t,locks,P=None,log_ev=None):
    P=P or P6; apply_interp_cr(SN,t); kk=min(max(_nearest_key(t),0),NF-1); fx={}
    hy0=jena_hyaw()
    fx['knee_deg'],kd,hw=knee_spacing(P['m_knee'])
    try:
        if locks is not None and kk in SN: leg_capsules(locks,kk)
    except Exception as ex: fx['leg_err']=repr(ex)[:80]
    fx['foot_iters']=foot_fix(P['m_foot'],P['iters'])
    fx['hand_steps']=hand_fix(P['m_hand'],P['iters'])
    fx['yaw_fix']=head_world_yaw(t,cap=P['yaw_cap'])
    fx['hair_fixed']=hair_fix(P['m_hair'],P['hair_iters'])
    fx['hyaw_pre']=hy0; fx['knee_dist']=kd; fx['hipw']=hw
    return fx
QJ=['Hips','Head','Left wrist','Right wrist','Left elbow','Right elbow','Left ankle','Right ankle','Left knee','Right knee','Left toe','Right toe']
def d6_checks(s_tol=0.001):
    lp=leg_pen()[0]; fp=foot_pen(0.0)[0]; hl=hand_pen('L',0.0); hr=hand_pen('R',0.0); hc,hw_=hair_pen(0.0)
    lp=max(0.0,lp-0.004)
    return {'leg_vs_leg':lp if lp>s_tol else 0.0,'foot_vs_foot':fp if fp>s_tol else 0.0,
            'hand_vs_body_L':hl[0] if hl[0]>0.003 else 0.0,'hand_vs_body_R':hr[0] if hr[0]>0.003 else 0.0,'hand_hit_L':(hl[1][:2] if hl[1] else None),'hand_hit_R':(hr[1][:2] if hr[1] else None),
            'hair_vs_body':(hw_[0] if hw_[0]>0.004 else 0.0),'hair_n':hc,'hair_hit':(hw_[1] if hw_[1] else None)}
def d6_joints():
    out=[list(map(lambda x: round(x,5),PB[n].head)) for n in QJ if n in PB]
    for s in 'LR':
        tn=_tipn(s,'IndexFinger'); out.append(list(map(lambda x: round(x,5),PB[tn].tail)) if tn else [0,0,0])
    return out
def d6_qc_shard(SN,G,locks,sub=6):
    # 720 Hz: 6 samples per 120 fps output frame (24 per 30 fps source frame); fixes applied exactly as the render applies them
    meshes_eval(False); dt=float(TG[1]-TG[0]) if len(TG)>1 else 0.25; hist=[]; P=dict(P6); best=None
    for ps in range(6):
        cnt={'leg_vs_leg':0,'foot_vs_foot':0,'hand_vs_body':0,'hair_vs_body':0}; worst={k:(0.0,None) for k in cnt}; t0=time.time()
        for g in G:
            for j in range(sub):
                t=min(float(TG[g])+j*dt/sub,NF-1.0)
                d6_pose_at(SN,t,locks,P); c=d6_checks()
                for k_,v_ in (('leg_vs_leg',c['leg_vs_leg']),('foot_vs_foot',c['foot_vs_foot']),('hand_vs_body',max(c['hand_vs_body_L'],c['hand_vs_body_R'])),('hair_vs_body',c['hair_vs_body'])):
                    if v_>0: cnt[k_]+=1
                    if v_>worst[k_][0]: worst[k_]=(v_,round(t/30.0,4))
        tot=sum(cnt.values()); hist.append({'pass':ps,'params':dict(P),'counts':cnt,'worst_mm_s':{k:[round(v[0]*1000,1),v[1]] for k,v in worst.items()},'samples':len(G)*sub,'sec':round(time.time()-t0,1)})
        log('D6 qc720 pass',ps,cnt,{k:[round(v[0]*1000,1),v[1]] for k,v in worst.items()})
        if best is None or tot<best[0]: best=(tot,dict(P))
        if tot==0: break
        if ps>0 and tot>=0.95*sum(hist[-2]['counts'].values()): break
        P['iters']+=2
        if cnt['foot_vs_foot']: P['m_foot']+=0.002
        if cnt['hand_vs_body']: P['m_hand']+=0.002
        if cnt['hair_vs_body']: P['m_hair']+=0.002; P['hair_iters']+=1
        if cnt['leg_vs_leg']: P['m_knee']+=0.004
    P6.update(best[1]); return hist
def d6_qc_record(SN,G,locks,sub=6):
    # final 720 Hz record with the chosen params: per sample joints, contact flags, and collision events (before fix -> after fix)
    meshes_eval(False); dt=float(TG[1]-TG[0]) if len(TG)>1 else 0.25; S=[]; EV=[]
    for g in G:
        for j in range(sub):
            t=min(float(TG[g])+j*dt/sub,NF-1.0); apply_interp_cr(SN,t); pre=d6_checks()
            fx=d6_pose_at(SN,t,locks,P6); post=d6_checks(); kk=min(max(_nearest_key(t),0),NF-1); lk=(info['frames'].get(kk) or {}).get('locked',[])
            S.append({'t':round(t,5),'g':g,'j':j,'J':d6_joints(),'lock':['Left' in lk,'Right' in lk],'hy':round(jena_hyaw(),2),'hs':(round(src_hyaw(t),2) if src_hyaw(t) is not None else None),
                      'post':{k:round(v*1000,2) for k,v in post.items() if isinstance(v,float)}})
            for k_ in ('leg_vs_leg','foot_vs_foot','hand_vs_body_L','hand_vs_body_R','hair_vs_body'):
                if pre[k_]>0 or post[k_]>0:
                    pair={'hand_vs_body_L':pre.get('hand_hit_L'),'hand_vs_body_R':pre.get('hand_hit_R'),'hair_vs_body':pre.get('hair_hit')}.get(k_)
                    EV.append({'t_s':round(t/30.0,5),'frame30':round(t,3),'out120':g,'sub720':j,'check':k_,'pair':pair,'depth_mm_before':round(pre[k_]*1000,2),'depth_mm_after':round(post[k_]*1000,2),
                               'fix':{'leg_vs_leg':'knee swing about hip-ankle line','foot_vs_foot':'feet apart sideways (IK, foot turn kept)','hair_vs_body':'hair bone turned out about its root'}.get(k_,'arm turned at the shoulder along the surface normal')})
    return S,EV
# ---- first-person POV camera: at her eyes, slightly forward, ~90 deg FOV; head, hair and eyes hidden from it
POVCAM=None; POV_HIDE=[]
try:
    _cd=bpy.data.cameras.new('POVCamD'); _cd.lens_unit='FOV'; _cd.angle=math.radians(90.0); _cd.clip_start=0.01; _cd.clip_end=100.0; _cd.sensor_fit='AUTO'
    POVCAM=bpy.data.objects.new('POVCam',_cd); sc.collection.objects.link(POVCAM)
    POV_HIDE=[o for o in MESHES if o is FH or o is HAIR or any(t in o.name.lower() for t in ('head','hair','eye','lash','brow','teeth','tongue','bang','pigg'))]
    log('D6 POV hides',[o.name for o in POV_HIDE])
except Exception as ex: log('D6 POV cam failed',repr(ex)[:200])
def pov_place():
    M_=B.matrix_world@PB['Head'].matrix; R_=M_.to_3x3().normalized(); Rd=PB['Head'].matrix.to_3x3()@HEAD0.inverted()
    fwd=_nz((B.matrix_world.to_3x3()@(Rd@HEADF0))); up=_nz(B.matrix_world.to_3x3()@(Rd@Vector((0,0,1))))
    try:
        eye=(M_@FACEL['eyeL']+M_@FACEL['eyeR'])/2
    except Exception:
        eye=M_.to_translation()+up*0.06+fwd*0.06
    loc=eye+fwd*0.035; POVCAM.location=loc
    z=-fwd; x=_nz(up.cross(z)); y=z.cross(x); POVCAM.rotation_euler=Matrix((x,y,z)).transposed().to_euler(); upd()
    r,yw,p=head_rpy(); return {'eye':[round(c,4) for c in loc],'pitch':p,'yaw':yw,'roll':r}
def pov_render(path,res=640):
    if POVCAM is None: return None
    info_=pov_place(); oc=sc.camera; ox,oy=sc.render.resolution_x,sc.render.resolution_y
    for o in POV_HIDE: o.hide_render=True
    sc.camera=POVCAM; sc.render.resolution_x=res; sc.render.resolution_y=res
    try:
        loc=POVCAM.location.copy(); fwd=(POVCAM.matrix_world.to_3x3()@Vector((0,0,-1))).normalized()
        c0=w2c(sc,POVCAM,loc+fwd*0.6); c1=w2c(sc,POVCAM,loc+fwd*0.6+Vector((0,0,-0.15)))
        info_['down_px']=[[round(c0.x,4),round(1-c0.y,4)],[round(c1.x,4),round(1-c1.y,4)]]
        render(path)
    finally:
        sc.camera=oc; sc.render.resolution_x=ox; sc.render.resolution_y=oy
        for o in POV_HIDE: o.hide_render=False
    return info_
log('D6 ready',{'colliders':len(COLL),'hair_bones':len(HAIRB),'flex_joints':len(FLEX0),'pov':POVCAM is not None})
