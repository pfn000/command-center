
# dance4 FACE TRACK (runs on Actions): MediaPipe Face Landmarker on the source clip, the same 300 frames the body mocap covers.
# Per frame: facial transformation matrix (head pose), 52 ARKit-style blendshapes, and the contour landmarks (jaw/eyes/brows/lips) for the overlay.
import sys, json, urllib.request, numpy as np, cv2, mediapipe as mp
from mediapipe.tasks import python as mpt
from mediapipe.tasks.python import vision
VID, SRCJ, OUTJ = sys.argv[1:4]
S = json.load(open(SRCJ)); N = len(S['w']); t0 = S['t0']; FPS = S['fps']
MODEL = '/tmp/face_landmarker.task'
urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task', MODEL)
OVAL=[10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109,10]
EYE_L=[263,249,390,373,374,380,381,382,362,398,384,385,386,387,388,466,263]; EYE_R=[33,7,163,144,145,153,154,155,133,173,157,158,159,160,161,246,33]
BROW_L=[276,283,282,295,285,300,293,334,296,336]; BROW_R=[46,53,52,65,55,70,63,105,66,107]
LIPS_O=[61,146,91,181,84,17,314,405,321,375,291,409,270,269,267,0,37,39,40,185,61]; LIPS_I=[78,95,88,178,87,14,317,402,318,324,308,415,310,311,312,13,82,81,80,191,78]
CONT={'oval':OVAL,'eyeL':EYE_L,'eyeR':EYE_R,'browL':BROW_L,'browR':BROW_R,'lipsO':LIPS_O,'lipsI':LIPS_I}
IDX=sorted({i for v in CONT.values() for i in v})
opts = vision.FaceLandmarkerOptions(base_options=mpt.BaseOptions(model_asset_path=MODEL), running_mode=vision.RunningMode.VIDEO, num_faces=1,
    output_face_blendshapes=True, output_facial_transformation_matrixes=True, min_face_detection_confidence=0.3, min_face_presence_confidence=0.3, min_tracking_confidence=0.3)
det = vision.FaceLandmarker.create_from_options(opts)
cap = cv2.VideoCapture(VID); vf = cap.get(cv2.CAP_PROP_FPS) or 30.0; print('video fps', vf, 'frames', cap.get(cv2.CAP_PROP_FRAME_COUNT))
want = [int(round((t0 + k / FPS) * vf)) for k in range(N)]; frames = []; fi = -1; k = 0; ts = 0
def ear(P, a): # eye openness: lid gap / eye width
    return float(np.linalg.norm(P[a[12]] - P[a[4]]) / max(1e-6, np.linalg.norm(P[a[0]] - P[a[8]])))
# the dancer's face is ~100 px in a 720x1280 frame, too small for the face detector: crop a box around her head from the body track
# (nose + ears, 5-frame mean so the crop doesn't jitter), upscale it to 512 px, and map the landmarks back to full-frame coordinates.
B2 = np.array(S['body2d_px'], float); HC = (B2[:, 0] + B2[:, 7] + B2[:, 8]) / 3; EW = np.linalg.norm(B2[:, 7] - B2[:, 8], axis=1)
k5 = np.ones(5) / 5; sm = lambda a: np.convolve(np.pad(a, 2, mode='edge'), k5, 'valid')
HC = np.stack([sm(HC[:, 0]), sm(HC[:, 1])], 1); SIDE = np.clip(sm(EW) * 3.4, 140, 600)
while k < N:
    ok, img = cap.read(); fi += 1
    if not ok: break
    if fi < want[k]: continue
    while k < N and want[k] <= fi:
        Hh, Ww = img.shape[:2]; sx_ = Ww / float(S.get('res_w', Ww)); s = float(SIDE[k]); cx, cy = HC[k]
        x0 = int(round(cx - s / 2)); y0 = int(round(cy - s * 0.55)); s_ = int(round(s))
        pad = cv2.copyMakeBorder(img, s_, s_, s_, s_, cv2.BORDER_CONSTANT, value=0); crop = pad[y0 + s_:y0 + 2 * s_, x0 + s_:x0 + 2 * s_]
        crop = cv2.resize(crop, (512, 512), interpolation=cv2.INTER_CUBIC)
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB); ts += 33
        r = det.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)
        e = {'M': None, 'bs': None, 'lm': None, 'crop': [x0, y0, s_]}
        if r.face_landmarks:
            P = np.array([[p.x, p.y, p.z] for p in r.face_landmarks[0]]); Pf = P.copy(); Pf[:, 0] = (x0 + P[:, 0] * s_) / Ww; Pf[:, 1] = (y0 + P[:, 1] * s_) / Hh
            e['lm'] = {n: [[round(float(Pf[i, 0]), 5), round(float(Pf[i, 1]), 5)] for i in v] for n, v in CONT.items()}
            e['ear'] = [ear(P, EYE_L), ear(P, EYE_R)]
            if r.face_blendshapes: e['bs'] = {c.category_name: round(float(c.score), 4) for c in r.face_blendshapes[0]}
            if r.facial_transformation_matrixes: e['M'] = np.array(r.facial_transformation_matrixes[0]).round(5).tolist()
        frames.append(e); k += 1
okf = [e for e in frames if e['bs']]
bm = None
if len(okf) > 20:
    eL = np.array([e['ear'][0] for e in okf]); eR = np.array([e['ear'][1] for e in okf]); bL = np.array([e['bs']['eyeBlinkLeft'] for e in okf]); bR = np.array([e['bs']['eyeBlinkRight'] for e in okf])
    c = lambda a, b: float(np.corrcoef(a, b)[0, 1]) if np.std(a) > 1e-6 and np.std(b) > 1e-6 else 0.0
    straight = -c(eL, bL) - c(eR, bR); swapped = -c(eL, bR) - c(eR, bL)
    bm = 'swapped' if swapped > straight else 'straight'; print('blink map (subject-left eye EAR vs eyeBlinkLeft)', round(straight, 3), 'swapped', round(swapped, 3), '->', bm)
json.dump({'frames': frames, 'n': len(frames), 'with_face': len(okf), 'video_fps': vf, 'blink_map': bm, 'contours': list(CONT)}, open(OUTJ, 'w'))
print('face frames', len(frames), 'with face', len(okf))
