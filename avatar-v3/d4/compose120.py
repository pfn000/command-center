
# dance4 compose (runner): 120 fps split video. LEFT = clean render + source inset (with its face-track contour); RIGHT = V4 tracking overlay
# drawn from Jena's own posed bones every output frame + every body bone as thin glowing lines + head axes + face points; music strip below.
# Also: head strip + face strip (Jena over source, 12 frames), and a re-track QC (MediaPipe face on Jena's own render vs the source).
import os, sys, json, glob, subprocess, math, cv2, numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import overlay as OV
FR,WR,OUT,NAME=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]; os.makedirs(OUT,exist_ok=True)
T={}; INFO=[]
for p in sorted(glob.glob(FR+'/track-shard*.json')): T.update({int(k):v for k,v in json.load(open(p)).items()})
for p in sorted(glob.glob(FR+'/dance2-shard*.json')): INFO.append(json.load(open(p)))
LMJ=json.load(open(WR)); SRCV=os.environ['SRCVID']; ST0=LMJ['t0']; ST1=LMJ['t1']; NS=len(LMJ['w'])
FJ=None
try: FJ=json.load(open(os.environ.get('FACEJ','')))
except Exception as ex: print('no face json',ex)
ks=sorted(T); print('frames',len(ks)); W,H=720,1280; fps=30; NOUT=len(ks); FPO=float(os.environ.get('FPS_OUT','120'))
src=cv2.VideoCapture(SRCV); sfps=src.get(cv2.CAP_PROP_FPS) or 30; src.set(cv2.CAP_PROP_POS_MSEC,ST0*1000); SRCF=[]
while True:
    ok,f=src.read()
    if not ok or len(SRCF)>=int(round((ST1-ST0)*sfps)): break
    SRCF.append(f)
SC_=min(250/SRCF[0].shape[1],440/SRCF[0].shape[0]) if SRCF else 1.0
def P(a): return np.array(a,float)*np.array([W,H])
YEL=(0,235,255); GRN=(80,255,120); CYA=(255,229,34)
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'strip_music.py')).read())
def draw_grid(img,segs,fx,fy,bh):
    lay=np.zeros_like(img)
    for a,b in segs:
        a=np.array(a)*[W,H]; b=np.array(b)*[W,H]
        if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))): continue
        cv2.line(lay,tuple(int(x) for x in a),tuple(int(x) for x in b),(42,42,255),2,cv2.LINE_AA)
    yy,xx=np.mgrid[0:H,0:W]; m=np.clip(1.25-np.sqrt(((xx-fx)/(0.62*bh))**2+((yy-fy)/(0.11*bh))**2),0,1)[...,None]*0.85
    return (img*(1-m*(lay.max(2,keepdims=True)>0))+lay*m).astype(np.uint8)
def fit_affine(Wd,Px):
    X=np.c_[Wd,np.ones(len(Wd))]; A,*_=np.linalg.lstsq(X,Px,rcond=None); return A
def bcol(n):
    if n.startswith('Left') or n.endswith('_L') or n.endswith('.L'): return OV.COL['L']
    if n.startswith('Right') or n.endswith('_R') or n.endswith('.R'): return OV.COL['R']
    if n in ('Neck','Neck2','Head'): return (255,255,255)
    if n in ('Chest','UpperChest','Sternum'): return OV.COL['chest']
    if n in ('Hips','Hip_L','Hip_R','Sacrum'): return OV.COL['hips']
    return OV.COL['spine']
def glow_bones(img,bp):
    lay=np.zeros_like(img); core=[]
    for n,(a,b) in bp.items():
        a=P(a); b=P(b); c=bcol(n); fing=any(n.startswith(x) for x in ('Thumb','Index','Middle','Ring','Little'))
        cv2.line(lay,(int(a[0]),int(a[1])),(int(b[0]),int(b[1])),c,4 if not fing else 3,cv2.LINE_AA); core.append((a,b,c,fing))
    g=cv2.GaussianBlur(lay,(0,0),3.0); out=cv2.addWeighted(img,1.0,g,0.9,0)
    for a,b,c,fing in core:
        cc=tuple(int(min(255,x*0.4+160)) for x in c)
        cv2.line(out,(int(a[0]),int(a[1])),(int(b[0]),int(b[1])),cc,1,cv2.LINE_AA)
        if not fing: cv2.circle(out,(int(a[0]),int(a[1])),2,cc,-1,cv2.LINE_AA)
    return out
def head_gizmo(img,ax):
    o=P(ax[0])
    for i,c in enumerate(((60,60,255),(80,255,80),(255,120,60))):
        e=P(ax[i+1]); cv2.line(img,(int(o[0]),int(o[1])),(int(e[0]),int(e[1])),c,2,cv2.LINE_AA)
def src_face(img,x0,y0,iw,ih,lm,sx,sy):
    if not lm: return
    for n,pts in lm.items():
        q=np.array([[x0+p[0]*sx,y0+p[1]*sy] for p in pts],np.int32)
        cv2.polylines(img,[q],n not in ('browL','browR'),(80,255,255) if 'lips' in n else (255,255,120),1,cv2.LINE_AA)
first=ks[0]; hz0=np.mean([T[k]['hips_w'][2] for k in ks])
NB=len(next(iter(T.values())).get('bones_px',{}))
SH_=200; tmp=OUT+'/_v.mp4'
def enc(br):
    return subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{2*W}x{H+SH_}','-r',str(FPO),'-i','-','-ss',str(ST0),'-t',str(ST1-ST0),'-i',SRCV,'-map','0:v','-map','1:a',
        '-c:v','libx264','-preset','medium','-crf','21','-maxrate',f'{br}k','-bufsize',f'{2*br}k','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',tmp],stdin=subprocess.PIPE)
BR=int(os.environ.get('VBR','10500')); pipe=enc(BR)
sheet=[]; picks=set(np.linspace(ks[0],ks[-1],8).astype(int).tolist()); STRIPK=set(np.linspace(ks[0],ks[-1],12).astype(int).tolist()); HS=[]; FS=[]
os.makedirs('/tmp/jclean',exist_ok=True)
for k in ks:
    e=T[k]; img=cv2.imread(FR+f'/g{k:04d}.jpg')
    if img is None: print('missing',k); continue
    img=cv2.resize(img,(W,H)); clean=img.copy(); ov=img.copy(); t=e.get('t',k); si=min(int(round(t)),NS-1)
    if k%4==0: cv2.imwrite(f'/tmp/jclean/{k:04d}.jpg',clean,[cv2.IMWRITE_JPEG_QUALITY,90])
    b=P(e['mp33_px']); body=np.c_[b,np.ones(33)]; wd=np.array(e['mp33_w'],float)
    A=fit_affine(wd,b); ppm=float(np.linalg.norm(b[23]-b[24])/max(1e-6,np.linalg.norm(wd[23]-wd[24])))
    fx=float((b[29,0]+b[30,0]+b[31,0]+b[32,0])/4); fy=float(max(b[29,1],b[30,1],b[31,1],b[32,1])); bh=float(np.linalg.norm(b[0]-(b[27]+b[28])/2)*1.12)
    ov=draw_grid(ov,e['grid_px'],fx,fy,bh)
    fc=e['face']; fp=lambda n: (np.array(fc[n])*[W,H]).tolist() if n in fc else None
    face=[[fp('earR'),fp('chin'),fp('earL')],[fp('mouthR'),fp('mouthL')]]
    if 'eyeL' in fc: face.append([fp('eyeR'),fp('eyeL')]); face.append([((np.array(fc['eyeL'])+np.array(fc['eyeR']))/2*[W,H]).tolist(),fp('nose')])
    face=[[q for q in pl if q] for pl in face]
    hr=e.get('head_rel',[0,0,0]); sr=e.get('src_head_rel',[0,0,0])
    F={'size':[W,H],'body':body.tolist(),'world':wd.tolist(),'proj':A.tolist(),'px_per_m':ppm,
       'hands':{s:(np.array(e['hands'][s])*[W,H]).tolist() for s in 'LR'},'jaw':[fp('chin')],'face':face,
       'floor':{'y':fy,'x':fx,'grid':True},'contact':{'L':e['contact']['L'],'R':e['contact']['R'],'L_glide':False,'R_glide':False},
       'hip_bounce_cm':(e['hips_w'][2]-hz0)*100,
       'hud':{'title':f'MOCAP v4 self-view   Jena dance4 ({NB} bones drawn, 120 fps)','lines':['driven by her V4 mocap + face track of the TikTok, One-Euro filtered, poses slerped to 120 fps',
              f'HEAD vs chest  pitch {hr[0]:+.0f} yaw {hr[1]:+.0f} roll {hr[2]:+.0f}   (source {sr[0]:+.0f} {sr[1]:+.0f} {sr[2]:+.0f})',
              'her RIGHT side blue, LEFT side magenta | red grid = floor | green = planted foot']}}
    try: OV.draw(ov,F); OV.hand_insets(ov,F['hands'])
    except Exception as ex: print('overlay err',k,repr(ex)[:200])
    if e.get('bones_px'): ov=glow_bones(ov,e['bones_px'])
    if e.get('head_axes_px'): head_gizmo(ov,e['head_axes_px'])
    kv=e.get('keys') or {}
    for i,(kn,lab) in enumerate((('Blink L','blink L'),('Blink R','blink R'),('vrc.v_aa','jaw'),(':)','smile'),('brow ^','brow up'))):
        if kn in kv:
            y=H-150+i*22; cv2.putText(ov,lab,(14,y),cv2.FONT_HERSHEY_SIMPLEX,0.45,(230,230,230),1,cv2.LINE_AA); cv2.rectangle(ov,(90,y-10),(90+int(120*kv[kn]),y),CYA,-1); cv2.rectangle(ov,(90,y-10),(210,y),(120,120,120),1)
    allp=np.vstack([b,np.array(F['hands']['L']),np.array(F['hands']['R'])]); x1,y1=allp.min(0)-[26,40]; x2,y2=allp.max(0)+[26,18]
    cv2.rectangle(ov,(int(x1),int(y1)),(int(x2),int(y2)),YEL,2,cv2.LINE_AA); OV.text(ov,'TRACK  Jena  1.00',(x1+4,y1-8),0.55,YEL)
    for s,ia,it in (('L',29,31),('R',30,32)):
        if e['contact'][s]:
            for j in (ia,it): cv2.circle(ov,tuple(int(x) for x in b[j]),7,(0,0,0),-1,cv2.LINE_AA); cv2.circle(ov,tuple(int(x) for x in b[j]),5,GRN,-1,cv2.LINE_AA)
    if SRCF:
        fr0=SRCF[min(si,len(SRCF)-1)]; ins=cv2.resize(fr0,(int(fr0.shape[1]*SC_),int(fr0.shape[0]*SC_))); iw=ins.shape[1]; ih=ins.shape[0]; x0=W-iw-14; y0=14
        ins=ins.copy(); lm=(FJ['frames'][si].get('lm') if FJ and si<len(FJ['frames']) else None); src_face(ins,0,0,iw,ih,lm,iw,ih)
        clean[y0:y0+ih,x0:x0+iw]=ins; cv2.rectangle(clean,(x0-1,y0-1),(x0+iw,y0+ih),(255,255,255),2)
        OV.text(clean,'source dance (ref, 30 fps) + face track',(x0-40,y0+ih+20),0.45,(255,255,255))
    OV.text(clean,'Jena v3.7  clean render  120 fps',(14,H-20),0.55,(255,255,255))
    fr=np.vstack([np.hstack([clean,ov]),strip(si)])
    pipe.stdin.write(fr.tobytes())
    if k in picks: sheet.append(cv2.resize(fr,(720,int(fr.shape[0]/2))))
    if k in STRIPK and SRCF:
        # head strip (head+shoulders) and face strip (tight), Jena on top, source below
        hp=np.array(fc.get('nose',[0.5,0.2]))*[W,H]; ex_=np.linalg.norm(np.array(fc.get('earL',[0.5,0.2]))*[W,H]-np.array(fc.get('earR',[0.5,0.2]))*[W,H])+1
        def crop(im,c,half):
            x0_=int(max(0,c[0]-half)); y0_=int(max(0,c[1]-half)); return cv2.resize(im[y0_:int(c[1]+half),x0_:int(c[0]+half)],(180,180))
        fr0=SRCF[min(si,len(SRCF)-1)]; lm=(FJ['frames'][si].get('lm') if FJ and si<len(FJ['frames']) else None)
        if lm: sp=np.array(lm['oval'])*[fr0.shape[1],fr0.shape[0]]; scn=sp.mean(0); sw=np.ptp(sp[:,0])
        else: sb=np.array(LMJ['body2d_px'][si]); scn=sb[0]; sw=abs(sb[7][0]-sb[8][0])+1
        HS.append(np.vstack([crop(clean,hp,ex_*2.2),crop(fr0,scn,sw*1.6)])); FS.append(np.vstack([crop(clean,hp,ex_*0.9),crop(fr0,scn,sw*0.7)]))
pipe.stdin.close(); pipe.wait()
sz=os.path.getsize(tmp)/1e6; print('video MB',round(sz,2),'at maxrate',BR)
tries=0
while sz>15.0 and tries<3:
    BR=int(BR*14.2/sz); tries+=1; subprocess.run(['ffmpeg','-v','error','-y','-i',tmp,'-c:v','libx264','-preset','medium','-crf','23','-maxrate',f'{BR}k','-bufsize',f'{2*BR}k','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',OUT+'/_v2.mp4']); os.replace(OUT+'/_v2.mp4',tmp); sz=os.path.getsize(tmp)/1e6; print('re-encoded MB',round(sz,2),'maxrate',BR)
os.replace(tmp,OUT+f'/{NAME}.mp4')
if sheet: cv2.imwrite(OUT+f'/{NAME}-sheet.jpg',np.vstack([np.hstack(sheet[i:i+4]) for i in range(0,len(sheet),4)]),[cv2.IMWRITE_JPEG_QUALITY,85])
if HS: cv2.imwrite(OUT+f'/{NAME}-headstrip.jpg',np.hstack(HS),[cv2.IMWRITE_JPEG_QUALITY,88]); cv2.imwrite(OUT+f'/{NAME}-facestrip.jpg',np.hstack(FS),[cv2.IMWRITE_JPEG_QUALITY,88])
# re-track QC: MediaPipe face landmarker on Jena's own clean render (every 4th output frame = the source's 30 fps grid) vs the source's face track
RT={'ran':False}
try:
    import urllib.request, mediapipe as mp
    from mediapipe.tasks import python as mpt
    from mediapipe.tasks.python import vision
    urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task','/tmp/fl.task')
    det=vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(base_options=mpt.BaseOptions(model_asset_path='/tmp/fl.task'),running_mode=vision.RunningMode.VIDEO,num_faces=1,output_face_blendshapes=True,output_facial_transformation_matrixes=True,min_face_detection_confidence=0.2,min_face_presence_confidence=0.2,min_tracking_confidence=0.2))
    def ypr(M):
        R=np.array(M)[:3,:3]; return (math.degrees(math.asin(max(-1,min(1,-R[1,2])))),math.degrees(math.atan2(R[0,2],R[2,2])),math.degrees(math.atan2(R[1,0],R[1,1])))
    J={};ts=0
    for p in sorted(glob.glob('/tmp/jclean/*.jpg')):
        k=int(os.path.basename(p)[:4]); im=cv2.cvtColor(cv2.imread(p),cv2.COLOR_BGR2RGB); ts+=33
        r=det.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,data=im),ts)
        if r.face_landmarks and r.facial_transformation_matrixes:
            J[int(round(T[k].get('t',k/4)))]=(ypr(r.facial_transformation_matrixes[0]),{c.category_name:c.score for c in r.face_blendshapes[0]} if r.face_blendshapes else {})
    S_={i:(ypr(fr_['M']),fr_['bs']) for i,fr_ in enumerate(FJ['frames']) if fr_.get('M')} if FJ else {}
    common=sorted(set(J)&set(S_)); RT={'ran':True,'jena_frames_checked':len(glob.glob('/tmp/jclean/*.jpg')),'jena_face_found':len(J),'common':len(common)}
    if len(common)>20:
        a=np.array([J[i][0] for i in common]); b=np.array([S_[i][0] for i in common]); a-=np.median(a,0); b-=np.median(b,0)
        RT['corr_pitch_yaw_roll']=[round(float(np.corrcoef(a[:,j],b[:,j])[0,1]),3) for j in range(3)]; RT['range_ratio_pyr']=[round(float(np.ptp(a[:,j])/max(1e-6,np.ptp(b[:,j]))),2) for j in range(3)]
        for side in ('Left','Right'):
            sb=np.array([S_[i][1].get('eyeBlink'+side,0) for i in common]); jb=np.array([J[i][1].get('eyeBlink'+side,0) for i in common])
            RT['blink_'+side]={'source_blink_frames':[common[i] for i in range(len(common)) if sb[i]>0.5],'jena_retrack_blink_frames':[common[i] for i in range(len(common)) if jb[i]>0.5]}
except Exception as ex: RT['error']=repr(ex)[:300]
json.dump({'nout':NOUT,'fps_out':FPO,'video_mb':round(sz,2),'maxrate_k':BR,'retrack':RT},open(OUT+f'/{NAME}-compose.json','w'),indent=1); print('RETRACK',json.dumps(RT)[:1500])
