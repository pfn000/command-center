
# dance4 FILTER stage (big-fix pass Oct 19): L/R swap repair first, then a zero-phase One-Euro filter on every channel the clip uses
# (33 body markers, 2D body track, 21+21 hand landmarks, pelvis track, face transform + 52 blendshapes). Zero-phase = run forward and
# backward and average, so peaks are not delayed (measured below as peak lag in frames). Jitter = mean |frame-to-frame acceleration|.
def _oe1(x,fps,mc,beta,dc=1.0):
    x=np.asarray(x,float); y=np.empty_like(x); y[0]=x[0]; dp=0.0; te=1.0/fps
    al=lambda c: 1.0/(1.0+(1.0/(2*math.pi*c))/te); ad=al(dc)
    for i in range(1,len(x)):
        dx=(x[i]-y[i-1])*fps; dp=ad*dx+(1-ad)*dp; a=al(mc+beta*abs(dp)); y[i]=a*x[i]+(1-a)*y[i-1]
    return y
def one_euro(X,fps=30.0,mc=3.0,beta=2.0,scale=1.0):
    X=np.asarray(X,float); sh=X.shape; F=X.reshape(sh[0],-1)/scale; O=np.empty_like(F)
    for j in range(F.shape[1]):
        c=F[:,j]
        if not np.all(np.isfinite(c)): O[:,j]=c; continue
        O[:,j]=0.5*(_oe1(c,fps,mc,beta)+_oe1(c[::-1],fps,mc,beta)[::-1])
    return (O*scale).reshape(sh)
def _acc(P): P=np.asarray(P,float); return float(np.linalg.norm(np.diff(P,2,axis=0),axis=-1).mean()) if len(P)>3 else 0.0
def _gz(a,s=1.5):
    k=np.exp(-0.5*(np.arange(-6,7)/s)**2); k/=k.sum(); return np.convolve(np.pad(a,6,mode='edge'),k,'valid')
def _peaklag(raw,fil,win=3):
    r=raw-raw.mean(0); u,s,vt=np.linalg.svd(r,full_matrices=False); ax=vt[0]; a=_gz(r@ax); b=(fil-fil.mean(0))@ax; L_=[]; rng=np.ptp(a)
    for i in range(4,len(a)-4):
        for sg in (1,-1):
            seg=sg*a[max(0,i-8):i+9]
            if sg*a[i]==seg.max() and (sg*a[i]-seg.min())>0.15*rng:
                j0=max(0,i-win); L_.append(j0+int(np.argmax(sg*b[j0:i+win+1]))-i)
    return (int(np.abs(L_).max()) if L_ else 0, round(float(np.mean(np.abs(L_))),2) if L_ else 0.0, len(L_))
def _mp2b_np(A): return np.stack([A[...,0],A[...,2],-A[...,1]],axis=-1)
# ---- 1) L/R swaps (same rule as dance2: hip-line yaw jumps >110 deg from its running reference)
_PAIRS=[(1,4),(2,5),(3,6),(7,8),(9,10),(11,12),(13,14),(15,16),(17,18),(19,20),(21,22),(23,24),(25,26),(27,28),(29,30),(31,32)]
_W=np.array(LM['w'],float); _B2=np.array(LM['body2d_px'],float); _CT=LM.get('contact')
def _hy(w): h=_mp2b_np(w[23])-_mp2b_np(w[24]); return math.degrees(math.atan2(h[1],h[0]))
_ys=[_hy(_W[k]) for k in range(len(_W))]; _ref=float(np.median(_ys[:15])); _nsw=0
for k in range(len(_W)):
    d_=(_ys[k]-_ref+180)%360-180
    if abs(d_)>110:
        for a_,b_ in _PAIRS:
            _W[k,[a_,b_]]=_W[k,[b_,a_]]; _B2[k,[a_,b_]]=_B2[k,[b_,a_]]
        if _CT and _CT[k]: _CT[k]={'L':_CT[k].get('R'),'R':_CT[k].get('L'),**{kk:vv for kk,vv in _CT[k].items() if kk not in('L','R')}}
        _nsw+=1; _ys[k]=_hy(_W[k])
    _ref=0.85*_ref+0.15*_ys[k] if abs((_ys[k]-_ref+180)%360-180)<60 else _ref
# ---- 2) One-Euro (zero-phase). Units: metres for 3D; 2D px scaled to metres by the torso; degrees as radians; blendshapes 0..1
OE=dict(body=(3.0,2.0),hands=(3.0,2.0),pelvis=(3.0,1.0),face_rot=(3.0,1.0),blend=(4.0,6.0))
_tpx=float(np.linalg.norm((_B2[:,11]+_B2[:,12])/2-(_B2[:,23]+_B2[:,24])/2,axis=1).mean()); _tm=float(np.linalg.norm((_W[:,11]+_W[:,12])/2-(_W[:,23]+_W[:,24])/2,axis=1).mean()); _pxm=_tpx/max(_tm,1e-6)
_Wf=one_euro(_W,LM['fps'],*OE['body']); _B2f=one_euro(_B2,LM['fps'],*OE['body'],scale=_pxm)
_HPr=LM.get('hands_px') or [{}]*len(_W)
for _s in ('L','R'):
    A_=np.full((len(_W),21,2),np.nan)
    for k in range(len(_W)):
        h_=_HPr[k].get(_s) if isinstance(_HPr[k],dict) else None
        if h_ and len(h_)>=21: A_[k]=np.array(h_[:21],float)
    ok_=~np.isnan(A_[:,0,0])
    if ok_.sum()>5:
        for j in range(21):
            for c in range(2): A_[~ok_,j,c]=np.interp(np.flatnonzero(~ok_),np.flatnonzero(ok_),A_[ok_,j,c])
        Af=one_euro(A_,LM['fps'],*OE['hands'],scale=_pxm)
        for k in range(len(_W)):
            if ok_[k]: _HPr[k][_s]=Af[k].tolist()
_PRr=LM.get('pelvis_rpy') or [{'roll':0,'pitch':0,'yaw':0}]*len(_W)
_PA=np.radians(np.unwrap(np.radians([[d['roll'],d['pitch'],d['yaw']] for d in _PRr]),axis=0)*180/np.pi)
_PAf=np.degrees(one_euro(_PA,LM['fps'],*OE['pelvis']))
LM['pelvis_rpy']=[{'roll':float(a[0]),'pitch':float(a[1]),'yaw':float(a[2])} for a in _PAf]
JIT={}
_seg={'pelvis_2d':None,'wrist_L':[15],'wrist_R':[16],'ankle_L':[27],'ankle_R':[28],'head':[0,7,8]}
for k_,ix in _seg.items():
    if ix is None:
        a=np.c_[(_B2[:,23]+_B2[:,24])/2/_pxm]; b=np.c_[(_B2f[:,23]+_B2f[:,24])/2/_pxm]
    else: a=_W[:,ix].mean(1); b=_Wf[:,ix].mean(1)
    JIT[k_]={'acc_mm_per_frame2_before':round(_acc(a)*1000,2),'acc_after':round(_acc(b)*1000,2),'peak_lag_frames_max_mean_n':_peaklag(a,b)}
LM['w']=_Wf.tolist(); LM['body2d_px']=_B2f.tolist(); LM['hands_px']=_HPr; FR=LM['w']
info['d4_filter']={'one_euro':OE,'lr_swaps_fixed_before_filter':_nsw,'jitter_source_markers':JIT,'px_per_m':round(_pxm,1)}
log('D4 FILTER',info['d4_filter'])
# ---- 3) face track (MediaPipe Face Landmarker, run on Actions by the face job): head transform + 52 blendshapes per frame
FACE=None
try:
    _fj=json.load(open('avatar-v3/d4/face.json')); _ff=_fj['frames'][:len(_W)]
    _okf=np.array([fr_.get('M') is not None for fr_ in _ff]); log('D4 FACE frames with a face',int(_okf.sum()),'of',len(_ff))
    if _okf.sum()>=0.5*len(_ff):
        Q_=np.zeros((len(_ff),4)); 
        for k,fr_ in enumerate(_ff):
            if fr_.get('M') is not None: Q_[k]=list(Matrix([r[:3] for r in fr_['M'][:3]]).to_quaternion())
        idx_=np.flatnonzero(_okf)
        for i in range(1,len(idx_)):
            if np.dot(Q_[idx_[i]],Q_[idx_[i-1]])<0: Q_[idx_[i]]*=-1
        for c in range(4): Q_[~_okf,c]=np.interp(np.flatnonzero(~_okf),idx_,Q_[_okf,c])
        Q_=one_euro(Q_,LM['fps'],*OE['face_rot']); Q_/=np.linalg.norm(Q_,axis=1)[:,None]
        names_=sorted({n for fr_ in _ff if fr_.get('bs') for n in fr_['bs']}); BS=np.full((len(_ff),len(names_)),np.nan)
        for k,fr_ in enumerate(_ff):
            if fr_.get('bs'): BS[k]=[fr_['bs'].get(n,0.0) for n in names_]
        okb=~np.isnan(BS[:,0])
        for c in range(BS.shape[1]): BS[~okb,c]=np.interp(np.flatnonzero(~okb),np.flatnonzero(okb),BS[okb,c])
        BSr=BS.copy(); BS=np.clip(one_euro(BS,LM['fps'],*OE['blend']),0,1)
        FACE=dict(q=Q_,ok=_okf,names=names_,bs=BS,bs_raw=BSr,blink_map=_fj.get('blink_map'),lm=[fr_.get('lm') for fr_ in _ff])
except Exception as ex: log('D4 FACE unavailable',repr(ex)[:200])
info['d4_face_track']=None if FACE is None else {'frames_with_face':int(FACE['ok'].sum()),'blendshapes':len(FACE['names']),'blink_map':FACE['blink_map']}
