
import cv2, json, sys, os, numpy as np, urllib.request, mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
D,OUT=sys.argv[1],sys.argv[2]; os.makedirs(OUT,exist_ok=True)
HINT={'hand_on_hip_6.jpg':'left','contrapposto_2.jpg':'left','side_saddle_3.jpg':'middle'}
urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task','/tmp/pl.task')
det=vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(base_options=BaseOptions(model_asset_path='/tmp/pl.task'),running_mode=vision.RunningMode.IMAGE,num_poses=3,min_pose_detection_confidence=0.3))
meta=json.load(open(D+'/refs.json')); res={}
E=[(11,12),(11,13),(13,15),(12,14),(14,16),(11,23),(12,24),(23,24),(23,25),(25,27),(24,26),(26,28),(27,29),(29,31),(27,31),(28,30),(30,32),(28,32),(0,7),(0,8)]
for m in meta:
    fn=m['file']; img=cv2.imread(D+'/'+fn); H,W=img.shape[:2]
    r=det.detect(mp.Image(image_format=mp.ImageFormat.SRGB,data=cv2.cvtColor(img,cv2.COLOR_BGR2RGB)))
    if not r.pose_landmarks: print('none',fn); continue
    cx=[np.mean([l.x for l in p]) for p in r.pose_landmarks]; order=np.argsort(cx); h=HINT.get(fn)
    i=int(order[0]) if h=='left' else (int(order[-1]) if h=='right' else (int(order[len(order)//2]) if h=='middle' else int(np.argmax([np.ptp([l.y for l in p]) for p in r.pose_landmarks]))))
    w=[[l.x,l.y,l.z] for l in r.pose_world_landmarks[i]]; n=[[l.x,l.y,l.visibility] for l in r.pose_landmarks[i]]
    res[fn]={'pose':m['pose'],'w':w,'n':n,'people':len(r.pose_landmarks)}
    for a,b in E: cv2.line(img,(int(n[a][0]*W),int(n[a][1]*H)),(int(n[b][0]*W),int(n[b][1]*H)),(80,230,255),max(2,W//200))
    for p in n: cv2.circle(img,(int(p[0]*W),int(p[1]*H)),max(3,W//150),(255,255,255),-1)
    s=480/max(H,W); cv2.imwrite(OUT+'/sk_'+fn,cv2.resize(img,(int(W*s),int(H*s))))
    print(fn,'people',len(r.pose_landmarks),'picked',i)
json.dump(res,open(OUT+'/refs-landmarks.json','w'))
