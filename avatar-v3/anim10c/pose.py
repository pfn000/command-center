
# MediaPipe Pose (heavy) on Saidie's TikTok dance ref -> 3D world landmarks for retargeting onto Jena. Solo dancer (num_poses=1).
import cv2, json, sys, numpy as np, urllib.request, mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
src,out,win_s=sys.argv[1],sys.argv[2],float(sys.argv[3])
urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task','/tmp/pl.task')
det=vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path='/tmp/pl.task'),running_mode=vision.RunningMode.VIDEO,num_poses=1,min_pose_detection_confidence=0.5,min_pose_presence_confidence=0.5,min_tracking_confidence=0.5))
cap=cv2.VideoCapture(src); fps=cap.get(cv2.CAP_PROP_FPS) or 30; W=int(cap.get(3)); H=int(cap.get(4)); Wd=[]; Nm=[]; i=0
while True:
    ok,fr=cap.read()
    if not ok: break
    r=det.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,data=cv2.cvtColor(fr,cv2.COLOR_BGR2RGB)),int(i*1000/fps))
    if r.pose_world_landmarks:
        Wd.append([[l.x,l.y,l.z] for l in r.pose_world_landmarks[0]]); Nm.append([[l.x,l.y,l.visibility] for l in r.pose_landmarks[0]])
    else: Wd.append(None); Nm.append(None)
    i+=1
N=len(Wd); det_=np.array([w is not None for w in Wd]); print('frames',N,'fps',fps,'detected',int(det_.sum()))
vis=np.array([[n[k][2] for k in (27,28,31,32)] if n else [0,0,0,0] for n in Nm]).mean(1)
inb=np.array([np.mean([0<=n[k][1]<=1.0 for k in (27,28,29,30,31,32)]) if n else 0 for n in Nm])
Wa=np.array([w if w is not None else [[np.nan]*3]*33 for w in Wd],dtype=float)
vel=np.nan_to_num(np.linalg.norm(np.diff(Wa,axis=0),axis=2).mean(1),nan=0); vel=np.append(vel,0)
L=int(round(win_s*fps)); best=None
for s in range(0,max(1,N-L+1),3):
    sc=det_[s:s+L].mean()*2+vis[s:s+L].mean()+inb[s:s+L].mean()+min(vel[s:s+L].mean()*40,1.0)
    if best is None or sc>best[0]: best=(sc,s)
s0=best[1]; s1=min(N,s0+L); print('window',s0,s1,'score',round(best[0],3))
seg=Wa[s0:s1].copy()
for j in range(33):
    for c in range(3):
        y=seg[:,j,c]; ok=~np.isnan(y)
        if ok.sum()>1: seg[:,j,c]=np.interp(np.arange(len(y)),np.where(ok)[0],y[ok])
k=np.exp(-0.5*(np.arange(-4,5)/1.6)**2); k/=k.sum()
sm=np.stack([np.stack([np.convolve(np.pad(seg[:,j,c],4,mode='edge'),k,mode='valid') for c in range(3)],1) for j in range(33)],1)
nm=[Nm[i] for i in range(s0,s1)]
json.dump({'src':src,'fps':fps,'size':[W,H],'start_frame':s0,'end_frame':s1,'start_s':round(s0/fps,3),'end_s':round(s1/fps,3),'detected_frac':float(det_[s0:s1].mean()),
           'feet_visibility':float(vis[s0:s1].mean()),'w':np.round(sm,4).tolist(),'n':nm},open(out,'w'))
# proof sheet: tracked skeleton drawn on 8 source frames (to check it tracks the dancer)
E=[(11,12),(11,13),(13,15),(12,14),(14,16),(11,23),(12,24),(23,24),(23,25),(25,27),(24,26),(26,28),(27,29),(29,31),(27,31),(28,30),(30,32),(28,32)]
cap=cv2.VideoCapture(src); tiles=[]; picks=set(np.linspace(s0,s1-1,8).astype(int).tolist()); i=0
while True:
    ok,fr=cap.read()
    if not ok: break
    if i in picks and Nm[i]:
        n=Nm[i]
        for a,b in E: cv2.line(fr,(int(n[a][0]*W),int(n[a][1]*H)),(int(n[b][0]*W),int(n[b][1]*H)),(80,230,255),3)
        for p in n: cv2.circle(fr,(int(p[0]*W),int(p[1]*H)),5,(255,255,255),-1)
        tiles.append(cv2.resize(fr,(270,int(270*H/W))))
    i+=1
if tiles: cv2.imwrite(out.replace('.json','-sheet.jpg'),np.vstack([np.hstack(tiles[:4]),np.hstack(tiles[4:8])]) if len(tiles)==8 else np.hstack(tiles))
