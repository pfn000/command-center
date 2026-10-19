
# D6 QC (runner, numpy only): merges the shards' 720 Hz samples (6 per 120 fps output frame = 24 per 30 fps source frame) and collision events.
# Reports: collision counts before/after fix with worst timestamps, foot slide on locked feet, joint-velocity/acceleration spikes, jitter
# (hip-relative HF RMS at 120 fps and 30 fps-grid acceleration vs the filtered source), world head yaw correlation.
import os, sys, json, glob, math, numpy as np
FR,OUT,NAME=sys.argv[1],sys.argv[2],sys.argv[3]
S=[]; JN=None
for p in sorted(glob.glob(FR+'/q720-shard*.json')):
    d=json.load(open(p)); JN=d['joints']; S+=d['samples']
S=sorted({round(s['t'],5):s for s in S}.values(),key=lambda s:s['t'])
R={'samples':len(S),'rate_hz':720,'joints':JN}
EV=[]
for p in sorted(glob.glob(FR+'/collisions-shard*.jsonl')):
    for l in open(p):
        try: EV.append(json.loads(l))
        except Exception: pass
seen=set(); EVU=[]
for e in sorted(EV,key=lambda e:e['t_s']):
    k=(e['t_s'],e['check'])
    if k in seen: continue
    seen.add(k); EVU.append(e)
with open(OUT+f'/{NAME}-collisions.jsonl','w') as f:
    for e in EVU: f.write(json.dumps(e)+'\n')
chk={}
for e in EVU:
    c=chk.setdefault(e['check'],{'detected_samples':0,'remaining_samples':0,'worst_before_mm':0,'worst_before_t_s':None,'worst_after_mm':0,'worst_after_t_s':None})
    if e['depth_mm_before']>0: c['detected_samples']+=1
    if e['depth_mm_after']>0: c['remaining_samples']+=1
    if e['depth_mm_before']>c['worst_before_mm']: c['worst_before_mm']=e['depth_mm_before']; c['worst_before_t_s']=e['t_s']
    if e['depth_mm_after']>c['worst_after_mm']: c['worst_after_mm']=e['depth_mm_after']; c['worst_after_t_s']=e['t_s']
R['collisions_720hz']=chk
if S:
    t=np.array([s['t'] for s in S])/30.0; J=np.array([s['J'] for s in S],float); dt=1/720.0
    # foot slide: locked runs, ankle xy drift from the run start
    fs={}
    for i,sd in enumerate(('Left','Right')):
        ja=JN.index(sd+' ankle'); lk=np.array([s['lock'][i] for s in S]); worst=(0.0,None); vmax=(0.0,None); run=None; nrun=0
        for n in range(len(S)):
            if lk[n] and run is None: run=n; nrun+=1
            if run is not None and lk[n]:
                d=np.linalg.norm(J[n,ja,:2]-J[run,ja,:2])*1000
                if d>worst[0]: worst=(d,round(float(t[n]),4))
                if n>run:
                    v=np.linalg.norm(J[n,ja,:2]-J[n-1,ja,:2])/max(1e-9,t[n]-t[n-1])*1000
                    if v>vmax[0]: vmax=(v,round(float(t[n]),4))
            if not lk[n]: run=None
        fs[sd]={'locked_runs':nrun,'max_drift_mm':round(worst[0],1),'at_s':worst[1],'max_speed_mm_s':round(vmax[0],1),'speed_at_s':vmax[1]}
    R['foot_slide_720hz']=fs
    # joint velocity / acceleration spikes (robust: > 8x the joint's median and > 40 m/s^2)
    sp={}; allsp=[]
    tt=np.diff(t); ok=tt>1e-6
    for j,n in enumerate(JN):
        P=J[:,j,:]; V=np.diff(P,axis=0)/np.maximum(tt[:,None],1e-6); A=np.linalg.norm(np.diff(V,axis=0),axis=1)/np.maximum(tt[1:],1e-6)
        med=float(np.median(A)) if len(A) else 0.0; thr=max(8*med,40.0); idx=np.where(A>thr)[0]
        sp[n]={'spikes':int(len(idx)),'median_acc_m_s2':round(med,2),'max_acc_m_s2':round(float(A.max()) if len(A) else 0,1),'worst_s':[round(float(t[i+1]),4) for i in idx[np.argsort(-A[idx])][:5]]}
        allsp+=[(float(A[i]),n,round(float(t[i+1]),4)) for i in idx]
    R['velocity_spikes_720hz']={'total':len(allsp),'per_joint':sp,'worst':[{'acc_m_s2':round(a,1),'joint':n,'t_s':ts} for a,n,ts in sorted(allsp,reverse=True)[:10]]}
    # jitter at 120 fps (every 6th sample): hip-relative high-frequency RMS (residual vs a 4-frame-sigma Gaussian) + hip root
    J120=J[::6]; ih=JN.index('Hips')
    def gz(X,s=4.0):
        r=int(3*s); k=np.exp(-0.5*(np.arange(-r,r+1)/s)**2); k/=k.sum(); Xp=np.pad(X,((r,r),(0,0)),mode='edge'); return np.stack([np.convolve(Xp[:,c],k,mode='valid') for c in range(X.shape[1])],1)
    jit={}
    for n in ('Head','Left wrist','Right wrist','Left ankle','Right ankle','Left index tip','Right index tip'):
        if n not in JN: continue
        X=J120[:,JN.index(n)]-J120[:,ih]; jit[n]=round(float(np.sqrt((np.linalg.norm(X-gz(X),axis=1)**2).mean()))*1000,2)
    X=J120[:,ih]; R['jitter_120fps_hf_rms_mm']={'hip_relative':jit,'hip_root':round(float(np.sqrt((np.linalg.norm(X-gz(X),axis=1)**2).mean()))*1000,2),'def':'RMS of (pos - Gaussian(sigma 4 frames @120 fps)), mm'}
    J30=J[::24]; acc30={}
    for n in ('Hips','Left wrist','Right wrist','Left ankle','Right ankle','Head'):
        if n in JN: acc30[n]=round(float(np.linalg.norm(np.diff(J30[:,JN.index(n)],2,axis=0),axis=1).mean())*1000,2)
    R['acc_30fps_grid_mm_per_frame2']=acc30
    hy=np.array([s['hy'] for s in S],float); hs=np.array([s['hs'] if s['hs'] is not None else np.nan for s in S],float); m=np.isfinite(hs)
    if m.sum()>20:
        a=np.degrees(np.unwrap(np.radians(hy[m]))); b=hs[m]
        R['world_head_yaw']={'corr':round(float(np.corrcoef(a,b)[0,1]),3),'range_jena':round(float(np.ptp(a)),1),'range_src':round(float(np.ptp(b)),1),'mean_abs_err_deg':round(float(np.mean(np.abs((a-np.median(a))-(b-np.median(b))))),1)}
        lagc=[(L_,float(np.corrcoef(a[max(0,L_):len(a)+min(0,L_)],b[max(0,-L_):len(b)-max(0,L_)])[0,1])) for L_ in range(-72,73,6)]
        R['world_head_yaw']['best_lag_ms']=round(max(lagc,key=lambda x:x[1])[0]/720*1000,1)
    post={}
    for s in S:
        for k,v in (s.get('post') or {}).items():
            if v>0: post.setdefault(k,[0,0.0,None]); post[k][0]+=1
            if v>post.get(k,[0,0.0,None])[1]: post.setdefault(k,[0,0.0,None]); post[k][1]=v; post[k][2]=round(s['t']/30.0,4)
    R['post_fix_720hz']={k:{'samples':v[0],'worst_mm':round(v[1],2),'at_s':v[2]} for k,v in post.items()}
for p in sorted(glob.glob(FR+'/dance2-shard*.json')):
    try:
        d=json.load(open(p)).get('d6') or {}
        R.setdefault('autofix_passes_by_shard',{})[os.path.basename(p)]=[{'pass':h['pass'],'counts':h['counts'],'worst_mm_s':h.get('worst_mm_s')} for h in d.get('qc720_passes',[])]
        if d.get('qc720_error'): R.setdefault('errors',[]).append(d['qc720_error'][-300:])
    except Exception as ex: R.setdefault('errors',[]).append(repr(ex)[:200])
if os.path.exists(FR+'/jena-colliders.json'):
    import shutil; shutil.copy(FR+'/jena-colliders.json',OUT+'/jena-colliders.json')
json.dump(R,open(OUT+f'/{NAME}-qc720.json','w'),indent=1)
print('QC720',json.dumps({k:R.get(k) for k in ('samples','collisions_720hz','foot_slide_720hz','jitter_120fps_hf_rms_mm','world_head_yaw','post_fix_720hz')})[:3000])
