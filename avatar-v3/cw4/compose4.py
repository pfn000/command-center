
# catwalk4 step 3 (runner): split video. LEFT = clean render + small inset of the real runway model; RIGHT = V4-style tracking
# (box, facing cones/arrows, skeleton, face, hands, contact dots, floor grid under her feet only) drawn from Jena's own bones.
import os, sys, json, glob, subprocess, math, cv2, numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import overlay as OV
FR,WR,OUT=sys.argv[1],sys.argv[2],sys.argv[3]; os.makedirs(OUT,exist_ok=True); NAME=sys.argv[4] if len(sys.argv)>4 else 'v37r10c-split-catwalk4'
T={}; INFO=[]
for p in sorted(glob.glob(FR+'/track-shard*.json')): T.update({int(k):v for k,v in json.load(open(p)).items()})
for p in sorted(glob.glob(FR+'/catwalk4-shard*.json')): INFO.append(json.load(open(p)))
wr=json.load(open(WR+'/walkref.json')); ks=sorted(T); print('frames',len(ks))
W,H=720,1280; fps=30
src=cv2.VideoCapture(WR+'/walkref-src.mp4'); SRC=[]
while True:
    ok,f=src.read()
    if not ok: break
    SRC.append(f)
sfps=wr.get('fps',30) or 30
def P(a): return np.array(a,float)*np.array([W,H])
YEL=(0,235,255); GRN=(80,255,120)
def draw_grid(img,segs,fx,fy,bh):
    lay=np.zeros_like(img); 
    for a,b in segs:
        a=np.array(a)*[W,H]; b=np.array(b)*[W,H]
        if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))): continue
        cv2.line(lay,tuple(int(x) for x in a),tuple(int(x) for x in b),(42,42,255),2,cv2.LINE_AA)
    yy,xx=np.mgrid[0:H,0:W]; m=np.clip(1.25-np.sqrt(((xx-fx)/(0.62*bh))**2+((yy-fy)/(0.11*bh))**2),0,1)[...,None]*0.85
    return (img*(1-m*(lay.max(2,keepdims=True)>0))+lay*m).astype(np.uint8)
gates={}
def fit_affine(Wd,Px):
    X=np.c_[Wd,np.ones(len(Wd))]; A,*_=np.linalg.lstsq(X,Px,rcond=None); return A
first=ks[0]; hz0=np.mean([T[k]['hips_w'][2] for k in ks])
tmp=OUT+'/_raw.mp4'
pipe=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{2*W}x{H}','-r',str(fps),'-i','-','-c:v','libx264','-preset','medium','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',OUT+f'/{NAME}.mp4'],stdin=subprocess.PIPE)
sheet=[]; picks=set(np.linspace(ks[0],ks[-1],8).astype(int).tolist())
for k in ks:
    e=T[k]; img=cv2.imread(FR+f'/f{k:03d}.jpg')
    if img is None: continue
    img=cv2.resize(img,(W,H)); clean=img.copy(); ov=img.copy()
    b=P(e['mp33_px']); body=np.c_[b,np.ones(33)]; wd=np.array(e['mp33_w'],float)
    A=fit_affine(wd,b); ppm=float(np.linalg.norm(b[23]-b[24])/max(1e-6,np.linalg.norm(wd[23]-wd[24])))
    fx=float((b[29,0]+b[30,0]+b[31,0]+b[32,0])/4); fy=float(max(b[29,1],b[30,1],b[31,1],b[32,1])); bh=float(np.linalg.norm(b[0]-(b[27]+b[28])/2)*1.12)
    ov=draw_grid(ov,e['grid_px'],fx,fy,bh)
    fc=e['face']; fp=lambda n: (np.array(fc[n])*[W,H]).tolist() if n in fc else None
    face=[[fp('earR'),fp('chin'),fp('earL')],[fp('mouthR'),fp('mouthL')]]
    if 'eyeL' in fc: face.append([fp('eyeR'),fp('eyeL')]); face.append([((np.array(fc['eyeL'])+np.array(fc['eyeR']))/2*[W,H]).tolist(),fp('nose')])
    face=[[q for q in pl if q] for pl in face]
    F={'size':[W,H],'body':body.tolist(),'world':wd.tolist(),'proj':A.tolist(),'px_per_m':ppm,
       'hands':{s:(np.array(e['hands'][s])*[W,H]).tolist() for s in 'LR'},'jaw':[fp('chin')],'face':face,
       'floor':{'y':fy,'x':fx,'grid':True},'contact':{'L':e['contact']['L'],'R':e['contact']['R'],'L_glide':False,'R_glide':False},
       'hip_bounce_cm':(e['hips_w'][2]-hz0)*100,
       'hud':{'title':'MOCAP v4 self-view   Jena catwalk4 (her own bones)','lines':[f"walk retargeted from a real runway model ({wr['src']['id']}, MediaPipe)",
              'her RIGHT side blue, LEFT side magenta | red grid = floor | green = planted foot',f"PELVIS  roll {e['roll']:+.0f}  yaw {e['yaw']:+.0f} deg   heel/toe pitch L {e['pitch']['L']:+.0f} R {e['pitch']['R']:+.0f}"]}}
    try: OV.draw(ov,F); OV.hand_insets(ov,F['hands'])
    except Exception as ex: print('overlay err',k,repr(ex)[:200])
    # tracking box around her (all body + finger points) with label
    allp=np.vstack([b,np.array(F['hands']['L']),np.array(F['hands']['R'])]); x1,y1=allp.min(0)-[26,40]; x2,y2=allp.max(0)+[26,18]
    cv2.rectangle(ov,(int(x1),int(y1)),(int(x2),int(y2)),YEL,2,cv2.LINE_AA); OV.text(ov,'TRACK  Jena  1.00',(x1+4,y1-8),0.55,YEL)
    for s,ia,it in (('L',29,31),('R',30,32)):
        if e['contact'][s]:
            for j in (ia,it): cv2.circle(ov,tuple(int(x) for x in b[j]),7,(0,0,0),-1,cv2.LINE_AA); cv2.circle(ov,tuple(int(x) for x in b[j]),5,GRN,-1,cv2.LINE_AA)
    # inset: the real model, same moment of her stride (source played at its own speed, looped)
    if SRC:
        si=int((k/fps)*sfps)%len(SRC); s=SRC[si]; iw=210; ih=int(s.shape[0]*iw/s.shape[1]); ins=cv2.resize(s,(iw,ih))
        x0=W-iw-14; y0=14; clean[y0:y0+ih,x0:x0+iw]=ins; cv2.rectangle(clean,(x0-1,y0-1),(x0+iw,y0+ih),(255,255,255),2)
        OV.text(clean,'real runway model (ref)',(x0,y0+ih+20),0.45,(255,255,255))
    OV.text(clean,'Jena v3.7  clean render',(14,H-20),0.55,(255,255,255))
    fr=np.hstack([clean,ov]); pipe.stdin.write(fr.tobytes())
    if k in picks: sheet.append(cv2.resize(fr,(720,640)))
pipe.stdin.close(); pipe.wait()
if sheet: cv2.imwrite(OUT+f'/{NAME}-sheet.jpg',np.vstack([np.hstack(sheet[i:i+4]) for i in range(0,len(sheet),4)]),[cv2.IMWRITE_JPEG_QUALITY,85])
# gates
M={}
for inf in INFO:
    for kk,v in (inf.get('metrics_raw') or {}).items():
        if isinstance(v,list): M.setdefault(kk,[]).extend(x for x in v if x is not None)
        else: M[kk]=max(M.get(kk,0),v)
fr_=[f for inf in INFO for f in inf['frames'].values()]
clip=[f['clip'] for f in fr_ if f.get('clip')]
hx=M.get('hip_sway_cm',[0]); hxs=np.array(hx)
G={'foot_slide_mm_max':round(M.get('slide_mm',0),2),
   'foot_centre_lines_gap_cm':[round(min(M['foot_line_gap_cm']),2),round(max(M['foot_line_gap_cm']),2)] if M.get('foot_line_gap_cm') else None,'feet_crossed_frames':M.get('cross'),
   'knee_gap_midstance_cm_min':round(min(M['knee_gap_midstance_cm']),2) if M.get('knee_gap_midstance_cm') else None,
   'knee_vs_toe_lateral_cm_max':round(max(M['knee_over_toe_cm']),2) if M.get('knee_over_toe_cm') else None,
   'elbow_bend_deg':[min(M['elbow_deg']),max(M['elbow_deg'])] if M.get('elbow_deg') else None,
   'hip_sway_cm_halfrange':round(float((hxs.max()-hxs.min())/2),2) if len(hxs) else None,
   'head_roll_deg':[min(M['head_roll_deg']),max(M['head_roll_deg'])] if M.get('head_roll_deg') else None,
   'head_pitch_deg':[min(M['head_pitch_deg']),max(M['head_pitch_deg'])] if M.get('head_pitch_deg') else None,
   'heel_strike_pitch_deg':sorted(set(M.get('heel_strike_deg',[])))[:6],'toe_off_pitch_deg':sorted(set(M.get('toe_off_deg',[])))[:6],
   'back_hair_max_deg':max([f.get('max_back_hair_deg',0) for f in fr_] or [0]),
   'clip_max':{kk:max(c.get(kk) or 0 for c in clip) for kk in (clip[0] if clip else {})},
   'gait':INFO[0].get('gait') if INFO else None,'source':INFO[0].get('source') if INFO else None,'frames':len(fr_)}
json.dump(G,open(OUT+f'/{NAME}-gates.json','w'),indent=1); print(json.dumps(G))
