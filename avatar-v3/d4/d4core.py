
# dance4 CORE (big-fix pass Oct 19): spine/neck split, head + neck from the face track relative to the chest, wrist twist,
# leg capsule colliders, face blendshapes -> her own shape keys, pose snapshots + 120 fps slerp, spring camera, head QC.
def _q_pow(q,fr):
    q=q.copy()
    if q.w<0: q.negate()
    return Quaternion().slerp(q,fr)
def _orient(n): return PB[n].matrix.to_3x3()
def _set_orient(n,R3):
    pb=PB[n]; loc=pb.matrix.to_translation(); pb.matrix=Matrix.Translation(loc)@R3.to_4x4(); upd()
def _nz(v): return v.normalized() if v.length>1e-9 else v
# ---- rest frames
rest()
CJ0=frame_rot(PB['Left arm'].head-PB['Right arm'].head,PB['UpperChest'].tail-PB['UpperChest'].head)
R0={n:rest_rot(n) for n in ('Neck','Neck2','Head','UpperChest')}
# ---- source head relative to source chest, per frame (chest coords: x her left, y back, z up)
def _src_chest(w): LS_,RS_,LH_,RH_=L(w,11),L(w,12),L(w,23),L(w,24); return frame_rot(LS_-RS_,(LS_+RS_)/2-(LH_+RH_)/2)
def _src_head_lm(w):
    e7,e8,nz_=L(w,7),L(w,8),L(w,0); x=_nz(e7-e8); y=(e7+e8)/2-nz_; y=_nz(y-x*y.dot(x)); z=x.cross(y); return Matrix((x,y,z)).transposed()
def _qmean(Qs):
    A=np.array([list(q) for q in Qs]); 
    for i in range(1,len(A)):
        if np.dot(A[i],A[0])<0: A[i]*=-1
    m=A.mean(0); m/=np.linalg.norm(m); return Quaternion(m.tolist())
def _dev(RELS):
    q0=_qmean([r.to_quaternion() for r in RELS]); R0_=q0.to_matrix(); return [r@R0_.transposed() for r in RELS]
CS=[_src_chest(w) for w in FR]
DV_LM=_dev([CS[k].transposed()@_src_head_lm(FR[k]) for k in range(NF)])
def hpyr(Dm):
    # head direction metrics in chest coords, no Euler wrap: pitch = back axis rising (chin up +), yaw = turn, roll = ear line tilt
    y_=Dm@Vector((0,1,0)); x_=Dm@Vector((1,0,0))
    return (math.degrees(math.asin(max(-1,min(1,y_.z)))), math.degrees(math.atan2(-y_.x,y_.y)), math.degrees(math.asin(max(-1,min(1,x_.z)))))
DV=DV_LM; HEAD_SRC='landmarks (ears, nose) from the 33-point body track'
if FACE is not None:
    # camera metric space (x right, y up, z toward camera) -> pose world (x right, y down, z away) = flip Y,Z; then mp2b and the level correction.
    # Checked on this clip (Oct 19): the face matrix's left axis tilts with the ear line in the image (corr 0.94, same mean). The 3D body-marker
    # head is the weak one (its ear depth is noisy: roll range 17 deg vs 55 deg in the image), so the face matrix leads.
    A_=Mc@Matrix(((1,0,0),(0,0,1),(0,-1,0)))@Matrix(((1,0,0),(0,-1,0),(0,0,-1)))
    HF=[A_@Quaternion(FACE['q'][k].tolist()).to_matrix() for k in range(NF)]
    DVF=_dev([CS[k].transposed()@HF[k] for k in range(NF)])
    okf=[bool(x) for x in FACE['ok']]; DV=list(DVF); gaps=[]; s_=None
    for k in range(NF):
        if not okf[k] and s_ is None: s_=k
        if okf[k] and s_ is not None: gaps.append((s_,k-1)); s_=None
    if s_ is not None: gaps.append((s_,NF-1))
    for a_,b_ in gaps:
        # where no face was found: the face rotation slerped across the gap, plus the body-marker head's own motion inside the gap
        L0=a_-1 if a_>0 else None; L1=b_+1 if b_<NF-1 else None
        for k in range(a_,b_+1):
            if L0 is not None and L1 is not None:
                t_=(k-L0)/(L1-L0); base=DV_LM[L0].to_quaternion().slerp(DV_LM[L1].to_quaternion(),t_).to_matrix()
            else: base=DV_LM[L1 if L0 is None else L0]
            DV[k]=(DV_LM[k]@base.transposed())@DVF[k]
    ag=[float(np.corrcoef([hpyr(DVF[k])[j] for k in range(NF) if okf[k]],[hpyr(DV_LM[k])[j] for k in range(NF) if okf[k]])[0,1]) for j in range(3)]
    HEAD_SRC=f'MediaPipe face transform matrix on {sum(okf)}/{NF} frames; {NF-sum(okf)} frames in {len(gaps)} gaps bridged (slerp + body-marker head detail)'
    info['d4_face_axes']={'mapping':'flipYZ (camera -> pose world)','gaps':gaps,'corr_vs_bodymarker_head_pyr':[round(a,2) for a in ag],'used':HEAD_SRC}
SRC_HPYR=np.array([hpyr(d) for d in DV]); log('D4 HEAD source',HEAD_SRC,'ranges p/y/r',[round(float(np.ptp(SRC_HPYR[:,j])),1) for j in range(3)])
HEAD_SPLIT=(0.30,0.30,0.40)
def head_drive(f):
    # head + 2 neck bones from the source's head-vs-chest rotation; no offsets, no chin floor, no lag. Q is that rotation in her chest frame.
    Q=(CJ0@DV[f]@CJ0.transposed()).to_quaternion(); dUC=cur_rot('UpperChest'); acc=0.0
    for n,fr_ in zip(('Neck','Neck2','Head'),HEAD_SPLIT):
        acc+=fr_; _set_orient(n,dUC@_q_pow(Q,acc).to_matrix()@R0[n])
def head_rel_jena():
    Rel=cur_rot('UpperChest').transposed()@cur_rot('Head'); return hpyr(CJ0.transposed()@Rel@CJ0)
def neck_pr_jena():
    Rel=cur_rot('UpperChest').transposed()@cur_rot('Neck2'); p,y,r=hpyr(CJ0.transposed()@Rel@CJ0); return (p,r)
# ---- spine: whatever rotation dance2 put on Spine / Chest is spread over Spine+Spine2 / Chest+UpperChest (3 joints bend, not 1)
def spine_split():
    for lo,hi in (('Spine','Spine2'),('Chest','UpperChest')):
        q=PB[lo].matrix_basis.to_quaternion(); h=_q_pow(q,0.5); loc=PB[lo].matrix_basis.to_translation()
        PB[lo].matrix_basis=Matrix.Translation(loc)@h.to_matrix().to_4x4(); PB[hi].matrix_basis=h.to_matrix().to_4x4()
    upd()
# ---- pelvis yaw at 1.15x (about its 1 s mean), on top of the hip line
_YAWX=[None]
def pelvis_yaw_extra(f):
    if _YAWX[0] is None:
        ys=np.unwrap(np.radians([math.degrees(math.atan2((L(w,23)-L(w,24)).y,(L(w,23)-L(w,24)).x)) for w in FR])); ys=np.degrees(ys)
        mm=np.convolve(np.pad(ys,15,mode='edge'),np.ones(31)/31,mode='valid'); _YAWX[0]=0.15*(ys-mm)
    wrot_v('Hips',float(_YAWX[0][f]),Vector((0,0,1)))
# ---- forearm twist: Wrist_Twist takes half of the wrist's roll about the forearm
def wrist_twist():
    for sd,s in (('Left','L'),('Right','R')):
        tn=f'Wrist_Twist.{s}'
        if tn not in PB: continue
        a=_nz(PB[sd+' elbow'].tail-PB[sd+' elbow'].head); qd=(cur_rot(sd+' wrist')@cur_rot(sd+' elbow').transposed()).to_quaternion()
        if qd.w<0: qd.negate()
        v=Vector((qd.x,qd.y,qd.z)); tw=2*math.degrees(math.atan2(v.dot(a),qd.w))
        tw=max(-90,min(90,tw)); wrot_v(tn,0.5*tw,a)
# ---- leg capsules (radii fitted to her mesh at rest): thigh, shin, foot per leg; L vs R never closer than r1+r2+4 mm
def _seg_dist(p1,q1,p2,q2):
    d1=q1-p1; d2=q2-p2; r=p1-p2; a=d1.dot(d1); e=d2.dot(d2); f_=d2.dot(r)
    if a<1e-12 and e<1e-12: return (p1-p2).length,p1,p2,0.0,0.0
    if a<1e-12: s=0.0; t=max(0,min(1,f_/e))
    else:
        c=d1.dot(r)
        if e<1e-12: t=0.0; s=max(0,min(1,-c/a))
        else:
            b=d1.dot(d2); den=a*e-b*b; s=max(0,min(1,(b*f_-c*e)/den)) if den>1e-12 else 0.0; t=(b*s+f_)/e
            if t<0: t=0.0; s=max(0,min(1,-c/a))
            elif t>1: t=1.0; s=max(0,min(1,(b-c)/a))
    c1=p1+d1*s; c2=p2+d2*t; return (c1-c2).length,c1,c2,s,t
def _fit_caps():
    rest(); co=np.array([tuple(B.matrix_world.inverted()@(BODY.matrix_world@v.co)) for v in BODY.data.vertices]); vgn={g.index:g.name for g in BODY.vertex_groups}
    dom=[]
    for v in BODY.data.vertices:
        best=None; w=0.0
        for ge in v.groups:
            if ge.weight>w: w=ge.weight; best=vgn.get(ge.group)
        dom.append(best)
    dom=np.array(dom,dtype=object); R={}
    for sd in ('Left','Right'):
        for part,(bn,a_,b_) in {'thigh':(sd+' leg',sd+' leg',sd+' knee'),'shin':(sd+' knee',sd+' knee',sd+' ankle'),'foot':(sd+' ankle',sd+' ankle',sd+' toe')}.items():
            P_=co[dom==bn]; h=np.array(tuple(PB[a_].head)); t=np.array(tuple(PB[b_].head if part!='foot' else PB[b_].tail))
            if len(P_)<10: R[(sd,part)]=(0.05,0.04); continue
            d=t-h; u=np.clip((P_-h)@d/max(d@d,1e-9),0,1); rad=np.linalg.norm(P_-(h+u[:,None]*d),axis=1)
            r0=float(np.percentile(rad[u<0.35],60)) if (u<0.35).sum()>5 else float(np.median(rad)); r1=float(np.percentile(rad[u>0.65],60)) if (u>0.65).sum()>5 else float(np.median(rad))
            R[(sd,part)]=(r0,r1)
    return R
CAPR=_fit_caps(); info['d4_leg_capsule_radii_cm']={f'{k[0][0]}_{k[1]}':[round(x*100,1) for x in v] for k,v in CAPR.items()}; log('D4 leg capsules (cm)',info['d4_leg_capsule_radii_cm'])
def _caps(sd):
    return [('thigh',PB[sd+' leg'].head.copy(),PB[sd+' knee'].head.copy()),('shin',PB[sd+' knee'].head.copy(),PB[sd+' ankle'].head.copy()),('foot',PB[sd+' ankle'].head.copy(),PB[sd+' toe'].tail.copy())]
def leg_pen():
    worst=(0.0,None)
    for pa,a0,a1 in _caps('Left'):
        for pb_,b0,b1 in _caps('Right'):
            d,c1,c2,s,t=_seg_dist(a0,a1,b0,b1); ra=CAPR[('Left',pa)]; rb=CAPR[('Right',pb_)]
            r=(ra[0]+(ra[1]-ra[0])*s)+(rb[0]+(rb[1]-rb[0])*t)+0.004; p=r-d
            if p>worst[0]: worst=(p,(pa,pb_,c1,c2))
    return worst
LEGFIX={'frames':0,'iters':0}
def leg_capsules(locks,f):
    # 1) both feet planted: swing knees apart about each hip->ankle line (feet stay put); 2) a free leg is moved off the other leg (ankle moves, foot keeps its turn)
    fixed=False
    for it in range(6):
        p,hit=leg_pen()
        if p<=0.0005: break
        fixed=True; pa,pb_,c1,c2=hit; sep=c1-c2; sep.z=0
        if sep.length<1e-6: sep=PB['Left leg'].head-PB['Right leg'].head; sep.z=0
        sep.normalize()
        planted={sd:(locks is not None and locks[sd][f] is not None and locks[sd][f][1]>0.99) for sd in ('Left','Right')}
        for sd,sg in (('Left',1.0),('Right',-1.0)):
            push=sep*(sg*(p*0.5+0.001))
            hip=PB[sd+' leg'].head.copy(); ank=PB[sd+' ankle'].head.copy(); Ra={n_:_orient(n_).copy() for n_ in (sd+' ankle',sd+' toe') if n_ in PB}
            if planted[sd] or (pa=='thigh' and pb_=='thigh'):
                ax=_nz(ank-hip); kn=PB[sd+' knee'].head-hip; r_=(kn-ax*kn.dot(ax)).length
                if r_<0.02: continue
                tang=ax.cross(_nz(kn-ax*kn.dot(ax))); ang=math.degrees(push.length/r_)*(1 if tang.dot(push)>=0 else -1)
                wrot_v(sd+' leg',ang,ax)
            else:
                kn=PB[sd+' knee'].head.copy(); pole=kn+_nz(kn-(hip+ank)/2)*0.5; ik2(sd+' leg',sd+' knee',ank+push*2.0,pole)
            for n_,R_ in Ra.items(): _set_orient(n_,R_)
        LEGFIX['iters']+=1
    if fixed: LEGFIX['frames']+=1
    return leg_pen()[0]
# ---- face: ARKit blendshapes -> HER existing shape keys only (no new keys). gain per key; unmapped ARKit shapes are logged.
BMAP=[('Blink L',lambda b:b['eyeBlinkLeft'],1.0),('Blink R',lambda b:b['eyeBlinkRight'],1.0),('vrc.v_aa',lambda b:b['jawOpen'],1.0),
      ('vrc.v_oh',lambda b:b['mouthFunnel'],1.0),('vrc.v_ou',lambda b:b['mouthPucker'],0.8),(':)',lambda b:0.5*(b['mouthSmileLeft']+b['mouthSmileRight']),1.0),
      ('Smirk L',lambda b:max(0.0,b['mouthSmileLeft']-b['mouthSmileRight']),1.5),('Smirk R',lambda b:max(0.0,b['mouthSmileRight']-b['mouthSmileLeft']),1.5),
      (':(',lambda b:0.5*(b['mouthFrownLeft']+b['mouthFrownRight']),1.0),('Lips -',lambda b:0.5*(b['mouthRollLower']+b['mouthRollUpper']),0.7),
      (':|',lambda b:0.5*(b['mouthPressLeft']+b['mouthPressRight']),0.5),('brow sad',lambda b:b['browInnerUp'],0.8),
      ('brow ^',lambda b:0.5*(b['browOuterUpLeft']+b['browOuterUpRight']),1.0),('brow v',lambda b:0.5*(b['browDownLeft']+b['browDownRight']),1.0),
      ('brow furrow',lambda b:0.5*(b['browDownLeft']+b['browDownRight']),0.5),('Happy Blink',lambda b:0.5*(b['eyeSquintLeft']+b['eyeSquintRight']),0.3),
      ('cheekies',lambda b:b['cheekPuff'],1.0)]
USED_ARKIT={'eyeBlinkLeft','eyeBlinkRight','jawOpen','mouthFunnel','mouthPucker','mouthSmileLeft','mouthSmileRight','mouthFrownLeft','mouthFrownRight','mouthRollLower','mouthRollUpper','mouthPressLeft','mouthPressRight','browInnerUp','browOuterUpLeft','browOuterUpRight','browDownLeft','browDownRight','eyeSquintLeft','eyeSquintRight','cheekPuff'}
if FACE is not None:
    if FACE.get('blink_map')=='swapped':
        BMAP[0]=('Blink L',lambda b:b['eyeBlinkRight'],1.0); BMAP[1]=('Blink R',lambda b:b['eyeBlinkLeft'],1.0)
    BMAP=[m for m in BMAP if m[0] in KB]
    info['d4_shape_key_map']={'mapped':[(k,g) for k,_,g in BMAP],'arkit_unmapped':sorted(set(FACE['names'])-USED_ARKIT-{'_neutral'}),'blink_map':FACE.get('blink_map')}
    log('D4 FACE MAP',info['d4_shape_key_map'])
FKEYS=[m[0] for m in BMAP] if FACE is not None else []
def face_drive(f):
    if FACE is None: return
    b=dict(zip(FACE['names'],FACE['bs'][f].tolist())); tot={}
    for k,fn,gn in BMAP:
        try: tot[k]=tot.get(k,0.0)+gn*float(fn(b))
        except KeyError: pass
    for k,v in tot.items(): KB[k].value=max(0.0,min(1.0,KBASE.get(k,0.0)+v))
# ---- snapshots + 120 fps interpolation
def snap():
    return ({pb.name:(pb.matrix_basis.to_translation(),pb.matrix_basis.to_quaternion(),pb.matrix_basis.to_scale()) for pb in PB},{k:KB[k].value for k in FKEYS})
def apply_interp(S0,S1,a):
    b0,k0=S0; b1,k1=S1
    for n,(l0,q0,s0) in b0.items():
        l1,q1,s1=b1[n]; q1_=q1.copy()
        if q0.dot(q1_)<0: q1_.negate()
        PB[n].matrix_basis=Matrix.LocRotScale(l0.lerp(l1,a),q0.slerp(q1_,a),s0.lerp(s1,a))
    for k in k0: KB[k].value=k0[k]+(k1[k]-k0[k])*a
    upd()
def crit_spring(x,fps,omega):
    # critically damped spring follow (no overshoot, no snaps); starts settled on the first second's mean
    y=float(np.mean(x[:int(fps)])); v=0.0; dt=1.0/fps; out=[]
    for xi in x:
        a=omega*omega*(xi-y)-2*omega*v; v+=a*dt; y+=v*dt; out.append(y)
    return np.array(out)
D4_BONES=[n for n in RIG27_BODY]
def bone_px():
    out={}
    for n in D4_BONES+[b.name for b in PB if any(b.name.startswith(x) for x in ('Thumb','IndexFinger','MiddleFinger','RingFinger','LittleFinger'))]:
        out[n]=[px(B.matrix_world@PB[n].head),px(B.matrix_world@PB[n].tail)]
    return out
def head_axes_px():
    M_=B.matrix_world@PB['Head'].matrix; o=M_.to_translation(); R_=M_.to_3x3()@R0['Head'].transposed()@CJ0
    return [px(o)]+[px(o+R_.col[i]*0.09) for i in range(3)]
