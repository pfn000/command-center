
# catwalk4 step 1 (runs on the Actions runner): fetch real runway walk clips, MediaPipe-track the model, pick the cleanest
# front-on walking stretch (single model, full body, feet visible), and measure her gait so anim.py can retarget it onto Jena.
import os, sys, json, math, subprocess, urllib.request, cv2, numpy as np, mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
OUT=sys.argv[1]; G=json.load(open(sys.argv[2]))['walkref']; os.makedirs(OUT,exist_ok=True); os.makedirs('/tmp/src',exist_ok=True)
LOG=[]
def log(*a):
    s=' '.join(str(x) for x in a); print('[wr]',s,flush=True); LOG.append(s)
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'
def fetch(s):
    p=f"/tmp/src/{s['id']}.mp4"
    if s['kind']=='yt':
        for pc in ['', 'tv', 'web_safari', 'mweb', 'ios', 'android_vr', 'web_embedded']:
            cmd=['yt-dlp','--no-playlist','-q','--no-warnings','-f','bv*[height<=720][ext=mp4]/bv*[height<=720]/b[height<=720]/b','-o',p]
            if pc: cmd+=['--extractor-args',f'youtube:player_client={pc}']
            if s.get('sections'): cmd+=['--download-sections',s['sections']]
            r=subprocess.run(cmd+['https://www.youtube.com/watch?v='+s['id']],capture_output=True,text=True,timeout=600)
            if os.path.exists(p) and os.path.getsize(p)>100000: log('fetched',s['id'],'client',pc or 'default',os.path.getsize(p)); return p
            log('yt fail',s['id'],pc or 'default',(r.stderr or r.stdout).strip().splitlines()[-1:] )
        return None
    if s['kind']=='ytdlp':
        cmd=['yt-dlp','--no-playlist','-q','--no-warnings','-f','bv*[height<=1080]+ba/b[height<=1080]/b','--merge-output-format','mp4','-o',p]
        if s.get('sections'): cmd+=['--download-sections',s['sections']]
        r=subprocess.run(cmd+[s['url']],capture_output=True,text=True,timeout=600)
        if os.path.exists(p) and os.path.getsize(p)>100000: log('fetched',s['id'],os.path.getsize(p)); return p
        log('ytdlp fail',s['id'],(r.stderr or r.stdout).strip().splitlines()[-1:]); return None
    r=subprocess.run(['curl','-sL','-A',UA,'-o',p,s['url']],timeout=300)
    if os.path.exists(p) and os.path.getsize(p)>100000: log('fetched',s['id'],os.path.getsize(p)); return p
    log('fetch fail',s['id']); return None
def model(name):
    f=f'/tmp/pl_{name}.task'
    if not os.path.exists(f): urllib.request.urlretrieve(f'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_{name}/float16/latest/pose_landmarker_{name}.task',f)
    return f
TRK={}
def track(path,name,step=1,maxw=720,t0=0.0,t1=1e9,np_=1):
    TRK.clear()
    det=vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path=model(name)),running_mode=vision.RunningMode.VIDEO,num_poses=np_,min_pose_detection_confidence=0.5,min_pose_presence_confidence=0.5,min_tracking_confidence=0.5))
    cap=cv2.VideoCapture(path); fps=cap.get(cv2.CAP_PROP_FPS) or 30; W=int(cap.get(3)); H=int(cap.get(4)); R=[]; i=0; prev=None
    cap.set(cv2.CAP_PROP_POS_MSEC,t0*1000); i=int(round(t0*fps))
    while True:
        ok,fr=cap.read()
        if not ok or i/fps>t1: break
        if (i-int(round(t0*fps)))%step==0:
            sm=cv2.resize(fr,(64,36)); g=cv2.cvtColor(sm,cv2.COLOR_BGR2GRAY).astype(np.float32); cut=prev is not None and float(np.abs(g-prev).mean())>28; prev=g
            if fr.shape[1]>maxw: fr=cv2.resize(fr,(maxw,int(fr.shape[0]*maxw/fr.shape[1])))
            r=det.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,data=cv2.cvtColor(fr,cv2.COLOR_BGR2RGB)),int(i*1000/fps))
            if r.pose_world_landmarks:
                k=0
                if len(r.pose_landmarks)>1:   # first frame: the biggest person is the model; after that, stay on the same person (nearest hip centre)
                    hs=[max(l.y for l in p_)-min(l.y for l in p_) for p_ in r.pose_landmarks]; others=sum(1 for h in hs if h>0.35*max(hs))-1
                    cs=[((p_[23].x+p_[24].x)/2,(p_[23].y+p_[24].y)/2) for p_ in r.pose_landmarks]
                    if TRK.get('c') is None: k=int(np.argmax(hs))
                    else: k=int(np.argmin([(c[0]-TRK['c'][0])**2+(c[1]-TRK['c'][1])**2 for c in cs]))
                else: others=0; k=0
                if TRK.get('c') is not None:   # never jump to someone else: a detection far from her last spot = she was missed this frame
                    pk_=r.pose_landmarks[k]; cc_=((pk_[23].x+pk_[24].x)/2,(pk_[23].y+pk_[24].y)/2)
                    if (cc_[0]-TRK['c'][0])**2+(cc_[1]-TRK['c'][1])**2>0.09**2:
                        TRK['miss']=TRK.get('miss',0)+1; R.append((i,cut,None,None,others)); i+=1; continue

                pk=r.pose_landmarks[k]; TRK['c']=((pk[23].x+pk[24].x)/2,(pk[23].y+pk[24].y)/2)
                R.append((i,cut,[[l.x,l.y,l.z] for l in r.pose_world_landmarks[k]],[[l.x,l.y,l.visibility] for l in r.pose_landmarks[k]],others))
            else: R.append((i,cut,None,None,0))
        i+=1
    det.close(); return R,fps,W,H
REJ={}; SRCBONUS=0.0
def windows(R,fps,step,win_s):
    REJ.clear()
    # score every window that sits inside one shot: single model, whole body in frame, feet visible, front-on, legs alternating
    n=len(R); L=max(4,int(round(win_s*fps/step))); best=[]
    cuts=[k for k,r in enumerate(R) if r[1]]
    for s in range(0,max(1,n-L),max(1,int(fps/step/3))):
        seg=R[s:s+L]
        if any(c for c in cuts if s<c<s+L): continue
        if sum(1 for r in seg if r[3])<0.95*L: continue
        N=np.array([r[3] for r in seg if r[3]]); vis=N[:,[27,28,29,30,31,32],2].mean()
        inb=((N[:,[0,27,28,29,30,31,32],1]>0.0)&(N[:,[0,27,28,29,30,31,32],1]<0.985)).all(1).mean()
        torso=np.linalg.norm((N[:,11,:2]+N[:,12,:2])/2-(N[:,23,:2]+N[:,24,:2])/2,axis=1); torso=np.maximum(torso,1e-3)
        front=np.median(np.abs(N[:,11,0]-N[:,12,0])/torso)
        hipx=(N[:,23,0]+N[:,24,0])/2; armout=float(np.max(np.maximum(np.abs(N[:,15,0]-hipx),np.abs(N[:,16,0]-hipx))/torso))   # arms out = posing / turning, not walking
        grow=float(np.polyfit(np.arange(len(N)),np.max(N[:,[27,28,31,32],1],1)-N[:,0,1],1)[0]*len(N))                 # body grows in frame = walking toward camera
        height=np.median(np.max(N[:,[27,28,31,32],1],1)-N[:,0,1])
        d=(N[:,27,1]-N[:,28,1])/torso; d=d-np.convolve(d,np.ones(5)/5,'same')*0
        zc=int(np.sum(np.diff(np.sign(d-np.median(d)))!=0)); amp=float(np.percentile(d,90)-np.percentile(d,10))
        st_=dict(vis=round(float(vis),3),inb=round(float(inb),3),front=round(float(front),3),zc=zc,amp=round(amp,3))
        if REJ.get('n',0)<3 and (vis<0.5 or inb<0.85 or front<0.35 or amp<0.03): REJ['n']=REJ.get('n',0)+1; REJ.setdefault('ex',[]).append(st_)
        if vis<0.5 or inb<0.97 or front<0.35 or amp<0.03 or armout>0.9 or grow<0.0: continue
        solo=1.0-np.mean([r[4]>0 for r in seg])
        if solo<0.8: continue
        sc=vis*2+inb+min(height,0.9)+min(zc,8)*0.15+min(amp,0.3)+float(SRCBONUS)
        best.append((round(float(sc),3),s,dict(vis=round(float(vis),3),inb=round(float(inb),3),front=round(float(front),3),height=round(float(height),3),zc=zc,amp=round(amp,3),armout=round(armout,2),grow=round(grow,3))))
    best.sort(key=lambda b:-b[0]); return best[:5]
cands=[]
FORCE=G.get('force')
if FORCE:   # a window already judged by eye: that source, that start
    for s in G['sources']:
        if s['id']!=FORCE['id']: continue
        p=fetch(s)
        if p:
            cap=cv2.VideoCapture(p); fps=cap.get(cv2.CAP_PROP_FPS) or 30; W=int(cap.get(3)); H=int(cap.get(4)); cap.release()
            cands.append((9.9,s,p,float(FORCE['t0']),{'forced':True},fps,W,H)); log('FORCED',s['id'],FORCE)
for s in ([] if FORCE else G['sources']):
    try:
        p=fetch(s)
        if not p: continue
        cap=cv2.VideoCapture(p); fps=cap.get(cv2.CAP_PROP_FPS) or 30; nfr=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); cap.release()
        step=2 if nfr/fps>40 else 1
        R,fps,W,H=track(p,'lite',step=step,maxw=640,np_=2)
        global_dummy=0; SRCBONUS=s.get('bonus',0.0); ws=windows(R,fps,step,G.get('win_s',3.0))
        log('scan',s['id'],'frames',len(R),'det',sum(1 for r in R if r[3]),'cuts',sum(1 for r in R if r[1]),'fps',round(fps,2),'size',W,H,'best',ws[:2],'rejected eg',REJ.get('ex'))
        for sc,st,info in ws[:2]: cands.append((sc,s,p,R[st][0]/fps,info,fps,W,H))
    except Exception as e: log('source error',s['id'],repr(e)[:300])
if not cands: log('NO usable walk found'); json.dump({'ok':False,'log':LOG},open(OUT+'/walkref.json','w')); sys.exit(0)
cands.sort(key=lambda c:-c[0]); sc,S,P,t0,info,fps,W,H=cands[0]
WIN=G.get('win_s',3.0); t0=max(0,t0); t1=t0+WIN
log('PICK',S['id'],'t0',round(t0,2),'score',sc,info,'others',[(c[1]['id'],round(c[3],1),c[0]) for c in cands[1:6]])
R,fps,W,H=track(P,'heavy',1,1280,t0,t1,np_=2)
N=np.array([r[3] if r[3] else [[np.nan]*3]*33 for r in R],float); Wd=np.array([r[2] if r[2] else [[np.nan]*3]*33 for r in R],float)
for A in (N,Wd):
    for j in range(33):
        for c in range(3):
            y=A[:,j,c]; ok=~np.isnan(y)
            if ok.sum()>2: A[:,j,c]=np.interp(np.arange(len(y)),np.where(ok)[0],y[ok])
k=np.exp(-0.5*(np.arange(-3,4)/1.2)**2); k/=k.sum()
def sm(x): return np.convolve(np.pad(x,3,mode='edge'),k,'valid')
for A in (N,Wd):
    for j in range(33):
        for c in range(2 if A is N else 3): A[:,j,c]=sm(A[:,j,c])
T=len(R); t=np.arange(T)/fps
torso=np.linalg.norm(((N[:,11,:2]+N[:,12,:2])-(N[:,23,:2]+N[:,24,:2]))/2*np.array([W,H]),axis=1)
d=((N[:,27,1]-N[:,28,1])*H)/torso
def peaks(x,mind):
    P=[]
    for i in range(1,len(x)-1):
        if x[i]>=x[i-1] and x[i]>x[i+1] and x[i]>np.median(x)+0.25*(np.percentile(x,95)-np.median(x)):
            if P and i-P[-1]<mind:
                if x[i]>x[P[-1]]: P[-1]=i
            else: P.append(i)
    return P
mind=int(0.35*fps)
LP=peaks(d,mind); RP=peaks(-d,mind)
log('left strikes',LP,'right strikes',RP)
cyc=[(LP[i],LP[i+1]) for i in range(len(LP)-1) if 0.6*fps<LP[i+1]-LP[i]<2.6*fps]
if not cyc and len(RP)>1: cyc=[(RP[i],RP[i+1]) for i in range(len(RP)-1)]; shift=0.5
else: shift=0.0
Tc=float(np.median([b-a for a,b in cyc])/fps) if cyc else None
def ang(a,b,c):
    v1=a-b; v2=c-b; return np.degrees(np.arccos(np.clip(np.sum(v1*v2,-1)/(np.linalg.norm(v1,axis=-1)*np.linalg.norm(v2,axis=-1)+1e-9),-1,1)))
# body frame per frame (MediaPipe world: x = image right, y = down, z = away from camera)
pel=(Wd[:,23]+Wd[:,24])/2; ch=(Wd[:,11]+Wd[:,12])/2; up=ch-pel; up/=np.linalg.norm(up,axis=1,keepdims=True)
lat=Wd[:,23]-Wd[:,24]; lat=lat-up*np.sum(lat*up,1,keepdims=True); lat/=np.linalg.norm(lat,axis=1,keepdims=True)
fwd=np.cross(lat,up)   # points the way she faces (toward the camera = -z)
def sag(v):   # angle of limb vector v from straight-down, in her sagittal plane; + = forward
    dn=-up; return np.degrees(np.arctan2(np.sum(v*fwd,1),np.sum(v*dn,1)))
F={}
F['knee_L']=180-ang(Wd[:,23],Wd[:,25],Wd[:,27]); F['knee_R']=180-ang(Wd[:,24],Wd[:,26],Wd[:,28])
F['elbow_L']=180-ang(Wd[:,11],Wd[:,13],Wd[:,15]); F['elbow_R']=180-ang(Wd[:,12],Wd[:,14],Wd[:,16])
F['thigh_L']=sag(Wd[:,25]-Wd[:,23]); F['thigh_R']=sag(Wd[:,26]-Wd[:,24])
F['arm_L']=sag(Wd[:,13]-Wd[:,11]); F['arm_R']=sag(Wd[:,14]-Wd[:,12])
F['foot_L']=np.degrees(np.arctan2(-(Wd[:,31,1]-Wd[:,29,1]),np.sum((Wd[:,31]-Wd[:,29])*fwd,1)))
F['foot_R']=np.degrees(np.arctan2(-(Wd[:,32,1]-Wd[:,30,1]),np.sum((Wd[:,32]-Wd[:,30])*fwd,1)))
F['pelvis_roll']=np.degrees(np.arctan2(-(N[:,23,1]-N[:,24,1])*H,(N[:,23,0]-N[:,24,0])*W))      # + = her left hip higher
F['pelvis_yaw']=np.degrees(np.arctan2(Wd[:,24,2]-Wd[:,23,2],Wd[:,23,0]-Wd[:,24,0]))              # + = left hip toward camera
F['shoulder_yaw']=np.degrees(np.arctan2(Wd[:,12,2]-Wd[:,11,2],Wd[:,11,0]-Wd[:,12,0]))
hipw_px=np.abs(N[:,23,0]-N[:,24,0])*W; hipw_m=np.linalg.norm(Wd[:,23]-Wd[:,24],axis=1)
mpx=hipw_m/np.maximum(hipw_px,1)
F['sway_m']=((N[:,23,0]+N[:,24,0])/2*W-np.convolve(np.pad((N[:,23,0]+N[:,24,0])/2*W,int(fps),mode='edge'),np.ones(2*int(fps)+1)/(2*int(fps)+1),'valid'))*mpx
F['head_tilt']=np.degrees(np.arctan2(-(N[:,7,1]-N[:,8,1])*H,(N[:,7,0]-N[:,8,0])*W))
NP=50; curves={}
if cyc:
    for kf,x in F.items():
        rows=[]
        for a,b in cyc:
            ph=np.linspace(0,1,NP,endpoint=False); rows.append(np.interp(a+ph*(b-a),np.arange(T),x))
        c=np.median(np.array(rows),0)
        if shift: c=np.roll(c,NP//2)
        curves[kf]=np.round(c,3).tolist()
sw_w=[float(abs(Wd[i,27,0]-Wd[i,28,0])) for i in LP+RP]
res={'ok':bool(cyc),'src':S,'pick_score':sc,'pick_info':info,'fps':fps,'size':[W,H],'t0':round(t0,3),'t1':round(t0+T/fps,3),'cycle_s':Tc,'n_cycles':len(cyc),
     'left_strike_frames':LP,'right_strike_frames':RP,'phase_samples':NP,'curves':curves,
     'ranges':{k:[round(float(np.percentile(v,5)),2),round(float(np.percentile(v,95)),2)] for k,v in F.items()},
     'step_width_at_strike_m_mp':[round(x,3) for x in sw_w],'log':LOG}
json.dump(res,open(OUT+'/walkref.json','w'),indent=0)
log('cycle_s',Tc,'cycles',len(cyc),'ranges',res['ranges'])
# source segment for the inset (same frames), and a skeleton proof sheet
xs=N[:,[0,11,12,15,16,23,24,27,28,31,32],0]; cx0=max(0.0,float(np.nanmin(xs))-0.08); cx1=min(1.0,float(np.nanmax(xs))+0.08)
if G.get('inset_crop',True) and cx1-cx0<0.85:
    cw=int((cx1-cx0)*W)//2*2; cxp=int(cx0*W)//2*2; VF=f'crop={cw}:ih:{cxp}:0,scale=-2:720'; log('inset crop x',round(cx0,3),round(cx1,3))
else: VF='scale=-2:720'
subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t0),'-i',P,'-t',str(T/fps),'-vf',VF,'-an','-c:v','libx264','-crf','22','-pix_fmt','yuv420p',OUT+'/walkref-src.mp4'])
Eg=[(11,12),(11,13),(13,15),(12,14),(14,16),(11,23),(12,24),(23,24),(23,25),(25,27),(24,26),(26,28),(27,29),(29,31),(27,31),(28,30),(30,32),(28,32)]
cap=cv2.VideoCapture(P); cap.set(cv2.CAP_PROP_POS_MSEC,t0*1000); tiles=[]; picks=set(np.linspace(0,T-1,8).astype(int).tolist())
for i in range(T):
    ok,fr=cap.read()
    if not ok: break
    if i in picks:
        Hh,Ww=fr.shape[:2]
        for a,b in Eg: cv2.line(fr,(int(N[i,a,0]*Ww),int(N[i,a,1]*Hh)),(int(N[i,b,0]*Ww),int(N[i,b,1]*Hh)),(80,230,255),3,cv2.LINE_AA)
        lab='L strike' if any(abs(i-p)<=1 for p in LP) else ('R strike' if any(abs(i-p)<=1 for p in RP) else '')
        if lab: cv2.putText(fr,lab,(20,60),cv2.FONT_HERSHEY_SIMPLEX,1.6,(0,255,255),3)
        tiles.append(cv2.resize(fr,(int(360*Ww/Hh),360)))
if tiles: cv2.imwrite(OUT+'/walkref-sheet.jpg',np.vstack([np.hstack(tiles[:4]),np.hstack(tiles[4:8])]) if len(tiles)==8 else np.hstack(tiles))
